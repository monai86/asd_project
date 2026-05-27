import { createWordAlignment } from "../models/WordAlignment.js";

export function createAlignment(utterances, wordTimestamps = null) {
  const alignments = [];

  for (const utt of utterances) {
    const words = utt.text.split(/\s+/).filter(Boolean);
    if (wordTimestamps && wordTimestamps[utt.utterance_id]) {
      const timestamps = wordTimestamps[utt.utterance_id];
      timestamps.forEach(w => {
        alignments.push(
          createWordAlignment({
            word: w.word,
            start_time: w.start,
            end_time: w.end,
            confidence: w.confidence || 1.0,
            utterance_id: utt.utterance_id,
            alignment_status: "word_level"
          })
        );
      });
    } else {
      const step = utt.duration / Math.max(words.length, 1);
      words.forEach((word, idx) => {
        alignments.push(
          createWordAlignment({
            word: word.replace(/[.,?!]/g, ""),
            start_time: Number((utt.start_time + idx * step).toFixed(2)),
            end_time: Number((utt.start_time + (idx + 1) * step).toFixed(2)),
            confidence: utt.confidence,
            utterance_id: utt.utterance_id,
            alignment_status: "utterance_level"
          })
        );
      });
    }
  }

  return alignments;
}
