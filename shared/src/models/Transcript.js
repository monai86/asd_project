export function createTranscript({
  transcript_id,
  session_id,
  case_id,
  owner_user_id,
  original_filename = "",
  transcript_text = "",
  review_status = "awaiting_review",
  qa_status = "needs_review",
  qa_score = 100,
  qa_issues = [],
  reviewer_notes = "",
  created_at = new Date().toISOString(),
  updated_at = new Date().toISOString()
}) {
  return {
    transcript_id,
    session_id,
    case_id,
    owner_user_id,
    original_filename,
    transcript_text,
    review_status,
    qa_status,
    qa_score,
    qa_issues,
    reviewer_notes,
    created_at,
    updated_at
  };
}
