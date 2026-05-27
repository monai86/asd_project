import { store } from "../store/state.js";
import { getCaseSessions } from "./session-service.js";
import { getChildProgressFromData } from "@shared/services/progress-service.js";

export function getChildProgress(caseId) {
  const { cases, extractedFeatureOutputs, aiDecisionOutputs, goals } = store.getState();
  const caseItem = cases.find(c => c.case_id === caseId);
  const sessions = getCaseSessions(caseId);

  return getChildProgressFromData({
    caseItem,
    sessions,
    extractedFeatureOutputs,
    aiDecisionOutputs,
    goals
  });
}
