import { store } from "../store/state.js";
import { getCaseSessions } from "./session-service.js";
import { getChildProgressFromData } from "@shared/services/progress-service.js";
import { canAccessCase } from "./auth-service.js";

export function getChildProgress(caseId) {
  const { currentUser, cases, extractedFeatureOutputs, aiDecisionOutputs, goals } = store.getState();
  const repositoryProgress = getChildProgressFromRepositorySnapshot(caseId, currentUser, store.persistenceAdapter?.snapshot);
  if (repositoryProgress) return repositoryProgress;

  const caseItem = cases.find(c => c.case_id === caseId);
  if (!canAccessCase(currentUser, caseItem)) return null;
  const sessions = getCaseSessions(caseId);

  return getChildProgressFromData({
    caseItem,
    sessions,
    extractedFeatureOutputs,
    aiDecisionOutputs,
    goals
  });
}

export function getChildProgressFromRepositorySnapshot(caseId, currentUser, snapshot = null) {
  if (!snapshot?.child_cases) return null;
  const caseItem = snapshot.child_cases.find(c => c.case_id === caseId);
  if (!canAccessCase(currentUser, caseItem)) return null;
  const sessions = (snapshot.sessions || []).filter(s => s.case_id === caseId);
  return getChildProgressFromData({
    caseItem,
    sessions,
    extractedFeatureOutputs: snapshot.extracted_features || {},
    aiDecisionOutputs: snapshot.ai_screening_outputs || {},
    goals: snapshot.therapy_goals || []
  });
}
