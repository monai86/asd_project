import { beforeEach, describe, expect, it, vi, afterEach } from "vitest";
import { store } from "../store/state.js";
import { generateSessionReport } from "../services/report-service.js";
import { api } from "../services/api-client.js";

const testUser = {
  user_id: "therapist_a",
  name: "Therapist A",
  email: "therapist-a@example.test",
  role: "therapist"
};

const testSession = {
  session_id: "SESSION-001",
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  session_date: "2026-06-03",
  session_type: "free_play",
  processing_status: "transcript_ready",
  therapist_review_status: "reviewed",
  report_status: "pending"
};

describe("report-service API integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    store.setState({
      currentUser: testUser,
      dataMode: "mock",
      sessions: [testSession],
      generatedReports: [],
      auditLogs: []
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("API Mode", () => {
    beforeEach(() => {
      store.setState({ dataMode: "api" });
    });

    it("generateSessionReport posts to API and updates store", async () => {
      const mockBackendReport = {
        report_id: "REPORT-API-001",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        title: "Progress Report: CHI-001",
        ai_summary: "AI generated summary from backend",
        export_status: "completed",
        created_at: "2026-06-03T00:00:00.000Z"
      };

      const postSpy = vi.spyOn(api, "post").mockResolvedValue(mockBackendReport);

      const promise = generateSessionReport("SESSION-001");

      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;

      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith("/api/sessions/SESSION-001/report", {});

      const state = store.getState();
      expect(state.generatedReports).toHaveLength(1);
      expect(state.generatedReports[0].report_id).toBe("REPORT-API-001");
      expect(state.sessions[0].report_status).toBe("completed");

      expect(result.report_id).toBe("REPORT-API-001");
    });
  });

  describe("Mock Mode", () => {
    beforeEach(() => {
      store.setState({
        dataMode: "mock",
        cases: [{ case_id: "CASE-001", owner_user_id: "therapist_a", anonymized_child_code: "CHI-001" }],
        transcripts: { "SESSION-001": { transcript_id: "TRANSCRIPT-001", review_status: "reviewed" } },
        extractedFeatureOutputs: { "SESSION-001": { features: { mlu: 3.0, ttr: 0.5, echolalia_ratio: 0.1 } } },
        aiDecisionOutputs: {
          "SESSION-001": {
            concern_level: "low_concern",
            screening_support_score: 0.3,
            top_contributing_features: [],
            evidence_items: []
          }
        }
      });
    });

    it("generateSessionReport operates synchronously and does not call backend API", () => {
      const postSpy = vi.spyOn(api, "post");

      const result = generateSessionReport("SESSION-001");

      expect(result).not.toBeInstanceOf(Promise);
      expect(result.report_id).toBeDefined();
      expect(postSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.generatedReports).toHaveLength(1);
      expect(state.sessions[0].report_status).toBe("completed");
    });
  });
});
