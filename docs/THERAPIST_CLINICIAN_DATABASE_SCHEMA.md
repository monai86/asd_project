# Therapist Clinician Database Schema

This document describes database-ready tables for the therapist-clinician app.
The current app remains a clinical decision-support prototype with mock/demo
data by default. Do not store patient-identifiable data in this phase.

SQL migration drafts live in:

- `docs/sql/001_initial_clinical_schema.sql`
- `docs/sql/002_indexes_rls.sql`

## Access Rule

All query paths must filter records by `owner_user_id` unless the current user
has the `admin` role. Therapist and clinician users can access only their own
cases and sessions by default. Admin users may access all demo cases and audit
logs.

## Tables

### users

Primary key: `user_id`

Fields: `user_id`, `email`, `name`, `role`, `organization`, `created_at`,
`updated_at`, `last_login`

Notes: `role` is one of `therapist`, `clinician`, or `admin`.

### child_cases

Primary key: `case_id`

Foreign keys: `owner_user_id` references `users.user_id`

Fields: `case_id`, `owner_user_id`, `anonymized_child_code`, `display_label`,
`age_months`, `sex`, `primary_concerns`, `external_clinical_status`,
`consent_status`, `anonymization_status`, `notes`, `created_at`, `updated_at`

### sessions

Primary key: `session_id`

Foreign keys: `case_id` references `child_cases.case_id`, `owner_user_id`
references `users.user_id`, optional `audio_file_id` references
`audio_files.audio_file_id`, optional `transcript_id` references
`transcripts.transcript_id`

Fields: `session_id`, `case_id`, `owner_user_id`, `session_date`,
`session_type`, `audio_file_id`, `transcript_id`, `processing_status`,
`feature_extraction_status`, `ai_analysis_status`,
`therapist_review_status`, `report_status`, `notes`, `created_at`,
`updated_at`

### transcripts

Primary key: `transcript_id`

Foreign keys: `session_id` references `sessions.session_id`, `case_id`
references `child_cases.case_id`, `owner_user_id` references `users.user_id`

Fields: `transcript_id`, `session_id`, `case_id`, `owner_user_id`,
`original_filename`, `transcript_format`, `transcript_text`,
`chat_metadata`, `review_status`, `qa_status`, `qa_score`, `qa_issues`,
`reviewer_notes`, `created_at`, `updated_at`

### transcript_lines

Primary key: `line_id`

Foreign keys: `transcript_id` references `transcripts.transcript_id`,
`session_id` references `sessions.session_id`, `case_id` references
`child_cases.case_id`, `owner_user_id` and `updated_by_user_id` reference
`users.user_id`

Fields: `line_id`, `transcript_id`, `session_id`, `case_id`,
`owner_user_id`, `line_number`, `speaker_code`, `utterance_text`,
`start_time`, `end_time`, `confidence`, `flags`, `review_status`,
`reviewed`, `interpretation_note`, `version`, `updated_at`,
`updated_by_user_id`

Notes: therapist edits should update one transcript line with
`expected_version`. A mismatch returns a conflict instead of overwriting another
reviewer's edit. Any accepted line edit makes derived feature and AI support
outputs stale until extraction is rerun from the reviewed transcript.

### audio_files

Primary key: `audio_file_id`

Foreign keys: `session_id` references `sessions.session_id`, `case_id`
references `child_cases.case_id`, `owner_user_id` references `users.user_id`

Fields: `audio_file_id`, `session_id`, `case_id`, `owner_user_id`,
`original_filename`, `stored_filename`, `file_type`, `file_size`,
`duration_seconds`, `upload_time`, `processing_status`, `storage_mode`,
`file_object_id`, `created_at`, `updated_at`

Notes: `storage_mode` is `metadata_only` for demos or `secure_private` when
the backend has created a private object-store record. Frontend clients must
not receive permanent storage paths.

### consent_records

Primary key: `consent_id`

Foreign keys: `case_id` references `child_cases.case_id`, `owner_user_id`
and `recorded_by_user_id` reference `users.user_id`

Fields: `consent_id`, `case_id`, `owner_user_id`, `recorded_by_user_id`,
`consent_type`, `guardian_status`, `audio_permission`,
`transcript_permission`, `notes`, `expires_at`, `withdrawn_at`, `created_at`

Notes: secure audio upload and backend audio processing require an active,
non-withdrawn record with `audio_permission = true`.

### file_objects

Primary key: `file_object_id`

Foreign keys: `audio_file_id` references `audio_files.audio_file_id`,
`session_id`, `case_id`, and `owner_user_id`

Fields: `file_object_id`, `audio_file_id`, `case_id`, `session_id`,
`owner_user_id`, `storage_key`, `checksum_sha256`, `mime_type`,
`encryption_status`, `retention_delete_after`, `deleted_at`, `created_at`

Notes: `storage_key` is backend-only. Browser clients receive short-lived
signed upload/download URLs, never the permanent private key.

Upload-intent API responses must redact `storage_key` from the returned
`file_object` payload. The backend may keep the key internally for storage
operations, but the browser should only receive a signed URL, expiry, provider
label, encryption status, retention metadata, and the public file-object ID.

### processing_jobs

Primary key: `job_id`

Foreign keys: `session_id`, `case_id`, `owner_user_id`, optional
`audio_file_id`

Fields: `job_id`, `session_id`, `case_id`, `owner_user_id`,
`audio_file_id`, `job_type`, `status`, `stage`, `progress`, `error_code`,
`error_message`, `result_refs`, `started_at`, `finished_at`, `created_at`,
`updated_at`

Notes: statuses are `queued`, `processing`, `completed`, or `failed`. Stage is
the detailed pipeline step and should not be treated as final clinical review.

