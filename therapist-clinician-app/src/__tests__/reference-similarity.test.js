import { describe, expect, it } from "vitest";
import { renderReferenceComparisonPanel } from "../views/transcript-view.js";

describe("Reference Similarity UI", () => {
  it("renders similar descriptive cards without diagnostic terms", () => {
    const comparisonState = {
      status: "ready",
      payload: {
        status: "ok",
        cohorts: []
      },
      similarityPayload: {
        status: "ok",
        results: [
          {
            transcript_uid: "test-uid",
            corpus: "Eigsti",
            group: "ASD",
            distance: 0.12,
            features: { mlu: 2.5 }
          }
        ]
      }
    };

    const html = renderReferenceComparisonPanel({
      session: { session_id: "SESSION-001" },
      transcript: { review_status: "reviewed" },
      features: { extraction_status: "completed" },
      currentUser: { user_id: "therapist" },
      comparisonState
    });

    expect(html).toContain("Similar Reference Cases (Descriptive)");
    expect(html).toContain("Eigsti");
    expect(html).not.toContain("diagnostic");
    expect(html).not.toContain("norm");
  });
});
