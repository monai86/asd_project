import { store } from "../store/state.js";
import { addAudit } from "./audit-service.js";
import {
  authAdapter,
  AccessDeniedError,
  ACCESS_DENIED_MESSAGE
} from "./auth-adapter.js";
import { stateFromSnapshot } from "../persistence/repository.js";
import { createActiveClinicalRepository, isRemoteDataMode } from "../persistence/active-repository.js";

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
    if (isRemoteDataMode(store.getState().dataMode)) {
      const repository = createActiveClinicalRepository(store.getState().dataMode);
      return repository.hydrate().then(snapshot => {
        const stateUpdates = stateFromSnapshot(snapshot);
        store.setState(stateUpdates);
        addAudit("login_success", "User", user.user_id, `User ${user.name} logged in successfully.`);
        return user;
      }).catch(err => {
        authAdapter.signOut();
        store.setState({
          currentUser: null,
          authSession: null,
          authStatus: "signed_out",
          authError: `Failed to load backend data: ${err.message || err}`
        });
        addAudit("login_failed", "User", "anonymous", `Login hydration failed for user ${user.name}: ${err.message || err}`);
        throw err;
      });
    }
    addAudit("login_success", "User", user.user_id, `User ${user.name} logged in successfully.`);
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
    if (isRemoteDataMode(store.getState().dataMode)) {
      const repository = createActiveClinicalRepository(store.getState().dataMode);
      return repository.hydrate().then(snapshot => {
        const stateUpdates = stateFromSnapshot(snapshot);
        store.setState(stateUpdates);
        return result.user;
      }).catch(err => {
        authAdapter.signOut();
        store.setState({
          currentUser: null,
          authSession: null,
          authStatus: "signed_out",
          authError: `Failed to load backend data: ${err.message || err}`
        });
        throw err;
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
    throw new AccessDeniedError(ACCESS_DENIED_MESSAGE);
  }
  return session;
}

export function signUp(email, password, name, role, organization) {
  const result = authAdapter.signUp(email, password, name, role, organization, store.getState().users);
  if (result && typeof result.then === "function") {
    store.setState({ authStatus: "signing_up", authError: "" });
    return result.then(resolved => applySignUpResult(resolved, email));
  }
  return applySignUpResult(result, email);
}

function applySignUpResult(result, email) {
  if (result && result.user) {
    const users = store.getState().users || [];
    const exists = users.some(user => user.user_id === result.user.user_id || user.email?.toLowerCase() === result.user.email?.toLowerCase());
    store.setState({ authError: "", authStatus: "signed_out" });
    if (!exists) {
      store.setState({ users: [...users, result.user] });
    }
    addAudit("registration_success", "User", result.user.user_id, `User ${result.user.name} registered successfully.`);
    return result.user;
  }
  const errorMsg = result?.error || "Registration failed.";
  store.setState({ authError: errorMsg, authStatus: "signed_out" });
  addAudit("registration_failed", "User", "anonymous", `Registration failed for email ${email}: ${errorMsg}`);
  return null;
}

export const login = signIn;
export const logout = signOut;
