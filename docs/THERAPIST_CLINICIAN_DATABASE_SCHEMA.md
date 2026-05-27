# Therapist Clinician Database Schema

This document describes database-ready tables for the therapist-clinician app.
The current app remains a clinical decision-support prototype with mock/demo
data by default. Do not store patient-identifiable data in this phase.

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
`original_filename`, `transcript_text`, `review_status`, `qa_status`,
`qa_score`, `qa_issues`, `reviewer_notes`, `created_at`, `updated_at`

### audio_files

Primary key: `audio_file_id`

Foreign keys: `session_id` references `sessions.session_id`, `case_id`
references `child_cases.case_id`, `owner_user_id` references `users.user_id`

Fields: `audio_file_id`, `session_id`, `case_id`, `owner_user_id`,
`original_filename`, `stored_filename`, `file_type`, `file_size`,
`duration_seconds`, `upload_time`, `processing_status`, `storage_mode`,
`created_at`, `updated_at`

### extracted_features

Primary key: `feature_id`

Foreign keys: `session_id` references `sessions.session_id`, `case_id`
references `child_cases.case_id`, `owner_user_id` references `users.user_id`

Fields: `feature_id`, `session_id`, `case_id`, `owner_user_id`,
`feature_schema_version`, `features`, `extraction_status`, `review_status`,
`created_at`, `updated_at`

### ai_screening_outputs

Primary key: `output_id`

Foreign keys: `session_id` references `sessions.session_id`, `case_id`
references `child_cases.case_id`, `owner_user_id` references `users.user_id`

Fields: `output_id`, `session_id`, `case_id`, `owner_user_id`,
`concern_level`, `screening_support_score`, `explanation`,
`top_contributing_features`, `evidence_items`, `therapist_review_status`,
`created_at`, `updated_at`

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

Notes: audit-log reads are admin-only in the therapist-clinician app demo.
