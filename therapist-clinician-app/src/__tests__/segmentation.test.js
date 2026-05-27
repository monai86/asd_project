import { describe, it, expect } from "vitest";
import { segmentTranscript } from "@shared/services/segmentation-service.js";

describe("Utterance Segmentation Service", () => {
  it("should split raw transcript text into utterances", () => {
    const rawText = `
*CHI:\twant car .
*MOT:\twhich car do you want ?
*CHI:\tred car .
    `;
    const utts = segmentTranscript(rawText);
    expect(utts.length).toBe(3);
    expect(utts[0].speaker_label).toBe("CHILD");
    expect(utts[0].text).toBe("want car .");
    expect(utts[1].speaker_label).toBe("CAREGIVER");
    expect(utts[1].text).toBe("which car do you want ?");
  });

  it("should handle plain text speaker lines gracefully", () => {
    const rawText = `
THERAPIST: Hello child
CHILD: play train
    `;
    const utts = segmentTranscript(rawText);
    expect(utts.length).toBe(2);
    expect(utts[0].speaker_label).toBe("THERAPIST");
    expect(utts[1].speaker_label).toBe("CHILD");
  });

  it("should handle missing timestamps gracefully by generating estimated timings", () => {
    const rawText = "CHILD: train";
    const utts = segmentTranscript(rawText);
    expect(utts[0].start_time).toBe(0.0);
    expect(utts[0].end_time).toBe(0.4);
    expect(utts[0].duration).toBe(0.4);
  });
});
