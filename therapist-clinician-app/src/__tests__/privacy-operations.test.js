import { beforeEach, describe, expect, it } from "vitest";
import { store } from "../store/state.js";
import {
  buildCasePrivacyExport,
  requestCaseDeletion,
  requestCasePrivacyExport,
  requestConsentWithdrawal
} from "../services/privacy-operations-service.js";

function resetPrivacyState() {
  store.persistenceAdapter = null;
  store.setState({
    currentUser: { user_id: "therapist_a", role: "therapist", name: "Therapist A" },
    cases: [{ case_id: "CASE-A", owner_user_id: "therapist_a", anonymized_child_code: "CHI-A", consent_status: "granted" }],
    sessions: [{ session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" }],
    consentRecords: [{ consent_id: "CONSENT-A", case_id: "CASE-A", owner_user_id: "therapist_a", recorded_by_user_id: "therapist_a", audio_permission: true }],
    audioFiles: [{ audio_file_id: "AUDIO-A", case_id: "CASE-A", session_id: "SESSION-A", owner_user_id: "therapist_a" }],
    transcripts: { "SESSION-A": { transcript_id: "TRANSCRIPT-A", case_id: "CASE-A", session_id: "SESSION-A", owner_user_id: "therapist_a" } },
    transcriptLines: {},
    extractedFeatureOutputs: {},
    aiDecisionOutputs: {},
    generatedReports: [{ report_id: "REPORT-A", case_id: "CASE-A", owner_user_id: "therapist_a" }],
    clinicalSignoffs: [],
    privacyOperations: [],
    auditLogs: []
  });
}

describe("privacy operations", () => {
  beforeEach(() => {
    resetPrivacyState();
  });

  it("builds a case-scoped privacy export without cross-case records", () => {
    const payload = buildCasePrivacyExport("CASE-A");

    expect(payload.export_type).toBe("case_privacy_export");
    expect(payload.sessions).toHaveLength(1);
    expect(payload.audio_files[0].audio_file_id).toBe("AUDIO-A");
    expect(payload.safety_note).toContain("not a diagnosis");
  });

  it("records export, withdrawal, and deletion requests with audit events", () => {
    const exportRequest = requestCasePrivacyExport("CASE-A");
    const withdrawal = requestConsentWithdrawal("CASE-A", "Guardian request.");
    const deletion = requestCaseDeletion("CASE-A", "Retention review.");

    const state = store.getState();
    expect(exportRequest.operation.operation_type).toBe("case_export_request");
    expect(withdrawal.operation_type).toBe("consent_withdrawal_request");
    expect(deletion.operation_type).toBe("case_deletion_request");
    expect(state.cases[0]).toMatchObject({
      consent_status: "withdrawn",
      privacy_operation_status: "deletion_requested"
    });
    expect(state.consentRecords[0].withdrawn_at).toBeTruthy();
    expect(state.privacyOperations).toHaveLength(3);
    expect(state.auditLogs.map(log => log.event_type)).toEqual([
      "case_deletion_requested",
      "consent_withdrawal_requested",
      "privacy_export_requested"
    ]);
  });
});
