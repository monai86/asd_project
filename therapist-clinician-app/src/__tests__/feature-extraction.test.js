import { describe, it, expect } from "vitest";
import { segmentTranscript } from "@shared/services/segmentation-service.js";
import { extractAllFeatures } from "@shared/services/feature-extraction-service.js";

describe("Linguistic Feature Extraction", () => {
  it("should correctly compute features for the test transcript", () => {
    const rawTranscript = `
THERAPIST: What did you play today?
CHILD: I play train.
THERAPIST: You played with a train?
CHILD: Train train.
CAREGIVER: He likes trains.
CHILD: You want train.
    `;

    const utterances = segmentTranscript(rawTranscript);
    expect(utterances.length).toBe(6);

    const featureSet = extractAllFeatures(utterances, 56);
    const f = featureSet.features;

    // Verify 14-feature schema with optional interaction/acoustic-derived indicators
    expect(f.total_utterances).toBe(3); // CHILD spoke 3 times
    expect(f.age_months).toBe(56);
    
    // Total words = "I play train" (3) + "Train train" (2) + "You want train" (3) = 8 words
    expect(f.total_words).toBe(8);
    expect(f.mlu).toBeCloseTo(8 / 3, 2);

    // Echolalia / Repetitive words: "train train" should trigger repeated words
    expect(f.echolalia_count).toBeGreaterThanOrEqual(1);

    // Pronoun reversal: "You want train." starting with "you want"
    expect(f.pronoun_reversal_count).toBe(1);

    // Turn taking transitions count
    expect(f.turn_taking_count).toBe(5);
  });
});
