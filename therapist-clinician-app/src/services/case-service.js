import { store } from "../store/state.js";
import { createChildCase } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { assertCanAccessCase, canAccessCase, requireAuth } from "./auth-service.js";
import { createActiveClinicalRepository, isRemoteDataMode } from "../persistence/active-repository.js";

export function getVisibleCases() {
  const { currentUser, cases } = store.getState();
  return cases.filter(c => canAccessCase(currentUser, c));
}

export function createCase({ display_label, anonymized_child_code, age_months, sex, primary_concerns, notes, consent_status = "pending", anonymization_status = "anonymized" }) {
  const { currentUser, cases } = store.getState();
  requireAuth();

  const numericIds = cases
    .map(c => {
      const match = c.case_id.match(/^CASE-(\d+)$/i);
      return match ? parseInt(match[1], 10) : 0;
    })
    .filter(val => !isNaN(val));
  const nextNum = numericIds.length > 0 ? Math.max(...numericIds) + 1 : 1;
  const caseId = `CASE-${String(nextNum).padStart(3, "0")}`;
  const displayLabel = display_label || `Case ${String.fromCharCode(65 + (nextNum - 1))}`; // A, B, C...

  if (isRemoteDataMode(store.getState().dataMode)) {
    const repository = createActiveClinicalRepository(store.getState().dataMode);
    return repository.createCase({
      display_label: displayLabel,
      anonymized_child_code,
      age_months: parseInt(age_months) || 48,
      sex,
      primary_concerns,
      consent_status,
      anonymization_status,
      notes
    }).then(async (createdCase) => {
      if (consent_status === "granted") {
        await repository.recordConsent(createdCase.case_id, { audio_permission: true });
      }
      const formattedCase = createChildCase({
        display_label: displayLabel,
        ...createdCase
      });
      const { cases: currentCases } = store.getState();
      store.setState({
        cases: [...currentCases, formattedCase],
        selectedCaseId: formattedCase.case_id
      });
      addAudit("create_case", "ChildCase", formattedCase.case_id, `Created child case ${formattedCase.anonymized_child_code}`);
      return formattedCase;
    });
  }

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

  if (isRemoteDataMode(store.getState().dataMode)) {
    const repository = createActiveClinicalRepository(store.getState().dataMode);
    return repository.patchCase(caseId, { notes }).then(patchedCase => {
      const { cases: currentCases } = store.getState();
      const existingCase = currentCases.find(c => c.case_id === caseId) || {};
      const updatedCase = createChildCase({
        ...existingCase,
        ...patchedCase
      });
      const updatedCases = currentCases.map(c => c.case_id === caseId ? updatedCase : c);
      store.setState({ cases: updatedCases });
      addAudit("update_notes", "ChildCase", caseId, `Updated notes for case ${caseId}`);
      return updatedCase;
    });
  }

  const updatedCases = cases.map(c => {
    if (c.case_id === caseId) {
      addAudit("update_notes", "ChildCase", caseId, `Updated notes for case ${caseId}`);
      return { ...c, notes, updated_at: new Date().toISOString() };
    }
    return c;
  });
  store.setState({ cases: updatedCases });
  return updatedCases.find(c => c.case_id === caseId);
}
