import { store } from "../store/state.js";
import { mockUsers } from "../store/mock-data.js";

export function login(email, password) {
  const user = mockUsers.find(u => u.email === email && password === "demo-password");
  if (user) {
    const updatedUser = { ...user, last_login: new Date().toISOString() };
    store.setState({ currentUser: updatedUser });
    addAuditLog("login_success", "User", user.user_id, `User ${user.name} logged in successfully.`);
    return updatedUser;
  }
  addAuditLog("login_failed", "User", "anonymous", `Login attempt failed for email: ${email}`);
  return null;
}

export function logout() {
  const user = store.getState().currentUser;
  if (user) {
    addAuditLog("logout", "User", user.user_id, `User ${user.name} logged out.`);
  }
  store.setState({ currentUser: null });
}

function addAuditLog(event_type, target_type, target_id, message) {
  const state = store.getState();
  const newLog = {
    audit_id: `AUDIT-${String(state.auditLogs.length + 1).padStart(4, "0")}`,
    event_type,
    actor_user_id: state.currentUser ? state.currentUser.user_id : "anonymous",
    target_type,
    target_id,
    message,
    created_at: new Date().toISOString()
  };
  store.setState({ auditLogs: [newLog, ...state.auditLogs] });
}
