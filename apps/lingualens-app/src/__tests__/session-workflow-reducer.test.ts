import { describe, expect, test } from "vitest";

import {
  canApplyTranscriptSaveSettlement,
  derivePipelineStatus,
  canApplyMlDecisionSupportSettlement,
  canSettleWorkflowRequest,
  isWorkflowRequestCurrent,
  sessionWorkflowReducer,
} from "@/features/sessions/state/session-workflow-reducer";
import { createInitialWorkflowState, type WorkflowState } from "@/lib/workflow";

function reviewedState(overrides: Partial<WorkflowState> = {}): WorkflowState {
  return {
    ...createInitialWorkflowState(),
    transcriptReady: true,
    transcriptAttested: true,
    transcriptReviewStatus: "reviewed",
    transcriptSaveStatus: "saved",
    qaStatus: "pass",
    analysisStatus: "completed",
    featuresExtracted: true,
    reportStatus: "draft",
    reportMarkdown: "# Existing draft",
    reportSaveStatus: "saved",
    ...overrides,
  };
}

describe("sessionWorkflowReducer safety transitions", () => {
  test("transcript edits clear QA, attestation, findings, and report readiness", () => {
    const next = sessionWorkflowReducer(reviewedState(), {
      type: "transcript-edited",
      lines: [{ lineId: "1", speaker: "CHI", text: "changed" }],
    });

    expect(next).toMatchObject({
      transcriptSaveStatus: "unsaved",
      qaStatus: "not_run",
      transcriptAttested: false,
      analysisStatus: "stale",
      reportStatus: "stale",
    });
    expect(next.featuresExtracted).toBe(false);
    expect(next.reportMarkdown).toBeUndefined();
  });

  test("a first failed analysis remains not started after a transcript edit", () => {
    const next = sessionWorkflowReducer(reviewedState({
      analysisStatus: "failed",
      featuresExtracted: false,
      featureSetId: undefined,
      reportStatus: "not_started",
      reportMarkdown: undefined,
    }), {
      type: "transcript-edited",
      lines: [{ lineId: "1", speaker: "CHI", text: "changed" }],
    });

    expect(next.analysisStatus).toBe("not_started");
    expect(next.reportStatus).toBe("not_started");
  });

  test("failed findings regeneration preserves the stale provenance state", () => {
    const stale = reviewedState({
      analysisStatus: "stale",
      featuresExtracted: false,
      featureSetId: "FEATURE-STALE",
      reportStatus: "stale",
    });

    const processing = sessionWorkflowReducer(stale, { type: "findings-started" });
    const failed = sessionWorkflowReducer(processing, { type: "findings-failed", error: "Backend unavailable" });

    expect(failed.analysisStatus).toBe("stale");
    expect(failed.featureSetId).toBe("FEATURE-STALE");
    expect(failed.reportStatus).toBe("stale");
  });

  test("signed reports cannot transition back to editable", () => {
    const signedState = reviewedState({ reportStatus: "finalized" });

    expect(() => sessionWorkflowReducer(signedState, { type: "report-edit-requested" })).toThrow(
      "Signed reports are immutable",
    );
  });

  test("hydration replaces identity-scoped state and preserves backend provenance", () => {
    const hydrated = reviewedState({
      backendSessionId: "session-2",
      backendTranscriptId: "transcript-2",
      backendReportId: "report-2",
      reportId: "report-2",
      reportStatus: "stale",
      workflowLoading: false,
    });

    expect(sessionWorkflowReducer(reviewedState({ backendSessionId: "session-1" }), {
      type: "hydration-succeeded",
      state: hydrated,
    })).toEqual(hydrated);
  });

  test("transcript save and QA transitions do not restore stale downstream outputs", () => {
    const edited = sessionWorkflowReducer(reviewedState(), {
      type: "transcript-edited",
      lines: [{ lineId: "1", speaker: "CHI", text: "changed" }],
    });
    const saving = sessionWorkflowReducer(edited, {
      type: "transcript-save-started",
      transcriptText: "*CHI:\tchanged",
    });
    const saved = sessionWorkflowReducer(saving, { type: "transcript-save-succeeded" });
    const qa = sessionWorkflowReducer(saved, {
      type: "qa-succeeded",
      status: "pass",
      issues: [],
      summary: "QA passed.",
    });

    expect(qa).toMatchObject({
      transcriptSaveStatus: "saved",
      qaStatus: "pass",
      analysisStatus: "stale",
      reportStatus: "stale",
      featuresExtracted: false,
    });
  });

  test("findings regeneration makes only the new findings current", () => {
    const stale = reviewedState({
      analysisStatus: "stale",
      reportStatus: "stale",
      featuresExtracted: false,
      featureSetId: "feature-stale",
      featureTranscriptVersion: 2,
    });
    const processing = sessionWorkflowReducer(stale, { type: "findings-started" });
    const completed = sessionWorkflowReducer(processing, {
      type: "findings-succeeded",
      findings: {
        featureSetId: "feature-new",
        featureTranscriptVersion: 3,
        featuresExtracted: true,
        featurePercent: 100,
        featureSummary: [{ label: "MLU", value: "3.2" }],
        reviewNeededCount: 0,
        insights: [],
      },
    });

    expect(completed).toMatchObject({
      analysisStatus: "completed",
      featuresExtracted: true,
      featureSetId: "feature-new",
      featureTranscriptVersion: 3,
      reportStatus: "stale",
    });
  });

  test("report regeneration records the replacement report provenance", () => {
    const next = sessionWorkflowReducer(reviewedState({ reportStatus: "stale" }), {
      type: "report-succeeded",
      reportId: "report-new",
      markdown: "# Regenerated",
      finalized: false,
      version: 4,
      generatedFromVersions: { transcript_version: "3", feature_schema_version: "1.0" },
    });

    expect(next).toMatchObject({
      backendReportId: "report-new",
      reportId: "report-new",
      reportMarkdown: "# Regenerated",
      reportStatus: "draft",
      reportSaveStatus: "saved",
      backendReportVersion: 4,
      reportGeneratedFromVersions: { transcript_version: "3", feature_schema_version: "1.0" },
    });
  });

  test("request lifecycle clears stale errors without dropping workflow provenance", () => {
    const starting = sessionWorkflowReducer(reviewedState({ error: "Previous failure", backendTranscriptVersion: 3 }), {
      type: "request-started",
      message: "Loading persisted workflow...",
    });
    const failed = sessionWorkflowReducer(starting, {
      type: "request-failed",
      message: "Session unavailable.",
      error: "Retry the request.",
    });
    const succeeded = sessionWorkflowReducer(starting, {
      type: "request-succeeded",
      message: "Persisted workflow loaded.",
    });

    expect(starting).toMatchObject({ workflowLoading: true, error: undefined, backendTranscriptVersion: 3 });
    expect(failed).toMatchObject({
      workflowLoading: false,
      statusMessage: "Session unavailable.",
      error: "Retry the request.",
      backendTranscriptVersion: 3,
    });
    expect(succeeded).toMatchObject({
      workflowLoading: false,
      statusMessage: "Persisted workflow loaded.",
      error: undefined,
      backendTranscriptVersion: 3,
    });
  });

  test("session identity change replaces rather than merges prior child state", () => {
    const replacement = createInitialWorkflowState();
    replacement.backendSessionId = "session-new";
    replacement.childName = "New child";

    const next = sessionWorkflowReducer(reviewedState({ childName: "Prior child", backendReportId: "prior-report" }), {
      type: "session-identity-changed",
      state: replacement,
    });

    expect(next).toEqual(replacement);
    expect(next.backendReportId).toBeUndefined();
  });

  test("an in-flight findings response is obsolete after transcript revision or identity changes", () => {
    const request = {
      revision: 4,
      sessionId: "session-1",
      transcriptId: "transcript-1",
      transcriptVersion: 2,
    };

    expect(isWorkflowRequestCurrent(request, request)).toBe(true);
    expect(isWorkflowRequestCurrent(request, { ...request, revision: 5 })).toBe(false);
    expect(isWorkflowRequestCurrent(request, { ...request, transcriptVersion: 3 })).toBe(false);
    expect(isWorkflowRequestCurrent(request, { ...request, sessionId: "session-2" })).toBe(false);
  });

  test("stale rejection and finalization cannot settle over a newer findings or report request", () => {
    const staleRequest = { revision: 6, sessionId: "session-1", transcriptId: "transcript-1", transcriptVersion: 2 };
    const newestRequest = { ...staleRequest, revision: 7 };

    expect(canSettleWorkflowRequest(staleRequest, newestRequest, "rejected")).toBe(false);
    expect(canSettleWorkflowRequest(staleRequest, newestRequest, "finalized")).toBe(false);
    expect(canSettleWorkflowRequest(newestRequest, newestRequest, "fulfilled")).toBe(true);
  });

  test("late ML decision-support settlements cannot restore pre-edit state", () => {
    const mlRequest = { revision: 8, sessionId: "session-1", transcriptId: "transcript-1", transcriptVersion: 2 };
    const afterEdit = { ...mlRequest, revision: 9 };

    expect(canApplyMlDecisionSupportSettlement(mlRequest, afterEdit, "fulfilled")).toBe(false);
    expect(canApplyMlDecisionSupportSettlement(mlRequest, afterEdit, "rejected")).toBe(false);
    expect(canApplyMlDecisionSupportSettlement(mlRequest, afterEdit, "finalized")).toBe(false);
  });

  test("deferred transcript save cannot overwrite a newer edit and successful current save records backend version", async () => {
    const request = { revision: 10, sessionId: "session-1", transcriptId: "transcript-1", transcriptVersion: 2 };
    let resolveSave!: (value: { version: number }) => void;
    const save = new Promise<{ version: number }>((resolve) => { resolveSave = resolve; });
    let current = reviewedState({ backendTranscriptVersion: 2, transcriptLines: [{ lineId: "1", speaker: "CHI", text: "saving" }] });
    const pending = save.then((response) => {
      const afterEditIdentity = { ...request, revision: 11 };
      if (canApplyTranscriptSaveSettlement(request, afterEditIdentity, "fulfilled")) {
        current = sessionWorkflowReducer(current, { type: "transcript-save-succeeded", backendTranscriptVersion: response.version });
      }
    });
    current = sessionWorkflowReducer(current, { type: "transcript-edited", lines: [{ lineId: "1", speaker: "CHI", text: "newer edit" }] });
    resolveSave({ version: 3 });
    await pending;

    expect(current.transcriptLines[0].text).toBe("newer edit");
    expect(current.backendTranscriptVersion).toBe(2);
    const saved = sessionWorkflowReducer(current, { type: "transcript-save-succeeded", backendTranscriptVersion: 4 });
    expect(saved.backendTranscriptVersion).toBe(4);
  });

  test("stale report markdown never advances pipeline readiness to report ready", () => {
    expect(derivePipelineStatus(reviewedState({ reportStatus: "stale", reportMarkdown: "# Prior draft", featuresExtracted: false }), "granted", "idle")).not.toBe("report_ready");
    expect(derivePipelineStatus(reviewedState({ reportStatus: "finalized", reportMarkdown: "# Signed" }), "granted", "idle")).toBe("report_ready");
  });
});
