import { describe, expect, it, vi } from "vitest";
import {
  evaluateReferenceComparisonReadiness,
  loadReferenceComparisonForSession,
  REFERENCE_COMPARISON_STATUS,
  REFERENCE_COMPARISON_ROUTE,
  topReferenceFeatures
} from "../services/reference-comparison-service.js";
import { renderReferenceComparisonPanel } from "../views/transcript-view.js";

const session = {
  session_id: "SESSION-001",
  session_type: "free_play"
};

const reviewedTranscript = {
  transcript_id: "TRANSCRIPT-001",
  review_status: "reviewed",
  qa_status: "pass"
};

const completedFeatures = {
  extraction_status: "completed",
  features: {
    age_months: 56,
    mlu: 2.33,
    ttr: 0.86
  }
};

function okPayload() {
  return {
    status: "ok",
    reference_term: "Reference Comparison",
    age_band_12mo: "48-59",
    task_type: "toyplay",
    language: "eng",
    warnings: [],
    cohorts: [
      {
        group: "TD",
        cohort_n: 31,
        confidence_flag: "ok",
        feature_comparisons: [
          {
            feature: "mlu",
            value: 2.33,
            percentile: 58.06,
            position: "within_iqr",
            q1: 1.8,
            median: 2.3,
            q3: 2.9
          },
          {
            feature: "ttr",
            value: 0.86,
            percentile: 94.2,
            position: "above_iqr",
            q1: 0.45,
            median: 0.5,
            q3: 0.6
          }
        ],
        clan_metric_comparisons: [
          { metric: "kideval_mlu_utts", reference_n: 31 }
        ]
      }
    ]
  };
}

describe("Reference Comparison frontend boundary", () => {
  it("documents the backend route used by the transcript tab", () => {
    expect(REFERENCE_COMPARISON_ROUTE).toBe("GET /api/sessions/:sessionId/reference-comparison");
  });

  it("blocks comparison until transcript review and feature extraction are complete", () => {
    expect(
      evaluateReferenceComparisonReadiness({
        transcript: { review_status: "awaiting_review", qa_status: "pass" },
        features: { extraction_status: "preliminary" }
      })
    ).toMatchObject({
      ready: false,
      reasons: ["transcript_review_required", "features_preliminary"]
    });

    expect(
      evaluateReferenceComparisonReadiness({
        transcript: reviewedTranscript,
        features: { extraction_status: "stale" }
      })
    ).toMatchObject({
      ready: false,
      reasons: ["features_stale"]
    });
  });

  it("blocks failed QA but allows reviewed warning-level QA with caution", () => {
    expect(
      evaluateReferenceComparisonReadiness({
        transcript: { review_status: "reviewed", qa_status: "fail" },
        features: completedFeatures
      })
    ).toMatchObject({
      ready: false,
      reasons: ["qa_failed"]
    });

    expect(
      evaluateReferenceComparisonReadiness({
        transcript: { review_status: "reviewed", qa_status: "needs_review" },
        features: completedFeatures
      })
    ).toMatchObject({
      ready: true,
      warnings: ["qa_needs_review"]
    });
  });

  it("returns a status-only unavailable result when backend comparison is not configured", async () => {
    const result = await loadReferenceComparisonForSession({
      sessionId: "SESSION-001",
      transcript: reviewedTranscript,
      features: completedFeatures,
      currentUser: { user_id: "therapist_a" },
      apiBaseUrl: "",
      dataMode: "mock"
    });

    expect(result).toMatchObject({
      status: REFERENCE_COMPARISON_STATUS.UNAVAILABLE,
      source: "mock_status_only",
      reasons: ["backend_reference_unavailable_in_mock_mode"],
      payload: null
    });
  });

  it("loads backend Reference Comparison with X-User-Id and preserves payload", async () => {
    const fetchImpl = vi.fn(async (url, options) => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify(okPayload()),
      url,
      options
    }));

    const result = await loadReferenceComparisonForSession({
      sessionId: "SESSION-001",
      transcript: reviewedTranscript,
      features: completedFeatures,
      currentUser: { user_id: "therapist_a" },
      apiBaseUrl: "http://localhost:8000",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://localhost:8000/api/sessions/SESSION-001/reference-comparison",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ "X-User-Id": "therapist_a" })
      })
    );
    expect(result.status).toBe(REFERENCE_COMPARISON_STATUS.READY);
    expect(result.payload.cohorts[0].group).toBe("TD");
  });

  it("renders blocked, unavailable, and ready states without diagnostic wording", () => {
    const blockedHtml = renderReferenceComparisonPanel({
      session,
      transcript: { review_status: "awaiting_review", qa_status: "pass" },
      features: completedFeatures,
      aiOutput: {},
      currentUser: { user_id: "therapist_a" },
      comparisonState: null
    });
    expect(blockedHtml).toContain("transcript review");
    expect(blockedHtml).toContain("Reference: blocked");

    const unavailableHtml = renderReferenceComparisonPanel({
      session,
      transcript: reviewedTranscript,
      features: completedFeatures,
      aiOutput: {},
      currentUser: { user_id: "therapist_a" },
      comparisonState: {
        status: REFERENCE_COMPARISON_STATUS.UNAVAILABLE,
        reasons: ["backend_reference_unavailable_in_mock_mode"],
        warnings: [],
        payload: null
      }
    });
    expect(unavailableHtml).toContain("Mock mode does not generate percentiles");

    const readyHtml = renderReferenceComparisonPanel({
      session,
      transcript: reviewedTranscript,
      features: completedFeatures,
      aiOutput: { top_contributing_features: ["mlu"] },
      currentUser: { user_id: "therapist_a" },
      comparisonState: {
        status: REFERENCE_COMPARISON_STATUS.READY,
        warnings: [],
        payload: okPayload()
      }
    });

    expect(readyHtml).toContain("TD cohort");
    expect(readyHtml).toContain("within_iqr");
    expect(readyHtml.toLowerCase()).not.toContain("diagnostic");
  });

  it("prioritizes top contributing features before fallback rows", () => {
    const rows = topReferenceFeatures(okPayload(), { top_contributing_features: ["ttr"] });
    expect(rows.map(row => row.feature)).toEqual(["ttr"]);

    const fallbackRows = topReferenceFeatures(okPayload(), { top_contributing_features: [] }, 1);
    expect(fallbackRows.map(row => row.feature)).toEqual(["mlu"]);
  });
});
