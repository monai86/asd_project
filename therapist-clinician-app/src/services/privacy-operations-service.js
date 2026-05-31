import { store } from "../store/state.js";
import { addAudit } from "./audit-service.js";
import { assertCanAccessCase } from "./auth-service.js";

export const PRIVACY_OPERATION_TYPES = [
  "case_export_request",
  "consent_withdrawal_request",
  "case_deletion_request"
];

function createPrivacyOperation(type, caseItem, details = {}) {
  if (!PRIVACY_OPERATION_TYPES.includes(type)) {
    throw new Error(`Unknown privacy operation: ${type}`);
  }
  const state = store.getState();
  assertCanAccessCase(state.currentUser, caseItem);
  const now = new Date().toISOString();
  return {
    operation_id: `PRIV-${String((state.privacyOperations || []).length + 1).padStart(4, "0")}`,
    operation_type: type,
    case_id: caseItem.case_id,
    owner_user_id: caseItem.owner_user_id,
    requested_by_user_id: state.currentUser.user_id,
    status: "requested",
    details,
    created_at: now,
    updated_at: now
  };
}

export function buildCasePrivacyExport(caseId) {
  const state = store.getState();
  const caseItem = state.cases.find(item => item.case_id === caseId);
  if (!caseItem) throw new Error("Case not found");
  assertCanAccessCase(state.currentUser, caseItem);

  const caseSessions = state.sessions.filter(item => item.case_id === caseId && item.owner_user_id === caseItem.owner_user_id);
  const sessionIds = new Set(caseSessions.map(item => item.session_id));
  return {
    exported_at: new Date().toISOString(),
    export_type: "case_privacy_export",
    safety_note: "Clinical decision-support export. It is not a diagnosis and must be handled according to clinic privacy policy.",
    case: caseItem,
    sessions: caseSessions,
    consent_records: (state.consentRecords || []).filter(item => item.case_id === caseId),
    audio_files: (state.audioFiles || []).filter(item => item.case_id === caseId),
    transcripts: Object.fromEntries(Object.entries(state.transcripts || {}).filter(([sessionId]) => sessionIds.has(sessionId))),
    transcript_lines: Object.fromEntries(Object.entries(state.transcriptLines || {}).filter(([sessionId]) => sessionIds.has(sessionId))),
    extracted_features: Object.fromEntries(Object.entries(state.extractedFeatureOutputs || {}).filter(([sessionId]) => sessionIds.has(sessionId))),
    ai_screening_outputs: Object.fromEntries(Object.entries(state.aiDecisionOutputs || {}).filter(([sessionId]) => sessionIds.has(sessionId))),
    reports: (state.generatedReports || []).filter(item => item.case_id === caseId),
    clinical_signoffs: (state.clinicalSignoffs || []).filter(item => item.case_id === caseId)
  };
}

export function requestCasePrivacyExport(caseId) {
  const state = store.getState();
  const caseItem = state.cases.find(item => item.case_id === caseId);
  if (!caseItem) throw new Error("Case not found");
  const payload = buildCasePrivacyExport(caseId);
  const operation = createPrivacyOperation("case_export_request", caseItem, {
    record_counts: {
      sessions: payload.sessions.length,
      audio_files: payload.audio_files.length,
      reports: payload.reports.length
    }
  });
  store.setState({ privacyOperations: [...(state.privacyOperations || []), operation] });
  addAudit("privacy_export_requested", "ChildCase", caseId, `Requested privacy export for case ${caseId}`);
  return { operation, payload };
}

export function requestConsentWithdrawal(caseId, reason = "") {
  const state = store.getState();
  const caseItem = state.cases.find(item => item.case_id === caseId);
  if (!caseItem) throw new Error("Case not found");
  const operation = createPrivacyOperation("consent_withdrawal_request", caseItem, { reason });
  const now = new Date().toISOString();
  const updatedCases = state.cases.map(item =>
    item.case_id === caseId
      ? { ...item, consent_status: "withdrawn", privacy_operation_status: "consent_withdrawal_requested", updated_at: now }
      : item
  );
  const updatedConsentRecords = (state.consentRecords || []).map(record =>
    record.case_id === caseId && !record.withdrawn_at
      ? { ...record, withdrawn_at: now, notes: [record.notes, reason].filter(Boolean).join(" | ") }
      : record
  );
  store.setState({
    cases: updatedCases,
    consentRecords: updatedConsentRecords,
    privacyOperations: [...(state.privacyOperations || []), operation]
  });
  addAudit("consent_withdrawal_requested", "ChildCase", caseId, `Requested consent withdrawal for case ${caseId}`);
  return operation;
}

export function requestCaseDeletion(caseId, reason = "") {
  const state = store.getState();
  const caseItem = state.cases.find(item => item.case_id === caseId);
  if (!caseItem) throw new Error("Case not found");
  const operation = createPrivacyOperation("case_deletion_request", caseItem, { reason });
  const now = new Date().toISOString();
  const updatedCases = state.cases.map(item =>
    item.case_id === caseId
      ? { ...item, privacy_operation_status: "deletion_requested", deletion_requested_at: now, updated_at: now }
      : item
  );
  store.setState({
    cases: updatedCases,
    privacyOperations: [...(state.privacyOperations || []), operation]
  });
  addAudit("case_deletion_requested", "ChildCase", caseId, `Requested case deletion review for case ${caseId}`);
  return operation;
}
