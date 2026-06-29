# Legacy ASD Pilot Backend API Contract

> **Status:** This document describes the legacy `src/therapist_backend` API.
> The canonical lingualens API is `apps/api`, exposes `/api/v1`, and
> publishes its current OpenAPI contract at `/docs` when running. See
> `apps/api/README.md` and `docs/PROJECT_SOURCE_OF_TRUTH.md`.

This document describes the API contract for the therapist pilot backend, configured in `src/therapist_backend/app.py`.

> [!IMPORTANT]
> **Clinical Safety Disclaimer**: All outputs of this API are intended for **clinical decision-support and progress tracking only**. The system **never diagnoses ASD** and does not replace qualified clinical judgment. **Thai validation is not yet completed**, and model predictions have not been validated for Thai children.

## Key Safety Policies Enforced
1. **Consent-Gated Upload Intent**: Guardian consent must be granted (`audio_permission = true`) before creating secure audio upload intents or starting ASR jobs.
2. **Transcript Sign-off Gate**: A formal therapist transcript sign-off is required before speech-language features can be calculated or AI concern-level explanations are generated.
3. **Audited Actions**: Critical actions (login, consent logging, upload intents, sign-offs, and note-taking) generate immutable audit logs.
4. **Admin-Only Audit Access**: Only users with the `admin` role are permitted to view audit logs.
5. **No Raw Media Persistence**: Raw voice audio files are never persisted directly by the app backend; we only process short-lived signed upload/download URLs.

---

## 1. Authentication
Endpoints for credential validation and active session verification.

### Log In
* **Route**: `POST /api/auth/session`
* **Request Payload**:
  ```json
  {
    "email": "therapist@example.test",
    "password": "demo-password"
  }
  ```
* **Response Payload (200 OK)**:
  ```json
  {
    "user": {
      "user_id": "user_therapist_001",
      "name": "Jane Therapist",
      "email": "therapist@example.test",
      "role": "therapist",
      "organization": "ASD Clinic A"
    },
    "session_token": "user_therapist_001",
    "token_type": "mock-user-id",
    "safety": "This system is a clinical decision-support prototype. It does not diagnose ASD..."
  }
  ```

### Active Session Verification
* **Route**: `GET /api/me`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "user": {
      "user_id": "user_therapist_001",
      "name": "Jane Therapist",
      "email": "therapist@example.test",
      "role": "therapist"
    },
    "thai_safety_sentence": "ตอนนี้ระบบเป็น research prototype และ demo เพื่อการศึกษา ไม่ใช่เครื่องมือวินิจฉัยทางการแพทย์"
  }
  ```

---

## 2. Child Case Caseload
Operations for managing anonymized child case records.

### List Caseload
* **Route**: `GET /api/cases`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  [
    {
      "case_id": "CASE-001",
      "owner_user_id": "user_therapist_001",
      "anonymized_child_code": "CHI-A01",
      "age_months": 48,
      "sex": "male",
      "primary_concerns": "Speech delay, poor social interaction",
      "consent_status": "granted",
      "anonymization_status": "anonymized"
    }
  ]
  ```

### Create Anonymized Case
* **Route**: `POST /api/cases`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "anonymized_child_code": "CHI-A02",
    "age_months": 36,
    "sex": "female",
    "primary_concerns": "Does not respond to name, uses simple sounds only",
    "consent_status": "pending"
  }
  ```
  *(Note: `anonymized_child_code` must match `^[a-zA-Z0-9\-]+$` to prevent spaces or real child names.)*
* **Response Payload (201 Created)**:
  ```json
  {
    "case_id": "CASE-002",
    "owner_user_id": "user_therapist_001",
    "anonymized_child_code": "CHI-A02",
    "age_months": 36,
    "sex": "female",
    "primary_concerns": "Does not respond to name, uses simple sounds only",
    "consent_status": "pending",
    "anonymization_status": "anonymized",
    "created_at": "2026-05-31T12:00:00Z"
  }
  ```

### Update Case Details
* **Route**: `PATCH /api/cases/{case_id}`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "notes": "Follow-up schedule confirmed with parents"
  }
  ```
* **Response Payload (200 OK)**:
  ```json
  {
    "case_id": "CASE-001",
    "notes": "Follow-up schedule confirmed with parents",
    "updated_at": "2026-05-31T12:05:00Z"
  }
  ```

---

## 3. Consent Tracking
Logging guardian consent permissions before executing audio uploads or processing.

