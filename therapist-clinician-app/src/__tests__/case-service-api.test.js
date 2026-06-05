import { beforeEach, describe, expect, it, vi, afterEach } from "vitest";
import { store } from "../store/state.js";
import { createCase, updateCaseNotes, toggleStarCase } from "../services/case-service.js";
import { api } from "../services/api-client.js";

const testUser = {
  user_id: "therapist_a",
  name: "Therapist A",
  email: "therapist-a@example.test",
  role: "therapist"
};

describe("case-service API integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    store.setState({
      currentUser: testUser,
      dataMode: "mock",
      cases: [],
      selectedCaseId: null,
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

    it("createCase calls POST /api/cases, records consent if status is granted, and updates the store", async () => {
      const mockBackendCase = {
        case_id: "CASE-API-1",
        owner_user_id: "therapist_a",
        anonymized_child_code: "CHI-API",
        age_months: 48,
        sex: "female",
        primary_concerns: "Speech concerns",
        consent_status: "granted",
        anonymization_status: "anonymized",
        notes: "Some notes",
        created_at: "2026-06-03T00:00:00.000Z",
        updated_at: "2026-06-03T00:00:00.000Z"
      };

      const postSpy = vi.spyOn(api, "post").mockImplementation(async (path, payload) => {
        if (path === "/api/cases") {
          return mockBackendCase;
        }
        if (path === "/api/cases/CASE-API-1/consent") {
          return { success: true };
        }
        throw new Error(`Unexpected POST request to ${path}`);
      });

      const promise = createCase({
        anonymized_child_code: "CHI-API",
        age_months: 48,
        sex: "female",
        primary_concerns: "Speech concerns",
        consent_status: "granted",
        notes: "Some notes"
      });

      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;

      // Assert API is called with correct payload
      expect(postSpy).toHaveBeenCalledTimes(2);
      expect(postSpy).toHaveBeenNthCalledWith(1, "/api/cases", {
        anonymized_child_code: "CHI-API",
        age_months: 48,
        sex: "female",
        primary_concerns: "Speech concerns",
        consent_status: "granted",
        anonymization_status: "anonymized",
        display_label: "Case A",
        notes: "Some notes"
      });
      expect(postSpy).toHaveBeenNthCalledWith(2, "/api/cases/CASE-API-1/consent", {
        audio_permission: true
      });

      // Assert store was updated correctly
      const state = store.getState();
      expect(state.selectedCaseId).toBe("CASE-API-1");
      expect(state.cases).toHaveLength(1);
      expect(state.cases[0]).toMatchObject({
        case_id: "CASE-API-1",
        display_label: "Case A",
        anonymized_child_code: "CHI-API",
        consent_status: "granted"
      });

      // Assert audit log was recorded
      expect(state.auditLogs.some(log => log.event_type === "create_case" && log.target_id === "CASE-API-1")).toBe(true);

      // Assert returned case resolves properly
      expect(result).toMatchObject({
        case_id: "CASE-API-1",
        display_label: "Case A"
      });
    });

    it("createCase does NOT call consent endpoint if consent_status is pending", async () => {
      const mockBackendCase = {
        case_id: "CASE-API-2",
        owner_user_id: "therapist_a",
        anonymized_child_code: "CHI-API-2",
        age_months: 50,
        sex: "male",
        primary_concerns: "Language delay",
        consent_status: "pending",
        anonymization_status: "anonymized",
        notes: "Notes",
        created_at: "2026-06-03T00:00:00.000Z",
        updated_at: "2026-06-03T00:00:00.000Z"
      };

      const postSpy = vi.spyOn(api, "post").mockResolvedValue(mockBackendCase);

      const promise = createCase({
        anonymized_child_code: "CHI-API-2",
        age_months: 50,
        sex: "male",
        primary_concerns: "Language delay",
        consent_status: "pending",
        notes: "Notes"
      });

      const result = await promise;

      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith("/api/cases", {
        anonymized_child_code: "CHI-API-2",
        age_months: 50,
        sex: "male",
        primary_concerns: "Language delay",
        consent_status: "pending",
        anonymization_status: "anonymized",
        display_label: "Case A",
        notes: "Notes"
      });

      const state = store.getState();
      expect(state.cases.find(c => c.case_id === "CASE-API-2")).toBeDefined();
    });

    it("updateCaseNotes calls PATCH /api/cases/{caseId}, returns a Promise, and updates store notes", async () => {
      // Setup initial case in store
      const initialCase = {
        case_id: "CASE-API-1",
        owner_user_id: "therapist_a",
        anonymized_child_code: "CHI-API",
        display_label: "Case A",
        age_months: 48,
        sex: "female",
        primary_concerns: "Speech concerns",
        consent_status: "granted",
        anonymization_status: "anonymized",
        notes: "Old notes",
        support_level: "Needs review",
        latest_score: 0.0,
        score_trend: [],
        starred: false
      };

      store.setState({ cases: [initialCase] });

      const patchSpy = vi.spyOn(api, "patch").mockImplementation(async (path, payload) => {
        expect(path).toBe("/api/cases/CASE-API-1");
        return {
          case_id: "CASE-API-1",
          notes: payload.notes,
          updated_at: "2026-06-03T01:00:00.000Z"
        };
      });

      const promise = updateCaseNotes("CASE-API-1", "New notes");

      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;

      // Verify patch call
      expect(patchSpy).toHaveBeenCalledWith("/api/cases/CASE-API-1", { notes: "New notes" });

      // Verify store updated notes
      const state = store.getState();
      expect(state.cases[0].notes).toBe("New notes");
      // Other fields (like display_label) should remain intact
      expect(state.cases[0].display_label).toBe("Case A");
      expect(state.cases[0].consent_status).toBe("granted");

      // Verify audit log
      expect(state.auditLogs.some(log => log.event_type === "update_notes" && log.target_id === "CASE-API-1")).toBe(true);

      // Verify returned value
      expect(result.notes).toBe("New notes");
    });
  });

  describe("Mock Mode / Non-API Mode", () => {
    beforeEach(() => {
      store.setState({ dataMode: "mock" });
    });

    it("createCase operates synchronously and does not call backend API", () => {
      const postSpy = vi.spyOn(api, "post");

      const result = createCase({
        anonymized_child_code: "CHI-MOCK",
        age_months: 52,
        sex: "male",
        primary_concerns: "Language delay",
        consent_status: "pending",
        notes: "Mock data notes"
      });

      expect(result).not.toBeInstanceOf(Promise);
      expect(result.case_id).toBe("CASE-001");
      expect(postSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.selectedCaseId).toBe("CASE-001");
      expect(state.cases).toHaveLength(1);
    });

    it("updateCaseNotes operates synchronously and does not call backend API", () => {
      const initialCase = {
        case_id: "CASE-MOCK-1",
        owner_user_id: "therapist_a",
        anonymized_child_code: "CHI-MOCK",
        display_label: "Case A",
        age_months: 48,
        notes: "Old mock notes"
      };

      store.setState({ cases: [initialCase] });

      const patchSpy = vi.spyOn(api, "patch");

      const result = updateCaseNotes("CASE-MOCK-1", "New mock notes");

      expect(result).not.toBeInstanceOf(Promise);
      expect(result.notes).toBe("New mock notes");
      expect(patchSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.cases[0].notes).toBe("New mock notes");
    });

    it("toggleStarCase operates synchronously even if dataMode is api", () => {
      store.setState({ dataMode: "api" });
      const initialCase = {
        case_id: "CASE-API-1",
        owner_user_id: "therapist_a",
        anonymized_child_code: "CHI-API",
        display_label: "Case A",
        starred: false
      };

      store.setState({ cases: [initialCase] });

      const postSpy = vi.spyOn(api, "post");
      const patchSpy = vi.spyOn(api, "patch");

      const result = toggleStarCase("CASE-API-1");

      expect(result).toBeUndefined();
      expect(postSpy).not.toHaveBeenCalled();
      expect(patchSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.cases[0].starred).toBe(true);
    });
  });
});
