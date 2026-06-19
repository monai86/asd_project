"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, ClipboardPaste, FileText, MessageSquare, ShieldCheck, Sparkles, TrendingUp, UploadCloud, Wand2 } from "lucide-react";

import { GlassCard, GradientButton, ResultMetricCard, SafetyNote, WorkflowStep } from "@/components/liquid-ui";
import { BrowserAudioRecorder, type RecordingMetadata } from "@/components/browser-audio-recorder";
import { TranscriptEditorPanel } from "@/components/transcript-editor-panel";
import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import {
  createExperimentalTranscriptionJob,
  getExperimentalTranscriptionJob,
  releaseExperimentalAudioUpload,
  uploadRecordedAudio
} from "@/lib/experimental-transcription-service";
import {
  attestBackendTranscript,
  backendTranscriptLines,
  buildBasicChatExport,
  createBackendSession,
  createBackendTranscript,
  ensureWorkflowSession,
  createInitialWorkflowState,
  defaultTranscript,
  evaluateTranscriptQa,
  exportReviewedCha,
  createLocalMlDecisionSupport,
  generateBackendMlDecisionSupport,
  generateBackendReport,
  getBackendCase,
  getBackendSession,
  getBackendSessionTranscript,
  getBackendTranscript,
  loadWorkflowState,
  prepareTranscriptIntake,
  runBackendQa,
  runBackendAnalysis,
  saveWorkflowState,
  type TranscriptLine,
  updateBackendTranscript,
  type WorkflowSource,
  type WorkflowState
} from "@/lib/workflow";

type SessionWorkspaceClientProps = {
  sessionId?: string;
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
  view?: string;
  mode?: string;
};

