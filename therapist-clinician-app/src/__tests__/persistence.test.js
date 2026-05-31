import { describe, expect, it } from "vitest";
import {
  LOCAL_STORAGE_KEY,
  createPersistenceAdapter,
  stateFromSnapshot
} from "../persistence/repository.js";

function createMemoryStorage() {
  const data = new Map();
  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null;
    },
    setItem(key, value) {
      data.set(key, value);
    },
    removeItem(key) {
      data.delete(key);
    }
  };
}

function seedSnapshot() {
  return {
    users: [
      { user_id: "therapist_a", role: "therapist", email: "a@example.test" },
      { user_id: "therapist_b", role: "therapist", email: "b@example.test" },
      { user_id: "clinician_a", role: "clinician", email: "c@example.test" },
      { user_id: "admin_001", role: "admin", email: "admin@example.test" }
    ],
    child_cases: [
      { case_id: "CASE-A", owner_user_id: "therapist_a", anonymized_child_code: "CHI-A" },
      { case_id: "CASE-B", owner_user_id: "therapist_b", anonymized_child_code: "CHI-B" },
      { case_id: "CASE-C", owner_user_id: "clinician_a", anonymized_child_code: "CHI-C" }
    ],
    sessions: [
      { session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      { session_id: "SESSION-B", case_id: "CASE-B", owner_user_id: "therapist_b" },
      { session_id: "SESSION-C", case_id: "CASE-C", owner_user_id: "clinician_a" }
    ],
    transcripts: {
      "SESSION-A": { transcript_id: "TRANSCRIPT-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      "SESSION-B": { transcript_id: "TRANSCRIPT-B", session_id: "SESSION-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    },
    transcript_lines: {},
    audio_files: [
      { audio_file_id: "AUDIO-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      { audio_file_id: "AUDIO-B", session_id: "SESSION-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    ],
    consent_records: [
      { consent_id: "CONSENT-A", case_id: "CASE-A", owner_user_id: "therapist_a", recorded_by_user_id: "therapist_a", audio_permission: true },
      { consent_id: "CONSENT-B", case_id: "CASE-B", owner_user_id: "therapist_b", recorded_by_user_id: "therapist_b", audio_permission: true }
    ],
    processing_jobs: [
      { job_id: "JOB-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      { job_id: "JOB-B", session_id: "SESSION-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    ],
    extracted_features: {
      "SESSION-A": { feature_id: "FEATURE-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      "SESSION-B": { feature_id: "FEATURE-B", session_id: "SESSION-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    },
    ai_screening_outputs: {
      "SESSION-A": { output_id: "AI-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      "SESSION-B": { output_id: "AI-B", session_id: "SESSION-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    },
    therapy_goals: [
      { goal_id: "GOAL-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      { goal_id: "GOAL-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    ],
    therapist_notes: [
      { note_id: "NOTE-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      { note_id: "NOTE-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    ],
    reports: [
      { report_id: "REPORT-A", case_id: "CASE-A", owner_user_id: "therapist_a" },
      { report_id: "REPORT-B", case_id: "CASE-B", owner_user_id: "therapist_b" }
    ],
    privacy_operations: [
      { operation_id: "PRIV-A", case_id: "CASE-A", owner_user_id: "therapist_a", operation_type: "case_export_request" },
      { operation_id: "PRIV-B", case_id: "CASE-B", owner_user_id: "therapist_b", operation_type: "case_deletion_request" }
    ],
    audit_logs: [
      { audit_id: "AUDIT-A", actor_user_id: "therapist_a", event_type: "view" },
      { audit_id: "AUDIT-B", actor_user_id: "therapist_b", event_type: "view" }
    ]
  };
}

describe("clinical persistence repository adapters", () => {
  it("selects mock by default and normalizes unknown modes to mock", () => {
    expect(createPersistenceAdapter().mode).toBe("mock");
    expect(createPersistenceAdapter({ mode: "unexpected" }).mode).toBe("mock");
  });

  it("selects localStorage, database placeholder, and API adapters explicitly", () => {
    expect(createPersistenceAdapter({ mode: "localStorage", storage: createMemoryStorage() }).mode).toBe("localStorage");
    expect(createPersistenceAdapter({ mode: "database_placeholder" }).mode).toBe("database_placeholder");
    expect(createPersistenceAdapter({ mode: "api" }).mode).toBe("api");
  });

  it("saves and loads localStorage repository snapshots", () => {
    const storage = createMemoryStorage();
    const adapter = createPersistenceAdapter({ mode: "localStorage", storage });
    adapter.hydrate(seedSnapshot());
    adapter.childCases.save(
      { case_id: "CASE-D", owner_user_id: "therapist_a", anonymized_child_code: "CHI-D" },
      "case_id"
    );

    const reloaded = createPersistenceAdapter({ mode: "localStorage", storage });
    const snapshot = reloaded.hydrate(seedSnapshot());

    expect(JSON.parse(storage.getItem(LOCAL_STORAGE_KEY)).child_cases).toHaveLength(4);
    expect(snapshot.child_cases.map(item => item.case_id)).toContain("CASE-D");
  });

  it.each(["mock", "localStorage", "database_placeholder", "api"])(
    "filters case ownership in %s mode",
    mode => {
      const adapter = createPersistenceAdapter({ mode, storage: createMemoryStorage() });
      adapter.hydrate(seedSnapshot());
      const therapistA = { user_id: "therapist_a", role: "therapist" };
      const clinicianA = { user_id: "clinician_a", role: "clinician" };

      expect(adapter.childCases.listForUser(therapistA).map(item => item.case_id)).toEqual(["CASE-A"]);
      expect(adapter.childCases.listForUser(clinicianA).map(item => item.case_id)).toEqual(["CASE-C"]);
      expect(adapter.sessions.listForUser(therapistA).map(item => item.session_id)).toEqual(["SESSION-A"]);
      expect(adapter.transcripts.listForUser(therapistA).map(item => item.transcript_id)).toEqual(["TRANSCRIPT-A"]);
      expect(adapter.audioFiles.listForUser(therapistA).map(item => item.audio_file_id)).toEqual(["AUDIO-A"]);
      expect(adapter.consentRecords.listForUser(therapistA).map(item => item.consent_id)).toEqual(["CONSENT-A"]);
      expect(adapter.processingJobs.listForUser(therapistA).map(item => item.job_id)).toEqual(["JOB-A"]);
      expect(adapter.extractedFeatures.listForUser(therapistA).map(item => item.feature_id)).toEqual(["FEATURE-A"]);
      expect(adapter.aiScreeningOutputs.listForUser(therapistA).map(item => item.output_id)).toEqual(["AI-A"]);
      expect(adapter.therapyGoals.listForUser(therapistA).map(item => item.goal_id)).toEqual(["GOAL-A"]);
      expect(adapter.therapistNotes.listForUser(therapistA).map(item => item.note_id)).toEqual(["NOTE-A"]);
      expect(adapter.reports.listForUser(therapistA).map(item => item.report_id)).toEqual(["REPORT-A"]);
      expect(adapter.privacyOperations.listForUser(therapistA).map(item => item.operation_id)).toEqual(["PRIV-A"]);
      expect(adapter.auditLogs.listForUser(therapistA)).toEqual([]);
    }
  );

  it("allows admins to see all demo cases while preserving non-admin isolation", () => {
    const adapter = createPersistenceAdapter({ mode: "mock" });
    adapter.hydrate(seedSnapshot());

    const admin = { user_id: "admin_001", role: "admin" };
    const therapistB = { user_id: "therapist_b", role: "therapist" };

    expect(adapter.childCases.listForUser(admin).map(item => item.case_id)).toEqual(["CASE-A", "CASE-B", "CASE-C"]);
    expect(adapter.childCases.listForUser(therapistB).map(item => item.owner_user_id)).toEqual(["therapist_b"]);
  });

  it("does not leak cross-therapist cases through the store snapshot mapping", () => {
    const adapter = createPersistenceAdapter({ mode: "mock" });
    const snapshot = adapter.hydrate(seedSnapshot());
    const state = stateFromSnapshot(snapshot);
    const therapistA = { user_id: "therapist_a", role: "therapist" };

    const visibleCaseIds = new Set(adapter.childCases.listForUser(therapistA).map(item => item.case_id));
    const visibleSessions = state.sessions.filter(session => visibleCaseIds.has(session.case_id));

    expect([...visibleCaseIds]).toEqual(["CASE-A"]);
    expect(visibleSessions.every(session => session.owner_user_id === "therapist_a")).toBe(true);
  });
});
