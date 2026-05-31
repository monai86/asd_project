import { createApiClient } from "../api-client.js";

export function createLocalDevAuthProvider({
  apiBaseUrl = "",
  fetchImpl = null,
  sessionStore = null
} = {}) {
  const client = createApiClient({ baseUrl: apiBaseUrl, fetchImpl });

  return {
    async signIn(email, password) {
      const payload = await client.post("/api/auth/session", { email, password });
      const session = {
        mode: "local_dev",
        session_token: payload.session_token,
        token_type: payload.token_type || "mock-user-id",
        user: payload.user
      };
      sessionStore?.save(session);
      return { user: payload.user, session, error: "" };
    },

    async restoreSession(session) {
      if (!session?.session_token) return { user: null, session: null, error: "" };
      const restoreClient = createApiClient({
        baseUrl: apiBaseUrl,
        fetchImpl,
        defaultHeaders: { "X-User-Id": session.session_token }
      });
      const payload = await restoreClient.get("/api/me");
      const restored = { ...session, user: payload.user };
      sessionStore?.save(restored);
      return { user: payload.user, session: restored, error: "" };
    },

    signOut() {
      sessionStore?.clear();
      return { user: null, error: "" };
    }
  };
}