### Record Consent
* **Route**: `POST /api/cases/{case_id}/consent`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "audio_permission": true,
    "transcript_permission": true,
    "consent_type": "clinical_audio_processing",
    "guardian_status": "guardian",
    "notes": "Consent signed in-person during intake interview"
  }
  ```
* **Response Payload (201 Created)**:
  ```json
  {
    "consent_id": "CONSENT-001",
    "case_id": "CASE-001",
    "owner_user_id": "user_therapist_001",
    "recorded_by_user_id": "user_therapist_001",
    "audio_permission": true,
    "transcript_permission": true,
    "created_at": "2026-05-31T12:10:00Z"
  }
  ```

---

## 4. Sessions
Add evaluation or therapy session logs to a case timeline.

### List Sessions
* **Route**: `GET /api/sessions`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  [
    {
      "session_id": "SESSION-001",
      "case_id": "CASE-001",
      "owner_user_id": "user_therapist_001",
      "session_date": "2026-05-28",
      "session_type": "therapy_session",
      "processing_status": "transcript_ready",
      "feature_extraction_status": "completed"
    }
  ]
  ```

### Create Session
* **Route**: `POST /api/sessions`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "case_id": "CASE-001",
    "session_date": "2026-05-31",
    "session_type": "free_play",
    "notes": "Observe child interactions with block stacking toys"
  }
  ```
* **Response Payload (201 Created)**:
  ```json
  {
    "session_id": "SESSION-002",
    "case_id": "CASE-001",
    "owner_user_id": "user_therapist_001",
    "session_date": "2026-05-31",
    "session_type": "free_play",
    "notes": "Observe child interactions with block stacking toys",
    "created_at": "2026-05-31T12:15:00Z"
  }
  ```

---

## 5. Secure Audio Upload Intent
Before uploading recording files, clients request signed URLs through an intent record.

### Create Upload Intent
* **Route**: `POST /api/sessions/{session_id}/audio/upload-intent`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "original_filename": "CHI-A01_session2.wav",
    "file_size": 15728640,
    "mime_type": "audio/wav",
    "checksum_sha256": "abcdef1234567890",
    "retention_days": 90
  }
  ```
* **Response Payload (201 Created)**:
  ```json
  {
    "audio_file": {
      "audio_file_id": "AUDIO-001",
      "stored_filename": "CASE-001_SESSION-002_AUDIO-001.wav",
      "file_size": 15728640,
      "storage_mode": "secure_private"
    },
    "file_object": {
      "file_object_id": "FILEOBJ-001",
      "audio_file_id": "AUDIO-001",
      "encryption_status": "required",
      "retention_delete_after": "2026-08-29T12:20:00Z"
    },
    "upload": {
      "method": "PUT",
      "url": "https://private-storage.local/upload/FILEOBJ-001",
      "signed_upload_url": "https://private-storage.local/upload/FILEOBJ-001?token=xyz",
      "expires_in_seconds": 900,
      "storage_provider": "supabase",
      "headers": {
        "content-type": "audio/wav",
        "x-amz-server-side-encryption": "AES256"
      }
    }
  }
  ```

---

## 6. Processing Jobs
Tracks background speech-to-text (ASR) transcription.

### Submit Audio Processing
* **Route**: `POST /api/sessions/{session_id}/process-audio`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (202 Accepted)**:
  ```json
  {
    "job_id": "JOB-0001",
    "session_id": "SESSION-002",
    "status": "queued",
    "progress": 0,
    "created_at": "2026-05-31T12:25:00Z"
  }
  ```

### Get Job Status
* **Route**: `GET /api/jobs/{job_id}`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "job_id": "JOB-0001",
    "session_id": "SESSION-002",
    "status": "processing",
    "stage": "transcribing",
    "progress": 45,
    "updated_at": "2026-05-31T12:26:00Z"
  }
  ```

### List Session Processing Jobs
* **Route**: `GET /api/sessions/{session_id}/processing-jobs`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "jobs": [
      {
        "job_id": "JOB-0001",
        "session_id": "SESSION-002",
        "engine": "local_whisper",
        "operation": "audio_to_chat",
        "operation_config": {},
        "status": "completed",
        "artifact_ids": ["ARTIFACT-0001"]
      }
    ]
  }
  ```

---

## 7. Transcript Review & Sign-off
Routes for inline reviewing and signing off on CHAT transcripts.

