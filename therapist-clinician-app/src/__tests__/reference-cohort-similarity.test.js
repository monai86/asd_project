import { describe, expect, it } from "vitest";
import { mapBackendProcessingResultToFrontend } from "../services/audio-processing-api.js";

describe("reference cohort similarity frontend mapping", () => {
  it("maps preliminary similarity and safety warnings from backend output", () => {
    const result = mapBackendProcessingResultToFrontend(
      {
        transcript: { transcript_id: "TRANSCRIPT-REF", transcript_text: "@Begin\n@End\n" },
        transcript_lines: [],
        qa: { status: "needs_review", quality_score: 80, issues: [] },
        features: { feature_schema_version: "14-feature-schema", features: {}, extraction_status: "preliminary" },
        reference_cohort_similarity: {
          output_kind: "reference_cohort_similarity",
          inference_status: "preliminary",
          report_eligible: false,
          reference_cohort_probabilities: { ASD: 0.6, TD: 0.2, DD: 0.2 },
          most_similar_reference_cohort: "ASD",
          similarity_probability: 0.6,
          safety_warnings: [{ code: "PRELIMINARY_TRANSCRIPT", message: "Review required." }],
          plain_language_explanation: "This transcript has feature patterns most similar to the ASD reference cohort. It is not a diagnosis."
        }
      },
      {
        session: { session_id: "SESSION-REF", case_id: "CASE-REF", owner_user_id: "user_therapist_001" },
        childCase: { case_id: "CASE-REF" },
        currentUser: { user_id: "user_therapist_001" },
        transcriptCount: 1
      }
    );

    expect(result.aiOutput.output_kind).toBe("reference_cohort_similarity");
    expect(result.aiOutput.inference_status).toBe("preliminary");
    expect(result.aiOutput.report_eligible).toBe(false);
    expect(result.aiOutput.safety_warnings[0].code).toBe("PRELIMINARY_TRANSCRIPT");
    expect(result.aiOutput.therapist_review_status).toBe("requires_transcript_review");
  });
});
