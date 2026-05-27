import { store } from "../store/state.js";
import { addAudit } from "./audit-service.js";
import {
  authAdapter,
  AccessDeniedError,
  ACCESS_DENIED_MESSAGE
} from "./auth-adapter.js";

export function signIn(email, password) {
  const result = authAdapter.signIn(email, password, store.getState().users);
  const user = result.user;
  if (user) {
    store.setState({ currentUser: user, authError: "" });
    addAudit("login_success", "User", user.user_id, `User ${user.name} logged in successfully.`);
    return user;
  }
  store.setState({ authError: result.error });
  addAudit("login_failed", "User", "anonymous", `Login attempt failed for email: ${email}`);
  return null;
}

export function signOut() {
  const user = store.getState().currentUser;
  if (user) {
    addAudit("logout", "User", user.user_id, `User ${user.name} logged out.`);
  }
  authAdapter.signOut();
  store.setState({ currentUser: null, authError: "" });
}

export function getCurrentUser() {
  return authAdapter.getCurrentUser(store.getState());
}

export function getUserRole(user = getCurrentUser()) {
  return authAdapter.getUserRole(user);
}

export function requireAuth() {
  return authAdapter.requireAuth(getCurrentUser());
}

export function canAccessCase(user, childCase) {
  return authAdapter.canAccessCase(user, childCase);
}

export function canAccessSession(user, session) {
  return authAdapter.canAccessSession(user, session);
}

export function canViewAuditLogs(user = getCurrentUser()) {
  return authAdapter.canViewAuditLogs(user);
}

export function assertCanAccessCase(user, childCase) {
  if (!canAccessCase(user, childCase)) {
    throw new AccessDeniedError(ACCESS_DENIED_MESSAGE);
  }
  return childCase;
}

export function assertCanAccessSession(user, session) {
  if (!canAccessSession(user, session)) {
    throw new AccessDeniedError("Access denied: this session is not assigned to your account.");
  }
  return session;
}

export const login = signIn;
export const logout = signOut;