### Get Transcript
* **Route**: `GET /api/sessions/{session_id}/transcript`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "transcript_id": "TRANSCRIPT-001",
    "session_id": "SESSION-001",
    "transcript_text": "@UTF8\n@Begin\n*CHI:\tball .\n*MOT:\tyes .\n@End\n",
    "review_status": "awaiting_review",
    "qa_status": "pass",
    "qa_score": 98
  }
  ```

### Get Transcript QA
* **Route**: `GET /api/sessions/{session_id}/qa`
* **Headers**: `X-User-Id: user_therapist_001`
* **Behavior**:
  * Re-runs backend Transcript QA against the current CHAT transcript and returns readiness flags.
  * Does not persist a QA record and does not write an audit event.
  * Returns `404 Not Found` when the session has no transcript, is unknown, or is not visible to the user.
* **Response Payload (200 OK)**:
  ```json
  {
    "transcript_id": "TRANSCRIPT-001",
    "session_id": "SESSION-001",
    "status": "needs_review",
    "quality_score": 90,
    "summary": {
      "line_count": 42,
      "utterance_count": 30,
      "child_utterance_count": 14,
      "child_token_count": 38,
      "marker_counts": {
        "xxx": 0,
        "yyy": 0,
        "www": 0,
        "zero_vocalization": 1,
        "laugh": 0,
        "gasp": 0,
        "repetition": 0
      },
      "average_confidence": null
    },
    "readiness": {
      "feature_extraction_ready": true,
      "reference_comparison_ready": true,
      "clan_metric_ready": false,
      "blockers": {
        "feature_extraction": [],
        "reference_comparison": []
      },
      "warnings": {
        "clan_metric": ["SHORT_CHILD_SAMPLE_FOR_KIDEVAL"]
      }
    },
    "issues": [
      {
        "severity": "warning",
        "code": "SHORT_CHILD_SAMPLE_FOR_KIDEVAL",
        "message": "Child language sample has fewer than 50 child utterances.",
        "line": null,
        "suggestion": "Do not treat KIDEVAL-style comparisons as ready until the sample reaches the expected minimum."
      }
    ]
  }
  ```

### Edit Transcript Line
* **Route**: `PATCH /api/transcripts/{transcript_id}/lines/{line_id}`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "speaker_code": "CHI",
    "text": "want ball",
    "reviewed": true,
    "expected_version": 1
  }
  ```
  *(Note: expected_version prevents overwrite conflicts.)*
* **Response Payload (200 OK)**:
  ```json
  {
    "line_id": "LINE-001",
    "speaker_code": "CHI",
    "utterance_text": "want ball",
    "reviewed": true,
    "version": 2,
    "updated_at": "2026-05-31T12:30:00Z"
  }
  ```

