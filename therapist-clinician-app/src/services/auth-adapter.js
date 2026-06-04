import { AUTH_API_BASE_URL, AUTH_MODE, normalizeAuthMode } from "../constants.js";
import { authSessionStore } from "./auth-session-store.js";
import { createLocalDevAuthProvider } from "./providers/local-dev-auth-provider.js";
import { createSupabaseAuthProvider } from "./providers/supabase-auth-provider.js";

export const ACCESS_DENIED_MESSAGE = "Access denied: this case is not assigned to your account.";
export const AUTH_REQUIRED_MESSAGE = "Please sign in to access this clinical workspace.";
export const PROVIDER_NOT_CONFIGURED_MESSAGE =
  "Authentication provider not configured yet. Use AUTH_MODE=mock for demo sign-in.";

export class AuthRequiredError extends Error {
  constructor(message = AUTH_REQUIRED_MESSAGE) {
    super(message);
    this.name = "AuthRequiredError";
  }
}

export class AccessDeniedError extends Error {
  constructor(message = ACCESS_DENIED_MESSAGE) {
    super(message);
    this.name = "AccessDeniedError";
  }
}

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

export function createAuthAdapter({
  mode = AUTH_MODE,
  sessionStore = authSessionStore,
  localDevProvider: configuredLocalDevProvider = null,
  supabaseProvider: configuredSupabaseProvider = null,
  supabaseClient = null,
  apiBaseUrl = AUTH_API_BASE_URL,
  fetchImpl = null
} = {}) {
  const selectedMode = normalizeAuthMode(mode);
  const activeLocalDevProvider =
    configuredLocalDevProvider ||
    createLocalDevAuthProvider({
      apiBaseUrl,
      fetchImpl,
      sessionStore
    });
  const activeSupabaseProvider =
    configuredSupabaseProvider ||
    createSupabaseAuthProvider({
      client: supabaseClient,
      sessionStore
    });

  return {
    mode: selectedMode,

    signIn(email, password, users = []) {
      if (selectedMode === "local_dev") {
        return activeLocalDevProvider.signIn(email, password).catch(error => ({
          user: null,
          error: error.message || PROVIDER_NOT_CONFIGURED_MESSAGE
        }));
      }
      if (selectedMode === "supabase") {
        return activeSupabaseProvider.signIn(email, password).catch(error => ({
          user: null,
          error: error.message || PROVIDER_NOT_CONFIGURED_MESSAGE
        }));
      }
      if (selectedMode !== "mock") {
        return { user: null, error: PROVIDER_NOT_CONFIGURED_MESSAGE };
      }

      const normalizedEmail = normalizeEmail(email);
      // Allow custom-registered mock users as well as default ones
      const user = users.find(item => item.email?.toLowerCase() === normalizedEmail && (password === "demo-password" || item.password === password));
      if (!user) {
        return { user: null, error: "Demo login failed. Check email or use a sample account." };
      }

      const session = {
        mode: "mock",
        session_token: user.user_id,
        token_type: "mock-user-id",
        user: {
          ...user,
          last_login: new Date().toISOString()
        }
      };
      sessionStore.save(session);
      return {
        user: session.user,
        session,
        error: ""
      };
    },

    signUp(email, password, name, role, organization, users = []) {
      if (selectedMode === "supabase") {
        return activeSupabaseProvider.signUp(email, password, name, role, organization).catch(error => ({
          user: null,
          error: error.message || PROVIDER_NOT_CONFIGURED_MESSAGE
        }));
      }
      
      const normalizedEmail = normalizeEmail(email);
      if (users.some(u => u.email?.toLowerCase() === normalizedEmail)) {
        return { user: null, error: "User already exists." };
      }

      const newUser = {
        user_id: "mock-user-" + Math.random().toString(36).substr(2, 9),
        email: normalizedEmail,
        name: name || "Clinical User",
        role: role || "therapist",
        password: password, // Store for mock verification
        organization: organization || "Speech Workspace",
        credentials: role === "admin" ? "Systems Administrator" : (role === "clinician" ? "MD Clinician" : "Certified Speech Therapist"),
        last_login: new Date().toISOString()
      };

      return { user: newUser, error: "" };
    },

    signOut() {
      if (selectedMode === "supabase") return activeSupabaseProvider.signOut();
      if (selectedMode === "local_dev") return activeLocalDevProvider.signOut();
      sessionStore.clear();
      return { user: null, error: "" };
    },

    restoreSession(users = []) {
      const session = sessionStore.load();
      if (!session || session.mode !== selectedMode) return { user: null, session: null, error: "" };
      if (selectedMode === "mock") {
        const user = users.find(item => item.user_id === session.user?.user_id || item.user_id === session.session_token);
        if (!user) {
          sessionStore.clear();
          return { user: null, session: null, error: "" };
        }
        const restored = {
          ...session,
          user: {
            ...user,
            last_login: session.user?.last_login || new Date().toISOString()
          }
        };
        sessionStore.save(restored);
        return { user: restored.user, session: restored, error: "" };
      }
      if (selectedMode === "local_dev") {
        return activeLocalDevProvider.restoreSession(session).catch(error => ({
          user: null,
          session: null,
          error: error.message || "Session restore failed."
        }));
      }
      if (selectedMode === "supabase") {
        return activeSupabaseProvider.restoreSession(session).catch(error => ({
          user: null,
          session: null,
          error: error.message || "Session restore failed."
        }));
      }
      return { user: null, session: null, error: "" };
    },

    getCurrentUser(state) {
      return state?.currentUser || null;
    },

    getUserRole(user) {
      return user?.role || null;
    },

    requireAuth(user) {
      if (!user) throw new AuthRequiredError();
      return user;
    },

    canAccessCase(user, childCase) {
      if (!user || !childCase) return false;
      if (user.role === "admin") return true;
      return childCase.owner_user_id === user.user_id;
    },

    canAccessSession(user, session) {
      if (!user || !session) return false;
      if (user.role === "admin") return true;
      return session.owner_user_id === user.user_id;
    },

    canViewAuditLogs(user) {
      return user?.role === "admin";
    }
  };
}

export const authAdapter = createAuthAdapter();
