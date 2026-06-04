export function createUtterance({
  utterance_id,
  speaker_label,
  text,
  start_time = null,
  end_time = null,
  duration = null,
  word_count = 0,
  confidence = 1.0,
  is_reviewed = false,
  review_metadata = null
}) {
  return {
    utterance_id,
    speaker_label,
    text,
    start_time,
    end_time,
    duration,
    word_count,
    confidence,
    is_reviewed,
    review_metadata
  };
}