### Submit Transcript Sign-off (Clinical Gate)
* **Route**: `POST /api/sessions/{session_id}/transcript/signoff`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "notes": "Reviewed and checked CHI speaker tiers against raw video audio."
  }
  ```
* **Response Payload (200 OK)**:
  ```json
  {
    "signoff_id": "SIGNOFF-001",
    "target_type": "transcript",
    "target_id": "TRANSCRIPT-001",
    "session_id": "SESSION-001",
    "signed_by_user_id": "user_therapist_001",
    "notes": "Reviewed and checked CHI speaker tiers against raw video audio.",
    "created_at": "2026-05-31T12:35:00Z"
  }
  ```

### Export Reviewed CHAT
* **Route**: `GET /api/sessions/{session_id}/transcript/export.cha`
* **Headers**: `X-User-Id: user_therapist_001`
* **Query Parameters**:
  * `allow_preliminary=false` by default. When false, export requires transcript sign-off and reviewed transcript lines.
* **Response (200 OK)**:
  * Content type: `text/plain; charset=utf-8`
  * Content disposition filename: `{session_id}_reviewed.cha`
  * Body is a UTF-8 CHAT transcript containing `@Begin`, `@Languages`, `@Participants`, `@ID`, `@Media`, speaker tiers, media bullets, and `@End`.
* **Error (409 Conflict)**:
  ```json
  {
    "detail": "Transcript review signoff is required before reviewed CHAT export."
  }
  ```

### List Clinical Speech Artifacts
* **Route**: `GET /api/sessions/{session_id}/clinical-speech-artifacts`
* **Headers**: `X-User-Id: user_therapist_001`
* **Behavior**:
  * Returns artifact metadata and a short content preview, not private storage keys.
  * Artifacts can be `current`, `preliminary`, `stale`, `failed`, or `superseded`.
  * Reviewed transcript lines remain the source of truth; artifacts are generated provenance.
* **Response Payload (200 OK)**:
  ```json
  {
    "artifacts": [
      {
        "artifact_id": "ARTIFACT-0001",
        "session_id": "SESSION-001",
        "artifact_type": "reviewed_chat",
        "freshness": "current",
        "transcript_id": "TRANSCRIPT-001",
        "source_revision": "sha256...",
        "content_type": "text/x-chat; charset=utf-8",
        "content_preview": "@UTF8\n@Begin\n..."
      }
    ]
  }
  ```

---

## 8. Speech Feature Extraction
Operations to calculate Core 14-feature schema metrics once transcript review gates pass.

### Trigger Feature Extraction
* **Route**: `POST /api/sessions/{session_id}/features/extract`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "feature_id": "FEATURE-001",
    "session_id": "SESSION-001",
    "feature_schema_version": "14-feature-schema",
    "features": {
      "age_months": 48,
      "total_utterances": 60,
      "total_words": 100,
      "mlu": 1.5,
      "mluw": 1.6,
      "ttr": 0.35,
      "unintelligible_count": 2,
      "unintelligible_ratio": 0.033,
      "zero_vocalization_count": 1,
      "nonverbal_vocalization_count": 0,
      "question_ratio": 0.05,
      "echolalia_count": 2,
      "echolalia_ratio": 0.033,
      "pronoun_reversal_count": 0
    },
    "optional_indicators": {
      "restricted_interest_words": 0
    }
  }
  ```

### Review Feature Flag
* **Route**: `PATCH /api/features/{feature_id}/review-flags/{flag_key}`
* **Headers**: `X-User-Id: user_therapist_001`
* **Request Payload**:
  ```json
  {
    "disposition": "accepted",
    "note": "Pattern is relevant in context but not diagnostic."
  }
  ```
* **Allowed Dispositions**:
  * `needs_review`
  * `accepted`
  * `rejected`
  * `needs_context`
* **Response Payload (200 OK)**:
  ```json
  {
    "disposition_id": "FEATURE-DISP-001",
    "feature_id": "FEATURE-001",
    "flag_key": "possible_pronoun_reversal",
    "disposition": "accepted",
    "note": "Pattern is relevant in context but not diagnostic.",
    "source_revision": "sha256..."
  }
  ```

### List Feature Flag Reviews
* **Route**: `GET /api/features/{feature_id}/review-flags`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "dispositions": [
      {
        "flag_key": "possible_pronoun_reversal",
        "disposition": "accepted",
        "note": "Pattern is relevant in context but not diagnostic."
      }
    ]
  }
  ```

### Get AI Screening Output
* **Route**: `GET /api/sessions/{session_id}/ai-output`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "output_id": "AI-OUTPUT-001",
    "session_id": "SESSION-001",
    "case_id": "CASE-001",
    "owner_user_id": "user_therapist_001",
    "concern_level": "moderate_concern",
    "model_version": "screening-support-v1",
    "screening_support_score": 0.68,
    "confidence_interval": null,
    "explanation": "Decision-support only. Review transcript QA, session context, and therapist notes before interpreting this output. It is not a diagnosis.",
    "plain_language_explanation": "This output highlights speech-language patterns that may warrant closer clinical review. It is not a diagnosis.",
    "top_contributing_features": ["unintelligible_ratio", "echolalia_ratio", "ttr"],
    "evidence_items": [
      {
        "type": "feature",
        "feature_key": "unintelligible_ratio",
        "value": 0.033,
        "explanation": "Elevated ratio of unintelligible utterances."
      }
    ],
    "therapist_review_status": "awaiting_review",
    "created_at": "2026-05-05T09:40:00Z"
  }
  ```

### Reference Cohort Similarity
* **Route**: `POST /api/sessions/{session_id}/reference-cohort-similarity`
* **Headers**: `X-User-Id: user_therapist_001`
* **Purpose**: Generates a Reference Cohort Similarity output for therapist review. This endpoint compares transcript-derived language feature patterns with internal reference cohort labels. It does not diagnose ASD and must not be displayed as a diagnostic probability.
* **State Rules**:
  * `preliminary`: calculated from raw or unreviewed transcript-derived features for review prioritization only. It is not report-eligible.
  * `reviewed`: calculated after transcript review/sign-off using reviewed transcript lines. It may appear in reports only when `report_eligible` is `true`.
  * Similarity failure must not block transcript sign-off. Clients should show the unavailable state and continue transcript review.
