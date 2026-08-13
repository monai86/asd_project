"use client";

import { useEffect, useRef, useState } from "react";

import { useBackendAvailability } from "@/components/backend-availability-banner";
import { sessionReportService } from "@/features/sessions/report/session-report-service";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import {
  classifyWorkflowLoadFailure,
  createIdentityScopedWorkflowState,
  createInitialWorkflowState,
  loadWorkflowState,
  saveWorkflowState,
  type BackendReport,
  type WorkflowState,
} from "@/lib/workflow";
import {
  clinicianLabel,
  createDraftText,
  downloadTextFile,
  mergeReportInputs,
  parseGoals,
  replaceRevisionUrl,
  resetSignedReportForRevision,
  signedSnapshotString,
  type SnapshotIntegrityState,
  validateSignedSnapshotEnvelope,
  verifySignedSnapshotHash,
} from "@/features/sessions/report/session-report-model";

export type SessionReportViewProps = {
  caseId?: string;
  sessionId?: string;
  transcriptId?: string;
  reportId?: string;
};

export function useSessionReport({ caseId, sessionId, transcriptId, reportId }: SessionReportViewProps) {
  const hasLocator = Boolean(reportId || sessionId);
  const [state, setState] = useState<WorkflowState>(() => hasLocator
    ? createIdentityScopedWorkflowState({ workflowLoading: true, statusMessage: "Loading persisted report..." })
    : createInitialWorkflowState());
  const [busy, setBusy] = useState(false);
  const [reportText, setReportText] = useState("");
  const [therapistNotes, setTherapistNotes] = useState("");
  const [goalsText, setGoalsText] = useState("");
  const [exportedCha, setExportedCha] = useState("");
  const [providerId, setProviderId] = useState<string>("template");
  const [allowFallback, setAllowFallback] = useState<boolean>(false);
  const [backendReport, setBackendReport] = useState<BackendReport | null>(null);
  const [primaryTherapistLabel, setPrimaryTherapistLabel] = useState<string>(hasLocator ? "" : "Authenticated primary therapist");
  const [primaryTherapistAssigned, setPrimaryTherapistAssigned] = useState<boolean>(!hasLocator);
  const [confirmationChecked, setConfirmationChecked] = useState<boolean>(!hasLocator);
  const [snapshotIntegrity, setSnapshotIntegrity] = useState<SnapshotIntegrityState>({ status: "not_applicable" });
  const revisionInFlightRef = useRef(false);
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();

  const isFailedSafety = backendReport?.status === "Failed";
  const isFinalized = state.reportStatus === "finalized" || backendReport?.status === "Signed Off";
  const isStale = state.reportStatus === "stale" || backendReport?.status === "stale";
  const isNotStarted = state.reportStatus === "not_started" && !backendReport;
  const isSnapshotIntegrityChecking = isFinalized && snapshotIntegrity.status === "checking";
  const hasSnapshotIntegrityError = isFinalized && snapshotIntegrity.status === "invalid";
  const signedSnapshotVerified = isFinalized && snapshotIntegrity.status === "valid";
  const signedActionsBlocked = isFinalized && !signedSnapshotVerified;
  const canRenderReportMetadata = !isFinalized || signedSnapshotVerified;
  const isEditorLocked = isFinalized || isFailedSafety || isStale;
  const transcriptUnlocked = state.transcriptAttested && state.transcriptReviewStatus === "reviewed";

  useEffect(() => {
    let cancelled = false;
    if (!reportId && !sessionId) {
      const stored = loadWorkflowState();
      setState(stored);
      setReportText(stored.reportStatus === "not_started" ? "" : stored.reportMarkdown ?? createDraftText(stored));
      setTherapistNotes(stored.therapistNotes);
      setGoalsText(stored.therapyGoals.join("\n"));
      return;
    }

    const loadingState = saveWorkflowState(createIdentityScopedWorkflowState({
      workflowLoading: true,
      statusMessage: "Loading persisted report...",
      error: undefined,
    }));
    setBackendUnavailable(false);
    setState(loadingState);
    setReportText("");
    setTherapistNotes("");
    setGoalsText("");
    setExportedCha("");
    setBackendReport(null);
    setProviderId("template");
    setPrimaryTherapistLabel("");
    setPrimaryTherapistAssigned(false);
    setConfirmationChecked(false);
    void (async () => {
      try {
        const { session, report, transcript, childCase, resolvedReportId, resolvedCaseId } = await sessionReportService.load({
          caseId,
          sessionId,
          transcriptId,
          reportId,
        });
        const finalized = report.status === "Signed Off";

        if (cancelled) return;
        setBackendReport(report);
        setProviderId(report.requested_provider ?? "template");
        setPrimaryTherapistAssigned(Boolean(childCase?.primary_therapist_user_id));
        setPrimaryTherapistLabel(
          childCase?.primary_therapist_user_id
            ? clinicianLabel(childCase.primary_therapist_user_id)
            : "Primary therapist assignment required",
        );

        const hydrated = saveWorkflowState({
          ...createIdentityScopedWorkflowState(),
          sessionId: report.session_id ?? session?.session_id,
          caseId: resolvedCaseId,
          caseInfo: {
            caseId: resolvedCaseId,
            clientLabel: childCase?.nickname ?? childCase?.child_code ?? ""
          },
          childName: childCase?.nickname ?? childCase?.child_code ?? "",
          backendSessionId: report.session_id ?? session?.session_id,
          backendTranscriptSessionId: transcript?.session_id ?? report.session_id ?? session?.session_id,
          backendTranscriptId: transcript?.transcript_id,
          backendTranscriptVersion: transcript?.version,
          transcriptAttested: Boolean(transcript?.therapist_attested),
          transcriptReviewStatus: transcript?.therapist_attested ? "reviewed" : "in_review",
          backendReportId: resolvedReportId,
          backendReportVersion: report.version,
          reportId: resolvedReportId,
          reportMarkdown: finalized ? "" : report.markdown ?? "",
          therapistNotes: report.therapist_notes ?? "",
          therapyGoals: report.session_goals ?? [],
          featureSetId: report.feature_result_id,
          reportGeneratedFromVersions: report.generated_from_versions,
          reportStatus: report.status === "stale" ? "stale" : finalized ? "finalized" : report.status === "Failed" ? "reviewed" : "draft",
          reportSaveStatus: "saved",
          workflowLoading: false,
          finalizeStatus: finalized ? "Report finalized." : undefined,
          statusMessage: report.status === "Failed" ? "Safety check failed." : finalized ? "Finalized report loaded." : "Report draft loaded.",
          error: undefined
        });
        setState(hydrated);
        setReportText(hydrated.reportMarkdown ?? "");
        setTherapistNotes(hydrated.therapistNotes);
        setGoalsText(hydrated.therapyGoals.join("\n"));
      } catch (error) {
        if (cancelled) return;
        const failure = classifyWorkflowLoadFailure(error, "report");
        setBackendUnavailable(failure.backendUnavailable);
        const failedState = saveWorkflowState(createIdentityScopedWorkflowState({
          workflowLoading: false,
          statusMessage: failure.statusMessage,
          error: failure.error,
        }));
        setState(failedState);
        setReportText("");
        setTherapistNotes("");
        setGoalsText("");
        setExportedCha("");
        setBackendReport(null);
        setPrimaryTherapistLabel("");
        setPrimaryTherapistAssigned(false);
        setConfirmationChecked(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseId, reportId, sessionId, setBackendUnavailable, transcriptId]);

  useEffect(() => {
    let cancelled = false;
    if (!isFinalized || backendReport?.status !== "Signed Off") {
      setSnapshotIntegrity({ status: "not_applicable" });
      return;
    }

    const envelope = validateSignedSnapshotEnvelope(backendReport);
    if (!envelope.valid) {
      setReportText("");
      setSnapshotIntegrity({ status: "invalid", reason: envelope.reason });
      return;
    }

    setReportText("");
    setSnapshotIntegrity({ status: "checking" });
    void verifySignedSnapshotHash(backendReport).then((result) => {
      if (cancelled) return;
      if (!result.valid) {
        setReportText("");
        setSnapshotIntegrity({ status: "invalid", reason: result.reason });
        return;
      }
      setReportText(signedSnapshotString(backendReport, "markdown") ?? "");
      setSnapshotIntegrity({ status: "valid" });
    });

    return () => {
      cancelled = true;
    };
  }, [backendReport, isFinalized]);

  useEffect(() => {
    if (state.reportSaveStatus !== "unsaved" && state.reportSaveStatus !== "failed") return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [state.reportSaveStatus]);

  const identityLoaded = !hasLocator || Boolean(state.backendReportId && !state.workflowLoading && !state.error);

  function persist(next: WorkflowState) {
    const saved = saveWorkflowState(next);
    setState(saved);
    return saved;
  }

  async function handleGenerateDraft(forceTemplate: boolean = false) {
    if (isFinalized || isStale || !transcriptUnlocked) return;
    setBusy(true);
    const selectedProvider = forceTemplate ? "template" : providerId;
    const reportingState = persist({
      ...state,
      therapistNotes,
      therapyGoals: parseGoals(goalsText),
      statusMessage: "Generating report draft...",
      error: undefined
    });
    try {
      const targetSession = reportingState.backendTranscriptSessionId ?? reportingState.backendSessionId;
      if (!targetSession) throw new Error("Persistent session unavailable.");
      const report = await sessionReportService.generate(targetSession, selectedProvider, allowFallback, therapistNotes, parseGoals(goalsText));
      if (!report.report_id) throw new Error("Report ID missing.");
      setBackendReport(report);
      const markdown = report.content_markdown ?? report.markdown ?? "";
      setReportText(markdown);

      persist({
        ...reportingState,
        backendReportId: report.report_id,
        backendReportVersion: report.version,
        reportId: report.report_id,
        reportMarkdown: markdown,
        featureSetId: report.feature_result_id,
        featureSchemaVersion: report.feature_schema_version,
        reportGeneratedFromVersions: report.generated_from_versions,
        reportStatus: "draft",
        reportSaveStatus: "saved",
        statusMessage: report.status === "Failed"
          ? "Safety check failed. The drafted text contains prohibited phrases or missing disclaimers."
          : "Draft report preview generated successfully. Therapist edits required.",
        error: undefined
      });
    } catch (err: any) {
      persist({ ...reportingState, reportSaveStatus: "failed", statusMessage: "Report generation failed.", error: err?.message ?? "Error drafting report." });
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveDraft() {
    if (!state.reportId || isFinalized || isStale) return;
    setBusy(true);
    const saving = persist({ ...state, reportSaveStatus: "saving", statusMessage: "Saving report draft...", error: undefined });
    try {
      const markdown = mergeReportInputs(reportText, therapistNotes, parseGoals(goalsText));
      const report = await sessionReportService.save(state.reportId, markdown, therapistNotes);
      setBackendReport(report);
      setReportText(report.markdown ?? markdown);

      persist({
        ...saving,
        reportMarkdown: report.markdown ?? markdown,
        therapistNotes,
        therapyGoals: parseGoals(goalsText),
        reportStatus: "reviewed",
        reportSaveStatus: "saved",
        statusMessage: report.status === "Failed" ? "Saved, but safety validation issues exist." : "Report draft saved.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({ ...saving, reportSaveStatus: "failed", statusMessage: "Failed to save report.", error: "Backend unavailable. Report edits remain unsaved." });
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(format: "markdown" | "html") {
    if (!state.reportId || !isFinalized || signedActionsBlocked) return;
    try {
      const exported = await sessionReportService.export(state.reportId, format);
      downloadTextFile(exported.content, exported.filename, exported.content_type);
      persist({ ...state, statusMessage: `${format === "markdown" ? "Markdown" : "HTML"} report exported.`, error: undefined });
    } catch {
      setBackendUnavailable(true);
      persist({ ...state, statusMessage: "Export failed.", error: "Backend report export was unavailable." });
    }
  }

  async function handleExportCha() {
    if (!state.backendTranscriptId || !state.transcriptAttested) return;
    try {
      const exported = await sessionReportService.exportReviewedTranscript(state.backendTranscriptId);
      setExportedCha(exported.cha_text);
      downloadTextFile(exported.cha_text, exported.filename, "text/x-chat");
    } catch {
      setBackendUnavailable(true);
      persist({ ...state, statusMessage: "Export failed.", error: "Backend transcript export was unavailable." });
    }
  }

  async function handleCopyLocalDemoShareLink() {
    if (isStale || signedActionsBlocked) return;
    const localLink = resolveSessionHref("report", state.backendSessionId ?? state.sessionId, {
      caseId: state.caseId,
      transcriptId: state.backendTranscriptId,
      reportId: state.reportId,
    });
    await navigator.clipboard?.writeText(localLink);
    persist({
      ...state,
      reportMarkdown: reportText,
      shareStatus: "Local demo share link copied",
      statusMessage: "Local demo share-link status recorded. No caregiver delivery endpoint was created."
    });
  }

  function handleMarkSent() {
    if (isStale || signedActionsBlocked) return;
    persist({
      ...state,
      reportMarkdown: reportText,
      shareStatus: "Caregiver share recorded locally",
      statusMessage: "Caregiver share status recorded locally. No external delivery was sent."
    });
  }

  async function handleFinalize() {
    if (isFinalized || isStale || !state.reportId || state.reportSaveStatus !== "saved" || !confirmationChecked) return;
    setBusy(true);
    try {
      const finalized = await sessionReportService.finalize(state.reportId, confirmationChecked);
      setBackendReport(finalized);
      const markdown = finalized.status === "Signed Off" ? "" : finalized.markdown ?? "";
      setReportText(markdown);
      persist({
        ...state,
        reportStatus: "finalized",
        reportMarkdown: markdown,
        reportSaveStatus: "saved",
        finalizeStatus: "Report finalized.",
        statusMessage: "Report finalized.",
        error: undefined
      });
    } catch (err: any) {
      persist({ ...state, statusMessage: "Report finalization failed.", error: err?.message ?? "Safety validation error. Correct prohibited claims and missing disclaimers." });
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateRevision() {
    const currentReportId = backendReport?.report_id ?? state.reportId;
    if (!isFinalized || signedActionsBlocked || !currentReportId || revisionInFlightRef.current || backendUnavailable) return;
    revisionInFlightRef.current = true;
    setBusy(true);
    persist({ ...state, statusMessage: "Creating a report revision...", error: undefined });
    try {
      const revision = await sessionReportService.createRevision(currentReportId, resetSignedReportForRevision(reportText), therapistNotes);
      if (!revision.report_id) throw new Error("Report revision ID missing.");
      const markdown = revision.markdown ?? reportText;
      setBackendReport(revision);
      setReportText(markdown);
      setTherapistNotes(revision.therapist_notes ?? therapistNotes);
      setGoalsText((revision.session_goals ?? state.therapyGoals).join("\n"));
      setConfirmationChecked(false);
      replaceRevisionUrl(
        revision.session_id ?? state.backendSessionId ?? state.sessionId,
        revision.report_id,
        revision.case_id ?? state.caseId,
        revision.transcript_id ?? state.backendTranscriptId,
      );
      persist({
        ...state,
        backendReportId: revision.report_id,
        backendReportVersion: revision.version,
        reportId: revision.report_id,
        reportMarkdown: markdown,
        therapistNotes: revision.therapist_notes ?? therapistNotes,
        therapyGoals: revision.session_goals ?? state.therapyGoals,
        featureSetId: revision.feature_result_id ?? state.featureSetId,
        featureSchemaVersion: revision.feature_schema_version ?? state.featureSchemaVersion,
        reportGeneratedFromVersions: revision.generated_from_versions ?? state.reportGeneratedFromVersions,
        reportStatus: "draft",
        reportSaveStatus: "saved",
        finalizeStatus: undefined,
        statusMessage: "Draft revision created. Review and save it before sign-off.",
        error: undefined,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Report revision could not be created.";
      persist({ ...state, statusMessage: "Report revision failed.", error: message });
    } finally {
      revisionInFlightRef.current = false;
      setBusy(false);
    }
  }

  const isFinalizeDisabled = busy ||
    state.reportStatus === "not_started" ||
    isStale ||
    isFinalized ||
    state.reportSaveStatus !== "saved" ||
    !confirmationChecked ||
    !primaryTherapistAssigned ||
    isFailedSafety ||
    backendReport?.finalization_blocked === true ||
    backendUnavailable;


  return {
    hasLocator,
    state,
    setState,
    busy,
    reportText,
    setReportText,
    therapistNotes,
    setTherapistNotes,
    goalsText,
    setGoalsText,
    exportedCha,
    providerId,
    setProviderId,
    allowFallback,
    setAllowFallback,
    backendReport,
    primaryTherapistLabel,
    primaryTherapistAssigned,
    confirmationChecked,
    setConfirmationChecked,
    snapshotIntegrity,
    backendUnavailable,
    isFailedSafety,
    isFinalized,
    isStale,
    isNotStarted,
    isSnapshotIntegrityChecking,
    hasSnapshotIntegrityError,
    signedSnapshotVerified,
    signedActionsBlocked,
    canRenderReportMetadata,
    isEditorLocked,
    transcriptUnlocked,
    identityLoaded,
    persist,
    handleGenerateDraft,
    handleSaveDraft,
    handleExport,
    handleExportCha,
    handleCopyLocalDemoShareLink,
    handleMarkSent,
    handleFinalize,
    handleCreateRevision,
    isFinalizeDisabled,
  };
}

export type SessionReportController = ReturnType<typeof useSessionReport>;
