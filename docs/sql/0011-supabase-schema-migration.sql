-- Consolidated supabase schema migration for the Supabase pilot therapist workspace.

-- Drop enums if they exist (safe migration block)
DROP TYPE IF EXISTS app_role CASCADE;
DROP TYPE IF EXISTS sex_value CASCADE;
DROP TYPE IF EXISTS consent_status_value CASCADE;
DROP TYPE IF EXISTS anonymization_status_value CASCADE;
DROP TYPE IF EXISTS session_type_value CASCADE;
DROP TYPE IF EXISTS workflow_status_value CASCADE;
DROP TYPE IF EXISTS review_status_value CASCADE;
DROP TYPE IF EXISTS artifact_freshness_value CASCADE;
DROP TYPE IF EXISTS feature_review_disposition_value CASCADE;

-- Create custom enums
CREATE TYPE app_role AS ENUM ('therapist', 'clinician', 'admin');
CREATE TYPE sex_value AS ENUM ('female', 'male', 'other', 'not_specified');
CREATE TYPE consent_status_value AS ENUM ('not_recorded', 'pending', 'granted', 'withdrawn', 'declined');
CREATE TYPE anonymization_status_value AS ENUM ('pending', 'anonymized', 'needs_review');
CREATE TYPE session_type_value AS ENUM ('free_play', 'parent_child_interaction', 'structured_assessment', 'therapy_session');
CREATE TYPE workflow_status_value AS ENUM ('not_started', 'pending', 'uploaded', 'queued', 'processing', 'awaiting_review', 'completed', 'failed', 'stale', 'cancelled');
CREATE TYPE review_status_value AS ENUM ('not_started', 'awaiting_review', 'reviewed', 'needs_correction', 'stale');
CREATE TYPE artifact_freshness_value AS ENUM ('current', 'preliminary', 'stale', 'failed', 'superseded');
CREATE TYPE feature_review_disposition_value AS ENUM ('needs_review', 'accepted', 'rejected', 'needs_context');

-- Create tables
CREATE TABLE users (
  user_id UUID PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  role app_role NOT NULL DEFAULT 'therapist',
  organization TEXT,
  credentials TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login TIMESTAMPTZ
);