* **Response Payload (200 OK)**:
  ```json
  {
    "output_kind": "reference_cohort_similarity",
    "inference_status": "reviewed",
    "reference_cohort_probabilities": {
      "ASD": 0.62,
      "TD": 0.18,
      "DD": 0.20
    },
    "most_similar_reference_cohort": "ASD",
    "similarity_probability": 0.62,
    "report_eligible": true,
    "safety_warnings": [],
    "top_contributing_features": ["mluw", "ttr", "echolalia_ratio"],
    "plain_language_explanation": "This transcript has feature patterns most similar to the ASD reference cohort. AI output is for clinical decision support only and must be reviewed by a qualified clinician."
  }
  ```

Preliminary output may support review prioritization, but it must not be exported as a reviewed clinical result or shown in report surfaces.

---

## 9. Reference Comparison
Descriptive comparison of extracted Core 14 features against matched English Reference Cohorts, with CLAN-Derived Metrics shown in a separate section when matched reference data is ready. This is clinical decision-support context only; it does not make clinical determinations and must not be treated as a scoring system.

### Get Session Reference Comparison
* **Route**: `GET /api/sessions/{session_id}/reference-comparison`
* **Headers**: `X-User-Id: user_therapist_001`
* **Requirements**:
  * Extracted features must already exist for the session.
  * The endpoint does not run feature extraction and does not persist a comparison record.
  * The therapist UI only loads this endpoint after transcript review is `reviewed`, feature extraction is `completed`, backend Transcript QA is available in API runtime, and `readiness.reference_comparison_ready` is true.
  * Mock/default frontend mode shows a status-only unavailable panel instead of generating mock percentiles or reference distributions.
* **Response Payload (200 OK)**:
  ```json
  {
    "status": "ok",
    "reference_term": "Reference Comparison",
    "age_band_12mo": "48-59",
    "task_type": "toyplay",
    "language": "eng",
    "warnings": ["low_n:48-59|toyplay|DD"],
    "cohorts": [
      {
        "group": "TD",
        "cohort_n": 31,
        "confidence_flag": "ok",
        "corpora": "Ambrose;Eigsti",
        "design_types": "cross;long",
        "feature_comparisons": [
          {
            "feature": "mlu",
            "value": 2.4,
            "percentile": 58.06,
            "position": "within_iqr",
            "q1": 1.8,
            "median": 2.3,
            "q3": 2.9,
            "min": 0.8,
            "max": 4.2
          }
        ],
        "clan_metric_comparisons": [
          {
            "metric": "kideval_mlu_utts",
            "value": null,
            "percentile": null,
            "position": "missing",
            "q1": 76.0,
            "median": 132.0,
            "q3": 188.0,
            "min": 51.0,
            "max": 415.0,
            "reference_n": 31,
            "metric_source": "clan_kideval"
          }
        ]
      }
    ]
  }
  ```
  `clan_metric_comparisons` is separate from Core 14 `feature_comparisons`. It is returned only for matched cohorts with enough reference rows, and only for CLAN metrics that have numeric reference values in that cohort. If the uploaded/session feature row does not yet contain `kideval_*` values, the CLAN metric `value`, `percentile`, and `position` remain missing while the descriptive reference distribution is still shown.
* **Error Semantics**:
  * `404 Not Found`: session does not exist or user cannot access it.
  * `400 Bad Request`: extracted features are missing.
  * `200 OK` with `"status": "insufficient_reference_data"`: no matched Reference Cohort is available for the session's age band and task type.

### Get Reference Readiness Index
* **Route**: `GET /api/reference/readiness`
* **Headers**: `X-User-Id: user_therapist_001`
* **Behavior**:
  * Returns metadata about the readiness, low-count caution, or unavailable status for Reference Cohort cells.
  * Does not calculate screen scores, diagnoses, or percentiles.
  * If the index is missing or stale, returns default/unavailable status metadata.
