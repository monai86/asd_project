export function createWordAlignment({
  word,
  start_time = null,
  end_time = null,
  confidence = 1.0,
  utterance_id,
  alignment_status = "not_available"
}) {
  return {
    word,
    start_time,
    end_time,
    confidence,
    utterance_id,
    alignment_status
  };
}