export function SessionWorkspaceClient({ sessionId, caseId, transcriptId, reportId, view = "record", mode }: SessionWorkspaceClientProps) {
  const [state, setState] = useState<WorkflowState>(() => createInitialWorkflowState());
  const [busy, setBusy] = useState(false);
  const [draftTranscript, setDraftTranscript] = useState(defaultTranscript);
  const [editorLines, setEditorLines] = useState<TranscriptLine[]>([]);
  const [sourceFilename, setSourceFilename] = useState<string | undefined>();
  const [intakeError, setIntakeError] = useState("");
  const [intakeWarnings, setIntakeWarnings] = useState<string[]>([]);
  const [intakeValidationIssues, setIntakeValidationIssues] = useState<string[]>([]);
  const [recordedAudio, setRecordedAudio] = useState<{ blob: Blob; metadata: RecordingMetadata } | null>(null);
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    const stored = loadWorkflowState();
    const hasLocator = Boolean(sessionId || transcriptId);
    if (!hasLocator) {
      setState(stored);
      setDraftTranscript(stored.transcriptText || (mode === "paste" || mode === "cha" ? "" : defaultTranscript));
      setEditorLines(stored.transcriptLines);
      setSourceFilename(stored.sourceFilename);
      setIntakeWarnings(stored.chatWarnings);
      setIntakeValidationIssues(stored.chatValidationIssues);
      return;
    }

    setState({
      ...stored,
      transcriptText: "",
      transcriptLines: [],
      transcriptReady: false,
      transcriptAttested: false,
      transcriptReviewStatus: "not_started",
      qaStatus: "not_run",
      qaIssues: [],
      workflowLoading: true,
      statusMessage: "Loading persisted workflow...",
      error: undefined
    });
    void (async () => {
      try {
        const backendSession = sessionId ? await getBackendSession(sessionId) : undefined;
        const resolvedTranscriptId = transcriptId ?? backendSession?.transcript_id;
        const transcript = resolvedTranscriptId
          ? await getBackendTranscript(resolvedTranscriptId)
          : backendSession
            ? await getBackendSessionTranscript(backendSession.session_id).catch(() => undefined)
            : undefined;
        const resolvedCaseId = caseId ?? backendSession?.case_id ?? transcript?.case_id;
        const childCase = resolvedCaseId ? await getBackendCase(resolvedCaseId) : undefined;
        const lines = transcript ? backendTranscriptLines(transcript) : [];
        const parsed = transcript?.raw_text ? prepareTranscriptIntake("cha-upload", transcript.raw_text) : undefined;
        const hydrated = saveWorkflowState({
          ...createInitialWorkflowState(),
          ...stored,
          caseId: resolvedCaseId,
          caseInfo: {
            caseId: resolvedCaseId,
            clientLabel: childCase?.nickname ?? childCase?.child_code ?? stored.caseInfo.clientLabel
          },
          childName: childCase?.nickname ?? childCase?.child_code ?? stored.childName,
          backendSessionId: backendSession?.session_id ?? sessionId,
          backendTranscriptSessionId: transcript?.session_id ?? backendSession?.session_id ?? sessionId,
          backendTranscriptId: transcript?.transcript_id,
          backendReportId: reportId ?? backendSession?.report_id,
          reportId: reportId ?? backendSession?.report_id,
          transcriptText: transcript?.raw_text ?? "",
          transcriptLines: lines,
          chatMetadata: parsed?.metadata ?? stored.chatMetadata,
          chatWarnings: parsed?.warnings ?? [],
          chatValidationIssues: parsed?.validationIssues ?? [],
          transcriptReady: Boolean(transcript),
          transcriptAttested: Boolean(transcript?.therapist_attested),
          transcriptReviewStatus: transcript?.therapist_attested ? "reviewed" : transcript ? "in_review" : "not_started",
          qaStatus: normalizeBackendQaStatus(transcript?.qa_status),
          qaIssues: (transcript?.qa_issues ?? []).map((issue) => typeof issue === "string" ? issue : issue.message ?? "Transcript QA issue"),
          transcriptSaveStatus: transcript ? "saved" : "idle",
          workflowLoading: false,
          statusMessage: transcript ? "Persisted transcript loaded." : "Persisted session loaded.",
          error: undefined
        });
        if (cancelled) return;
        setState(hydrated);
        setDraftTranscript(hydrated.transcriptText);
        setEditorLines(hydrated.transcriptLines);
        setIntakeWarnings(hydrated.chatWarnings);
        setIntakeValidationIssues(hydrated.chatValidationIssues);
      } catch {
        if (cancelled) return;
        setBackendUnavailable(true);
        setState({
          ...stored,
          backendSessionId: sessionId,
          backendTranscriptId: transcriptId,
          caseId,
          workflowLoading: false,
          statusMessage: "Backend unavailable.",
          error: "Could not load the persisted workflow. Check the backend and retry."
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseId, mode, reportId, sessionId, setBackendUnavailable, transcriptId]);

  useEffect(() => {
    if (state.transcriptSaveStatus !== "unsaved" && state.transcriptSaveStatus !== "failed") return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [state.transcriptSaveStatus]);

  const transcriptLines = useMemo(() => previewLines(state.transcriptText), [state.transcriptText]);
  const activeMode = mode ?? (state.source === "paste-transcript" ? "paste" : state.source === "cha-upload" ? "cha" : state.source === "audio-upload" ? "audio" : undefined);

  function persist(next: WorkflowState) {
    const saved = saveWorkflowState(next);
    setState(saved);
    return saved;
  }

  function handleRecordingMetadata(metadata: RecordingMetadata) {
    setState((current) => {
      const startingNewRecording = metadata.recordingStatus === "recording"
        && current.recordingStatus !== "recording"
        && current.recordingStatus !== "paused";
      return saveWorkflowState(ensureWorkflowSession(current, "recording", {
        recordingStatus: metadata.recordingStatus,
        recordingSeconds: metadata.durationSeconds,
        audioMimeType: metadata.mimeType,
        recordingCreatedAt: metadata.createdAt,
        hasUnsavedRecording: metadata.hasUnsavedRecording,
        recordingClearedForPrivacy: false,
        mockAudioStored: false,
        transcriptionJobId: startingNewRecording ? undefined : current.transcriptionJobId,
        transcriptionJobStatus: startingNewRecording ? undefined : current.transcriptionJobStatus,
        transcriptionJobMessage: startingNewRecording ? undefined : current.transcriptionJobMessage,
        transcriptDraftLabel: startingNewRecording ? undefined : current.transcriptDraftLabel,
        transcriptText: startingNewRecording ? "" : current.transcriptText,
        transcriptLines: startingNewRecording ? [] : current.transcriptLines,
        transcriptReady: false,
        transcriptReviewStatus: "not_started",
        qaStatus: "not_run",
        qaIssues: [],
        analysisStatus: "not_started",
        reportStatus: "Not started",
        statusMessage: metadata.hasUnsavedRecording
          ? "Recording is available for playback on this page only. It has not been uploaded or transcribed."
          : metadata.recordingStatus === "recording"
            ? "Microphone recording started. Audio remains in memory only."
            : metadata.recordingStatus === "paused"
              ? "Recording paused. Audio remains in memory only."
              : metadata.recordingStatus === "idle"
                ? "In-memory recording cleared."
                : "ASR/transcription remains experimental and is not connected.",
        error: metadata.error
      }));
    });
  }

  async function handleRecordedAudioTranscription() {
    if (!recordedAudio) {
      persist({
        ...state,
        transcriptionJobStatus: "failed",
        transcriptionJobMessage: "No in-memory recording is available. Record audio again.",
        error: "No in-memory recording is available. Record audio again."
      });
      return;
    }

    setBusy(true);
    try {
      const upload = await uploadRecordedAudio(recordedAudio.blob, {
        durationSeconds: recordedAudio.metadata.durationSeconds,
        mimeType: recordedAudio.metadata.mimeType || recordedAudio.blob.type || "audio/webm"
      });
      const job = await createExperimentalTranscriptionJob(upload.uploadId);
      persist(ensureWorkflowSession(state, "recording", {
        mockAudioStored: true,
        transcriptionJobId: job.jobId,
        transcriptionJobStatus: job.status,
        transcriptionJobMessage: job.message,
        transcriptDraftLabel: job.label,
        transcriptReady: false,
        transcriptAttested: false,
        transcriptReviewStatus: "not_started",
        qaStatus: "not_run",
        analysisStatus: "not_started",
        featuresExtracted: false,
        featurePercent: 0,
        featureSummary: [],
        statusMessage: job.message,
        error: undefined
      }));
      window.setTimeout(() => void pollExperimentalTranscriptionJob(job.jobId, upload.uploadId), 350);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Experimental transcription upload failed.";
      persist({
        ...state,
        transcriptionJobStatus: "failed",
        transcriptionJobMessage: message,
        statusMessage: "Experimental transcription job failed.",
        error: message
      });
      setBusy(false);
    }
  }

  async function pollExperimentalTranscriptionJob(jobId: string, uploadId: string) {
    try {
      const job = await getExperimentalTranscriptionJob(jobId);
      if (job.status === "completed" && job.draftTranscript) {
        const draft = prepareTranscriptIntake("cha-upload", job.draftTranscript);
        releaseExperimentalAudioUpload(uploadId);
        setDraftTranscript(draft.transcriptText);
        setEditorLines(draft.transcriptLines);
        setIntakeWarnings([...draft.warnings, "Experimental ASR output may be inaccurate. Verify all wording and speaker labels."]);
        setIntakeValidationIssues(draft.validationIssues);
        setState((current) => saveWorkflowState({
          ...current,
          source: "recording",
          mockAudioStored: true,
          transcriptionJobId: job.jobId,
          transcriptionJobStatus: "completed",
          transcriptionJobMessage: job.message,
          transcriptDraftLabel: job.label,
          transcriptText: draft.transcriptText,
          transcriptLines: draft.transcriptLines,
          chatMetadata: draft.metadata,
          chatWarnings: [...draft.warnings, "Experimental ASR output may be inaccurate. Verify all wording and speaker labels."],
          chatValidationIssues: draft.validationIssues,
          transcriptReady: true,
          transcriptAttested: false,
          transcriptReviewStatus: "draft",
          transcriptCompleteness: 0,
          qaStatus: "not_run",
          qaIssues: [],
          qaSummary: undefined,
          analysisStatus: "not_started",
          featuresExtracted: false,
          featurePercent: 0,
          featureSummary: [],
          reportStatus: "Not started",
          reportMarkdown: undefined,
          statusMessage: job.message,
          error: undefined
        }));
        setBusy(false);
        router.push(workflowHref("/review-transcript", {
          ...state,
          backendSessionId: state.backendSessionId,
          backendTranscriptId: state.backendTranscriptId
        }));
        return;
      }
      if (job.status === "failed") {
        releaseExperimentalAudioUpload(uploadId);
        setState((current) => saveWorkflowState({
          ...current,
          transcriptionJobStatus: "failed",
          transcriptionJobMessage: job.error || job.message,
          statusMessage: "Experimental transcription job failed.",
          error: job.error || job.message
        }));
        setBusy(false);
        return;
      }
      setState((current) => saveWorkflowState({
        ...current,
        transcriptionJobId: job.jobId,
        transcriptionJobStatus: job.status,
        transcriptionJobMessage: job.message,
        statusMessage: job.message,
        error: undefined
      }));
      window.setTimeout(() => void pollExperimentalTranscriptionJob(jobId, uploadId), 350);
    } catch (error) {
      releaseExperimentalAudioUpload(uploadId);
      const message = error instanceof Error ? error.message : "Experimental transcription job failed.";
      setState((current) => saveWorkflowState({
        ...current,
        transcriptionJobStatus: "failed",
        transcriptionJobMessage: message,
        statusMessage: "Experimental transcription job failed.",
        error: message
      }));
      setBusy(false);
    }
  }

  async function handleAudioUpload() {
    setBusy(true);
    const localSession = persist(ensureWorkflowSession(state, "audio-upload", {
      mockAudioStored: true,
      recordingStatus: "stopped",
      transcriptReviewStatus: "not_started",
      qaStatus: "not_run",
      qaIssues: [],
      analysisStatus: "not_started",
      reportStatus: "Not started",
      statusMessage: "Audio upload is represented in local workflow state while the optional session service is checked.",
      error: undefined
    }));
    try {
      const session = await createBackendSession("audio-upload");
      persist({
        ...localSession,
        backendSessionId: session.session_id,
        caseId: session.case_id,
        caseInfo: {
          ...localSession.caseInfo,
          caseId: session.case_id
        },
        mockAudioStored: true,
        recordingStatus: "stopped",
        statusMessage: "Audio upload is experimental. A backend session was created, but real ASR is not enabled in this UI step.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({
        ...localSession,
        statusMessage: "Audio upload is experimental and is represented in local workflow state.",
        error: "Backend session endpoint unavailable; no audio bytes were uploaded."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleTranscriptSubmit(source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">, reviewed = false) {
    let intake;
    try {
      intake = prepareTranscriptIntake(source, draftTranscript);
      setIntakeError("");
      setIntakeWarnings(intake.warnings);
      setIntakeValidationIssues(intake.validationIssues);
    } catch (error) {
      setIntakeError(error instanceof Error ? error.message : "Transcript could not be read.");
      return;
    }
    setBusy(true);
    const localSession = persist(ensureWorkflowSession(state, source, {
      sourceFilename: source === "cha-upload" ? sourceFilename : undefined,
      transcriptText: intake.transcriptText,
      transcriptLines: intake.transcriptLines,
      chatMetadata: intake.metadata,
      chatWarnings: intake.warnings,
      chatValidationIssues: intake.validationIssues,
      transcriptReady: true,
      transcriptReviewStatus: reviewed ? "in_review" : "draft",
      transcriptAttested: false,
      qaStatus: "not_run",
      qaIssues: [],
      analysisStatus: "not_started",
      reportStatus: "Not started",
      statusMessage: reviewed ? "Saving therapist transcript review..." : "Saving transcript source material...",
      error: undefined
    }));
    try {
      let backendSessionId = localSession.backendSessionId;
      let backendCaseId = localSession.caseId;
      if (!backendSessionId) {
        const backendSession = await createBackendSession(source);
        backendSessionId = backendSession.session_id;
        backendCaseId = backendSession.case_id;
      }
      const reviewerNote = reviewed
        ? "Therapist reviewed the transcript in the simplified workflow."
        : source === "cha-upload"
          ? "CHA transcript added to the simplified workflow."
          : "Pasted transcript added to the simplified workflow.";
      const updated = localSession.backendTranscriptId
        ? await updateBackendTranscript(localSession.backendTranscriptId, intake.transcriptText, reviewerNote)
        : await createBackendTranscript(
            backendSessionId,
            source,
            draftTranscript,
            intake.transcriptText,
            sourceFilename
          );
      const savedState = persist({
        ...localSession,
        backendSessionId,
        backendTranscriptId: updated.transcript_id,
        backendTranscriptSessionId: backendSessionId,
        caseId: backendCaseId,
        caseInfo: {
          ...localSession.caseInfo,
          caseId: backendCaseId
        },
        transcriptText: intake.transcriptText,
        transcriptLines: intake.transcriptLines,
        chatMetadata: intake.metadata,
        chatWarnings: intake.warnings,
        chatValidationIssues: intake.validationIssues,
        transcriptReady: true,
        transcriptCompleteness: 92,
        transcriptAttested: Boolean(updated.therapist_attested),
        transcriptReviewStatus: updated.therapist_attested ? "reviewed" : "draft",
        transcriptSaveStatus: "saved",
        statusMessage: "Transcript saved and ready for therapist review.",
        error: undefined
      });
      router.push(workflowHref("/review-transcript", savedState));
      return;
    } catch {
      setBackendUnavailable(true);
      persist({
        ...localSession,
        transcriptText: intake.transcriptText,
        transcriptLines: intake.transcriptLines,
        chatMetadata: intake.metadata,
        chatWarnings: intake.warnings,
        chatValidationIssues: intake.validationIssues,
        transcriptReady: false,
        transcriptAttested: false,
        transcriptReviewStatus: "draft",
        transcriptSaveStatus: "failed",
        transcriptCompleteness: 0,
        statusMessage: "Failed to save transcript.",
        error: "Backend unavailable. Transcript input remains available for retry and was not persisted."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyze() {
    if (!isTranscriptUnlocked(state)) {
      persist({
        ...state,
        statusMessage: "Feature extraction is locked until the transcript is reviewed and attested.",
        error: "Review the transcript, run QA, and attest it before extracting features."
      });
      return;
    }
    setBusy(true);
    const analyzingState = persist(ensureWorkflowSession(state, state.source ?? "recording", {
      analysisStatus: "processing",
      statusMessage: "Extracting descriptive language-sample cues from the reviewed transcript..."
    }));
    try {
      const targetSession = analyzingState.backendTranscriptSessionId ?? analyzingState.backendSessionId;
      if (!targetSession || !analyzingState.backendTranscriptId) throw new Error("Persistent transcript unavailable.");
      const backendAnalysis = await runBackendAnalysis(targetSession, analyzingState.backendTranscriptId);
      persist({
        ...analyzingState,
        ...backendAnalysis,
        analysisStatus: "completed",
        statusMessage: "Language-sample feature extraction completed from the reviewed, attested transcript.",
        error: undefined
      });
      router.push(workflowHref("/results", analyzingState));
    } catch {
      setBackendUnavailable(true);
      persist({
        ...analyzingState,
        analysisStatus: "failed",
        featuresExtracted: false,
        statusMessage: "Feature extraction failed.",
        error: "Backend unavailable. No feature result was recorded."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateReport() {
    if (!isTranscriptUnlocked(state)) {
      persist({
        ...state,
        statusMessage: "Report generation is locked until the transcript is reviewed and attested.",
        error: "Review the transcript, run QA, and attest it before generating a report."
      });
      return;
    }
    setBusy(true);
    const reportingState = persist(ensureWorkflowSession(state, state.source ?? "recording", {
      statusMessage: "Preparing a draft report..."
    }));
    try {
      const targetSession = reportingState.backendTranscriptSessionId ?? reportingState.backendSessionId;
      if (!targetSession) throw new Error("Persistent session unavailable.");
      const report = await generateBackendReport(targetSession);
      if (!report.report_id) throw new Error("Report ID missing.");
      const savedState = persist({
        ...reportingState,
        backendReportId: report.report_id,
        reportId: report.report_id,
        reportMarkdown: report.content_markdown ?? report.markdown ?? "",
        reportStatus: report.status === "Signed Off" ? "Finalized" : "Draft",
        reportSaveStatus: "saved",
        statusMessage: "Draft report generated. All text remains editable and therapist review is required.",
        error: undefined
      });
      router.push(workflowHref("/report-summary", savedState, report.report_id));
    } catch {
      setBackendUnavailable(true);
      persist({
        ...reportingState,
        reportSaveStatus: "failed",
        statusMessage: "Report generation failed.",
        error: "Backend unavailable. No report draft was created."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateMlDecisionSupport() {
    if (!state.featuresExtracted) {
      persist({
        ...state,
        statusMessage: "ML decision support requires extracted features from a reviewed transcript.",
        error: "Extract transcript features before generating model-informed review cues."
      });
      return;
    }
    setBusy(true);
    try {
      const targetSession = state.backendTranscriptSessionId ?? state.backendSessionId;
      let mlDecisionSupport = createLocalMlDecisionSupport(state.featureSummary);
      if (targetSession) {
        try {
          mlDecisionSupport = await generateBackendMlDecisionSupport(targetSession);
        } catch {
          setBackendUnavailable(true);
          // Local model-informed cue formatting preserves the non-diagnostic workflow when the API is unavailable.
        }
      }
      persist({
        ...state,
        mlDecisionSupport,
        statusMessage: "ML decision-support draft generated. Therapist review, editing, or dismissal is required.",
        error: undefined
      });
    } finally {
      setBusy(false);
    }
  }

  function handleUpdateMlSuggestions(value: string) {
    if (!state.mlDecisionSupport) return;
    persist({
      ...state,
      mlDecisionSupport: {
        ...state.mlDecisionSupport,
        reviewSuggestions: value.split("\n").map((line) => line.trim()).filter(Boolean)
      }
    });
  }

  function handleDismissMlDecisionSupport() {
    if (!state.mlDecisionSupport) return;
    persist({
      ...state,
      mlDecisionSupport: {
        ...state.mlDecisionSupport,
        dismissed: true
      },
      statusMessage: "ML decision-support draft dismissed. Report workflow remains available."
    });
  }

  if (view === "results") {
    return (
      <>
        <BackendAvailabilityBanner unavailable={backendUnavailable} />
        <SessionResultsView
          state={state}
          busy={busy}
          onGenerateReport={handleGenerateReport}
          onGenerateMlDecisionSupport={handleGenerateMlDecisionSupport}
          onUpdateMlSuggestions={handleUpdateMlSuggestions}
          onDismissMlDecisionSupport={handleDismissMlDecisionSupport}
        />
      </>
    );
  }

  if (view === "transcript") {
    return (
      <>
        <BackendAvailabilityBanner unavailable={backendUnavailable} />
        <TranscriptReviewView
          state={state}
          lines={editorLines}
          busy={busy}
          onLinesChange={(lines) => {
          setEditorLines(lines);
          persist({
            ...state,
            transcriptLines: lines,
            transcriptAttested: false,
            transcriptReviewStatus: "in_review",
            qaStatus: "not_run",
            qaIssues: [],
            qaSummary: undefined,
            transcriptSaveStatus: "unsaved",
            analysisStatus: "not_started",
            featuresExtracted: false,
            featurePercent: 0,
            featureSummary: [],
            reportStatus: "Not started",
            reportMarkdown: undefined,
            statusMessage: "Unsaved transcript edits.",
            error: undefined
          });
        }}
        onSaveDraft={() => handleSaveTranscriptDraft(editorLines)}
        onRunQa={() => handleRunTranscriptQa(editorLines)}
        onAttest={handleAttestTranscript}
        onGenerateReport={handleGenerateReport}
          onExport={handleExportCha}
        />
      </>
    );
  }

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <div className="grid gap-6 lg:grid-cols-[430px_1fr]">
      <div className="space-y-5">
        <header>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold text-ink">Record & Analyze</h1>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-800">Experimental</span>
          </div>
          <p className="mt-2 text-slate-600">Capture session audio and prepare decision-support materials for therapist review.</p>
        </header>

        <GlassCard className="p-5 text-center">
          <BrowserAudioRecorder
            initialDurationSeconds={state.recordingSeconds}
            hadUnsavedRecording={state.recordingClearedForPrivacy}
            onMetadataChange={handleRecordingMetadata}
            onRecordingReady={(blob, metadata) => setRecordedAudio({ blob, metadata })}
            onRecordingCleared={() => setRecordedAudio(null)}
          />
        </GlassCard>

        <ExperimentalTranscriptionPanel
          hasRecording={Boolean(recordedAudio)}
          status={state.transcriptionJobStatus}
          message={state.transcriptionJobMessage}
          busy={busy}
          onUpload={handleRecordedAudioTranscription}
        />

        <SourceInputPanel
          mode={activeMode}
          draftTranscript={draftTranscript}
          busy={busy}
          error={intakeError}
          warnings={intakeWarnings}
          validationIssues={intakeValidationIssues}
          onDraftChange={(value) => {
            setDraftTranscript(value);
            setIntakeError("");
            setIntakeWarnings([]);
            setIntakeValidationIssues([]);
          }}
          onChaFile={async (file) => {
            if (!file.name.toLowerCase().endsWith(".cha")) {
              setSourceFilename(undefined);
              setIntakeError("Invalid .cha file: choose a file with the .cha extension.");
              return;
            }
            const text = await file.text();
            try {
              const intake = prepareTranscriptIntake("cha-upload", text);
              setSourceFilename(file.name);
              setDraftTranscript(intake.transcriptText);
              setIntakeError("");
              setIntakeWarnings(intake.warnings);
              setIntakeValidationIssues(intake.validationIssues);
            } catch (error) {
              setSourceFilename(undefined);
              setDraftTranscript(text);
              setIntakeError(error instanceof Error ? error.message : "Invalid .cha file.");
              setIntakeWarnings([]);
              setIntakeValidationIssues([]);
            }
          }}
          onAudioUpload={handleAudioUpload}
          onTranscriptSubmit={handleTranscriptSubmit}
        />

        <GlassCard className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-bold text-ink">Live Transcript <span className="font-normal text-slate-600">(preview)</span></h2>
            <span className="inline-flex items-center gap-1 text-sm font-semibold text-moss">
              <span className="h-2 w-2 rounded-full bg-moss" />
              {state.transcriptReady ? "Ready" : "Preview"}
            </span>
          </div>
          <div className="space-y-2 text-slate-700">
            {state.transcriptReady && transcriptLines.length > 0
              ? transcriptLines.map((line) => <p key={line}>{line}</p>)
              : (
                <div className="rounded-xl border border-dashed border-line bg-white/40 p-4 text-center">
                  <p className="font-semibold text-ink">No transcript available yet</p>
                  <p className="mt-1 text-sm text-slate-600">Record and upload audio for experimental ASR, paste a transcript, or import a .cha file.</p>
                </div>
              )}
          </div>
        </GlassCard>

        {state.transcriptReady && !isTranscriptUnlocked(state) ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900" role="alert">
            Feature extraction requires a saved, reviewed, and attested transcript.
          </div>
        ) : null}

        <GradientButton
          icon={Sparkles}
          className="w-full text-xl"
          onClick={handleAnalyze}
          disabled={busy || !isTranscriptUnlocked(state)}
          aria-label="Extract language-sample features"
        >
          {busy ? "Extracting..." : "Extract language-sample features"}
        </GradientButton>

        <GlassCard className="p-5">
          <h2 className="mb-4 font-bold text-ink">What happens next</h2>
          <div className="flex gap-2">
            <WorkflowStep icon={FileText} title="Transcript ready" helper={state.transcriptReady ? "Available" : "After upload or recording"} tone="purple" />
            <WorkflowStep icon={CheckCircle2} title="Features extracted" helper={state.featuresExtracted ? "Complete" : "After review gate"} tone="green" />
            <WorkflowStep icon={Wand2} title="Suggested next step" helper="Review" tone="orange" />
          </div>
        </GlassCard>
        <WorkflowStatus state={state} />
        <SafetyNote>Decision-support only. Not diagnostic. Transcript must be reviewed before report use.</SafetyNote>
      </div>

      <SessionResultsPreview state={state} onGenerateReport={handleGenerateReport} busy={busy} />
      </div>
    </>
  );

  async function handleSaveTranscriptDraft(lines: TranscriptLine[]) {
    setBusy(true);
    const transcriptText = buildBasicChatExport({
      lines,
      metadata: state.chatMetadata,
      includeMedia: state.mockAudioStored || Boolean(state.chatMetadata.media),
      fallbackMediaName: `${state.sessionId ?? "local-session"}_audio`,
      allowInvalid: true
    }).trimEnd();
    const next = persist(ensureWorkflowSession(state, state.source ?? "paste-transcript", {
      transcriptText,
      transcriptLines: lines,
      transcriptReady: lines.length > 0,
      transcriptAttested: false,
      transcriptReviewStatus: "in_review",
      qaStatus: "not_run",
      qaIssues: [],
      qaSummary: undefined,
      analysisStatus: "not_started",
      featuresExtracted: false,
      featurePercent: 0,
      featureSummary: [],
      reportStatus: "Not started",
      reportMarkdown: undefined,
      transcriptSaveStatus: "saving",
      statusMessage: "Saving transcript draft...",
      error: undefined
    }));
    setDraftTranscript(transcriptText);
    try {
      if (!next.backendTranscriptId) throw new Error("No persistent transcript exists.");
      const updated = await updateBackendTranscript(next.backendTranscriptId, transcriptText, "Therapist saved transcript editor draft.");
      const savedLines = backendTranscriptLines(updated);
      setEditorLines(savedLines.length ? savedLines : lines);
      persist({
        ...next,
        transcriptLines: savedLines.length ? savedLines : lines,
        transcriptSaveStatus: "saved",
        statusMessage: "Transcript draft saved.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({
        ...next,
        transcriptSaveStatus: "failed",
        statusMessage: "Failed to save transcript.",
        error: "Backend unavailable. Edits remain unsaved and can be retried."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleRunTranscriptQa(lines: TranscriptLine[]) {
    if (!state.backendTranscriptId || state.transcriptSaveStatus !== "saved") {
      persist({ ...state, statusMessage: "Save transcript edits before running QA.", error: "Transcript QA requires a backend-saved draft." });
      return;
    }
    const localQa = evaluateTranscriptQa(lines, state.chatMetadata);
    setBusy(true);
    const transcriptText = buildBasicChatExport({
      lines,
      metadata: state.chatMetadata,
      includeMedia: state.mockAudioStored || Boolean(state.chatMetadata.media),
      fallbackMediaName: `${state.sessionId ?? "local-session"}_audio`,
      allowInvalid: true
    }).trimEnd();
    let next = persist({
      ...state,
      transcriptText,
      transcriptLines: lines,
      transcriptReady: lines.length > 0,
      transcriptAttested: false,
      transcriptReviewStatus: "in_review",
      qaStatus: localQa.status,
      qaIssues: localQa.issues,
      qaSummary: localQa.summary,
      statusMessage: "QA running...",
      error: undefined
    });
    const targetTranscriptId = next.backendTranscriptId;
    if (targetTranscriptId) {
      try {
        const backendQa = await runBackendQa(targetTranscriptId);
        next = persist({
          ...next,
          qaStatus: (backendQa.status ?? backendQa.qa_status ?? next.qaStatus) as any,
          qaIssues: backendQa.issues ?? next.qaIssues,
          qaSummary: backendQa.summary ?? localQa.summary,
          statusMessage: backendQa.summary ?? localQa.summary
        });
      } catch {
        setBackendUnavailable(true);
        persist({ ...next, qaStatus: "fail", statusMessage: "QA failed.", error: "Backend QA was unavailable. Retry when the backend is available." });
      }
    } else {
      persist({ ...next, qaStatus: "fail", statusMessage: "QA failed.", error: "No persistent transcript ID is available." });
    }
    setBusy(false);
  }

  async function handleAttestTranscript() {
    if (state.qaStatus === "not_run" || state.qaStatus === "fail" || !state.backendTranscriptId || state.transcriptSaveStatus !== "saved") return;
    setBusy(true);
    persist({ ...state, statusMessage: "Recording transcript attestation...", error: undefined });
    try {
      await attestBackendTranscript(state.backendTranscriptId);
      persist({
        ...state,
        transcriptAttested: true,
        transcriptReviewStatus: "reviewed",
        statusMessage: "Attestation complete.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({
        ...state,
        transcriptAttested: false,
        transcriptReviewStatus: "in_review",
        statusMessage: "Attestation failed.",
        error: "Backend unavailable. Attestation was not recorded."
      });
    }
    setBusy(false);
  }

  function handleExportCha() {
    if (!state.backendTranscriptId) return;
    void exportReviewedCha(state.backendTranscriptId).then((result) => {
      downloadText(result.cha_text, result.filename, "text/x-chat");
    }).catch(() => persist({ ...state, statusMessage: "Export failed.", error: "Backend unavailable. The transcript was not exported." }));
  }
}

function normalizeBackendQaStatus(status?: string): WorkflowState["qaStatus"] {
  const normalized = status?.toLowerCase();
  if (normalized === "pass") return "pass";
  if (normalized === "warning") return "warning";
  if (normalized === "fail") return "fail";
  return "not_run";
}

function workflowQuery(state: WorkflowState, reportId?: string) {
  const params = new URLSearchParams();
  if (state.caseId) params.set("case_id", state.caseId);
  if (state.backendSessionId) params.set("session_id", state.backendSessionId);
  if (state.backendTranscriptId) params.set("transcript_id", state.backendTranscriptId);
  if (reportId ?? state.backendReportId ?? state.reportId) {
    params.set("report_id", reportId ?? state.backendReportId ?? state.reportId ?? "");
  }
  return params.toString();
}

function workflowHref(path: string, state: WorkflowState, reportId?: string) {
  const query = workflowQuery(state, reportId);
  return query ? `${path}?${query}` : path;
}

function downloadText(text: string, filename: string, contentType: string) {
  if (typeof document === "undefined" || typeof URL.createObjectURL !== "function") return;
  const url = URL.createObjectURL(new Blob([text], { type: `${contentType};charset=utf-8` }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function SourceInputPanel({
  mode,
  draftTranscript,
  busy,
  error,
  warnings,
  validationIssues,
  onDraftChange,
  onChaFile,
  onAudioUpload,
  onTranscriptSubmit
}: {
  mode?: string;
  draftTranscript: string;
  busy: boolean;
  error: string;
  warnings: string[];
  validationIssues: string[];
  onDraftChange: (value: string) => void;
  onChaFile: (file: File) => void;
  onAudioUpload: () => void;
  onTranscriptSubmit: (source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">) => void;
}) {
  if (mode === "audio") {
    return (
      <GlassCard className="p-5">
        <h2 className="font-bold text-ink">Upload audio</h2>
        <p className="mt-2 text-sm text-slate-600">Experimental only. This creates a session record, but real ASR is not implemented in this step.</p>
        <GradientButton icon={UploadCloud} className="mt-4 w-full" onClick={onAudioUpload} disabled={busy}>
          Mark audio upload as experimental
        </GradientButton>
      </GlassCard>
    );
  }

  if (mode === "cha" || mode === "paste") {
    const source = mode === "cha" ? "cha-upload" : "paste-transcript";
    return (
      <GlassCard className="p-5">
        <div className="mb-3 flex items-center gap-2">
          {mode === "cha" ? <FileText size={22} aria-hidden="true" className="text-blossom" /> : <ClipboardPaste size={22} aria-hidden="true" className="text-aqua" />}
          <h2 className="font-bold text-ink">{mode === "cha" ? "Upload .cha" : "Paste transcript"}</h2>
        </div>
        {mode === "cha" ? (
          <>
            <label className="sr-only" htmlFor="cha-transcript-file">CHA transcript file</label>
            <input
              id="cha-transcript-file"
              type="file"
              accept=".cha"
              className="mb-3 block w-full rounded-2xl border border-line bg-white/70 px-3 py-3 text-sm"
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                if (file) void onChaFile(file);
              }}
            />
          </>
        ) : null}
        <textarea className="min-h-44 w-full rounded-2xl border border-line bg-white/70 p-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical" value={draftTranscript} onChange={(event) => onDraftChange(event.target.value)} aria-label={mode === "cha" ? "CHA transcript text" : "Pasted transcript text"} />
        {error ? (
          <p className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-900 animate-fade-in" role="alert">
            {error}
          </p>
        ) : null}
        {warnings.length > 0 ? (
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
            <p className="font-semibold">Import warnings</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
          </div>
        ) : null}
        {validationIssues.length > 0 ? (
          <div className="mt-3 rounded-xl border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900" role="alert">
            <p className="font-semibold">CHAT validation</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{validationIssues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          </div>
        ) : null}
        <GradientButton icon={CheckCircle2} className="mt-3 w-full" onClick={() => onTranscriptSubmit(source)} disabled={busy || Boolean(error)}>
          Save transcript
        </GradientButton>
      </GlassCard>
    );
  }

  return null;
}

function SessionResultsView({
  state,
  busy,
  onGenerateReport,
  onGenerateMlDecisionSupport,
  onUpdateMlSuggestions,
  onDismissMlDecisionSupport
}: {
  state: WorkflowState;
  busy: boolean;
  onGenerateReport: () => void;
  onGenerateMlDecisionSupport: () => void;
  onUpdateMlSuggestions: (value: string) => void;
  onDismissMlDecisionSupport: () => void;
}) {
  if (!state.transcriptReady && !state.featuresExtracted) {
    return (
      <div className="mx-auto max-w-2xl">
        <GlassCard className="p-8 text-center">
          <Sparkles className="mx-auto text-clinical" size={38} aria-hidden="true" />
          <h1 className="mt-4 text-3xl font-bold text-ink">Session Results</h1>
          <h2 className="mt-3 text-xl font-bold text-ink">No analysis results yet</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-600">
            Add a transcript, complete therapist review and attestation, then extract language-sample features.
          </p>
          <div className="mt-3 flex flex-wrap justify-center gap-2 text-sm text-slate-600">
            <span>Transcript Ready</span>
            <span>Feature Summary</span>
            <span>Review Needed</span>
          </div>
          <div className="mt-5 flex flex-wrap justify-center gap-3">
            <GradientButton href="/record" icon={FileText}>Record or add a transcript</GradientButton>
            <GradientButton href="/review-transcript" icon={FileText}>Review Transcript</GradientButton>
          </div>
          <GradientButton icon={ShieldCheck} className="mt-3" disabled>Generate Report</GradientButton>
        </GlassCard>
      </div>
    );
  }
  return (
    <div className="grid gap-6 lg:grid-cols-[430px_1fr]">
      <div className="space-y-5">
        <header>
          <h1 className="text-3xl font-bold text-ink">Session Results</h1>
          <p className="mt-2 text-slate-600">Here is the session support summary for therapist review.</p>
        </header>
        <GlassCard className="flex items-center gap-3 p-4">
          <span className="grid h-14 w-14 place-items-center rounded-full bg-[#efeaff] font-bold text-clinical">EL</span>
          <div>
            <h2 className="font-bold text-ink">{state.childName}</h2>
            <p className="text-sm text-slate-600">Session workspace · {state.backendTranscriptSessionId ?? state.backendSessionId ?? "local preview"}</p>
          </div>
        </GlassCard>
        <div className="grid grid-cols-3 gap-3">
          <ResultMetricCard icon={FileText} value={`${state.transcriptCompleteness || (state.transcriptReady ? 82 : 0)}%`} label="Transcript Ready" helper={state.transcriptReady ? "Transcript available for review" : "Add transcript before report use"} tone="purple" />
          <ResultMetricCard icon={Sparkles} value={`${state.featurePercent || 0}%`} label="Feature Summary" helper={state.featuresExtracted ? "Feature summary prepared" : "Run analyze after transcript"} tone="green" />
          <ResultMetricCard icon={AlertTriangle} value={String(state.reviewNeededCount)} label="Review Needed" helper="Therapist review required" tone="orange" />
        </div>
        <InsightsCard insights={state.insights} />
        {state.featuresExtracted ? <LanguageSampleFeatureGrid features={state.featureSummary} /> : null}
        {state.featuresExtracted ? (
          <GradientButton icon={Wand2} className="w-full" onClick={onGenerateMlDecisionSupport} disabled={busy}>
            {busy ? "Generating..." : "Generate ML decision support"}
          </GradientButton>
        ) : null}
        {state.mlDecisionSupport && !state.mlDecisionSupport.dismissed ? (
          <GlassCard className="space-y-4 p-5">
            <div>
              <h2 className="text-lg font-bold text-ink">ML decision-support draft</h2>
              <p className="mt-1 text-sm text-slate-600">Editable review aid. It does not control report generation or finalization.</p>
            </div>
            <section>
              <h3 className="font-bold text-ink">Pattern cues</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {state.mlDecisionSupport.patternCues.map((cue) => <li key={cue}>{cue}</li>)}
              </ul>
            </section>
            <section>
              <h3 className="font-bold text-ink">Review suggestions</h3>
              <textarea
                aria-label="Editable ML review suggestions"
                className="mt-2 min-h-32 w-full rounded-2xl border border-line bg-white/80 p-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                value={state.mlDecisionSupport.reviewSuggestions.join("\n")}
                onChange={(event) => onUpdateMlSuggestions(event.target.value)}
              />
            </section>
            <section>
              <h3 className="font-bold text-ink">Confidence and limitations</h3>
              <p className="mt-2 text-sm font-semibold capitalize text-slate-700">Confidence: {state.mlDecisionSupport.confidence}</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {state.mlDecisionSupport.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
              </ul>
            </section>
            <button type="button" className="text-sm font-bold text-slate-600 underline" onClick={onDismissMlDecisionSupport}>
              Dismiss ML decision support
            </button>
          </GlassCard>
        ) : null}
        <GradientButton href="/review-transcript" icon={FileText} className="w-full text-xl">
          Review Transcript
        </GradientButton>
        <GradientButton icon={ShieldCheck} className="w-full text-xl" onClick={onGenerateReport} disabled={busy || !isTranscriptUnlocked(state)}>
          {busy ? "Generating..." : "Generate Report"}
        </GradientButton>
        <WorkflowStatus state={state} />
        <SafetyNote>Decision-support only. Not diagnostic.</SafetyNote>
      </div>
      <SessionResultsPreview state={state} onGenerateReport={onGenerateReport} busy={busy} />
    </div>
  );
}

function TranscriptReviewView({
  state,
  lines,
  busy,
  onLinesChange,
  onSaveDraft,
  onRunQa,
  onAttest,
  onGenerateReport,
  onExport
}: {
  state: WorkflowState;
  lines: TranscriptLine[];
  busy: boolean;
  onLinesChange: (lines: TranscriptLine[]) => void;
  onSaveDraft: () => void;
  onRunQa: () => void;
  onAttest: () => void;
  onGenerateReport: () => void;
  onExport: () => void;
}) {
  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header>
        <h1 className="text-3xl font-bold text-ink">Review Transcript</h1>
        <p className="mt-2 text-slate-600">Confirm speaker labels and transcript quality before report generation.</p>
      </header>
      <WorkflowStatus state={state} />
      {state.transcriptDraftLabel ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
          <p className="font-bold">{state.transcriptDraftLabel}</p>
          <p className="mt-1 text-sm">Experimental ASR can be inaccurate. Verify wording, timestamps, and speaker labels before attestation.</p>
        </div>
      ) : null}
      {state.chatWarnings && state.chatWarnings.length > 0 ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-950" role="status">
          <p className="font-bold">Import Warnings</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
            {state.chatWarnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}
      <GlassCard className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-bold text-ink">Transcript review</h2>
          <span className={`rounded-full px-3 py-1 text-sm font-bold ${state.transcriptAttested ? "bg-emerald-100 text-emerald-700" : "bg-orange-100 text-orange-700"}`}>
            {state.transcriptAttested ? "Attested" : "Review required"}
          </span>
        </div>
        <TranscriptEditorPanel
          lines={lines}
          qaStatus={state.qaStatus}
          qaIssues={state.qaIssues}
          attested={state.transcriptAttested}
          busy={busy}
          saveStatus={state.transcriptSaveStatus}
          onChange={onLinesChange}
          onSaveDraft={onSaveDraft}
          onRunQa={onRunQa}
          onAttest={onAttest}
          onExport={onExport}
        />
      </GlassCard>
      <GradientButton icon={ShieldCheck} className="w-full text-xl" onClick={onGenerateReport} disabled={busy || !isTranscriptUnlocked(state)}>
        Generate Report
      </GradientButton>
      <SafetyNote>Transcript must be reviewed before report use. Decision-support only. Not diagnostic.</SafetyNote>
    </div>
  );
}

function ExperimentalTranscriptionPanel({
  hasRecording,
  status,
  message,
  busy,
  onUpload
}: {
  hasRecording: boolean;
  status?: WorkflowState["transcriptionJobStatus"];
  message?: string;
  busy: boolean;
  onUpload: () => void;
}) {
  return (
    <GlassCard className="p-5">
      <h2 className="font-bold text-ink">Experimental transcription</h2>
      <p className="mt-2 text-sm text-slate-600">
        Upload is explicit. This local mock processing API creates review workflow output; it does not claim accurate ASR.
      </p>
      {status ? (
        <div className="mt-3 rounded-xl border border-line bg-white/65 p-3" role="status">
          <p className="text-sm font-bold capitalize">Job status: {status}</p>
          {message ? <p className="mt-1 text-xs text-slate-600">{message}</p> : null}
        </div>
      ) : null}
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs font-semibold sm:grid-cols-4" aria-label="Processing job statuses">
        {(["queued", "processing", "completed", "failed"] as const).map((item) => (
          <span
            key={item}
            className={`rounded-lg border px-2 py-2 capitalize ${
              status === item ? "border-clinical bg-[#efeaff] text-clinical" : "border-line bg-white/50 text-slate-500"
            }`}
          >
            {item[0].toUpperCase() + item.slice(1)}
          </span>
        ))}
      </div>
      <GradientButton icon={UploadCloud} className="mt-4 w-full" onClick={onUpload} disabled={!hasRecording || busy}>
        Upload for transcription
      </GradientButton>
      <p className="mt-3 text-xs text-slate-600">Draft transcript — therapist review required.</p>
    </GlassCard>
  );
}

function SessionResultsPreview({ state, onGenerateReport, busy }: { state: WorkflowState; onGenerateReport: () => void; busy: boolean }) {
  return (
    <GlassCard className="hidden p-6 lg:block">
      <div className="mb-5 flex items-center gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-[#efeaff] font-bold text-clinical">EL</span>
        <div>
          <h2 className="text-xl font-bold text-ink">Session Results</h2>
          <p className="text-sm text-slate-600">{state.childName} · {state.qaStatus ?? "Not analyzed"}</p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <MiniResult value={`${state.transcriptCompleteness || 0}%`} label="Transcript Ready" />
        <MiniResult value={`${state.featurePercent || 0}%`} label="Feature Summary" />
        <MiniResult value={String(state.reviewNeededCount)} label="Review Needed" />
      </div>
      <div className="mt-6 rounded-[1.3rem] border border-line bg-white/55 p-4">
        <h3 className="font-bold text-ink">Key insights</h3>
        <ul className="mt-3 space-y-3 text-sm text-slate-700">
          {state.insights.map((insight) => <li key={insight.title}>{insight.title}: {insight.text}</li>)}
        </ul>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <GradientButton href="/review-transcript" icon={FileText}>Review Transcript</GradientButton>
        <GradientButton icon={ShieldCheck} onClick={onGenerateReport} disabled={busy || !isTranscriptUnlocked(state)}>Generate Report</GradientButton>
      </div>
    </GlassCard>
  );
}

function InsightsCard({ insights }: { insights: WorkflowState["insights"] }) {
  return (
    <GlassCard className="p-5">
      <h2 className="mb-4 text-lg font-bold text-ink">Key Insights</h2>
      {insights.map((insight) => (
        <Insight key={insight.title} icon={insight.tone === "orange" ? AlertTriangle : insight.title.includes("question") ? MessageSquare : TrendingUp} title={insight.title} text={insight.text} tone={insight.tone} />
      ))}
    </GlassCard>
  );
}

function LanguageSampleFeatureGrid({ features }: { features: WorkflowState["featureSummary"] }) {
  return (
    <GlassCard className="p-5">
      <h2 className="text-lg font-bold text-ink">Language-sample cues</h2>
      <p className="mt-1 text-sm text-slate-600">Descriptive language-sample cues only. No diagnosis or ML prediction.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {features.map((feature) => (
          <div key={feature.label} className="rounded-xl border border-line bg-white/60 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{feature.label}</p>
            <p className="mt-1 text-xl font-bold text-ink">{feature.value}</p>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

function Insight({ icon: Icon, title, text, tone }: { icon: LucideIcon; title: string; text: string; tone: "green" | "orange" }) {
  return (
    <div className="mb-4 flex gap-3 last:mb-0">
      <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-full ${tone === "green" ? "bg-emerald-100 text-emerald-700" : "bg-orange-100 text-orange-600"}`}>
        <Icon size={23} aria-hidden="true" />
      </span>
      <div>
        <h3 className="font-bold text-ink">{title}</h3>
        <p className="mt-1 text-sm text-slate-600">{text}</p>
      </div>
    </div>
  );
}

function WorkflowStatus({ state }: { state: WorkflowState }) {
  if (!state.statusMessage && !state.error) {
    return null;
  }
  const isError = Boolean(state.error);
  const isSuccess = Boolean(state.statusMessage && !isError);
  const className = isError
    ? "rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-950 animate-fade-in"
    : isSuccess
      ? "rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 animate-fade-in"
      : "demo-note rounded-2xl p-4 text-sm";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}

function MiniResult({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[1.25rem] border border-line bg-white/60 p-4 text-center">
      <p className="text-3xl font-bold text-ink">{value}</p>
      <p className="mt-2 text-sm font-semibold text-slate-700">{label}</p>
    </div>
  );
}

function previewLines(transcriptText: string) {
  return transcriptText
    .split("\n")
    .filter((line) => line.startsWith("*"))
    .slice(0, 4)
    .map((line) => line.replace(/^\*/, "").replace(":\t", ": "));
}

function isTranscriptUnlocked(state: WorkflowState) {
  return state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
}

function createLocalReportMarkdown(state: WorkflowState) {
  return [
    "# Draft Report Preview",
    "",
    `Child/session: ${state.childName}`,
    `Transcript status: ${state.transcriptReady ? "Ready for therapist review" : "Not ready"}`,
    `Feature summary: ${state.featureSummary.map((item) => `${item.label} ${item.value}`).join(", ") || "Pending"}`,
    "",
    "All content is decision-support only and must be edited and finalized by the therapist."
  ].join("\n");
}
