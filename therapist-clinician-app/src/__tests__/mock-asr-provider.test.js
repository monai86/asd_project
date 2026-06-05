import { describe, expect, it } from "vitest";
import { MockASRProvider } from "@shared/providers/mock-asr-provider";

describe("MockASRProvider", () => {
  it("returns a fuller default therapy sample", async () => {
    const provider = new MockASRProvider(0);

    const result = await provider.transcribeAudio({ name: "session_audio.wav" });

    expect(result.utterances.length).toBeGreaterThanOrEqual(10);
    expect(result.fullText).toContain("THERAPIST:");
    expect(result.fullText).toContain("CHILD:");
  });

  it("uses text or CHAT file content when supplied", async () => {
    const provider = new MockASRProvider(0);
    const file = new File([
      "*MOT:\tlet's build blocks.\n*CHI:\tred car.\n*CHI:\tblue block here."
    ], "sample.cha", { type: "text/plain" });

    const result = await provider.transcribeAudio(file);

    expect(result.utterances).toHaveLength(3);
    expect(result.utterances[0]).toMatchObject({
      speaker_label: "CAREGIVER",
      text: "let's build blocks."
    });
    expect(result.utterances[1]).toMatchObject({
      speaker_label: "CHILD",
      text: "red car."
    });
  });
});
