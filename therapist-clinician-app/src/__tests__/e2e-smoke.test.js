import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { store } from "../store/state.js";
import { signIn } from "../services/auth-service.js";
import { createCase } from "../services/case-service.js";
import { createNewSession, updateSessionStatus } from "../services/session-service.js";
import { uploadSessionAudio } from "../services/audio-service.js";
import { startTranscription } from "../services/transcription-service.js";
import { saveTherapistReview } from "../services/review-service.js";
import { buildFeatureAndAiOutputs } from "../services/transcript-workflow-service.js";
import { buildProgressReportMarkdown, generateSessionReport } from "../services/report-service.js";
import { addAudit } from "../services/audit-service.js";

function resetE2EState() {
  store.persistenceAdapter = null;
  store.setState({
    currentUser: null,
    authError: "",
    authStatus: "signed_out",
    authSession: null,
    dataMode: "mock",
    persistenceStatus: "not_loaded",
    activeView: "dashboard",
    selectedCaseId: null,
    selectedSessionId: null,
    cases: [],
    sessions: [],
    audioFiles: [],
    consentRecords: [],
    processingJobs: [],
    transcripts: {},
    transcriptLines: {},
    goals: [],
    notes: [],
    generatedReports: [],
    clinicalSignoffs: [],
    privacyOperations: [],
    aiDecisionOutputs: {},
    extractedFeatureOutputs: {},
    developmentalNorms: {},
    audioUrls: {},
    sessionVocabs: {},
    auditLogs: [],
    users: [
      {
        user_id: "user_therapist_001",
        email: "therapist@example.test",
        name: "Dr. Anya Therapist",
        role: "therapist",
        organization: "Mock Speech Clinic"
      }
    ]
  });
}

describe("therapist workflow smoke path", () => {
  beforeEach(() => {
    resetE2EState();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("covers login, case/session creation, mock processing, transcript review, feature rerun, report generation, and report export", async () => {
    const user = signIn("therapist@example.test", "demo-password");
    expect(user?.role).toBe("therapist");

    const childCase = createCase({
      anonymized_child_code: "CHI-SMOKE",
      age_months: 52,
      sex: "not_specified",
      primary_concerns: "Smoke test workflow case.",
      consent_status: "granted",
      notes: "No direct child identifiers."
    });
    const session = createNewSession({
      case_id: childCase.case_id,
      session_date: "2026-05-31",
      session_type: "therapy_session",
      notes: "Mock parent-child language sample."
    });
    const audio = uploadSessionAudio(
      { name: "sample-session.wav", size: 2048, type: "audio/wav" },
      session.session_id,
      childCase.case_id
    );

    const transcription = startTranscription(session.session_id);
    await vi.advanceTimersByTimeAsync(1500);
    await transcription;

    saveTherapistReview({
      sessionId: session.session_id,
      notes: "Transcript lines reviewed for smoke test.",
      approvedSummary: "Reviewed transcript is acceptable for prototype report generation."
    });

    const reviewedState = store.getState();
    const reviewedSession = reviewedState.sessions.find(item => item.session_id === session.session_id);
    const reviewedCase = reviewedState.cases.find(item => item.case_id === childCase.case_id);
    const artifacts = buildFeatureAndAiOutputs({
      session: reviewedSession,
      childCase: reviewedCase,
      transcriptLines: reviewedState.transcriptLines[session.session_id],
      reviewed: true
    });
    store.setState({
      extractedFeatureOutputs: {
        ...reviewedState.extractedFeatureOutputs,
        [session.session_id]: artifacts.featuresSet
      },
      aiDecisionOutputs: {
        ...reviewedState.aiDecisionOutputs,
        [session.session_id]: artifacts.aiOutput
      }
    });
    updateSessionStatus(session.session_id, {
      feature_extraction_status: "completed",
      ai_analysis_status: "completed",
      therapist_review_status: "reviewed",
      report_status: "pending"
    });
    addAudit("feature_rerun_completed", "Session", session.session_id, "Re-ran feature extraction after transcript review.");

    const report = generateSessionReport(session.session_id);
    const exportMarkdown = buildProgressReportMarkdown(
      reviewedCase,
      [store.getState().sessions.find(item => item.session_id === session.session_id)],
      store.getState().extractedFeatureOutputs,
      store.getState().aiDecisionOutputs,
      store.getState().transcripts
    );
    addAudit("report_exported", "ChildCase", childCase.case_id, `Exported progress report markdown for case ${childCase.case_id}`);

    const finalState = store.getState();
    expect(audio.audio_file_id).toBe("AUDIO-001");
    expect(finalState.transcripts[session.session_id].review_status).toBe("reviewed");
    expect(finalState.extractedFeatureOutputs[session.session_id].extraction_status).toBe("completed");
    expect(finalState.aiDecisionOutputs[session.session_id].therapist_review_status).toBe("awaiting_review");
    expect(report.export_status).toBe("completed");
    expect(exportMarkdown).toContain("does not diagnose ASD");
    expect(finalState.generatedReports).toHaveLength(1);
    expect(finalState.clinicalSignoffs).toHaveLength(1);
    expect(finalState.auditLogs.map(log => log.event_type)).toEqual(
      expect.arrayContaining([
        "login_success",
        "create_case",
        "create_session",
        "audio_upload",
        "transcription_complete",
        "clinical_signoff_created",
        "feature_rerun_completed",
        "generate_report",
        "report_exported"
      ])
    );
  });
});
