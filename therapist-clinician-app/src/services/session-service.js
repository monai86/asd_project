import { store } from "../store/state.js";
import { createSession } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { getVisibleCases } from "./case-service.js";
import { assertCanAccessSession, canAccessSession, requireAuth } from "./auth-service.js";

export function getVisibleSessions() {
  const { currentUser, sessions } = store.getState();
  return sessions.filter(s => canAccessSession(currentUser, s));
}

export function getCaseSessions(caseId) {
  return getVisibleSessions().filter(s => s.case_id === caseId);
}

export function createNewSession({ case_id, session_date, session_type, notes }) {
  const { currentUser, sessions } = store.getState();
  requireAuth();
  const targetCase = getVisibleCases().find(c => c.case_id === case_id);
  if (!targetCase) throw new Error("Access denied: this case is not assigned to your account.");

  const sessionId = `SESSION-${String(sessions.length + 1).padStart(3, "0")}`;
  const newSession = createSession({
    session_id: sessionId,
    case_id,
    owner_user_id: targetCase.owner_user_id,
    session_date,
    session_type,
    notes,
    processing_status: "not_started"
  });

  store.setState({
    sessions: [...sessions, newSession],
    selectedSessionId: sessionId,
    activeView: "session"
  });

  addAudit("create_session", "Session", sessionId, `Created session ${sessionId} for case ${case_id}`);
  return newSession;
}

export function updateSessionStatus(sessionId, updates) {
  const { currentUser, sessions } = store.getState();
  const targetSession = sessions.find(s => s.session_id === sessionId);
  if (!targetSession) return;
  assertCanAccessSession(currentUser, targetSession);
  const updated = sessions.map(s => {
    if (s.session_id === sessionId) {
      return { ...s, ...updates, updated_at: new Date().toISOString() };
    }
    return s;
  });
  store.setState({ sessions: updated });
}
