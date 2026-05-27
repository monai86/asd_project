import { store } from "../store/state.js";
import { createChildCase } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { assertCanAccessCase, canAccessCase, requireAuth } from "./auth-service.js";

export function getVisibleCases() {
  const { currentUser, cases } = store.getState();
  return cases.filter(c => canAccessCase(currentUser, c));
}

export function createCase({ anonymized_child_code, age_months, sex, primary_concerns, notes, consent_status = "pending", anonymization_status = "anonymized" }) {
  const { currentUser, cases } = store.getState();
  requireAuth();

  const caseId = `CASE-${String(cases.length + 1).padStart(3, "0")}`;
  const displayLabel = `Case ${String.fromCharCode(65 + cases.length)}`; // A, B, C...

  const newCase = createChildCase({
    case_id: caseId,
    owner_user_id: currentUser.user_id,
    anonymized_child_code,
    display_label: displayLabel,
    age_months: parseInt(age_months) || 48,
    sex,
    primary_concerns,
    consent_status,
    anonymization_status,
    notes,
    support_level: "Needs review",
    latest_score: 0.0,
    score_trend: []
  });

  store.setState({
    cases: [...cases, newCase],
    selectedCaseId: caseId
  });

  addAudit("create_case", "ChildCase", caseId, `Created child case ${anonymized_child_code}`);
  return newCase;
}

export function toggleStarCase(caseId) {
  const { currentUser, cases } = store.getState();
  const targetCase = cases.find(c => c.case_id === caseId);
  if (!targetCase) return;
  assertCanAccessCase(currentUser, targetCase);
  const updatedCases = cases.map(c => {
    if (c.case_id === caseId) {
      const starred = !c.starred;
      addAudit("toggle_star", "ChildCase", caseId, `${starred ? "Starred" : "Unstarred"} case ${caseId}`);
      return { ...c, starred, updated_at: new Date().toISOString() };
    }
    return c;
  });
  store.setState({ cases: updatedCases });
}

export function updateCaseNotes(caseId, notes) {
  const { currentUser, cases } = store.getState();
  const targetCase = cases.find(c => c.case_id === caseId);
  if (!targetCase) return;
  assertCanAccessCase(currentUser, targetCase);
  const updatedCases = cases.map(c => {
    if (c.case_id === caseId) {
      addAudit("update_notes", "ChildCase", caseId, `Updated notes for case ${caseId}`);
      return { ...c, notes, updated_at: new Date().toISOString() };
    }
    return c;
  });
  store.setState({ cases: updatedCases });
}
