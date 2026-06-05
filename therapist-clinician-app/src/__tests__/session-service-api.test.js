import { beforeEach, describe, expect, it, vi, afterEach } from "vitest";
import { store } from "../store/state.js";
import { createNewSession, deleteSession, updateSessionStatus } from "../services/session-service.js";
import { api } from "../services/api-client.js";

const testUser = {
  user_id: "therapist_a",
  name: "Therapist A",
  email: "therapist-a@example.test",
  role: "therapist"
};

const testCase = {
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  anonymized_child_code: "CHI-001",
  display_label: "Case A",
  age_months: 48,
  sex: "female"
};

describe("session-service API integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    store.setState({
      currentUser: testUser,
      dataMode: "mock",
      cases: [testCase],
      sessions: [],
      selectedSessionId: null,
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

    it("createNewSession calls POST /api/sessions and updates the store", async () => {
      const mockBackendSession = {
        session_id: "SESSION-API-1",
        case_id: "CASE-001",
        session_date: "2026-06-03",
        session_type: "free_play",
        notes: "API session notes",
        processing_status: "not_started",
        created_at: "2026-06-03T00:00:00.000Z",
        updated_at: "2026-06-03T00:00:00.000Z"
      };

      const postSpy = vi.spyOn(api, "post").mockResolvedValue(mockBackendSession);

      const promise = createNewSession({
        case_id: "CASE-001",
        session_date: "2026-06-03",
        session_type: "free_play",
        notes: "API session notes"
      });

      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;

      // Assert API is called with correct payload
      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith("/api/sessions", {
        case_id: "CASE-001",
        session_date: "2026-06-03",
        session_type: "free_play",
        notes: "API session notes"
      });

      // Assert store was updated correctly
      const state = store.getState();
      expect(state.selectedSessionId).toBe("SESSION-API-1");
      expect(state.sessions).toHaveLength(1);
      expect(state.sessions[0]).toMatchObject({
        session_id: "SESSION-API-1",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        notes: "API session notes"
      });

      // Assert audit log was recorded
      expect(state.auditLogs.some(log => log.event_type === "create_session" && log.target_id === "SESSION-API-1")).toBe(true);

      // Assert returned session resolves properly
      expect(result).toMatchObject({
        session_id: "SESSION-API-1",
        case_id: "CASE-001"
      });
    });

    it("updateSessionStatus with notes calls PATCH /api/sessions/{sessionId} and updates the store", async () => {
      const initialSession = {
        session_id: "SESSION-API-1",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        session_date: "2026-06-03",
        session_type: "free_play",
        notes: "Old notes",
        processing_status: "not_started"
      };

      store.setState({ sessions: [initialSession] });

      const patchSpy = vi.spyOn(api, "patch").mockImplementation(async (path, payload) => {
        expect(path).toBe("/api/sessions/SESSION-API-1");
        return {
          session_id: "SESSION-API-1",
          notes: payload.notes,
          updated_at: "2026-06-03T01:00:00.000Z"
        };
      });

      const promise = updateSessionStatus("SESSION-API-1", { notes: "Updated API notes" });

      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;

      // Verify patch call
      expect(patchSpy).toHaveBeenCalledWith("/api/sessions/SESSION-API-1", { notes: "Updated API notes" });

      // Verify store updated session
      const state = store.getState();
      expect(state.sessions[0].notes).toBe("Updated API notes");

      // Verify returned value
      expect(result.notes).toBe("Updated API notes");
    });

    it("updateSessionStatus without notes updates store synchronously without API calls even in api mode", () => {
      const initialSession = {
        session_id: "SESSION-API-1",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        session_date: "2026-06-03",
        session_type: "free_play",
        notes: "Old notes",
        processing_status: "not_started"
      };

      store.setState({ sessions: [initialSession] });

      const patchSpy = vi.spyOn(api, "patch");

      const result = updateSessionStatus("SESSION-API-1", { processing_status: "completed" });

      expect(result).not.toBeInstanceOf(Promise);
      expect(result.processing_status).toBe("completed");
      expect(result.notes).toBe("Old notes");
      expect(patchSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.sessions[0].processing_status).toBe("completed");
    });

    it("deleteSession calls DELETE /api/sessions/{sessionId} and removes linked store artifacts", async () => {
      const initialSession = {
        session_id: "SESSION-API-1",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        session_date: "2026-06-03",
        session_type: "free_play",
        notes: "Delete me",
        processing_status: "completed"
      };
      store.setState({
        sessions: [initialSession],
        selectedSessionId: "SESSION-API-1",
        audioFiles: [{ audio_file_id: "AUDIO-1", session_id: "SESSION-API-1" }],
        processingJobs: [{ job_id: "JOB-1", session_id: "SESSION-API-1" }],
        generatedReports: [{ report_id: "REPORT-1", session_id: "SESSION-API-1" }],
        transcripts: { "SESSION-API-1": { transcript_id: "TRANSCRIPT-1" } },
        transcriptLines: { "SESSION-API-1": [{ line_id: "LINE-1" }] },
        extractedFeatureOutputs: { "SESSION-API-1": { feature_id: "FEATURE-1" } },
        aiDecisionOutputs: { "SESSION-API-1": { output_id: "AI-1" } },
        transcriptQaResults: { "SESSION-API-1": { status: "pass" } },
        referenceComparisons: { "SESSION-API-1": { status: "loaded" } },
        observationsReviews: { "SESSION-API-1": { echolalia_marker: { status: "accepted", note: "reviewed" } } }
      });

      const deleteSpy = vi.spyOn(api, "delete").mockResolvedValue({ session_id: "SESSION-API-1", deleted: true });

      const result = await deleteSession("SESSION-API-1");

      expect(deleteSpy).toHaveBeenCalledWith("/api/sessions/SESSION-API-1");
      expect(result).toMatchObject({ deleted: true, nextSelectedSessionId: null });

      const state = store.getState();
      expect(state.sessions).toHaveLength(0);
      expect(state.selectedSessionId).toBe(null);
      expect(state.audioFiles).toHaveLength(0);
      expect(state.processingJobs).toHaveLength(0);
      expect(state.generatedReports).toHaveLength(0);
      expect(state.transcripts["SESSION-API-1"]).toBeUndefined();
      expect(state.transcriptLines["SESSION-API-1"]).toBeUndefined();
      expect(state.extractedFeatureOutputs["SESSION-API-1"]).toBeUndefined();
      expect(state.aiDecisionOutputs["SESSION-API-1"]).toBeUndefined();
      expect(state.observationsReviews["SESSION-API-1"]).toBeUndefined();
      expect(state.auditLogs.some(log => log.event_type === "delete_session")).toBe(true);
    });
  });

  describe("Mock Mode / Non-API Mode", () => {
    beforeEach(() => {
      store.setState({ dataMode: "mock" });
    });

    it("createNewSession operates synchronously and does not call backend API", () => {
      const postSpy = vi.spyOn(api, "post");

      const result = createNewSession({
        case_id: "CASE-001",
        session_date: "2026-06-03",
        session_type: "structured_assessment",
        notes: "Mock notes"
      });

      expect(result).not.toBeInstanceOf(Promise);
      expect(result.session_id).toBe("SESSION-001");
      expect(postSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.selectedSessionId).toBe("SESSION-001");
      expect(state.sessions).toHaveLength(1);
    });

    it("createNewSession uses the highest numeric local session id", () => {
      store.setState({
        sessions: [
          { session_id: "SESSION-001", case_id: "CASE-001", owner_user_id: "therapist_a" },
          { session_id: "SESSION-009", case_id: "CASE-001", owner_user_id: "therapist_a" }
        ]
      });

      const result = createNewSession({
        case_id: "CASE-001",
        session_date: "2026-06-04",
        session_type: "free_play",
        notes: ""
      });

      expect(result.session_id).toBe("SESSION-010");
    });

    it("updateSessionStatus operates synchronously and does not call backend API", () => {
      const initialSession = {
        session_id: "SESSION-001",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        session_date: "2026-06-03",
        session_type: "free_play",
        notes: "Old mock notes"
      };

      store.setState({ sessions: [initialSession] });

      const patchSpy = vi.spyOn(api, "patch");

      const result = updateSessionStatus("SESSION-001", { notes: "New mock notes" });

      expect(result).not.toBeInstanceOf(Promise);
      expect(result.notes).toBe("New mock notes");
      expect(patchSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.sessions[0].notes).toBe("New mock notes");
    });
  });
});
