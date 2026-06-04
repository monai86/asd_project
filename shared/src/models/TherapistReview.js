export function createTherapistReview({
  review_id,
  session_id,
  reviewer_id,
  review_status = "pending_review",
  therapist_notes = "",
  approved_summary = "",
  rejected_summary_reason = "",
  created_at = new Date().toISOString(),
  updated_at = new Date().toISOString()
}) {
  return {
    review_id,
    session_id,
    reviewer_id,
    review_status,
    therapist_notes,
    approved_summary,
    rejected_summary_reason,
    created_at,
    updated_at
  };
}
