import { describe, expect, it, vi } from "vitest";
import { createAuthAdapter } from "../services/auth-adapter.js";
import { createAuthSessionStore } from "../services/auth-session-store.js";
import { createLocalDevAuthProvider } from "../services/providers/local-dev-auth-provider.js";

function createMemoryStorage() {
  const data = new Map();
  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null;
    },
    setItem(key, value) {
      data.set(key, value);
    },
    removeItem(key) {
      data.delete(key);
    }
  };
}

const users = [
  { user_id: "therapist_a", name: "Therapist A", email: "therapist-a@example.test", role: "therapist" }
];

describe("auth session persistence", () => {
  it("persists and restores mock sessions without changing mock sign-in behavior", () => {
    const sessionStore = createAuthSessionStore({ storage: createMemoryStorage() });
    const adapter = createAuthAdapter({ mode: "mock", sessionStore });

    const result = adapter.signIn("therapist-a@example.test", "demo-password", users);
    const restored = adapter.restoreSession(users);

    expect(result.user.user_id).toBe("therapist_a");
    expect(restored.user.user_id).toBe("therapist_a");
    expect(restored.session.mode).toBe("mock");
  });

  it("clears stored sessions on sign-out", () => {
    const sessionStore = createAuthSessionStore({ storage: createMemoryStorage() });
    const adapter = createAuthAdapter({ mode: "mock", sessionStore });

    adapter.signIn("therapist-a@example.test", "demo-password", users);
    adapter.signOut();

    expect(adapter.restoreSession(users).user).toBeNull();
  });

  it("registers mock users without depending on the global app store", () => {
    const sessionStore = createAuthSessionStore({ storage: createMemoryStorage() });
    const adapter = createAuthAdapter({ mode: "mock", sessionStore });

    const result = adapter.signUp(
      "new-therapist@example.test",
      "secure-demo-password",
      "New Therapist",
      "therapist",
      "Speech Clinic",
      users
    );
    const duplicate = adapter.signUp(
      "therapist-a@example.test",
      "secure-demo-password",
      "Duplicate Therapist",
      "therapist",
      "Speech Clinic",
      users
    );

    expect(result.user.email).toBe("new-therapist@example.test");
    expect(result.user.organization).toBe("Speech Clinic");
    expect(duplicate.user).toBeNull();
    expect(duplicate.error).toContain("already exists");
  });
});

describe("local_dev auth provider", () => {
  it("uses the backend auth/session and me contract", async () => {
    const sessionStore = createAuthSessionStore({ storage: createMemoryStorage() });
    const fetchImpl = vi.fn(async (url, options) => {
      if (url.endsWith("/api/auth/session")) {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({
            user: users[0],
            session_token: "therapist_a",
            token_type: "mock-user-id"
          })
        };
      }
      if (url.endsWith("/api/me")) {
        expect(options.headers["X-User-Id"]).toBe("therapist_a");
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ user: users[0] })
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });
    const provider = createLocalDevAuthProvider({
      apiBaseUrl: "http://localhost:8000",
      fetchImpl,
      sessionStore
    });

    const signIn = await provider.signIn("therapist-a@example.test", "demo-password");
    const restored = await provider.restoreSession(signIn.session);

    expect(signIn.user.user_id).toBe("therapist_a");
    expect(restored.user.user_id).toBe("therapist_a");
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });
});
