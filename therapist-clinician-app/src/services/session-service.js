import { store } from "../store/state.js";
import { createSession } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { getVisibleCases } from "./case-service.js";

export function getVisibleSessions() {
  const { sessions } = store.getState();
  const visibleCases = getVisibleCases();
  const visibleCaseIds = new Set(visibleCases.map(c => c.case_id));
  return sessions.filter(s => visibleCaseIds.has(s.case_id));
}

export function getCaseSessions(caseId) {
  return getVisibleSessions().filter(s => s.case_id === caseId);
}

export function createNewSession({ case_id, session_date, session_type, notes }) {
  const { currentUser, sessions } = store.getState();
  if (!currentUser) throw new Error("Authentication required");

  const sessionId = `SESSION-${String(sessions.length + 1).padStart(3, "0")}`;
  const newSession = createSession({
    session_id: sessionId,
    case_id,
    owner_user_id: currentUser.user_id,
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
  const { sessions } = store.getState();
  const updated = sessions.map(s => {
    if (s.session_id === sessionId) {
      return { ...s, ...updates, updated_at: new Date().toISOString() };
    }
    return s;
  });
  store.setState({ sessions: updated });
}
