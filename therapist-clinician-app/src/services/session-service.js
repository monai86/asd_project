import { store } from "../store/state.js";
import { createSession } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { getVisibleCases } from "./case-service.js";
import { assertCanAccessSession, canAccessSession, requireAuth } from "./auth-service.js";
import { createActiveClinicalRepository, isRemoteDataMode } from "../persistence/active-repository.js";

function withoutKey(map = {}, key) {
  const { [key]: _removed, ...rest } = map || {};
  return rest;
}

function nextLocalSessionId(sessions) {
  const numericIds = sessions
    .map(s => {
      const match = String(s.session_id || "").match(/^SESSION-(\d+)$/i);
      return match ? parseInt(match[1], 10) : 0;
    })
    .filter(val => Number.isFinite(val) && val > 0);
  const nextNum = numericIds.length > 0 ? Math.max(...numericIds) + 1 : 1;
  return `SESSION-${String(nextNum).padStart(3, "0")}`;
}

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

  const sessionId = nextLocalSessionId(sessions);
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

export function deleteSession(sessionId) {
  const { currentUser, sessions } = store.getState();
  requireAuth();
  const targetSession = sessions.find(s => s.session_id === sessionId);
  if (!targetSession) throw new Error("Session not found");
  assertCanAccessSession(currentUser, targetSession);

  if (isRemoteDataMode(store.getState().dataMode)) {
    const repository = createActiveClinicalRepository(store.getState().dataMode);
    if (typeof repository.deleteSession !== "function") {
      throw new Error("The active repository does not support deleting sessions.");
    }
    return repository.deleteSession(sessionId).then(() => {
      const deleted = removeSessionFromStore(sessionId);
      addAudit("delete_session", "Session", sessionId, `Deleted session ${sessionId} for case ${targetSession.case_id}`);
      return deleted;
    });
  }

  const deleted = removeSessionFromStore(sessionId);
  addAudit("delete_session", "Session", sessionId, `Deleted session ${sessionId} for case ${targetSession.case_id}`);
  return deleted;
}

function removeSessionFromStore(sessionId) {
  const state = store.getState();
  const targetSession = state.sessions.find(s => s.session_id === sessionId);
  if (!targetSession) throw new Error("Session not found");

  const remainingSessions = state.sessions.filter(s => s.session_id !== sessionId);
  const nextSelectedSession =
    remainingSessions.find(s => s.case_id === targetSession.case_id)?.session_id ||
    remainingSessions[0]?.session_id ||
    null;

  store.setState({
    sessions: remainingSessions,
    selectedSessionId: state.selectedSessionId === sessionId ? nextSelectedSession : state.selectedSessionId,
    audioFiles: (state.audioFiles || []).filter(a => a.session_id !== sessionId),
    processingJobs: (state.processingJobs || []).filter(j => j.session_id !== sessionId),
    generatedReports: (state.generatedReports || []).filter(r => r.session_id !== sessionId),
    transcripts: withoutKey(state.transcripts, sessionId),
    transcriptLines: withoutKey(state.transcriptLines, sessionId),
    extractedFeatureOutputs: withoutKey(state.extractedFeatureOutputs, sessionId),
    aiDecisionOutputs: withoutKey(state.aiDecisionOutputs, sessionId),
    transcriptQaResults: withoutKey(state.transcriptQaResults, sessionId),
    referenceComparisons: withoutKey(state.referenceComparisons, sessionId),
    observationsReviews: withoutKey(state.observationsReviews, sessionId),
    audioUrls: withoutKey(state.audioUrls, sessionId)
  });

  return { session_id: sessionId, deleted: true, nextSelectedSessionId: nextSelectedSession };
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