* **Response Payload (200 OK)**:
  ```json
  {
    "summary": {
      "ok": 28,
      "low_n": 20,
      "not_cohort_ready": 1
    },
    "cells": [
      {
        "language": "eng",
        "age_band_12mo": "36-47",
        "task_type": "toyplay",
        "group": "ASD",
        "cohort_n": 33,
        "coverage_status": "ok",
        "confidence_flag": "ok",
        "clan_metric_ready": true
      }
    ],
    "status": "ready",
    "generated_at": "2026-06-02T19:04:00Z",
    "source_files": [
      "data/reference/english_child_reference_coverage.csv",
      "data/reference/english_child_reference_cohorts.csv",
      "data/manifests/english_child_clan_qc_summary.csv"
    ]
  }
  ```

---

## 10. Progress Tracking & Reports
Longitudinal summaries and progress reporting.

### Get Longitudinal Progress
* **Route**: `GET /api/cases/{case_id}/progress`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "child": "CHI-A01",
    "n_sessions": 2,
    "metric_changes": {
      "mlu": {
        "first": 1.1,
        "last": 1.5,
        "delta": 0.4,
        "improved": true
      }
    }
  }
  ```

### Generate Case Brief / Progress Report
* **Route**: `POST /api/sessions/{session_id}/report`
* **Headers**: `X-User-Id: user_therapist_001`
* **Response Payload (200 OK)**:
  ```json
  {
    "report_id": "REPORT-001",
    "case_id": "CASE-001",
    "title": "Progress Report: CHI-A01",
    "content_markdown": "# Progress Report: CHI-A01\n\n- MLU improved from 1.1 to 1.5\n- Safety Warning: decision-support only...",
    "export_status": "completed",
    "created_at": "2026-05-31T12:40:00Z"
  }
  ```

---

## 11. Privacy Operations
Case export, consent withdrawal, and deletion review are tracked as privacy
operations. Deletion review records retention and legal-hold metadata and never
silently deletes audit/sign-off evidence.

### Create Case Privacy Request
* **Route**: `POST /api/v1/cases/{case_id}/privacy-requests`
* **Request Payload**:
  ```json
  {
    "operation_type": "deletion_review",
    "reason": "Guardian deletion request.",
    "retention_days": 90,
    "legal_hold": false
  }
  ```
* **Response Payload (200 OK)**:
  ```json
  {
    "privacy_operation_id": "priv_abc123",
    "case_id": "case_abc123",
    "operation_type": "deletion_review",
    "status": "requested",
    "retention_days": 90,
    "legal_hold": false,
    "deletion_review_required": true,
    "preserve_evidence": true,
    "eligible_for_deletion_at": "2026-09-22T12:00:00Z",
    "completed_at": null,
    "evidence_retained": {}
  }
  ```

### Complete Privacy Request
* **Route**: `PATCH /api/v1/privacy/requests/{privacy_operation_id}`
* **Admin only**
* **Request Payload**:
  ```json
  {
    "status": "completed",
    "admin_note": "Deletion review approved."
  }
  ```
* **Response Payload (200 OK)**:
  ```json
  {
    "privacy_operation_id": "priv_abc123",
    "organization_id": "pilot_org_001",
    "case_id": "case_abc123",
    "operation_type": "deletion_review",
    "status": "completed",
    "requester_role": "therapist",
    "retention_days": 90,
    "legal_hold": false,
    "deletion_review_required": true,
    "preserve_evidence": true,
    "eligible_for_deletion_at": "2026-09-22T12:00:00Z",
    "completed_at": "2026-09-22T12:30:00Z",
    "evidence_retained": {
      "audit_events": 12,
      "signed_reports": 1
    }
  }
  ```

Deletion review completion is rejected while `legal_hold` is true. Successful
completion records `completed_at` and retained evidence counts such as audit
events and signed reports. Org-admin queue/update responses are assignment-safe
summaries and do not echo free-text request reasons, requester identity, or
admin notes.

---

## 12. Audit Logs (Admin-Only)
Immutable log of clinician actions.

* **Route**: `GET /api/audit-logs`
* **Headers**: `X-User-Id: user_admin_001`
* **Response Payload (200 OK)**:
  ```json
  [
    {
      "audit_id": "AUDIT-001",
      "event_type": "login",
      "actor_user_id": "user_therapist_001",
      "target_type": "user",
      "target_id": "user_therapist_001",
      "message": "Mock login for therapist@example.test",
      "created_at": "2026-05-31T12:00:00Z"
    }
  ]
  ```
  *(Note: Request by a user with role `therapist` or `clinician` returns HTTP `403 Forbidden`.)*
