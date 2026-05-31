-- Indexes and Row Level Security policy examples for Supabase.
-- Production deployments must review admin/supervisor policy details before
-- exposing any clinical schema through client-accessible APIs.

create index idx_child_cases_owner on child_cases(owner_user_id);
create index idx_sessions_owner_case on sessions(owner_user_id, case_id);
create index idx_audio_files_owner_session on audio_files(owner_user_id, session_id);
create index idx_file_objects_owner_audio on file_objects(owner_user_id, audio_file_id);
create index idx_consent_records_owner_case on consent_records(owner_user_id, case_id);
create index idx_transcripts_owner_session on transcripts(owner_user_id, session_id);
create index idx_transcript_lines_owner_transcript on transcript_lines(owner_user_id, transcript_id);
create index idx_processing_jobs_owner_session on processing_jobs(owner_user_id, session_id);
create index idx_extracted_features_owner_session on extracted_features(owner_user_id, session_id);
create index idx_ai_outputs_owner_session on ai_screening_outputs(owner_user_id, session_id);
create index idx_reports_owner_case on reports(owner_user_id, case_id);
create index idx_privacy_operations_owner_case on privacy_operations(owner_user_id, case_id);
create index idx_audit_logs_actor_created on audit_logs(actor_user_id, created_at desc);

alter table child_cases enable row level security;
alter table sessions enable row level security;
alter table consent_records enable row level security;
alter table audio_files enable row level security;
alter table file_objects enable row level security;
alter table transcripts enable row level security;
alter table transcript_lines enable row level security;
alter table processing_jobs enable row level security;
alter table extracted_features enable row level security;
alter table ai_screening_outputs enable row level security;
alter table therapy_goals enable row level security;
alter table therapist_notes enable row level security;
alter table reports enable row level security;
alter table clinical_signoffs enable row level security;
alter table model_runs enable row level security;
alter table privacy_operations enable row level security;
alter table audit_logs enable row level security;

create policy owners_read_child_cases on child_cases
  for select using (owner_user_id = auth.uid());
create policy owners_write_child_cases on child_cases
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_sessions on sessions
  for select using (owner_user_id = auth.uid());
create policy owners_write_sessions on sessions
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_consent_records on consent_records
  for select using (owner_user_id = auth.uid());
create policy owners_write_consent_records on consent_records
  for all using (owner_user_id = auth.uid() and recorded_by_user_id = auth.uid())
  with check (owner_user_id = auth.uid() and recorded_by_user_id = auth.uid());

create policy owners_read_audio_files on audio_files
  for select using (owner_user_id = auth.uid());
create policy owners_write_audio_files on audio_files
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_file_objects on file_objects
  for select using (owner_user_id = auth.uid());
create policy owners_write_file_objects on file_objects
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_transcripts on transcripts
  for select using (owner_user_id = auth.uid());
create policy owners_write_transcripts on transcripts
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_transcript_lines on transcript_lines
  for select using (owner_user_id = auth.uid());
create policy owners_write_transcript_lines on transcript_lines
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_processing_jobs on processing_jobs
  for select using (owner_user_id = auth.uid());
create policy owners_write_processing_jobs on processing_jobs
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_extracted_features on extracted_features
  for select using (owner_user_id = auth.uid());
create policy owners_write_extracted_features on extracted_features
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_ai_outputs on ai_screening_outputs
  for select using (owner_user_id = auth.uid());
create policy owners_write_ai_outputs on ai_screening_outputs
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_therapy_goals on therapy_goals
  for select using (owner_user_id = auth.uid());
create policy owners_write_therapy_goals on therapy_goals
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_therapist_notes on therapist_notes
  for select using (owner_user_id = auth.uid());
create policy owners_write_therapist_notes on therapist_notes
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_reports on reports
  for select using (owner_user_id = auth.uid());
create policy owners_write_reports on reports
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_clinical_signoffs on clinical_signoffs
  for select using (owner_user_id = auth.uid());
create policy owners_write_clinical_signoffs on clinical_signoffs
  for all using (owner_user_id = auth.uid() and signed_by_user_id = auth.uid())
  with check (owner_user_id = auth.uid() and signed_by_user_id = auth.uid());

create policy owners_read_model_runs on model_runs
  for select using (owner_user_id = auth.uid());
create policy owners_write_model_runs on model_runs
  for all using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

create policy owners_read_privacy_operations on privacy_operations
  for select using (owner_user_id = auth.uid());
create policy owners_create_privacy_operations on privacy_operations
  for insert with check (owner_user_id = auth.uid() and requested_by_user_id = auth.uid());

-- Audit logs are intentionally not exposed through direct client RLS.
-- Admin review should use a backend/service-role endpoint that verifies role
-- membership before querying this table.
