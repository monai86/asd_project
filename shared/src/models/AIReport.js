export function createAIReport({
  report_id,
  session_id,
  case_id,
  owner_user_id,
  title = "AI-Assisted Language Analysis Report",
  ai_summary = "",
  safety_disclaimer = "This is an AI-assisted language analysis report for clinical decision support. It does not diagnose ASD and must be interpreted with qualified clinical judgment.",
  export_status = "pending",
  created_at = new Date().toISOString()
}) {
  return {
    report_id,
    session_id,
    case_id,
    owner_user_id,
    title,
    ai_summary,
    safety_disclaimer,
    export_status,
    created_at
  };
}
