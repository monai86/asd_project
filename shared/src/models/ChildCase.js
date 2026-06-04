export function createChildCase({
  case_id,
  owner_user_id,
  anonymized_child_code,
  display_label = "",
  age_months,
  sex = "not_specified",
  primary_concerns = "",
  external_clinical_status = "under_evaluation",
  consent_status = "pending",
  anonymization_status = "anonymized",
  support_level = "Needs review",
  latest_score = 0.0,
  score_trend = [],
  starred = false,
  notes = "",
  created_at = new Date().toISOString(),
  updated_at = new Date().toISOString()
}) {
  return {
    case_id,
    owner_user_id,
    anonymized_child_code,
    display_label,
    age_months,
    sex,
    primary_concerns,
    external_clinical_status,
    consent_status,
    anonymization_status,
    support_level,
    latest_score,
    score_trend,
    starred,
    notes,
    created_at,
    updated_at
  };
}
