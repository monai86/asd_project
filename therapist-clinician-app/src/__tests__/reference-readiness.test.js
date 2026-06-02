import { describe, expect, it, vi } from "vitest";
import {
  loadReferenceReadiness,
  REFERENCE_READINESS_ROUTE,
  REFERENCE_READINESS_STATUS
} from "../services/reference-readiness-service.js";
import { renderResourceLibrary } from "../views/library-view.js";
import { renderReferenceComparisonPanel } from "../views/transcript-view.js";
import { store } from "../store/state.js";

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

describe("Reference Readiness frontend boundary", () => {
  it("defines the correct backend route constant", () => {
    expect(REFERENCE_READINESS_ROUTE).toBe("GET /api/reference/readiness");
  });

  it("returns mock data correctly when in mock mode", async () => {
    const result = await loadReferenceReadiness({
      currentUser: { user_id: "therapist_a" },
      dataMode: "mock"
    });
    expect(result.status).toBe(REFERENCE_READINESS_STATUS.READY);
    expect(result.summary.ok).toBe(28);
    expect(result.summary.low_n).toBe(20);
    expect(result.summary.not_cohort_ready).toBe(1);
    expect(result.cells.length).toBeGreaterThan(0);
  });

  it("calls the backend endpoint with X-User-Id in live mode", async () => {
    const mockPayload = {
      summary: { ok: 5, low_n: 2, not_cohort_ready: 0 },
      cells: [
        {
          language: "eng",
          age_band_12mo: "24-35",
          task_type: "toyplay",
          group: "TD",
          cohort_n: 12,
          coverage_status: "ok",
          confidence_flag: "ok",
          clan_metric_ready: true
        }
      ],
      generated_at: "2026-06-02T12:00:00Z",
      source_files: []
    };

    const fetchImpl = vi.fn(async (url, options) => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify(mockPayload),
      url,
      options
    }));

    const result = await loadReferenceReadiness({
      currentUser: { user_id: "therapist_b" },
      apiBaseUrl: "http://localhost:8080",
      dataMode: "api",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://localhost:8080/api/reference/readiness",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ "X-User-Id": "therapist_b" })
      })
    );
    expect(result.status).toBe(REFERENCE_READINESS_STATUS.READY);
    expect(result.summary.ok).toBe(5);
    expect(result.cells[0].age_band_12mo).toBe("24-35");
  });

  it("returns unavailable when no current user is provided", async () => {
    const result = await loadReferenceReadiness({
      currentUser: null,
      dataMode: "mock"
    });
    expect(result.status).toBe(REFERENCE_READINESS_STATUS.UNAVAILABLE);
  });

  it("renders Resource Library states correctly", () => {
    // 1. Loading State
    vi.spyOn(store, "getState").mockReturnValue({
      referenceReadiness: {
        status: "loading",
        summary: { ok: 0, low_n: 0, not_cohort_ready: 0 }
      }
    });
    let html = renderResourceLibrary();
    expect(html).toContain("Loading Reference Readiness Index...");

    // 2. Error State
    vi.spyOn(store, "getState").mockReturnValue({
      referenceReadiness: {
        status: "error",
        error_detail: "Connection failed"
      }
    });
    html = renderResourceLibrary();
    expect(html).toContain("Error loading index: Connection failed");

    // 3. Ready State
    vi.spyOn(store, "getState").mockReturnValue({
      referenceReadiness: {
        status: "ready",
        summary: { ok: 10, low_n: 5, not_cohort_ready: 2 }
      }
    });
    html = renderResourceLibrary();
    expect(html).toContain("10");
    expect(html).toContain("5");
    expect(html).toContain("2");
    expect(html.toLowerCase()).not.toContain("diagnostic");
    expect(html.toLowerCase()).not.toContain("norm");
  });

  it("displays Caution warning badge for low_n cohorts in Transcript panel", () => {
    const cohortPayload = {
      status: "ok",
      reference_term: "Reference Comparison",
      age_band_12mo: "24-35",
      task_type: "toyplay",
      language: "eng",
      warnings: [],
      cohorts: [
        {
          group: "ASD",
          cohort_n: 5,
          confidence_flag: "low_n",
          feature_comparisons: [
            {
              feature: "mlu",
              value: 2.33,
              percentile: 58.06,
              position: "within_iqr",
              q1: 1.8,
              median: 2.3,
              q3: 2.9
            }
          ]
        }
      ]
    };

    const readyHtml = renderReferenceComparisonPanel({
      session: { session_id: "SESSION-001", session_type: "free_play" },
      transcript: reviewedTranscript,
      features: completedFeatures,
      aiOutput: {},
      currentUser: { user_id: "therapist_a" },
      comparisonState: {
        status: "ready",
        warnings: [],
        payload: cohortPayload
      }
    });

    expect(readyHtml).toContain("Caution: low-count context");
    expect(readyHtml).toContain("n=5");
    expect(readyHtml.toLowerCase()).not.toContain("diagnostic");
    expect(readyHtml.toLowerCase()).not.toContain("validation");
    expect(readyHtml.toLowerCase()).not.toContain("norm");
    expect(readyHtml.toLowerCase()).not.toContain("benchmark");
  });
});
