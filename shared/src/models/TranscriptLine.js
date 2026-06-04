export function createTranscriptLine({
  line_id,
  transcript_id,
  session_id,
  case_id,
  owner_user_id,
  line_number,
  speaker,
  speaker_code = speaker,
  text,
  utterance_text = text,
  timing = null,
  start_time = timing?.start_time ?? null,
  end_time = timing?.end_time ?? null,
  confidence = 1.0,
  clinical_flags = [],
  flags = clinical_flags,
  review_status = "needs_review",
  reviewed = false,
  interpretation_note = "",
  version = 1,
  updated_at = new Date().toISOString(),
  updated_by_user_id = null
} = {}) {
  const normalizedTiming = timing || (start_time != null || end_time != null
    ? { start_time, end_time }
    : null);

  return {
    line_id,
    transcript_id,
    session_id,
    case_id,
    owner_user_id,
    line_number,
    speaker: speaker_code,
    text: utterance_text,
    timing: normalizedTiming,
    confidence,
    clinical_flags: flags,
    review_status,
    reviewed,
    interpretation_note,
    version,
    updated_at,
    updated_by_user_id
  };
}
