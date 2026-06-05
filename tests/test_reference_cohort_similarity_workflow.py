from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_workflow.models import AIScreeningOutput  # noqa: E402
from src.clinical_workflow import MockClinicalRepository  # noqa: E402


def test_ai_screening_output_can_represent_reference_cohort_similarity():
    output = AIScreeningOutput(
        output_id="AI-OUTPUT-REF-001",
        session_id="SESSION-001",
        case_id="CASE-001",
        owner_user_id="user_therapist_001",
        concern_level="review_support",
        output_kind="reference_cohort_similarity",
        inference_status="reviewed",
        reference_cohort_probabilities={"ASD": 0.62, "TD": 0.18, "DD": 0.20},
        most_similar_reference_cohort="ASD",
        similarity_probability=0.62,
        report_eligible=True,
        safety_warnings=[],
    )

    payload = output.to_dict()

    assert payload["output_kind"] == "reference_cohort_similarity"
    assert payload["inference_status"] == "reviewed"
    assert payload["most_similar_reference_cohort"] == "ASD"
    assert payload["similarity_probability"] == 0.62
    assert payload["report_eligible"] is True


def test_repository_generates_preliminary_reference_cohort_similarity():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    output = repo.generate_reference_cohort_similarity_for_session(
        "SESSION-001",
        therapist,
        inference_status="preliminary",
    )

    assert output.output_kind == "reference_cohort_similarity"
    assert output.inference_status == "preliminary"
    assert output.report_eligible is False
    assert output.reference_cohort_probabilities
    assert output.most_similar_reference_cohort in output.reference_cohort_probabilities
    assert any(run.session_id == "SESSION-001" for run in repo.model_runs.values())
    assert repo.sessions["SESSION-001"].ai_analysis_status == "completed"


def test_transcript_signoff_runs_reviewed_similarity_refresh_without_auto_report():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    signed = repo.signoff_transcript_for_session(
        "SESSION-001",
        therapist,
        "Reviewed for similarity refresh.",
    )

    outputs = [
        output for output in repo.ai_screening_outputs.values()
        if output.session_id == "SESSION-001"
        and output.output_kind == "reference_cohort_similarity"
        and output.inference_status == "reviewed"
    ]

    assert signed.target_type == "transcript"
    assert outputs
    assert outputs[-1].report_eligible is True
    assert repo.sessions["SESSION-001"].report_status == "pending"


def test_transcript_signoff_does_not_block_when_reviewed_similarity_refresh_fails():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    def fail_similarity_refresh(*_args, **_kwargs):
        raise RuntimeError("model artifact missing")

    repo.generate_reference_cohort_similarity_for_session = fail_similarity_refresh

    signed = repo.signoff_transcript_for_session("SESSION-001", therapist)

    assert signed.target_type == "transcript"
    assert repo.sessions["SESSION-001"].therapist_review_status == "reviewed"
    assert repo.sessions["SESSION-001"].ai_analysis_status == "failed"
    assert repo.sessions["SESSION-001"].report_status == "pending"
    assert any(
        audit.event_type == "reference_cohort_similarity_unavailable"
        for audit in repo.audit_logs
    )


def test_repository_returns_only_latest_reviewed_report_eligible_similarity():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    preliminary = repo.generate_reference_cohort_similarity_for_session(
        "SESSION-001",
        therapist,
        inference_status="preliminary",
    )
    reviewed = repo.signoff_transcript_for_session("SESSION-001", therapist, "Reviewed.")
    output = repo.get_report_eligible_similarity_for_session("SESSION-001", therapist)

    assert preliminary.report_eligible is False
    assert reviewed.target_type == "transcript"
    assert output is not None
    assert output.inference_status == "reviewed"
    assert output.report_eligible is True


def test_progress_report_excludes_preliminary_reference_cohort_similarity():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    preliminary = repo.generate_reference_cohort_similarity_for_session(
        "SESSION-001",
        therapist,
        inference_status="preliminary",
    )
    repo.ai_screening_outputs[preliminary.output_id].plain_language_explanation = "PRELIMINARY_REFERENCE_TEXT"
    repo.ai_screening_outputs[preliminary.output_id].explanation = "PRELIMINARY_REFERENCE_TEXT"

    report = repo.generate_progress_report_for_case("CASE-001", therapist)

    assert "PRELIMINARY_REFERENCE_TEXT" not in report.content_markdown
