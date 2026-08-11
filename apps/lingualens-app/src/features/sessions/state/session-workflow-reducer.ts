import type { TranscriptLine, TranscriptQaStatus, WorkflowState } from "@/lib/workflow";

type FindingsResult = Pick<
  WorkflowState,
  "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights"
> & Partial<Pick<WorkflowState, "featureSignals" | "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featureSetId" | "featureTranscriptVersion">>;

export type WorkflowRequestIdentity = {
  revision: number;
  sessionId?: string;
  transcriptId?: string;
  transcriptVersion?: number;
};

export function isWorkflowRequestCurrent(
  request: WorkflowRequestIdentity,
  current: WorkflowRequestIdentity,
): boolean {
  return request.revision === current.revision
    && request.sessionId === current.sessionId
    && request.transcriptId === current.transcriptId
    && request.transcriptVersion === current.transcriptVersion;
}

export function canSettleWorkflowRequest(
  request: WorkflowRequestIdentity,
  current: WorkflowRequestIdentity,
  _settlement: "fulfilled" | "rejected" | "finalized",
): boolean {
  return isWorkflowRequestCurrent(request, current);
}

export function canApplyMlDecisionSupportSettlement(
  request: WorkflowRequestIdentity,
  current: WorkflowRequestIdentity,
  settlement: "fulfilled" | "rejected" | "finalized",
): boolean {
  return canSettleWorkflowRequest(request, current, settlement);
}

export function canApplyTranscriptSaveSettlement(
  request: WorkflowRequestIdentity,
  current: WorkflowRequestIdentity,
  settlement: "fulfilled" | "rejected" | "finalized",
): boolean {
  return canSettleWorkflowRequest(request, current, settlement);
}

export function derivePipelineStatus(
  state: WorkflowState,
  caseConsent: string,
  uploadStep: string,
): string {
  if (caseConsent !== "granted") return "awaiting_consent";
  if (state.reportStatus === "reviewed" || state.reportStatus === "finalized") return "report_ready";
  if (state.featuresExtracted || state.transcriptAttested) return "ml_pending";
  if (state.transcriptReady || state.transcriptReviewStatus === "in_review" || state.transcriptReviewStatus === "reviewed") return "review_required";
  if (uploadStep === "uploading") return "uploading";
  if (["verifying", "normalizing", "transcribing"].includes(uploadStep)) return "transcribing";
  return "ready_for_audio";
}

export type SessionWorkflowAction =
  | { type: "transcript-edited"; lines: TranscriptLine[] }
  | { type: "report-edit-requested" }
  | { type: "hydration-succeeded"; state: WorkflowState }
  | { type: "transcript-save-started"; transcriptText: string }
  | { type: "transcript-save-succeeded"; lines?: TranscriptLine[]; backendTranscriptVersion?: number }
  | { type: "transcript-save-failed"; error: string }
  | { type: "qa-succeeded"; status: TranscriptQaStatus; issues: string[]; summary?: string }
  | { type: "qa-failed"; error: string }
  | { type: "attestation-succeeded" }
  | { type: "attestation-failed"; error: string }
  | { type: "findings-started" }
  | { type: "findings-succeeded"; findings: FindingsResult }
  | { type: "findings-failed"; error: string }
  | { type: "report-started" }
  | { type: "report-succeeded"; reportId: string; markdown: string; finalized: boolean; version?: number; generatedFromVersions?: Record<string, string> }
  | { type: "report-failed"; error: string }
  | { type: "request-started"; message: string }
  | { type: "request-succeeded"; message?: string }
  | { type: "request-failed"; message: string; error: string }
  | { type: "session-identity-changed"; state: WorkflowState };

