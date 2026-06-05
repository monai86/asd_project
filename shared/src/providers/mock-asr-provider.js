import { ASRProvider } from "./asr-provider.js";

export class MockASRProvider extends ASRProvider {
  constructor(delayMs = 1500) {
    super();
    this.delayMs = delayMs;
  }

  async transcribeAudio(file, language = "en", speakerCount = null) {
    await new Promise(resolve => setTimeout(resolve, this.delayMs));

    const textUtterances = await readTextUtterances(file);
    const testUtterances = textUtterances.length ? textUtterances : [
      { speaker_label: "THERAPIST", text: "What did you play today?", start_time: 1.2, end_time: 3.1 },
      { speaker_label: "CHILD", text: "I play train.", start_time: 3.8, end_time: 5.0 },
      { speaker_label: "THERAPIST", text: "You played with a train?", start_time: 5.5, end_time: 7.2 },
      { speaker_label: "CHILD", text: "Train train.", start_time: 7.8, end_time: 9.1 },
      { speaker_label: "CAREGIVER", text: "He likes trains.", start_time: 9.5, end_time: 11.0 },
      { speaker_label: "THERAPIST", text: "Can you put the red car on top?", start_time: 11.6, end_time: 14.0 },
      { speaker_label: "CHILD", text: "Red car on top.", start_time: 14.4, end_time: 16.0 },
      { speaker_label: "THERAPIST", text: "Where should the blue block go?", start_time: 16.5, end_time: 18.5 },
      { speaker_label: "CHILD", text: "Blue block here.", start_time: 19.0, end_time: 20.3 },
      { speaker_label: "CAREGIVER", text: "He is showing you the tower.", start_time: 20.8, end_time: 22.3 },
      { speaker_label: "CHILD", text: "You want train.", start_time: 22.7, end_time: 24.2 }
    ];

    const fullText = testUtterances.map(u => `${u.speaker_label}: ${u.text}`).join("\n");

    const utterances = testUtterances.map((u, i) => ({
      utterance_id: `UTT-${String(i + 1).padStart(3, "0")}`,
      speaker_label: u.speaker_label,
      text: u.text,
      start_time: u.start_time,
      end_time: u.end_time,
      duration: Number((u.end_time - u.start_time).toFixed(2)),
      word_count: u.text.split(/\s+/).filter(Boolean).length,
      confidence: 0.92,
      is_reviewed: false,
      review_metadata: null
    }));

    return {
      fullText,
      utterances,
      confidence: 0.94,
      detectedLanguage: language
    };
  }
}

async function readTextUtterances(file) {
  if (!file || typeof file.text !== "function") return [];
  const name = String(file.name || "").toLowerCase();
  const type = String(file.type || "").toLowerCase();
  if (!name.endsWith(".txt") && !name.endsWith(".cha") && !type.startsWith("text/")) return [];

  const raw = (await file.text()).trim();
  if (!raw) return [];

  let cursor = 1.0;
  return raw
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      const chatMatch = line.match(/^\*([A-Z]{3}):\s*(.+)$/);
      const plainMatch = line.match(/^([A-Za-z]+):\s*(.+)$/);
      const speaker = chatMatch?.[1] || plainMatch?.[1] || "THERAPIST";
      const text = chatMatch?.[2] || plainMatch?.[2] || line;
      const normalizedSpeaker = speaker === "CHI" || /^child$/i.test(speaker)
        ? "CHILD"
        : speaker === "MOT" || /^caregiver|parent|mother$/i.test(speaker)
          ? "CAREGIVER"
          : "THERAPIST";
      const duration = Math.max(0.8, text.split(/\s+/).filter(Boolean).length * 0.32);
      const utterance = {
        speaker_label: normalizedSpeaker,
        text: text.replace(/\s*[.?!]?\s*$/, "."),
        start_time: Number(cursor.toFixed(2)),
        end_time: Number((cursor + duration).toFixed(2))
      };
      cursor += duration + 0.45;
      return utterance;
    });
}
