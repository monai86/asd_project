import { store } from "../store/state.js";
import { createSession } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { getVisibleCases } from "./case-service.js";
import { assertCanAccessSession, canAccessSession, requireAuth } from "./auth-service.js";
import { createActiveClinicalRepository, isRemoteDataMode } from "../persistence/active-repository.js";

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

  if (isRemoteDataMode(store.getState().dataMode)) {
    const repository = createActiveClinicalRepository(store.getState().dataMode);
    return repository.createSession({ case_id, session_date, session_type, notes }).then(createdSession => {
      const formattedSession = createSession({
        ...createdSession,
        owner_user_id: targetCase.owner_user_id
      });
      const { sessions: currentSessions } = store.getState();
      store.setState({
        sessions: [...currentSessions, formattedSession],
        selectedSessionId: formattedSession.session_id,
        activeView: "session"
      });
      addAudit("create_session", "Session", formattedSession.session_id, `Created session ${formattedSession.session_id} for case ${case_id}`);
      return formattedSession;
    });
  }

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

  if (isRemoteDataMode(store.getState().dataMode) && updates && "notes" in updates) {
    const repository = createActiveClinicalRepository(store.getState().dataMode);
    return repository.patchSession(sessionId, { notes: updates.notes }).then(patchedSession => {
      const { sessions: currentSessions } = store.getState();
      const existingSession = currentSessions.find(s => s.session_id === sessionId) || {};
      const updatedSession = {
        ...existingSession,
        ...patchedSession,
        updated_at: new Date().toISOString()
      };
      const updatedSessions = currentSessions.map(s => s.session_id === sessionId ? updatedSession : s);
      store.setState({ sessions: updatedSessions });
      return updatedSession;
    });
  }

  const updatedSession = {
    ...targetSession,
    ...updates,
    updated_at: new Date().toISOString()
  };
  const updated = sessions.map(s => {
    if (s.session_id === sessionId) {
      return updatedSession;
    }
    return s;
  });
  store.setState({ sessions: updated });
  return updatedSession;
}