export function sessionWorkflowReducer(
  state: WorkflowState,
  action: SessionWorkflowAction,
): WorkflowState {
  switch (action.type) {
    case "transcript-edited": {
      const hadFindings = Boolean(
        state.featureSetId ||
        state.featuresExtracted ||
        state.analysisStatus === "completed" ||
        state.analysisStatus === "stale"
      );
      const hadEditableReport = state.reportStatus !== "not_started" && state.reportStatus !== "finalized";
      return {
        ...state,
        transcriptLines: action.lines,
        transcriptReady: action.lines.length > 0,
        transcriptSaveStatus: "unsaved",
        transcriptAttested: false,
        transcriptReviewStatus: "in_review",
        qaStatus: "not_run",
        qaIssues: [],
        qaSummary: undefined,
        analysisStatus: hadFindings ? "stale" : "not_started",
        featuresExtracted: false,
        mlReadiness: undefined,
        mlDecisionSupport: undefined,
        reportStatus: hadEditableReport ? "stale" : state.reportStatus,
        reportMarkdown: hadEditableReport ? undefined : state.reportMarkdown,
        reportSaveStatus: hadEditableReport ? "idle" : state.reportSaveStatus,
        error: undefined,
      };
    }
    case "report-edit-requested":
      if (state.reportStatus === "finalized") {
        throw new Error("Signed reports are immutable");
      }
      return state;
    case "hydration-succeeded":
      return action.state;
    case "transcript-save-started":
      return {
        ...state,
        transcriptText: action.transcriptText,
        transcriptSaveStatus: "saving",
        statusMessage: "Saving transcript draft...",
        error: undefined,
      };
    case "transcript-save-succeeded":
      return {
        ...state,
        transcriptLines: action.lines ?? state.transcriptLines,
        backendTranscriptVersion: action.backendTranscriptVersion ?? state.backendTranscriptVersion,
        transcriptSaveStatus: "saved",
        statusMessage: "Transcript draft saved.",
        error: undefined,
      };
    case "transcript-save-failed":
      return { ...state, transcriptSaveStatus: "failed", statusMessage: "Failed to save transcript.", error: action.error };
    case "qa-succeeded":
      return {
        ...state,
        qaStatus: action.status,
        qaIssues: action.issues,
        qaSummary: action.summary,
        statusMessage: action.summary,
        error: undefined,
      };
    case "qa-failed":
      return { ...state, qaStatus: "fail", statusMessage: "QA failed.", error: action.error };
    case "attestation-succeeded":
      return { ...state, transcriptAttested: true, transcriptReviewStatus: "reviewed", statusMessage: "Attestation complete.", error: undefined };
    case "attestation-failed":
      return { ...state, transcriptAttested: false, transcriptReviewStatus: "in_review", statusMessage: "Attestation failed.", error: action.error };
    case "findings-started":
      return { ...state, analysisStatus: "processing", statusMessage: "Extracting descriptive language-sample cues from the reviewed transcript...", error: undefined };
    case "findings-succeeded":
      return { ...state, ...action.findings, analysisStatus: "completed", statusMessage: "Language-sample feature extraction completed from the reviewed, attested transcript.", error: undefined };
    case "findings-failed":
      return {
        ...state,
        analysisStatus: state.featureSetId ? "stale" : "failed",
        featuresExtracted: false,
        statusMessage: "Feature extraction failed.",
        error: action.error,
      };
    case "report-started":
      return { ...state, reportSaveStatus: "saving", statusMessage: "Preparing a draft report...", error: undefined };
    case "report-succeeded":
      return {
        ...state,
        backendReportId: action.reportId,
        reportId: action.reportId,
        reportMarkdown: action.markdown,
        backendReportVersion: action.version,
        reportGeneratedFromVersions: action.generatedFromVersions,
        reportStatus: action.finalized ? "finalized" : "draft",
        reportSaveStatus: "saved",
        statusMessage: "Draft report generated. All text remains editable and therapist review is required.",
        error: undefined,
      };
    case "report-failed":
      return { ...state, reportSaveStatus: "failed", statusMessage: "Report generation failed.", error: action.error };
    case "request-started":
      return { ...state, workflowLoading: true, statusMessage: action.message, error: undefined };
    case "request-succeeded":
      return { ...state, workflowLoading: false, statusMessage: action.message ?? state.statusMessage, error: undefined };
    case "request-failed":
      return { ...state, workflowLoading: false, statusMessage: action.message, error: action.error };
    case "session-identity-changed":
      return action.state;
  }
}
