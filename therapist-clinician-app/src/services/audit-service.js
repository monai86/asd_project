import { store } from "../store/state.js";

export function addAudit(event_type, target_type, target_id, message) {
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
