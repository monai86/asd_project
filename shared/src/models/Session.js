export function createSession({
  session_id,
  case_id,
  owner_user_id,
  session_date = new Date().toISOString().split("T")[0],
  session_type = "free_play",
  audio_file_id = null,
  transcript_id = null,
  processing_status = "not_started",
  feature_extraction_status = "not_started",
  ai_analysis_status = "not_started",
  therapist_review_status = "not_started",
  report_status = "not_started",
  notes = "",
  created_at = new Date().toISOString(),
  updated_at = new Date().toISOString()
}) {
  return {
    session_id,
    case_id,
    owner_user_id,
    session_date,
    session_type,
    audio_file_id,
    transcript_id,
    processing_status,
    feature_extraction_status,
    ai_analysis_status,
    therapist_review_status,
    report_status,
    notes,
    created_at,
    updated_at
  };
}
