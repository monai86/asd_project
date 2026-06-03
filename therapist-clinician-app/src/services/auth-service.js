import { store } from "../store/state.js";
import { addAudit } from "./audit-service.js";
import {
  authAdapter,
  AccessDeniedError,
  ACCESS_DENIED_MESSAGE
} from "./auth-adapter.js";
import { api } from "./api-client.js";
import { createApiRepository } from "../persistence/api-repository.js";
import { stateFromSnapshot } from "../persistence/repository.js";

export function signIn(email, password) {
  const result = authAdapter.signIn(email, password, store.getState().users);
  if (result && typeof result.then === "function") {
    store.setState({ authStatus: "signing_in", authError: "" });
    return result.then(resolved => applySignInResult(resolved, email));
  }
  return applySignInResult(result, email);
}

function applySignInResult(result, email) {
  const user = result.user;
  if (user) {
    store.setState({
      currentUser: user,
      authSession: result.session || null,
      authStatus: "signed_in",
      authError: ""
    });
    addAudit("login_success", "User", user.user_id, `User ${user.name} logged in successfully.`);
    if (store.getState().dataMode === "api") {
      const apiRepository = createApiRepository({ apiClient: api });
      return apiRepository.hydrate().then(snapshot => {
        const stateUpdates = stateFromSnapshot(snapshot);
        store.setState(stateUpdates);
        return user;
      });
    }
    return user;
  }
  store.setState({ authStatus: "signed_out", authError: result.error });
  addAudit("login_failed", "User", "anonymous", `Login attempt failed for email: ${email}`);
  return null;
}

export function signOut() {
  const user = store.getState().currentUser;
  if (user) {
    addAudit("logout", "User", user.user_id, `User ${user.name} logged out.`);
  }
  authAdapter.signOut();
  store.setState({ currentUser: null, authSession: null, authStatus: "signed_out", authError: "" });
}

export function restoreAuthSession() {
  const result = authAdapter.restoreSession(store.getState().users);
  if (result && typeof result.then === "function") {
    store.setState({ authStatus: "restoring", authError: "" });
    return result.then(applyRestoreResult);
  }
  return applyRestoreResult(result);
}

function applyRestoreResult(result) {
  if (result?.user) {
    store.setState({
      currentUser: result.user,
      authSession: result.session || null,
      authStatus: "signed_in",
      authError: ""
    });
    if (store.getState().dataMode === "api") {
      const apiRepository = createApiRepository({ apiClient: api });
      return apiRepository.hydrate().then(snapshot => {
        const stateUpdates = stateFromSnapshot(snapshot);
        store.setState(stateUpdates);
        return result.user;
      });
    }
    return result.user;
  }
  store.setState({
    currentUser: null,
    authSession: null,
    authStatus: "signed_out",
    authError: result?.error || ""
  });
  return null;
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
