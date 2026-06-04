-- Initial clinical schema for the therapist-clinician product path.
-- This schema is Postgres/Supabase-oriented and keeps clinical records
-- owner-first, session-centric, and review-aware.

create type app_role as enum ('therapist', 'clinician', 'admin');
create type sex_value as enum ('female', 'male', 'other', 'not_specified');
create type consent_status_value as enum ('not_recorded', 'pending', 'granted', 'withdrawn', 'declined');
create type anonymization_status_value as enum ('pending', 'anonymized', 'needs_review');
create type session_type_value as enum ('free_play', 'parent_child_interaction', 'structured_assessment', 'therapy_session');
create type workflow_status_value as enum ('not_started', 'pending', 'uploaded', 'queued', 'processing', 'awaiting_review', 'completed', 'failed', 'stale', 'cancelled');
create type review_status_value as enum ('not_started', 'awaiting_review', 'reviewed', 'needs_correction', 'stale');

create table users (
  user_id uuid primary key,
  email text not null unique,
  name text not null,
  role app_role not null default 'therapist',
  organization text,
  credentials text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login timestamptz
);

create table child_cases (
  case_id uuid primary key,
  owner_user_id uuid not null references users(user_id),
  anonymized_child_code text not null unique check (anonymized_child_code ~ '^[A-Za-z0-9_-]{3,64}$'),
  display_label text,
  age_months integer not null check (age_months >= 0),
  sex sex_value not null default 'not_specified',
  primary_concerns text not null default '',
  external_clinical_status text not null default 'not_provided',
  consent_status consent_status_value not null default 'pending',
  anonymization_status anonymization_status_value not null default 'anonymized',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table consent_records (
  consent_id uuid primary key,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  recorded_by_user_id uuid not null references users(user_id),
  consent_type text not null default 'clinical_audio_processing',
  guardian_status text not null default 'guardian',
  audio_permission boolean not null default false,
  transcript_permission boolean not null default true,
  notes text not null default '',
  expires_at timestamptz,
  withdrawn_at timestamptz,
  created_at timestamptz not null default now()
);

create table sessions (
  session_id uuid primary key,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  session_date date not null,
  session_type session_type_value not null default 'therapy_session',
  audio_file_id uuid,
  transcript_id uuid,
  processing_status workflow_status_value not null default 'not_started',
  feature_extraction_status workflow_status_value not null default 'not_started',
  ai_analysis_status workflow_status_value not null default 'not_started',
  therapist_review_status review_status_value not null default 'not_started',
  report_status workflow_status_value not null default 'not_started',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table audio_files (
  audio_file_id uuid primary key,
  session_id uuid not null references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  original_filename text not null,
  stored_filename text not null,
  file_type text not null,
  file_size bigint not null check (file_size >= 0),
  duration_seconds numeric(10, 3),
  upload_time timestamptz not null default now(),
  processing_status workflow_status_value not null default 'uploaded',
  storage_mode text not null default 'metadata_only',
  file_object_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table file_objects (
  file_object_id uuid primary key,
  audio_file_id uuid not null references audio_files(audio_file_id) on delete cascade,
  session_id uuid not null references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  storage_key text not null,
  checksum_sha256 text,
  mime_type text not null default 'application/octet-stream',
  encryption_status text not null default 'required',
  retention_delete_after timestamptz,
  deleted_at timestamptz,
  created_at timestamptz not null default now()
);

alter table audio_files
  add constraint audio_files_file_object_id_fkey
  foreign key (file_object_id) references file_objects(file_object_id);

create table transcripts (
  transcript_id uuid primary key,
  session_id uuid not null unique references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  original_filename text,
  transcript_format text not null default 'CHAT',
  transcript_text text not null default '',
  chat_metadata jsonb not null default '[]'::jsonb,
  review_status review_status_value not null default 'awaiting_review',
  qa_status text not null default 'not_run',
  qa_score numeric(5, 2),
  qa_issues jsonb not null default '[]'::jsonb,
  reviewer_notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table transcript_lines (
  line_id uuid primary key,
  transcript_id uuid not null references transcripts(transcript_id) on delete cascade,
  session_id uuid not null references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  line_number integer not null,
  speaker_code text not null,
  utterance_text text not null,
  start_time numeric(10, 3),
  end_time numeric(10, 3),
  confidence numeric(5, 4),
  flags jsonb not null default '[]'::jsonb,
  review_status text not null default 'needs_review',
  reviewed boolean not null default false,
  interpretation_note text not null default '',
  version integer not null default 1,
  updated_at timestamptz not null default now(),
  updated_by_user_id uuid references users(user_id),
  unique (transcript_id, line_number)
);

create table processing_jobs (
  job_id uuid primary key,
  session_id uuid not null references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  audio_file_id uuid references audio_files(audio_file_id) on delete set null,
  job_type text not null default 'audio_pipeline',
  stage text not null default 'queued',
  status workflow_status_value not null default 'queued',
  progress integer not null default 0 check (progress between 0 and 100),
  error_code text,
  error_message text,
  result_refs jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table extracted_features (
  feature_id uuid primary key,
  session_id uuid not null unique references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  feature_schema_version text not null,
  features jsonb not null,
  core_features jsonb not null default '{}'::jsonb,
  optional_indicators jsonb not null default '{}'::jsonb,
  extraction_status workflow_status_value not null default 'completed',
  review_status review_status_value not null default 'awaiting_review',
  stale_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table ai_screening_outputs (
  output_id uuid primary key,
  session_id uuid not null unique references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  model_version text,
  concern_level text not null,
  screening_support_score numeric(6, 5),
  confidence_interval jsonb,
  top_contributing_features jsonb not null default '[]'::jsonb,
  evidence_items jsonb not null default '[]'::jsonb,
  explanation text not null default '',
  plain_language_explanation text not null default '',
  therapist_review_status review_status_value not null default 'awaiting_review',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table therapy_goals (
  goal_id uuid primary key,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  goal_text text not null,
  status text not null default 'active',
  target_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table therapist_notes (
  note_id uuid primary key,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  session_id uuid references sessions(session_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  note_text text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table reports (
  report_id uuid primary key,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  session_id uuid references sessions(session_id) on delete set null,
  owner_user_id uuid not null references users(user_id),
  report_type text not null default 'progress',
  title text not null,
  content_markdown text not null default '',
  export_status workflow_status_value not null default 'not_started',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table clinical_signoffs (
  signoff_id uuid primary key,
  target_type text not null,
  target_id text not null,
  session_id uuid references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  signed_by_user_id uuid not null references users(user_id),
  notes text not null default '',
  created_at timestamptz not null default now()
);

create table model_runs (
  model_run_id uuid primary key,
  session_id uuid not null references sessions(session_id) on delete cascade,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  model_card_version text not null,
  feature_schema_version text not null,
  thresholds jsonb not null default '{}'::jsonb,
  calibration_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table privacy_operations (
  operation_id uuid primary key,
  operation_type text not null,
  case_id uuid not null references child_cases(case_id) on delete cascade,
  owner_user_id uuid not null references users(user_id),
  requested_by_user_id uuid not null references users(user_id),
  status text not null default 'requested',
  details jsonb not null default '{}'::jsonb,
  reviewed_by_user_id uuid references users(user_id),
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table audit_logs (
  audit_id uuid primary key,
  actor_user_id uuid references users(user_id),
  event_type text not null,
  target_type text not null,
  target_id text not null,
  case_id uuid,
  session_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  message text not null default '',
  created_at timestamptz not null default now()
);
