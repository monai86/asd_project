import { describe, it, expect } from "vitest";
import { checkTranscriptQuality, wrapWithDisclaimer } from "@shared/services/safety-service.js";

describe("Clinical Safety & QA Checks", () => {
  it("should warn about short samples if utterance count is less than 5", () => {
    const rawText = "*CHI:\tcar .\n*MOT:\tyes .\n";
    const utterances = [
      { text: "car .", confidence: 0.9 },
      { text: "yes .", confidence: 0.9 }
    ];
    const qa = checkTranscriptQuality(rawText, utterances);
    expect(qa.warnings.some(w => w.code === "SHORT_SAMPLE")).toBe(true);
  });

  it("should warn about low confidence transcript segments", () => {
    const rawText = "*CHI:\tcar .\n*MOT:\tyes .\n*CHI:\tplay train\n*MOT:\tokay\n*CHI:\ttrain\n";
    const utterances = [
      { text: "car .", confidence: 0.9 },
      { text: "yes .", confidence: 0.9 },
      { text: "play train", confidence: 0.5 }, // low confidence
      { text: "okay", confidence: 0.9 },
      { text: "train", confidence: 0.9 }
    ];
    const qa = checkTranscriptQuality(rawText, utterances);
    expect(qa.warnings.some(w => w.code === "LOW_CONFIDENCE_UTTERANCES")).toBe(true);
  });

  it("should append clinical disclaimer to content", () => {
    const original = "Sample Report Content";
    const wrapped = wrapWithDisclaimer(original);
    expect(wrapped).toContain(original);
    expect(wrapped).toContain("does not diagnose ASD");
  });
});
