import { AUTH_MODE, normalizeAuthMode } from "../constants.js";

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

export function createAuthAdapter({ mode = AUTH_MODE } = {}) {
  const selectedMode = normalizeAuthMode(mode);

  return {
    mode: selectedMode,

    signIn(email, password, users = []) {
      if (selectedMode === "provider_placeholder") {
        return { user: null, error: PROVIDER_NOT_CONFIGURED_MESSAGE };
      }

      const normalizedEmail = normalizeEmail(email);
      const user = users.find(item => item.email?.toLowerCase() === normalizedEmail && password === "demo-password");
      if (!user) {
        return { user: null, error: "Demo login failed. Use one of the sample accounts." };
      }

      return {
        user: {
          ...user,
          last_login: new Date().toISOString()
        },
        error: ""
      };
    },

    signOut() {
      return { user: null, error: "" };
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
