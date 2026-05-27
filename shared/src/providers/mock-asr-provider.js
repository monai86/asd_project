import { ASRProvider } from "./asr-provider.js";

export class MockASRProvider extends ASRProvider {
  constructor(delayMs = 1500) {
    super();
    this.delayMs = delayMs;
  }

  async transcribeAudio(file, language = "en", speakerCount = null) {
    await new Promise(resolve => setTimeout(resolve, this.delayMs));

    const testUtterances = [
      { speaker_label: "THERAPIST", text: "What did you play today?", start_time: 1.2, end_time: 3.1 },
      { speaker_label: "CHILD", text: "I play train.", start_time: 3.8, end_time: 5.0 },
      { speaker_label: "THERAPIST", text: "You played with a train?", start_time: 5.5, end_time: 7.2 },
      { speaker_label: "CHILD", text: "Train train.", start_time: 7.8, end_time: 9.1 },
      { speaker_label: "CAREGIVER", text: "He likes trains.", start_time: 9.5, end_time: 11.0 },
      { speaker_label: "CHILD", text: "You want train.", start_time: 11.5, end_time: 13.0 }
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