CREATE TABLE child_cases (
  case_id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  anonymized_child_code TEXT NOT NULL UNIQUE CHECK (anonymized_child_code ~ '^[A-Za-z0-9_-]{3,64}$'),
  display_label TEXT,
  age_months INTEGER NOT NULL CHECK (age_months >= 0),
  sex sex_value NOT NULL DEFAULT 'not_specified',
  primary_concerns TEXT NOT NULL DEFAULT '',
  external_clinical_status TEXT NOT NULL DEFAULT 'not_provided',
  consent_status consent_status_value NOT NULL DEFAULT 'pending',
  anonymization_status anonymization_status_value NOT NULL DEFAULT 'anonymized',
  notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE consent_records (
  consent_id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  recorded_by_user_id UUID NOT NULL REFERENCES users(user_id),
  consent_type TEXT NOT NULL DEFAULT 'clinical_audio_processing',
  guardian_status TEXT NOT NULL DEFAULT 'guardian',
  audio_permission BOOLEAN NOT NULL DEFAULT false,
  transcript_permission BOOLEAN NOT NULL DEFAULT true,
  notes TEXT NOT NULL DEFAULT '',
  expires_at TIMESTAMPTZ,
  withdrawn_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  session_id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  session_date DATE NOT NULL,
  session_type session_type_value NOT NULL DEFAULT 'therapy_session',
  audio_file_id UUID,
  transcript_id UUID,
  processing_status workflow_status_value NOT NULL DEFAULT 'not_started',
  feature_extraction_status workflow_status_value NOT NULL DEFAULT 'not_started',
  ai_analysis_status workflow_status_value NOT NULL DEFAULT 'not_started',
  therapist_review_status review_status_value NOT NULL DEFAULT 'not_started',
  report_status workflow_status_value NOT NULL DEFAULT 'not_started',
  notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audio_files (
  audio_file_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  original_filename TEXT NOT NULL,
  stored_filename TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size BIGINT NOT NULL CHECK (file_size >= 0),
  duration_seconds NUMERIC(10, 3),
  upload_time TIMESTAMPTZ NOT NULL DEFAULT now(),
  processing_status workflow_status_value NOT NULL DEFAULT 'uploaded',
  storage_mode TEXT NOT NULL DEFAULT 'metadata_only',
  file_object_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE file_objects (
  file_object_id UUID PRIMARY KEY,
  audio_file_id UUID NOT NULL REFERENCES audio_files(audio_file_id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  storage_key TEXT NOT NULL,
  checksum_sha256 TEXT,
  mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
  encryption_status TEXT NOT NULL DEFAULT 'required',
  retention_delete_after TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE audio_files
  ADD CONSTRAINT audio_files_file_object_id_fkey
  FOREIGN KEY (file_object_id) REFERENCES file_objects(file_object_id);

CREATE TABLE transcripts (
  transcript_id UUID PRIMARY KEY,
  session_id UUID NOT NULL UNIQUE REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  original_filename TEXT,
  transcript_format TEXT NOT NULL DEFAULT 'CHAT',
  transcript_text TEXT NOT NULL DEFAULT '',
  chat_metadata JSONB NOT NULL DEFAULT '[]'::jsonb,
  review_status review_status_value NOT NULL DEFAULT 'awaiting_review',
  qa_status TEXT NOT NULL DEFAULT 'not_run',
  qa_score NUMERIC(5, 2),
  qa_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
  reviewer_notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transcript_lines (
  line_id TEXT PRIMARY KEY,
  transcript_id UUID NOT NULL REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  line_number INTEGER NOT NULL,
  speaker_code TEXT NOT NULL,
  speaker_role TEXT NOT NULL DEFAULT 'other',
  utterance_text TEXT NOT NULL,
  reviewed_text TEXT,
  start_time NUMERIC(10, 3),
  end_time NUMERIC(10, 3),
  start_ms INTEGER,
  end_ms INTEGER,
  confidence NUMERIC(5, 4),
  word_timestamps JSONB NOT NULL DEFAULT '[]'::jsonb,
  flags JSONB NOT NULL DEFAULT '[]'::jsonb,
  review_status TEXT NOT NULL DEFAULT 'needs_review',
  reviewed BOOLEAN NOT NULL DEFAULT false,
  interpretation_note TEXT NOT NULL DEFAULT '',
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by_user_id UUID REFERENCES users(user_id),
  UNIQUE (transcript_id, line_number)
);

CREATE TABLE processing_jobs (
  job_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  audio_file_id UUID REFERENCES audio_files(audio_file_id) ON DELETE SET NULL,
  job_type TEXT NOT NULL DEFAULT 'audio_pipeline',
  engine TEXT NOT NULL DEFAULT 'local_whisper',
  operation TEXT NOT NULL DEFAULT 'audio_to_chat',
  operation_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  dependency_check JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_revision TEXT,
  stage TEXT NOT NULL DEFAULT 'queued',
  status workflow_status_value NOT NULL DEFAULT 'queued',
  progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  error_code TEXT,
  error_message TEXT,
  result_refs JSONB NOT NULL DEFAULT '{}'::jsonb,
  artifact_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE clinical_speech_artifacts (
  artifact_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  artifact_type TEXT NOT NULL,
  freshness artifact_freshness_value NOT NULL DEFAULT 'current',
  transcript_id UUID REFERENCES transcripts(transcript_id) ON DELETE SET NULL,
  feature_id UUID,
  job_id UUID REFERENCES processing_jobs(job_id) ON DELETE SET NULL,
  source_revision TEXT,
  source_hash TEXT,
  storage_mode TEXT NOT NULL DEFAULT 'metadata_only',
  storage_key TEXT,
  content_type TEXT NOT NULL DEFAULT 'application/json',
  content_preview TEXT NOT NULL DEFAULT '',
  parsed_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  review_status review_status_value NOT NULL DEFAULT 'awaiting_review',
  created_by_user_id UUID REFERENCES users(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE extracted_features (
  feature_id UUID PRIMARY KEY,
  session_id UUID NOT NULL UNIQUE REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  feature_schema_version TEXT NOT NULL,
  features JSONB NOT NULL,
  core_features JSONB NOT NULL DEFAULT '{}'::jsonb,
  optional_indicators JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_revision TEXT,
  source_hash TEXT,
  extraction_status workflow_status_value NOT NULL DEFAULT 'completed',
  review_status review_status_value NOT NULL DEFAULT 'awaiting_review',
  stale_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE clinical_speech_artifacts
  ADD CONSTRAINT clinical_speech_artifacts_feature_id_fkey
  FOREIGN KEY (feature_id) REFERENCES extracted_features(feature_id) ON DELETE SET NULL;

CREATE TABLE feature_review_dispositions (
  disposition_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  feature_id UUID NOT NULL REFERENCES extracted_features(feature_id) ON DELETE CASCADE,
  flag_key TEXT NOT NULL,
  disposition feature_review_disposition_value NOT NULL DEFAULT 'needs_review',
  note TEXT NOT NULL DEFAULT '',
  reviewed_by_user_id UUID REFERENCES users(user_id),
  source_revision TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (feature_id, flag_key)
);

CREATE TABLE ai_screening_outputs (
  output_id UUID PRIMARY KEY,
  session_id UUID NOT NULL UNIQUE REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  model_version TEXT,
  concern_level TEXT NOT NULL,
  screening_support_score NUMERIC(6, 5),
  confidence_interval JSONB,
  top_contributing_features JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence_items JSONB NOT NULL DEFAULT '[]'::jsonb,
  explanation TEXT NOT NULL DEFAULT '',
  plain_language_explanation TEXT NOT NULL DEFAULT '',
  therapist_review_status review_status_value NOT NULL DEFAULT 'awaiting_review',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE therapy_goals (
  goal_id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  goal_text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  target_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE therapist_notes (
  note_id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  note_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
  report_id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  report_type TEXT NOT NULL DEFAULT 'progress',
  title TEXT NOT NULL,
  content_markdown TEXT NOT NULL DEFAULT '',
  export_status workflow_status_value NOT NULL DEFAULT 'not_started',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE clinical_signoffs (
  signoff_id UUID PRIMARY KEY,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  signed_by_user_id UUID NOT NULL REFERENCES users(user_id),
  notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE model_runs (
  model_run_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  model_card_version TEXT NOT NULL,
  feature_schema_version TEXT NOT NULL,
  thresholds JSONB NOT NULL DEFAULT '{}'::jsonb,
  calibration_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE privacy_operations (
  operation_id UUID PRIMARY KEY,
  operation_type TEXT NOT NULL,
  case_id UUID NOT NULL REFERENCES child_cases(case_id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(user_id),
  requested_by_user_id UUID NOT NULL REFERENCES users(user_id),
  status TEXT NOT NULL DEFAULT 'requested',
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  reviewed_by_user_id UUID REFERENCES users(user_id),
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
  audit_id UUID PRIMARY KEY,
  actor_user_id UUID REFERENCES users(user_id),
  event_type TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  case_id UUID,
  session_id UUID,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  message TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX transcript_lines_session_id_idx ON transcript_lines(session_id);
CREATE INDEX processing_jobs_session_id_idx ON processing_jobs(session_id, created_at DESC);
CREATE INDEX clinical_speech_artifacts_session_freshness_idx ON clinical_speech_artifacts(session_id, freshness, created_at DESC);
CREATE INDEX clinical_speech_artifacts_job_id_idx ON clinical_speech_artifacts(job_id);
CREATE INDEX feature_review_dispositions_feature_id_idx ON feature_review_dispositions(feature_id);

CREATE INDEX idx_child_cases_owner ON child_cases(owner_user_id);
CREATE INDEX idx_sessions_owner_case ON sessions(owner_user_id, case_id);
CREATE INDEX idx_audio_files_owner_session ON audio_files(owner_user_id, session_id);
CREATE INDEX idx_file_objects_owner_audio ON file_objects(owner_user_id, audio_file_id);
CREATE INDEX idx_consent_records_owner_case ON consent_records(owner_user_id, case_id);
CREATE INDEX idx_transcripts_owner_session ON transcripts(owner_user_id, session_id);
CREATE INDEX idx_transcript_lines_owner_transcript ON transcript_lines(owner_user_id, transcript_id);
CREATE INDEX idx_processing_jobs_owner_session ON processing_jobs(owner_user_id, session_id);
CREATE INDEX idx_extracted_features_owner_session ON extracted_features(owner_user_id, session_id);
CREATE INDEX idx_ai_outputs_owner_session ON ai_screening_outputs(owner_user_id, session_id);
CREATE INDEX idx_reports_owner_case ON reports(owner_user_id, case_id);
CREATE INDEX idx_privacy_operations_owner_case ON privacy_operations(owner_user_id, case_id);
CREATE INDEX idx_audit_logs_actor_created ON audit_logs(actor_user_id, created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE child_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_screening_outputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapy_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapist_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_signoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE privacy_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Current App Role helper
CREATE OR REPLACE FUNCTION public.current_app_role()
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
  SELECT role::text FROM public.users WHERE user_id = auth.uid()
$$;

-- RLS Policies
CREATE POLICY users_read_own_profile ON users
  FOR SELECT USING (user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY users_insert_own_profile ON users
  FOR INSERT WITH CHECK (user_id = auth.uid() AND role IN ('therapist', 'clinician'));
CREATE POLICY users_update_own_profile ON users
  FOR UPDATE USING (user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK ((user_id = auth.uid() AND role IN ('therapist', 'clinician')) OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_child_cases ON child_cases
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_child_cases ON child_cases
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_sessions ON sessions
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_sessions ON sessions
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_consent_records ON consent_records
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_consent_records ON consent_records
  FOR ALL USING ((owner_user_id = auth.uid() AND recorded_by_user_id = auth.uid()) OR public.current_app_role() = 'admin')
  WITH CHECK ((owner_user_id = auth.uid() AND recorded_by_user_id = auth.uid()) OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_audio_files ON audio_files
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_audio_files ON audio_files
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_file_objects ON file_objects
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_file_objects ON file_objects
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_transcripts ON transcripts
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_transcripts ON transcripts
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_transcript_lines ON transcript_lines
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_transcript_lines ON transcript_lines
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_processing_jobs ON processing_jobs
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_processing_jobs ON processing_jobs
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_extracted_features ON extracted_features
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_extracted_features ON extracted_features
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_ai_outputs ON ai_screening_outputs
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_ai_outputs ON ai_screening_outputs
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_therapy_goals ON therapy_goals
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_therapy_goals ON therapy_goals
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_therapist_notes ON therapist_notes
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_therapist_notes ON therapist_notes
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_reports ON reports
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_reports ON reports
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_clinical_signoffs ON clinical_signoffs
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_clinical_signoffs ON clinical_signoffs
  FOR ALL USING ((owner_user_id = auth.uid() AND signed_by_user_id = auth.uid()) OR public.current_app_role() = 'admin')
  WITH CHECK ((owner_user_id = auth.uid() AND signed_by_user_id = auth.uid()) OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_model_runs ON model_runs
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_write_model_runs ON model_runs
  FOR ALL USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin')
  WITH CHECK (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');

CREATE POLICY owners_read_privacy_operations ON privacy_operations
  FOR SELECT USING (owner_user_id = auth.uid() OR public.current_app_role() = 'admin');
CREATE POLICY owners_create_privacy_operations ON privacy_operations
  FOR INSERT WITH CHECK (owner_user_id = auth.uid() AND requested_by_user_id = auth.uid());

-- Storage Buckets Configuration
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'clinical-media',
  'clinical-media',
  false,
  262144000,
  ARRAY['audio/wav', 'audio/mpeg', 'audio/mp4', 'video/mp4', 'video/quicktime']
)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY clinical_media_owner_insert ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'clinical-media'
    AND (storage.foldername(name))[1] = 'private'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY clinical_media_owner_read ON storage.objects
  FOR SELECT USING (
    bucket_id = 'clinical-media'
    AND (
      (storage.foldername(name))[2] = auth.uid()::text
      OR public.current_app_role() = 'admin'
    )
  );
