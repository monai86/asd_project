from __future__ import annotations

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ConsentWithdrawalResult, ReviewStatus
from app.services.storage_service import get_storage_adapter


CONSENT_WITHDRAWN_MESSAGE = "Case consent has been withdrawn; new uploads, processing, edits, and exports are blocked."


def ensure_case_consent_active(repo: MockRepository, case_id: str) -> None:
    case = repo.cases[case_id]
    if case.consent_status.lower() == "withdrawn":
        raise ValueError(CONSENT_WITHDRAWN_MESSAGE)


def ensure_session_consent_active(repo: MockRepository, session_id: str) -> None:
    ensure_case_consent_active(repo, repo.sessions[session_id].case_id)


def ensure_transcript_consent_active(repo: MockRepository, transcript_id: str) -> None:
    ensure_case_consent_active(repo, repo.transcripts[transcript_id].case_id)


def ensure_report_consent_active(repo: MockRepository, report_id: str) -> None:
    ensure_case_consent_active(repo, repo.reports[report_id].case_id)


def ensure_audio_file_consent_active(repo: MockRepository, audio_file_id: str) -> None:
    ensure_case_consent_active(repo, repo.audio_files[audio_file_id].case_id)


def withdraw_consent(repo: MockRepository, case_id: str, reason: str, redact_notes: bool = True) -> ConsentWithdrawalResult:
    original_case = repo.cases[case_id]
    original_collections = {
        name: dict(getattr(repo, name))
        for name in (
            "sessions", "therapy_goals", "audio_files", "transcripts",
            "ai_reviews", "reports", "jobs",
        )
    }
    case = repo.clone(original_case)
    affected = {"sessions": 0, "therapy_goals": 0, "audio_metadata": 0, "transcripts": 0, "features": 0, "ml_results": 0, "ai_reviews": 0, "reports": 0, "jobs": 0}
    case.consent_status = "withdrawn"
    if redact_notes:
        case.notes = ""
    sessions = {}
    for session in repo.sessions.values():
        if session.case_id != case_id:
            continue
        affected["sessions"] += 1
        session = repo.clone(session)
        session.status = ReviewStatus.withdrawn
        if session.notes and redact_notes:
            session.notes = ""
        sessions[session.session_id] = session
    therapy_goals = {}
    for goal in repo.therapy_goals.values():
        if goal.case_id == case_id:
            affected["therapy_goals"] += 1
            goal = repo.clone(goal)
            goal.status = "withdrawn"
            goal.retained = False
            if redact_notes:
                goal.notes = ""
            therapy_goals[goal.goal_id] = goal
    transcripts = {}
    for transcript in repo.transcripts.values():
        if transcript.case_id == case_id:
            affected["transcripts"] += 1
            transcript = repo.clone(transcript)
            transcript.raw_text = ""
            transcript.utterances = []
            transcript.review_status = ReviewStatus.withdrawn
            transcripts[transcript.transcript_id] = transcript
    audio_files = {}
    for audio_file in repo.audio_files.values():
        if audio_file.case_id == case_id:
            affected["audio_metadata"] += 1
            audio_file = repo.clone(audio_file)
            deletion = get_storage_adapter().delete_object(audio_file.object_key)
            audio_file.storage_delete_status = deletion.status
            audio_file.object_key = None
            audio_file.upload_status = "withdrawn"
            audio_file.retained = False
            audio_files[audio_file.audio_file_id] = audio_file
    case_session_ids = {session.session_id for session in repo.sessions.values() if session.case_id == case_id}
    feature_ids_to_delete = set()
    for feature_id, feature_set in list(repo.features.items()):
        if feature_set.session_id in case_session_ids:
            affected["features"] += 1
            feature_ids_to_delete.add(feature_id)
            if feature_set.session_id in sessions:
                sessions[feature_set.session_id].feature_set_id = None
    ai_reviews = {}
    for review_id, review in list(repo.ai_reviews.items()):
        if review.session_id in {s.session_id for s in repo.sessions.values() if s.case_id == case_id}:
            affected["ai_reviews"] += 1
            review = repo.clone(review)
            review.summary = "Consent withdrawn. AI-assisted review content unlinked from clinical workflow."
            review.key_findings = []
            review.concerns = []
            review.strengths = []
            review.limitations = ["Consent withdrawn; prior AI-assisted review support is no longer retained for workflow use."]
            review.recommended_review_actions = []
            review.therapist_review_status = ReviewStatus.withdrawn
            review.rejected_reason = "Consent withdrawn."
            ai_reviews[review_id] = review
    ml_result_ids_to_delete = set()
    for result_id, result in list(repo.ml_results.items()):
        if result.session_id in case_session_ids:
            affected["ml_results"] += 1
            ml_result_ids_to_delete.add(result_id)
            if result.session_id in sessions:
                sessions[result.session_id].ml_result_id = None
    reports = {}
    for report in repo.reports.values():
        if report.case_id == case_id:
            affected["reports"] += 1
            report = repo.clone(report)
            report.status = ReviewStatus.withdrawn
            report.markdown = "Consent withdrawn. Report content unlinked from clinical workflow."
            report.html = "<p>Consent withdrawn. Report content unlinked from clinical workflow.</p>"
            reports[report.report_id] = report
    jobs = {}
    for job in repo.jobs.values():
        if job.session_id in case_session_ids:
            affected["jobs"] += 1
            job = repo.clone(job)
            job.details["consent_withdrawn"] = True
            job.details["storage_unlinked"] = True
            jobs[job.job_id] = job
    repo.withdraw_case_consent(
        case=case,
        sessions=sessions,
        therapy_goals=therapy_goals,
        audio_files=audio_files,
        transcripts=transcripts,
        feature_ids_to_delete=feature_ids_to_delete,
        ml_result_ids_to_delete=ml_result_ids_to_delete,
        ai_reviews=ai_reviews,
        reports=reports,
        jobs=jobs,
        actor_id="system",
    )
    _copy_model_state(original_case, case)
    for name, updates in (
        ("sessions", sessions),
        ("therapy_goals", therapy_goals),
        ("audio_files", audio_files),
        ("transcripts", transcripts),
        ("ai_reviews", ai_reviews),
        ("reports", reports),
        ("jobs", jobs),
    ):
        originals = original_collections[name]
        for item_id, updated in updates.items():
            if item_id in originals:
                _copy_model_state(originals[item_id], updated)
    return ConsentWithdrawalResult(
        case_id=case_id,
        affected_records=affected,
        audit_message="Consent withdrawal applied across case-linked records.",
    )


def _copy_model_state(target, source) -> None:
    for field_name in type(source).model_fields:
        setattr(target, field_name, getattr(source, field_name))
