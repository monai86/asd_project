import { describe, expect, it, vi } from "vitest";
import {
  buildLocalTranscriptQaResult,
  loadTranscriptQaForSession,
  normalizeTranscriptQaPayload,
  shouldLoadBackendTranscriptQa,
  TRANSCRIPT_QA_LOAD_STATUS,
  TRANSCRIPT_QA_ROUTE
} from "../services/transcript-qa-service.js";
import { renderTranscriptQaPanel } from "../views/transcript-view.js";

const transcript = {
  transcript_id: "TRANSCRIPT-001",
  session_id: "SESSION-001",
  transcript_text: "@Begin\n@Languages:\teng\n*CHI:\twant car .\n@End",
  qa_status: "needs_review",
  qa_score: 90
};

describe("Transcript QA frontend boundary", () => {
  it("documents the backend route used by the transcript tab", () => {
    expect(TRANSCRIPT_QA_ROUTE).toBe("GET /api/sessions/:sessionId/qa");
  });

  it("normalizes backend QA payload with readiness flags", () => {
    const qa = normalizeTranscriptQaPayload({
      transcript_id: "TRANSCRIPT-001",
      session_id: "SESSION-001",
      status: "needs_review",
      quality_score: 88,
      issues: [{ code: "SHORT_CHILD_SAMPLE_FOR_KIDEVAL", message: "Short sample." }],
      readiness: {
        feature_extraction_ready: true,
        reference_comparison_ready: false,
        clan_metric_ready: false
      }
    });

    expect(qa).toMatchObject({
      load_status: TRANSCRIPT_QA_LOAD_STATUS.READY,
      source: "api",
      quality: "needs_review",
      score: 88
    });
    expect(qa.readiness.reference_comparison_ready).toBe(false);
  });

  it("loads backend QA with X-User-Id and preserves payload semantics", async () => {
    const fetchImpl = vi.fn(async (url, options) => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        transcript_id: "TRANSCRIPT-001",
        session_id: "SESSION-001",
        status: "pass",
        quality_score: 96,
        issues: [],
        readiness: {
          feature_extraction_ready: true,
          reference_comparison_ready: true,
          clan_metric_ready: true
        }
      }),
      url,
      options
    }));

    const result = await loadTranscriptQaForSession({
      sessionId: "SESSION-001",
      currentUser: { user_id: "therapist_a" },
      apiBaseUrl: "http://localhost:8000",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://localhost:8000/api/sessions/SESSION-001/qa",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ "X-User-Id": "therapist_a" })
      })
    );
    expect(result.quality).toBe("pass");
    expect(result.readiness.clan_metric_ready).toBe(true);
  });

  it("keeps mock/local QA explicitly lightweight", () => {
    const qa = buildLocalTranscriptQaResult(transcript, []);

    expect(qa.source).toBe("local_lightweight");
    expect(qa.readiness.warnings.clan_metric).toContain("lightweight_local_qa");

    const html = renderTranscriptQaPanel({
      session: { session_id: "SESSION-001" },
      transcript,
      transcriptLines: [],
      qaState: qa
    });
    expect(html).toContain("lightweight local QA");
  });

  it("only auto-loads backend QA when runtime prerequisites exist", () => {
    expect(shouldLoadBackendTranscriptQa({
      transcript,
      currentUser: { user_id: "therapist_a" },
      apiBaseUrl: "http://localhost:8000",
      dataMode: "api"
    })).toBe(true);

    expect(shouldLoadBackendTranscriptQa({
      transcript,
      currentUser: { user_id: "therapist_a" },
      apiBaseUrl: "http://localhost:8000",
      dataMode: "mock"
    })).toBe(false);

    expect(shouldLoadBackendTranscriptQa({
      transcript,
      currentUser: { user_id: "therapist_a" },
      apiBaseUrl: "http://localhost:8000",
      dataMode: "api",
      qaState: {
        load_status: TRANSCRIPT_QA_LOAD_STATUS.ERROR,
        source: "api"
      }
    })).toBe(false);
  });
});
