import { beforeEach, describe, expect, it, vi, afterEach } from "vitest";
import { store } from "../store/state.js";
import { signIn, restoreAuthSession } from "../services/auth-service.js";
import { api } from "../services/api-client.js";
import { authSessionStore } from "../services/auth-session-store.js";

const testUsers = [
  { user_id: "therapist_a", name: "Therapist A", email: "therapist-a@example.test", role: "therapist" }
];

describe("auth API hydration on login/restore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    store.setState({
      currentUser: null,
      authError: "",
      dataMode: "mock",
      users: testUsers,
      cases: [],
      sessions: [],
      auditLogs: []
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("when dataMode is 'api', signing in returns a Promise and hydrates backend data", async () => {
    store.setState({ dataMode: "api" });

    const getSpy = vi.spyOn(api, "get").mockImplementation(async (path) => {
      if (path === "/api/me") return { user: { user_id: "therapist_a", name: "Therapist A", role: "therapist" } };
      if (path === "/api/cases") return [{ case_id: "CASE-API-1", owner_user_id: "therapist_a", display_label: "API Case" }];
      if (path === "/api/sessions") return [{ session_id: "SESSION-API-1", case_id: "CASE-API-1", owner_user_id: "therapist_a" }];
      if (path === "/api/audit-logs") return [{ audit_id: "AUDIT-API-1", actor_user_id: "therapist_a", event_type: "api_view" }];
      return [];
    });

    const result = signIn("therapist-a@example.test", "demo-password");
    
    expect(result).toBeInstanceOf(Promise);

    const user = await result;
    expect(user.user_id).toBe("therapist_a");

    expect(getSpy).toHaveBeenCalledWith("/api/me");
    expect(getSpy).toHaveBeenCalledWith("/api/cases");
    expect(getSpy).toHaveBeenCalledWith("/api/sessions");
    expect(getSpy).toHaveBeenCalledWith("/api/audit-logs");

    const state = store.getState();
    expect(state.currentUser.user_id).toBe("therapist_a");
    expect(state.cases).toEqual([{ case_id: "CASE-API-1", owner_user_id: "therapist_a", display_label: "API Case" }]);
    expect(state.sessions).toEqual([{ session_id: "SESSION-API-1", case_id: "CASE-API-1", owner_user_id: "therapist_a" }]);
    expect(state.auditLogs).toEqual([{ audit_id: "AUDIT-API-1", actor_user_id: "therapist_a", event_type: "api_view" }]);
  });

  it("when dataMode is 'api', restoring session returns a Promise and hydrates backend data", async () => {
    store.setState({ dataMode: "api" });

    const mockSession = {
      mode: "mock",
      session_token: "therapist_a",
      token_type: "mock-user-id",
      user: {
        user_id: "therapist_a",
        name: "Therapist A",
        email: "therapist-a@example.test",
        role: "therapist",
        last_login: new Date().toISOString()
      }
    };
    vi.spyOn(authSessionStore, "load").mockReturnValue(mockSession);

    const getSpy = vi.spyOn(api, "get").mockImplementation(async (path) => {
      if (path === "/api/me") return { user: { user_id: "therapist_a", name: "Therapist A", role: "therapist" } };
      if (path === "/api/cases") return [{ case_id: "CASE-API-1", owner_user_id: "therapist_a", display_label: "API Case" }];
      if (path === "/api/sessions") return [{ session_id: "SESSION-API-1", case_id: "CASE-API-1", owner_user_id: "therapist_a" }];
      if (path === "/api/audit-logs") return [{ audit_id: "AUDIT-API-1", actor_user_id: "therapist_a", event_type: "api_view" }];
      return [];
    });

    const result = restoreAuthSession();
    
    expect(result).toBeInstanceOf(Promise);

    const user = await result;
    expect(user.user_id).toBe("therapist_a");

    expect(getSpy).toHaveBeenCalledWith("/api/me");
    expect(getSpy).toHaveBeenCalledWith("/api/cases");
    expect(getSpy).toHaveBeenCalledWith("/api/sessions");
    expect(getSpy).toHaveBeenCalledWith("/api/audit-logs");

    const state = store.getState();
    expect(state.currentUser.user_id).toBe("therapist_a");
    expect(state.cases).toEqual([{ case_id: "CASE-API-1", owner_user_id: "therapist_a", display_label: "API Case" }]);
    expect(state.sessions).toEqual([{ session_id: "SESSION-API-1", case_id: "CASE-API-1", owner_user_id: "therapist_a" }]);
    expect(state.auditLogs).toEqual([{ audit_id: "AUDIT-API-1", actor_user_id: "therapist_a", event_type: "api_view" }]);
  });

  it("when dataMode is not 'api', signing in remains synchronous and does not call backend data", () => {
    store.setState({ dataMode: "mock" });

    const getSpy = vi.spyOn(api, "get");

    const result = signIn("therapist-a@example.test", "demo-password");
    
    expect(result).not.toBeInstanceOf(Promise);
    expect(result.user_id).toBe("therapist_a");

    expect(getSpy).not.toHaveBeenCalled();

    const state = store.getState();
    expect(state.currentUser.user_id).toBe("therapist_a");
    expect(state.cases).toEqual([]);
    expect(state.sessions).toEqual([]);
  });

  it("when dataMode is not 'api', restoring session remains synchronous and does not call backend data", () => {
    store.setState({ dataMode: "mock" });

    const mockSession = {
      mode: "mock",
      session_token: "therapist_a",
      token_type: "mock-user-id",
      user: {
        user_id: "therapist_a",
        name: "Therapist A",
        email: "therapist-a@example.test",
        role: "therapist",
        last_login: new Date().toISOString()
      }
    };
    vi.spyOn(authSessionStore, "load").mockReturnValue(mockSession);

    const getSpy = vi.spyOn(api, "get");

    const result = restoreAuthSession();
    
    expect(result).not.toBeInstanceOf(Promise);
    expect(result.user_id).toBe("therapist_a");

    expect(getSpy).not.toHaveBeenCalled();

    const state = store.getState();
    expect(state.currentUser.user_id).toBe("therapist_a");
    expect(state.cases).toEqual([]);
    expect(state.sessions).toEqual([]);
  });

  it("when dataMode is 'api' and hydration fails during signing in, the state rolls back to signed_out and propagates error", async () => {
    store.setState({ dataMode: "api" });

    const errorMsg = "Database offline";
    const getSpy = vi.spyOn(api, "get").mockRejectedValue(new Error(errorMsg));

    const result = signIn("therapist-a@example.test", "demo-password");
    
    expect(result).toBeInstanceOf(Promise);

    await expect(result).rejects.toThrow(errorMsg);

    const state = store.getState();
    expect(state.currentUser).toBeNull();
    expect(state.authSession).toBeNull();
    expect(state.authStatus).toBe("signed_out");
    expect(state.authError).toContain(`Failed to load backend data: ${errorMsg}`);
  });

  it("when dataMode is 'api' and hydration fails during session restore, the state rolls back to signed_out and propagates error", async () => {
    store.setState({ dataMode: "api" });

    const mockSession = {
      mode: "mock",
      session_token: "therapist_a",
      token_type: "mock-user-id",
      user: {
        user_id: "therapist_a",
        name: "Therapist A",
        email: "therapist-a@example.test",
        role: "therapist",
        last_login: new Date().toISOString()
      }
    };
    vi.spyOn(authSessionStore, "load").mockReturnValue(mockSession);

    const errorMsg = "Network timeout";
    const getSpy = vi.spyOn(api, "get").mockRejectedValue(new Error(errorMsg));

    const result = restoreAuthSession();
    
    expect(result).toBeInstanceOf(Promise);

    await expect(result).rejects.toThrow(errorMsg);

    const state = store.getState();
    expect(state.currentUser).toBeNull();
    expect(state.authSession).toBeNull();
    expect(state.authStatus).toBe("signed_out");
    expect(state.authError).toContain(`Failed to load backend data: ${errorMsg}`);
  });
});
