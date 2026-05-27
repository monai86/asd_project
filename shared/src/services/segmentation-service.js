import { createUtterance } from "../models/Utterance.js";

export function segmentTranscript(rawText) {
  if (!rawText) return [];

  const lines = rawText.split("\n");
  const utterances = [];
  let uttCount = 1;
  let currentTime = 0.0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("@") || trimmed.startsWith("#")) {
      continue;
    }

    let rawSpeaker = "";
    let text = "";

    if (trimmed.startsWith("*") || trimmed.startsWith("%")) {
      const match = trimmed.match(/^[*%]([A-Z]{3,4}):\s*(.*)$/);
      if (match) {
        rawSpeaker = match[1];
        text = match[2];
      }
    } else if (trimmed.includes(":")) {
      const parts = trimmed.split(":");
      rawSpeaker = parts[0].trim();
      text = parts.slice(1).join(":").trim();
    }

    if (!rawSpeaker) continue;

    let speakerLabel = "UNKNOWN";
    const speakerUpper = rawSpeaker.toUpperCase();
    if (speakerUpper === "CHI" || speakerUpper === "CHILD") {
      speakerLabel = "CHILD";
    } else if (speakerUpper === "MOT" || speakerUpper === "CAR" || speakerUpper === "CAREGIVER") {
      speakerLabel = "CAREGIVER";
    } else if (speakerUpper === "INV" || speakerUpper === "THE" || speakerUpper === "THERAPIST") {
      speakerLabel = "THERAPIST";
    }

    const words = text.split(/\s+/).filter(Boolean);
    const duration = Number((words.length * 0.4).toFixed(2));
    const start_time = currentTime;
    const end_time = Number((currentTime + duration).toFixed(2));
    currentTime = end_time + 0.5;

    utterances.push(
      createUtterance({
        utterance_id: `UTT-${String(uttCount++).padStart(3, "0")}`,
        speaker_label: speakerLabel,
        text,
        start_time,
        end_time,
        duration,
        word_count: words.length,
        confidence: 0.90
      })
    );
  }

  return utterances;
}