### extracted_features

Primary key: `feature_id`

Foreign keys: `session_id` references `sessions.session_id`, `case_id`
references `child_cases.case_id`, `owner_user_id` references `users.user_id`

Fields: `feature_id`, `session_id`, `case_id`, `owner_user_id`,
`feature_schema_version`, `features`, `core_features`,
`optional_indicators`, `extraction_status`, `review_status`, `created_at`,
`updated_at`

Notes: `core_features` contains the fixed 14-feature schema. Optional
indicators such as turn-taking, response latency, pause ratio, adult utterance
counts, and restricted-interest word count remain outside the core schema.

### ai_screening_outputs

Primary key: `output_id`

Foreign keys: `session_id` references `sessions.session_id`, `case_id`
references `child_cases.case_id`, `owner_user_id` references `users.user_id`

Fields: `output_id`, `session_id`, `case_id`, `owner_user_id`,
`model_version`, `concern_level`, `screening_support_score`,
`confidence_interval`, `explanation`, `plain_language_explanation`,
`top_contributing_features`, `evidence_items`, `therapist_review_status`,
`created_at`, `updated_at`

Notes: `confidence_interval` is nullable until a calibrated method exists. AI
support outputs must include plain-language not-a-diagnosis wording and
traceable evidence items.

### therapy_goals

Primary key: `goal_id`

Foreign keys: `case_id` references `child_cases.case_id`, `owner_user_id`
references `users.user_id`

Fields: `goal_id`, `case_id`, `owner_user_id`, `goal_text`, `status`,
`created_at`, `updated_at`

### therapist_notes

Primary key: `note_id`

Foreign keys: `case_id` references `child_cases.case_id`, optional
`session_id` references `sessions.session_id`, `owner_user_id` references
`users.user_id`

Fields: `note_id`, `case_id`, `session_id`, `owner_user_id`, `note_text`,
`created_at`, `updated_at`

### reports

Primary key: `report_id`

Foreign keys: `case_id` references `child_cases.case_id`, optional
`session_id` references `sessions.session_id`, `owner_user_id` references
`users.user_id`

Fields: `report_id`, `case_id`, `session_id`, `owner_user_id`,
`report_type`, `title`, `content_markdown`, `export_status`, `created_at`,
`updated_at`

### audit_logs

Primary key: `audit_id`

Foreign keys: `actor_user_id` references `users.user_id`

Fields: `audit_id`, `event_type`, `actor_user_id`, `target_type`,
`target_id`, `message`, `created_at`

Notes: audit-log reads are org-admin-only through the backend in the current
launch model. Direct client RLS must not expose audit logs to therapist,
clinical_supervisor, or platform_operator roles.

### privacy_operations

Primary key: `operation_id`

Foreign keys: `case_id`, `owner_user_id`, `requested_by_user_id`, optional
`reviewed_by_user_id`

Fields: `operation_id`, `operation_type`, `case_id`, `owner_user_id`,
`requested_by_user_id`, `status`, `details`, `reviewed_by_user_id`,
`reviewed_at`, `created_at`, `updated_at`

Notes: supported operation types are case privacy export request, consent
withdrawal request, and case deletion request. Deletion is an operational
review request and must not silently erase audit logs or required retention
records.

### clinical_signoffs

Primary key: `signoff_id`

Foreign keys: `case_id`, optional `session_id`, `owner_user_id`, and
`signed_by_user_id`

Fields: `signoff_id`, `target_type`, `target_id`, `session_id`, `case_id`,
`owner_user_id`, `signed_by_user_id`, `notes`, `created_at`

Notes: `target_type` is one of `transcript`, `features`, or `report`.
Reports and AI-assisted summaries should show sign-off status before export.

### model_runs

Primary key: `model_run_id`

Foreign keys: `session_id`, `case_id`, `owner_user_id`

Fields: `model_run_id`, `session_id`, `case_id`, `owner_user_id`,
`model_card_version`, `feature_schema_version`, `thresholds`,
`calibration_metadata`, `created_at`

Notes: model run metadata must preserve clinical safety context, including
that the output is screening support and not validated for Thai children.

## API Boundary

The pilot backend exposes a FastAPI boundary in `src/therapist_backend/app.py`
with these routes:

- `POST /api/auth/session`, `GET /api/me`
- `GET/POST/PATCH /api/cases`, `POST /api/cases/{case_id}/consent`
- `GET/POST/PATCH /api/sessions`
- `POST /api/sessions/{session_id}/audio/upload-intent`
- `POST /api/sessions/{session_id}/process-audio`, `GET /api/jobs/{job_id}`
- `GET/PATCH /api/sessions/{session_id}/transcript`
- `PATCH /api/transcripts/{transcript_id}/lines/{line_id}`
- `POST /api/sessions/{session_id}/transcript/signoff`
- `POST /api/sessions/{session_id}/features/extract`
- `GET /api/sessions/{session_id}/features`
- `POST /api/sessions/{session_id}/report`
- `GET /api/cases/{case_id}/progress`
- `GET /api/audit-logs`

Production privacy endpoints should use the same ownership checks as case
routes and should route deletion and consent withdrawal requests through
auditable admin review.

Frontend auth modes map to this boundary as follows:

- `mock`: sample-account sign-in with session restore for demo use only.
- `local_dev`: calls `POST /api/auth/session`, stores the returned mock token
  for the current browser session, and restores via `GET /api/me`.
- `supabase`: reserved for Supabase Auth/JWT integration; it must fail closed
  until a configured Supabase client is supplied.
- `enterprise_oidc_placeholder`: reserved for future OIDC/SSO and must fail
  closed until a real provider is configured.
