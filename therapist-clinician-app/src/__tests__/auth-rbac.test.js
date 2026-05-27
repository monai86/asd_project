import { beforeEach, describe, expect, it } from "vitest";
import { store } from "../store/state.js";
import { createAuthAdapter, PROVIDER_NOT_CONFIGURED_MESSAGE } from "../services/auth-adapter.js";
import {
  getCurrentUser,
  getUserRole,
  requireAuth,
  signIn,
  signOut
} from "../services/auth-service.js";
import { getVisibleCases } from "../services/case-service.js";
import { getVisibleSessions } from "../services/session-service.js";
import { renderDashboard } from "../views/dashboard-view.js";
import { renderSettings } from "../views/settings-view.js";
import { renderAuditLogs } from "../views/audit-view.js";

const users = [
  { user_id: "therapist_a", name: "Therapist A", email: "therapist-a@example.test", role: "therapist" },
  { user_id: "therapist_b", name: "Therapist B", email: "therapist-b@example.test", role: "therapist" },
  { user_id: "clinician_a", name: "Clinician A", email: "clinician-a@example.test", role: "clinician" },
  { user_id: "admin_001", name: "Admin User", email: "admin@example.test", role: "admin" }
];

const cases = [
  { case_id: "CASE-A", owner_user_id: "therapist_a", anonymized_child_code: "CHI-A", display_label: "Case A", age_months: 48, sex: "not_specified", latest_score: 0.4, score_trend: [], support_level: "Needs review", anonymization_status: "anonymized", external_clinical_status: "not_provided", primary_concerns: "" },
  { case_id: "CASE-B", owner_user_id: "therapist_b", anonymized_child_code: "CHI-B", display_label: "Case B", age_months: 52, sex: "not_specified", latest_score: 0.5, score_trend: [], support_level: "Needs review", anonymization_status: "anonymized", external_clinical_status: "not_provided", primary_concerns: "" },
  { case_id: "CASE-C", owner_user_id: "clinician_a", anonymized_child_code: "CHI-C", display_label: "Case C", age_months: 56, sex: "not_specified", latest_score: 0.6, score_trend: [], support_level: "Needs review", anonymization_status: "anonymized", external_clinical_status: "not_provided", primary_concerns: "" }
];

const sessions = [
  { session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a", session_date: "2026-05-20", session_type: "free_play", processing_status: "not_started" },
  { session_id: "SESSION-B", case_id: "CASE-B", owner_user_id: "therapist_b", session_date: "2026-05-21", session_type: "free_play", processing_status: "not_started" },
  { session_id: "SESSION-C", case_id: "CASE-C", owner_user_id: "clinician_a", session_date: "2026-05-22", session_type: "free_play", processing_status: "not_started" }
];

function resetAuthState(overrides = {}) {
  store.persistenceAdapter = null;
  store.setState({
    currentUser: null,
    authError: "",
    dataMode: "mock",
    persistenceStatus: "mock_ready",
    users,
    cases,
    sessions,
    selectedCaseId: "CASE-A",
    selectedSessionId: "SESSION-A",
    audioFiles: [],
    transcripts: {},
    transcriptLines: {},
    extractedFeatureOutputs: {},
    aiDecisionOutputs: {},
    goals: [],
    notes: [],
    generatedReports: [],
    auditLogs: [{ audit_id: "AUDIT-001", actor_user_id: "therapist_a", target_type: "ChildCase", target_id: "CASE-A", event_type: "view", message: "Viewed case", created_at: "2026-05-20T10:00:00Z" }],
    ...overrides
  });
}

describe("auth adapter and RBAC", () => {
  beforeEach(() => {
    resetAuthState();
  });

  it("supports mock sign-in, getCurrentUser, getUserRole, and sign-out", () => {
    const user = signIn("therapist-a@example.test", "demo-password");

    expect(user.user_id).toBe("therapist_a");
    expect(getCurrentUser().user_id).toBe("therapist_a");
    expect(getUserRole()).toBe("therapist");

    signOut();
    expect(getCurrentUser()).toBeNull();
  });

  it("fails closed in provider placeholder mode", () => {
    const adapter = createAuthAdapter({ mode: "provider_placeholder" });
    const result = adapter.signIn("therapist-a@example.test", "demo-password", users);

    expect(result.user).toBeNull();
    expect(result.error).toBe(PROVIDER_NOT_CONFIGURED_MESSAGE);
  });

  it("blocks unauthenticated users from case and session access", () => {
    expect(getVisibleCases()).toEqual([]);
    expect(getVisibleSessions()).toEqual([]);
    expect(() => requireAuth()).toThrow("Please sign in");
  });

  it("prevents therapist cross-case and cross-session leakage", () => {
    store.setState({ currentUser: users[0] });

    expect(getVisibleCases().map(item => item.case_id)).toEqual(["CASE-A"]);
    expect(getVisibleSessions().map(item => item.session_id)).toEqual(["SESSION-A"]);
  });

  it("prevents clinician cross-user access by default", () => {
    store.setState({ currentUser: users[2] });

    expect(getVisibleCases().map(item => item.case_id)).toEqual(["CASE-C"]);
    expect(getVisibleSessions().map(item => item.session_id)).toEqual(["SESSION-C"]);
  });

  it("allows admin users to view all demo cases, sessions, and audit logs", () => {
    store.setState({ currentUser: users[3] });

    expect(getVisibleCases().map(item => item.case_id)).toEqual(["CASE-A", "CASE-B", "CASE-C"]);
    expect(getVisibleSessions().map(item => item.session_id)).toEqual(["SESSION-A", "SESSION-B", "SESSION-C"]);
    expect(renderAuditLogs()).toContain("Audit Logs");
    expect(renderAuditLogs()).not.toContain("Access denied");
  });

  it("shows access denied for unauthorized selected cases and audit logs", () => {
    store.setState({ currentUser: users[0], selectedCaseId: "CASE-B" });

    expect(renderDashboard()).toContain("Access denied: this case is not assigned to your account.");
    expect(renderAuditLogs()).toContain("audit logs are available to admin users only");
  });

  it("displays current role, data mode, and auth mode in settings", () => {
    store.setState({ currentUser: users[2], dataMode: "localStorage" });
    const html = renderSettings();

    expect(html).toContain("Clinician A");
    expect(html).toContain("clinician");
    expect(html).toContain("localStorage");
    expect(html).toContain("mock");
  });
});
