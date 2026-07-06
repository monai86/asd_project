"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiBlob, apiRequest, apiGet } from "@/lib/api";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, ClipboardPaste, FileText, Loader2, Mic, ShieldCheck, Sparkles, UploadCloud, Wand2 } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { GlassCard, GradientButton, SafetyNote, WorkflowStep } from "@/components/liquid-ui";
import { BrowserAudioRecorder, type RecordingMetadata } from "@/components/browser-audio-recorder";
import { TranscriptEditorPanel } from "@/components/transcript-editor-panel";
import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { PageHeader } from "@/components/page-header";
import { RightRail } from "@/components/right-rail";
import { SafetyNotice } from "@/components/safety-notice";
import { StatCard } from "@/components/stat-card";
import { WorkflowStepper } from "@/components/workflow-stepper";
import {
  createExperimentalTranscriptionJob,
  getExperimentalTranscriptionJob,
  releaseExperimentalAudioUpload,
  uploadRecordedAudio
} from "@/lib/experimental-transcription-service";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
import {
  attestBackendTranscript,
  backendTranscriptLines,
  buildBasicChatExport,
  buildFeatureSignals,
  createBackendSession,
  createBackendTranscript,
  ensureWorkflowSession,
  createInitialWorkflowState,
  defaultTranscript,
  evaluateTranscriptQa,
  exportReviewedCha,
  generateBackendMlDecisionSupport,
  getBackendFeatureDefinitions,
  getBackendMlDecisionSupport,
  getBackendMlReadiness,
  generateBackendReport,
  getBackendCase,
  updateBackendCase,
  getBackendSessionFeatures,
  getBackendSession,
  getBackendSessionTranscript,
  getBackendTranscript,
  loadWorkflowState,
  prepareTranscriptIntake,
  runBackendQa,
  runBackendAnalysis,
  saveWorkflowState,
  summarizeAnalysis,
  type TranscriptLine,
  updateBackendTranscript,
  type WorkflowSource,
  type WorkflowState,
  updateProfileEvidenceReview,
  uploadAudioFileBytes,
  getSessionAudioFiles,
  uploadAudioBlobToBackend,
  startBackendTranscriptionJob,
  pollTranscriptionJob
} from "@/lib/workflow";

import { AudioUploadConfirmPanel } from "@/components/audio-upload-confirm-panel";
import { TranscriptionJobStatusPanel, type TranscriptionJobDisplayStatus } from "@/components/transcription-job-status-panel";

type SessionIntakeStepId = "details" | "source" | "setup" | "review";
type SessionIntakeSource = "recording" | "audio" | "cha" | "paste";

const sessionIntakeStepLabels: Array<{ id: SessionIntakeStepId; title: string; helper: string }> = [
  { id: "details", title: "Session Details", helper: "Set the session context before adding source material." },
  { id: "source", title: "Source Material", helper: "Record, upload, or paste the material for therapist review." },
  { id: "setup", title: "Transcript Setup", helper: "Define labels, metadata, and review requirements." },
  { id: "review", title: "Review & Start", helper: "Confirm safety notices before opening transcript review." }
];

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
  const [uploadStep, setUploadStep] = useState<
    "idle" | "confirm" | "uploading" | "polling" | "done" | "error"
  >("idle");
  const [transJobId, setTransJobId] = useState<string | undefined>();
  const [transJobStatus, setTransJobStatus] = useState<string>("queued");
  const [transJobMessage, setTransJobMessage] = useState<string>("");
  const [transJobRequestedProvider, setTransJobRequestedProvider] = useState<string | undefined>();
  const [transJobActualProvider, setTransJobActualProvider] = useState<string | undefined>();
  const [intakeStep, setIntakeStep] = useState<SessionIntakeStepId>(mode ? "source" : "details");
  const [selectedSource, setSelectedSource] = useState<SessionIntakeSource>(sourceFromMode(mode));
  const [sessionDetails, setSessionDetails] = useState(() => createSessionDetailsDraft(createInitialWorkflowState()));
  const [transcriptSetup, setTranscriptSetup] = useState(createTranscriptSetupDraft());
  const [caseConsent, setCaseConsent] = useState<string>("granted");
  const [consentSigner, setConsentSigner] = useState("Parent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentNotes, setConsentNotes] = useState("");
  const [isHydrated, setIsHydrated] = useState(false);

  const handleRecordingReady = (blob: Blob, metadata: RecordingMetadata) => {
    setRecordedAudio({ blob, metadata });
    setUploadStep("confirm");
  };

  const [audioUrl, setAudioUrl] = useState<string | undefined>(undefined);
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const router = useRouter();

  const pipelineStatusValue = useMemo(() => {
    if (caseConsent !== "granted") return "awaiting_consent";
    if (state.reportStatus === "Reviewed" || state.reportStatus === "Finalized" || state.reportMarkdown) return "report_ready";
    if (state.featuresExtracted) return "ml_pending";
    if (state.transcriptAttested) return "ml_pending";
    if (state.transcriptReady || state.transcriptReviewStatus === "in_review" || state.transcriptReviewStatus === "reviewed") return "review_required";
    if (uploadStep === "uploading") return "uploading";
    if (uploadStep === "polling") return "transcribing";
    return "ready_for_audio";
  }, [caseConsent, state.reportStatus, state.reportMarkdown, state.featuresExtracted, state.transcriptAttested, state.transcriptReady, state.transcriptReviewStatus, uploadStep]);

  useEffect(() => {
    let cancelled = false;
    const stored = loadWorkflowState();
    const hasLocator = Boolean(sessionId || transcriptId || caseId);
    if (!hasLocator) {
      setState(stored);
      setDraftTranscript(stored.transcriptText || (mode === "paste" || mode === "cha" ? "" : defaultTranscript));
      setEditorLines(stored.transcriptLines);
      setSourceFilename(stored.sourceFilename);
      setIntakeWarnings(stored.chatWarnings);
      setIntakeValidationIssues(stored.chatValidationIssues);
      setIsHydrated(true);
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
        if (childCase && !cancelled) {
          setCaseConsent(childCase.consent_status ?? "pending");
        }
        const lines = transcript ? backendTranscriptLines(transcript) : [];
        const parsed = transcript?.raw_text ? prepareTranscriptIntake("cha-upload", transcript.raw_text) : undefined;

        const audioFiles = sessionId || backendSession?.session_id
          ? await getSessionAudioFiles(sessionId ?? backendSession!.session_id).catch(() => [])
          : [];
        const primaryAudio = Array.isArray(audioFiles)
          ? audioFiles.find((f) => f.upload_status === "uploaded")
          : undefined;
        const resolvedAudioUrl = primaryAudio
          ? await createBackendAudioObjectUrl(primaryAudio.audio_file_id).catch(() => undefined)
          : undefined;
        const resolvedSessionId = backendSession?.session_id ?? transcript?.session_id ?? sessionId;
        const mlReadiness = transcript?.transcript_id
          ? await getBackendMlReadiness(transcript.transcript_id).catch(() => undefined)
          : undefined;
        const mlDecisionSupport = resolvedSessionId
          ? await getBackendMlDecisionSupport(resolvedSessionId).catch(() => undefined)
          : undefined;
        const backendFeatures = resolvedSessionId && backendSession?.feature_set_id
          ? await getBackendSessionFeatures(resolvedSessionId).catch(() => undefined)
          : undefined;
        const featureDefinitions = backendFeatures
          ? await getBackendFeatureDefinitions().catch(() => [])
          : [];
        const analysisSummary = backendFeatures
          ? summarizeAnalysis({
            status: transcript?.qa_status,
            qa_status: transcript?.qa_status,
            issues: (transcript?.qa_issues ?? []).map((issue) => typeof issue === "string" ? issue : issue.message ?? "Transcript QA issue")
          }, backendFeatures)
          : undefined;
        const featureSignals = buildFeatureSignals(backendFeatures, featureDefinitions);

        const hydrated = saveWorkflowState({
          ...createInitialWorkflowState(),
          ...stored,
          sessionId: resolvedSessionId ?? stored.sessionId,
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
          transcriptDraftLabel: transcript?.source?.includes("asr_draft")
            ? "Draft ASR transcript — therapist review required."
            : undefined,
          transcriptReviewStatus: transcript?.therapist_attested ? "reviewed" : transcript ? "in_review" : "not_started",
          qaStatus: normalizeBackendQaStatus(transcript?.qa_status),
          qaIssues: (transcript?.qa_issues ?? []).map((issue) => typeof issue === "string" ? issue : issue.message ?? "Transcript QA issue"),
          transcriptSaveStatus: transcript ? "saved" : "idle",
          ...(analysisSummary ?? {}),
          featuresExtracted: Boolean(backendSession?.feature_set_id),
          featureSignals,
          mlReadiness,
          mlDecisionSupport,
          workflowLoading: false,
          statusMessage: transcript ? "Persisted transcript loaded." : "Persisted session loaded.",
          error: undefined
        });
        if (cancelled) return;
        setAudioUrl(resolvedAudioUrl);
        setState(hydrated);
        setDraftTranscript(hydrated.transcriptText);
        setEditorLines(hydrated.transcriptLines);
        setIntakeWarnings(hydrated.chatWarnings);
        setIntakeValidationIssues(hydrated.chatValidationIssues);
        setIsHydrated(true);
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
        setDraftTranscript(stored.transcriptText || (mode === "paste" || mode === "cha" ? "" : defaultTranscript));
        setEditorLines(stored.transcriptLines);
        setSourceFilename(stored.sourceFilename);
        setIntakeWarnings(stored.chatWarnings);
        setIntakeValidationIssues(stored.chatValidationIssues);
        setIsHydrated(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseId, mode, reportId, sessionId, setBackendUnavailable, transcriptId]);

  useEffect(() => {
    return () => {
      if (audioUrl?.startsWith("blob:")) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

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
  const selectedWorkflowSource = workflowSourceFromSelection(selectedSource);
  const sessionDetailsComplete = Boolean(
    sessionDetails.childClient.trim()
      && sessionDetails.sessionDate
      && sessionDetails.sessionTime
      && sessionDetails.clinician.trim()
  );
  const transcriptSetupComplete = Boolean(
    transcriptSetup.speakerLabels.trim()
      && transcriptSetup.sessionMetadata.trim()
      && transcriptSetup.language
      && transcriptSetup.sampleType
      && transcriptSetup.reviewSpeakerLabels
      && transcriptSetup.reviewFeatureLock
  );
  const sourceReadyForReview = selectedSource === "paste" || selectedSource === "cha"
    ? Boolean(draftTranscript.trim())
    : Boolean(state.transcriptReady);
  const canStartTranscriptReview = sessionDetailsComplete && transcriptSetupComplete && sourceReadyForReview;

  useEffect(() => {
    if (!activeMode) return;
    setSelectedSource(sourceFromMode(activeMode));
    setIntakeStep("source");
  }, [activeMode]);

  useEffect(() => {
    setSessionDetails((current) => ({
      ...current,
      childClient: current.childClient || state.childName,
    }));
  }, [state.childName]);

  function persist(next: WorkflowState) {
    const saved = saveWorkflowState(next);
    setState(saved);
    return saved;
  }

  function buildIntakeBackedState(base: WorkflowState, source: WorkflowSource): WorkflowState {
    const childClient = sessionDetails.childClient.trim() || base.childName;
    return {
      ...base,
      childName: childClient,
      caseInfo: {
        ...base.caseInfo,
        clientLabel: childClient
      },
      therapyGoals: buildTherapyGoals(sessionDetails.sessionGoals),
      therapistNotes: buildSessionIntakeNotes(sessionDetails, transcriptSetup, selectedSource)
    };
  }

  function saveSessionIntakeDraft() {
    return persist(ensureWorkflowSession(buildIntakeBackedState(state, selectedWorkflowSource), selectedWorkflowSource, {
      statusMessage: "Session intake saved locally. Transcript review can start when source material is ready.",
      error: undefined
    }));
  }

  function handleRecordingMetadata(metadata: RecordingMetadata) {
    setState((current) => {
      const startingNewRecording = metadata.recordingStatus === "recording"
        && current.recordingStatus !== "recording"
        && current.recordingStatus !== "paused";
      return saveWorkflowState(ensureWorkflowSession(buildIntakeBackedState(current, "recording"), "recording", {
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

  async function handleUploadForTranscription() {
    if (!recordedAudio || !state.sessionId) return;
    setUploadStep("uploading");
    setBusy(true);
    try {
      const { audioFileId } = await uploadAudioBlobToBackend(
        state.sessionId, recordedAudio.blob,
        { durationSeconds: recordedAudio.metadata.durationSeconds,
          mimeType: recordedAudio.metadata.mimeType ?? "audio/webm" }
      );
      const { jobId } = await startBackendTranscriptionJob(state.sessionId, audioFileId, "mock");
      setTransJobId(jobId);
      setUploadStep("polling");
      setTransJobStatus("queued");
      setTransJobMessage("Audio processing queued...");
      void pollUntilComplete(jobId);
    } catch (err) {
      setTransJobMessage(err instanceof Error ? err.message : "Upload failed.");
      setTransJobStatus("failed");
      setUploadStep("error");
      setBusy(false);
    }
  }

  async function pollUntilComplete(jobId: string) {
    let attempts = 0;
    while (attempts < 30) {
      const interval = typeof process !== "undefined" && process.env.NODE_ENV === "test" ? 10 : 2000;
      await new Promise(r => setTimeout(r, interval));
      try {
        const poll = await pollTranscriptionJob(jobId);
        setTransJobStatus(poll.status);
        setTransJobMessage(poll.message);
        setTransJobRequestedProvider(poll.requestedProvider);
        setTransJobActualProvider(poll.actualProvider);
        if (poll.status === "needs_review" || poll.status === "completed") {
          setUploadStep("done");
          if (poll.transcriptId) {
            try {
              const transcript = await getBackendSessionTranscript(state.sessionId!);
              const lines = backendTranscriptLines(transcript);
              setState(prev => {
                const next: WorkflowState = {
                  ...prev,
                  backendTranscriptId: poll.transcriptId,
                  transcriptText: transcript.raw_text ?? "",
                  transcriptLines: lines,
                  transcriptReady: true,
                  transcriptionJobId: jobId,
                  transcriptionJobStatus: "completed",
                  transcriptionJobMessage: poll.message,
                  transcriptReviewStatus: "in_review",
                  transcriptDraftLabel: (transcript.source?.includes("asr_draft") || poll.status === "needs_review" || poll.status === "completed")
                    ? "Draft ASR transcript — therapist review required."
                    : undefined,
                  statusMessage: "Transcript ready for review.",
                  error: undefined
                };
                saveWorkflowState(next);
                return next;
              });
              setEditorLines(lines);
              setDraftTranscript(transcript.raw_text ?? "");
            } catch (err) {
              console.error("Failed to load transcript after job completion", err);
            }
          }
          setBusy(false);
          return;
        }
        if (poll.status === "failed" || poll.status === "cancelled") {
          setUploadStep("error");
          setBusy(false);
          return;
        }
      } catch { /* network error, keep polling */ }
      attempts++;
    }
    setTransJobStatus("failed");
    setTransJobMessage("Transcription timed out. Try again or use manual paste.");
    setUploadStep("error");
    setBusy(false);
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
    const mime = recordedAudio.metadata.mimeType || recordedAudio.blob.type || "audio/webm";
    const durationSeconds = recordedAudio.metadata.durationSeconds;

    if (!backendUnavailable && state.sessionId) {
      try {
        const ext = mime.includes("mp4") ? "mp4" : mime.includes("wav") ? "wav" : "webm";
        const filename = `recording_${Date.now()}.${ext}`;

        // 1. POST upload intent metadata
        const uploadIntentResponse = await apiRequest<{ details: { audio_file: any; upload_intent: any } }>(
          `/sessions/${state.sessionId}/audio/upload`,
          {
            method: "POST",
            body: JSON.stringify({
              filename,
              content_type: mime,
              size_bytes: recordedAudio.blob.size,
              duration_seconds: durationSeconds
            })
          }
        );

        const audioFile = uploadIntentResponse.details.audio_file;
        const uploadIntent = uploadIntentResponse.details.upload_intent;

        // 2. PUT raw binary blob bytes to backend
        await uploadAudioFileBytes(uploadIntent.upload_url, recordedAudio.blob);

        // 3. Complete audio upload metadata
        await apiRequest(`/audio/${audioFile.audio_file_id}/complete-upload`, {
          method: "POST",
          body: JSON.stringify({
            checksum_sha256: `sha-${audioFile.audio_file_id}`,
            size_bytes: recordedAudio.blob.size
          })
        });

        // 4. Trigger ASR mock job processing
        const processJob = await apiRequest<{ job_id: string; status: string; message: string }>(
          `/sessions/${state.sessionId}/audio/process`,
          {
            method: "POST",
            body: JSON.stringify({
              provider: "manual",
              draft_text: "Mock ASR transcript for workflow testing. CHI: Hello! [00:01.200 - 00:03.500] THER: Hi geographical boy [00:04.000 - 00:07.100]"
            })
          }
        );

        persist(ensureWorkflowSession(state, "recording", {
          mockAudioStored: true,
          transcriptionJobId: processJob.job_id,
          transcriptionJobStatus: processJob.status as any,
          transcriptionJobMessage: processJob.message,
          transcriptDraftLabel: "Draft transcript — therapist review required.",
          transcriptReady: false,
          transcriptAttested: false,
          transcriptReviewStatus: "not_started",
          qaStatus: "not_run",
          analysisStatus: "not_started",
          featuresExtracted: false,
          featurePercent: 0,
          featureSummary: [],
          featureSignals: [],
          statusMessage: processJob.message,
          error: undefined
        }));

        const resolvedAudioUrl = await createBackendAudioObjectUrl(audioFile.audio_file_id).catch(() => undefined);
        setAudioUrl(resolvedAudioUrl);

        window.setTimeout(() => void pollBackendTranscriptionJob(processJob.job_id), 350);
        return;
      } catch (err) {
        console.error("Backend audio upload/process failed, falling back to frontend mock", err);
      }
    }

    // Graceful fallback to frontend mock when offline
    try {
      const upload = await uploadRecordedAudio(recordedAudio.blob, {
        durationSeconds,
        mimeType: mime
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
        featureSignals: [],
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

  async function pollBackendTranscriptionJob(jobId: string) {
    try {
      const job = await apiGet<{ status: string; message: string; details?: any }>(`/jobs/${jobId}`);
      if (job.status === "failed") {
        persist({
          ...state,
          transcriptionJobStatus: "failed",
          transcriptionJobMessage: job.message,
          error: job.message
        });
        setBusy(false);
      } else if (job.status === "needs_review" || job.status === "completed") {
        const transcript = await getBackendSessionTranscript(state.sessionId!);
        const lines = backendTranscriptLines(transcript);
        persist({
          ...state,
          backendTranscriptId: transcript.transcript_id,
          transcriptText: transcript.raw_text ?? "",
          transcriptLines: lines,
          transcriptReady: true,
          transcriptionJobStatus: "completed",
          transcriptionJobMessage: "ASR processing complete.",
          transcriptReviewStatus: "in_review",
          statusMessage: "Transcript ready for review.",
          error: undefined
        });
        setEditorLines(lines);
        setDraftTranscript(transcript.raw_text ?? "");
        setBusy(false);
      } else {
        window.setTimeout(() => void pollBackendTranscriptionJob(jobId), 400);
      }
    } catch (err) {
      console.error("Polling backend job failed", err);
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
          featureSignals: [],
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
    const localSession = persist(ensureWorkflowSession(buildIntakeBackedState(state, "audio-upload"), "audio-upload", {
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
    const localSession = persist(ensureWorkflowSession(buildIntakeBackedState(state, source), source, {
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
      if (!state.backendTranscriptId) throw new Error("Persistent transcript unavailable.");
      const mlDecisionSupport = await generateBackendMlDecisionSupport(state.backendTranscriptId);
      persist({
        ...state,
        mlDecisionSupport,
        statusMessage: "Evidence review generated. Therapist interpretation is required.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({
        ...state,
        mlDecisionSupport: undefined,
        statusMessage: "ML review unavailable — backend verification required.",
        error: "Backend unavailable. No ML review result was generated or loaded."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleProfileEvidenceReview(
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote = ""
  ) {
    if (!state.mlDecisionSupport) return;
    setBusy(true);
    try {
      const mlDecisionSupport = await updateProfileEvidenceReview(
        state.mlDecisionSupport.resultId,
        profileCode,
        status,
        therapistNote
      );
      persist({
        ...state,
        mlDecisionSupport,
        statusMessage: status === "reviewed"
          ? `${profileCode} evidence marked reviewed. This records reading, not endorsement.`
          : `${profileCode} clinical disagreement recorded without deleting provider output.`,
        error: undefined
      });
    } catch {
      persist({
        ...state,
        statusMessage: "Evidence review state was not saved.",
        error: "Backend unavailable. The evidence disposition was not changed."
      });
    } finally {
      setBusy(false);
    }
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
          onProfileEvidenceReview={handleProfileEvidenceReview}
          backendUnavailable={backendUnavailable}
          isHydrated={isHydrated}
          hasLocator={Boolean(sessionId || transcriptId || caseId)}
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
          backendUnavailable={backendUnavailable}
          audioUrl={audioUrl}
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
            featureSignals: [],
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
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          <PageHeader
            title="Session Intake"
            description="Capture session context, prepare source material, and route the workflow into therapist transcript review without weakening the existing review and attestation gates."
            meta={[
              "Decision-support only",
              "Audio upload requires explicit confirmation",
              "ASR remains experimental"
            ]}
          />

          <PipelineProgressBar currentStatus={pipelineStatusValue} />

          <WorkflowStepper
            steps={sessionIntakeStepLabels.map((step) => ({
              id: step.id,
              title: step.title,
              helper: step.helper,
              status: step.id === intakeStep
                ? "current"
                : sessionIntakeStepLabels.findIndex((item) => item.id === step.id) < sessionIntakeStepLabels.findIndex((item) => item.id === intakeStep)
                  ? "complete"
                  : "pending"
            }))}
          />

          {intakeStep === "details" && caseConsent !== "granted" ? (
            <GlassCard className="space-y-5 p-5 sm:p-6" role="region" aria-label="Consent Intake Gate">
              <div>
                <h2 className="text-xl font-semibold text-ink">Consent Verification Required</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Audio processing, recording, and clinical observation suggested reviews are locked until parental/caregiver consent is verified.
                </p>
              </div>
              {intakeError && (
                <p className="rounded-[var(--radius-card)] border border-rose-100 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-950">
                  {intakeError}
                </p>
              )}
              <form onSubmit={async (e) => {
                e.preventDefault();
                if (!consentChecked || !caseId) return;
                setBusy(true);
                setIntakeError("");
                try {
                  await updateBackendCase(caseId, { consent_status: "granted" });
                  setCaseConsent("granted");
                } catch {
                  setIntakeError("Could not update case consent on the backend.");
                } finally {
                  setBusy(false);
                }
              }} className="space-y-4">
                <label className="flex items-start gap-3 text-sm text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consentChecked}
                    onChange={(event) => setConsentChecked(event.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-line"
                    required
                  />
                  <span>ข้าพเจ้ายืนยันว่าได้รับการลงนามยินยอมจากผู้ปกครองเพื่อรวบรวมตัวอย่างเสียงเรียบร้อยแล้ว</span>
                </label>
                <Field>
                  <label htmlFor="consent-signer" className="text-sm font-semibold text-ink">Signer Relation</label>
                  <select
                    id="consent-signer"
                    value={consentSigner}
                    onChange={(event) => setConsentSigner(event.target.value)}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none"
                  >
                    <option value="Parent">Parent</option>
                    <option value="Guardian">Guardian</option>
                    <option value="Self">Self</option>
                  </select>
                </Field>
                <div className="flex justify-end gap-3">
                  <ActionButton type="submit" disabled={!consentChecked || busy}>
                    {busy ? "Verifying..." : "Verify & Grant Consent"}
                  </ActionButton>
                </div>
              </form>
            </GlassCard>
          ) : intakeStep === "details" ? (
            <GlassCard className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">Session Details</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Set the session context first so the transcript workflow carries the correct child label, timing, and therapist-entered goals.
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Field>
                  <label htmlFor="session-child-client" className="text-sm font-semibold text-ink">Child or client</label>
                  <input
                    id="session-child-client"
                    type="text"
                    value={sessionDetails.childClient}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, childClient: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-clinician" className="text-sm font-semibold text-ink">Clinician</label>
                  <input
                    id="session-clinician"
                    type="text"
                    value={sessionDetails.clinician}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, clinician: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-date" className="text-sm font-semibold text-ink">Session date</label>
                  <input
                    id="session-date"
                    type="date"
                    value={sessionDetails.sessionDate}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, sessionDate: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-time" className="text-sm font-semibold text-ink">Session time</label>
                  <input
                    id="session-time"
                    type="time"
                    value={sessionDetails.sessionTime}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, sessionTime: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-setting" className="text-sm font-semibold text-ink">Setting</label>
                  <select
                    id="session-setting"
                    value={sessionDetails.setting}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, setting: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  >
                    <option value="clinic">Clinic</option>
                    <option value="home">Home</option>
                    <option value="telehealth">Telehealth</option>
                  </select>
                </Field>
                <Field>
                  <label htmlFor="session-duration" className="text-sm font-semibold text-ink">Duration</label>
                  <select
                    id="session-duration"
                    value={sessionDetails.durationMinutes}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, durationMinutes: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  >
                    <option value="30">30 minutes</option>
                    <option value="45">45 minutes</option>
                    <option value="60">60 minutes</option>
                    <option value="90">90 minutes</option>
                  </select>
                </Field>
              </div>
              <Field>
                <label htmlFor="session-goals" className="text-sm font-semibold text-ink">Session goals</label>
                <textarea
                  id="session-goals"
                  value={sessionDetails.sessionGoals}
                  onChange={(event) => setSessionDetails((current) => ({ ...current, sessionGoals: event.target.value }))}
                  className="min-h-32 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                />
              </Field>
              <SafetyNotice>
                Decision-support only. Do not use this intake to imply diagnosis, automated conclusions, or secure sharing beyond the implemented local workflow.
              </SafetyNotice>
              <div className="flex flex-wrap justify-end gap-3">
                <ActionButton
                  type="button"
                  onClick={() => setIntakeStep("source")}
                  disabled={!sessionDetailsComplete}
                >
                  Continue to Source Material
                </ActionButton>
              </div>
            </GlassCard>
          ) : null}

          {intakeStep === "source" ? (
            <GlassCard className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">Source Material</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Preserve the existing quick-start workflows while making the source choice explicit. Audio upload and ASR remain clearly labeled experimental.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <SourceChoiceButton label="Record in browser" active={selectedSource === "recording"} icon={Mic} onClick={() => setSelectedSource("recording")} />
                <SourceChoiceButton label="Upload audio" active={selectedSource === "audio"} icon={UploadCloud} onClick={() => setSelectedSource("audio")} />
                <SourceChoiceButton label="Upload .cha" active={selectedSource === "cha"} icon={FileText} onClick={() => setSelectedSource("cha")} />
                <SourceChoiceButton label="Paste transcript" active={selectedSource === "paste"} icon={ClipboardPaste} onClick={() => setSelectedSource("paste")} />
              </div>

              {selectedSource === "recording" ? (
                <>
                  <GlassCard className="p-5 text-center">
                    <BrowserAudioRecorder
                      initialDurationSeconds={state.recordingSeconds}
                      hadUnsavedRecording={state.recordingClearedForPrivacy}
                      onMetadataChange={handleRecordingMetadata}
                      onRecordingReady={handleRecordingReady}
                      onRecordingCleared={() => { setRecordedAudio(null); setUploadStep("idle"); }}
                    />
                  </GlassCard>

                  {view === "record" && uploadStep === "confirm" && recordedAudio ? (
                    <AudioUploadConfirmPanel
                      blob={recordedAudio.blob}
                      durationSeconds={recordedAudio.metadata.durationSeconds}
                      onUpload={handleUploadForTranscription}
                      onCancel={() => setUploadStep("idle")}
                      backendAvailable={!backendUnavailable}
                      uploading={busy}
                    />
                  ) : null}

                  {view === "record" && ["polling", "done", "error"].includes(uploadStep) ? (
                    <TranscriptionJobStatusPanel
                      status={transJobStatus as TranscriptionJobDisplayStatus}
                      message={transJobMessage}
                      requestedProvider={transJobRequestedProvider}
                      actualProvider={transJobActualProvider}
                      onOpenTranscript={
                        uploadStep === "done" && state.backendTranscriptId && state.sessionId
                          ? () => {
                              router.push(
                                `/review-transcript?session_id=${state.sessionId}&transcript_id=${state.backendTranscriptId}`
                              );
                            }
                          : undefined
                      }
                      onRetry={() => {
                        setUploadStep("idle");
                        setRecordedAudio(null);
                      }}
                      onUsePaste={() => {
                        setSelectedSource("paste");
                        setState((prev) => ({ ...prev, source: "paste-transcript" }));
                      }}
                    />
                  ) : null}

                  {view === "record" && uploadStep === "idle" && recordedAudio ? (
                    <GlassCard className="p-5 text-center">
                      <p className="mb-3 text-sm text-slate-600">Recording captured. Ready for explicit upload confirmation.</p>
                      <GradientButton icon={UploadCloud} className="w-full" onClick={() => setUploadStep("confirm")}>
                        Upload for transcription
                      </GradientButton>
                    </GlassCard>
                  ) : null}
                </>
              ) : (
                <SourceInputPanel
                  mode={selectedSource === "audio" ? "audio" : selectedSource === "cha" ? "cha" : "paste"}
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
              )}

              <GlassCard className="p-5">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="font-bold text-ink">Transcript preview</h3>
                  <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    <span className={`h-2 w-2 rounded-full ${state.transcriptReady ? "bg-emerald-500" : "bg-amber-500"}`} />
                    {state.transcriptReady ? "Ready for review" : "Preview only"}
                  </span>
                </div>
                <div className="space-y-2 text-sm text-slate-700">
                  {state.transcriptReady && transcriptLines.length > 0
                    ? transcriptLines.slice(0, 6).map((line) => <p key={line}>{line}</p>)
                    : draftTranscript.trim()
                      ? draftTranscript.trim().split("\n").slice(0, 6).map((line) => <p key={line}>{line}</p>)
                      : (
                        <div className="rounded-xl border border-dashed border-line bg-white/40 p-4 text-center">
                          <p className="font-semibold text-ink">No transcript available yet</p>
                          <p className="mt-1 text-sm text-slate-600">Add source material, then continue into transcript setup and therapist review.</p>
                        </div>
                      )}
                </div>
              </GlassCard>

              <div className="flex flex-wrap justify-between gap-3">
                <ActionButton type="button" tone="ghost" onClick={() => setIntakeStep("details")}>
                  Back to Session Details
                </ActionButton>
                <ActionButton type="button" onClick={() => setIntakeStep("setup")}>
                  Continue to Transcript Setup
                </ActionButton>
              </div>
            </GlassCard>
          ) : null}

          {intakeStep === "setup" ? (
            <GlassCard className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">Transcript Setup</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Define how the transcript should be reviewed. These fields do not unlock analysis on their own; QA and therapist attestation are still required later.
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Field className="md:col-span-2">
                  <label htmlFor="speaker-labels" className="text-sm font-semibold text-ink">Speaker labels</label>
                  <textarea
                    id="speaker-labels"
                    value={transcriptSetup.speakerLabels}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, speakerLabels: event.target.value }))}
                    className="min-h-28 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field className="md:col-span-2">
                  <label htmlFor="session-metadata" className="text-sm font-semibold text-ink">Session metadata</label>
                  <textarea
                    id="session-metadata"
                    value={transcriptSetup.sessionMetadata}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, sessionMetadata: event.target.value }))}
                    className="min-h-28 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="transcript-language" className="text-sm font-semibold text-ink">Language</label>
                  <select
                    id="transcript-language"
                    value={transcriptSetup.language}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, language: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  >
                    <option value="eng">English</option>
                    <option value="tha">Thai</option>
                    <option value="mixed">Mixed language sample</option>
                  </select>
                </Field>
                <Field>
                  <label htmlFor="sample-type" className="text-sm font-semibold text-ink">Sample type</label>
                  <select
                    id="sample-type"
                    value={transcriptSetup.sampleType}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, sampleType: event.target.value }))}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  >
                    <option value="conversation">Conversation</option>
                    <option value="play">Play-based interaction</option>
                    <option value="narrative">Narrative sample</option>
                  </select>
                </Field>
              </div>
              <div className="space-y-3 rounded-2xl border border-line bg-white/60 p-4">
                <p className="text-sm font-semibold text-ink">Review requirements</p>
                <label className="flex min-h-11 items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={transcriptSetup.reviewSpeakerLabels}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, reviewSpeakerLabels: event.target.checked }))}
                    aria-label="I will review speaker labels and transcript wording before attestation."
                    className="mt-1 h-4 w-4 rounded border-line"
                  />
                  <span>I will review speaker labels and transcript wording before attestation.</span>
                </label>
                <label className="flex min-h-11 items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={transcriptSetup.reviewFeatureLock}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, reviewFeatureLock: event.target.checked }))}
                    aria-label="I understand feature extraction stays locked until transcript review, QA, and attestation are complete."
                    className="mt-1 h-4 w-4 rounded border-line"
                  />
                  <span>I understand feature extraction stays locked until transcript review, QA, and attestation are complete.</span>
                </label>
              </div>
              <div className="flex flex-wrap justify-between gap-3">
                <ActionButton type="button" tone="ghost" onClick={() => setIntakeStep("source")}>
                  Back to Source Material
                </ActionButton>
                <ActionButton type="button" onClick={() => setIntakeStep("review")}>
                  Continue to Review & Start
                </ActionButton>
              </div>
            </GlassCard>
          ) : null}

          {intakeStep === "review" ? (
            <GlassCard className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">Review & Start</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Confirm the summary, keep the privacy notice visible, and route into the existing transcript review workflow.
                </p>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <ReviewSummaryCard title="Session summary" rows={[
                  { label: "Child/client", value: sessionDetails.childClient || "Not set" },
                  { label: "Date", value: sessionDetails.sessionDate || "Not set" },
                  { label: "Time", value: sessionDetails.sessionTime || "Not set" },
                  { label: "Setting", value: capitalizeWord(sessionDetails.setting) },
                  { label: "Duration", value: `${sessionDetails.durationMinutes} minutes` },
                  { label: "Clinician", value: sessionDetails.clinician || "Not set" }
                ]} />
                <ReviewSummaryCard title="Workflow summary" rows={[
                  { label: "Source type", value: sourceSummaryLabel(selectedSource) },
                  { label: "Transcript source", value: sourceReadyForReview ? "Ready for therapist review" : "Still needs transcript-ready input" },
                  { label: "Language", value: transcriptSetup.language },
                  { label: "Sample type", value: transcriptSetup.sampleType },
                  { label: "Goals", value: sessionDetails.sessionGoals || "Not set" }
                ]} />
              </div>
              <SafetyNotice>
                Decision-support only. Audio bytes are not stored in browser persistent storage. Experimental ASR output must be reviewed by a therapist before transcript attestation, feature extraction, or report use.
              </SafetyNotice>
              {selectedSource === "audio" || selectedSource === "recording" ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  Audio upload and ASR remain experimental in this workflow. Start transcript review only after a draft transcript is actually available.
                </div>
              ) : null}
              <div className="flex flex-wrap justify-between gap-3">
                <ActionButton type="button" tone="ghost" onClick={() => setIntakeStep("setup")}>
                  Back to Transcript Setup
                </ActionButton>
                <div className="flex flex-wrap gap-3">
                  <ActionButton type="button" tone="secondary" onClick={saveSessionIntakeDraft}>
                    Save session
                  </ActionButton>
                  <ActionButton
                    type="button"
                    onClick={() => {
                      const savedState = saveSessionIntakeDraft();
                      if (selectedSource === "paste" || selectedSource === "cha") {
                        void handleTranscriptSubmit(selectedSource === "paste" ? "paste-transcript" : "cha-upload");
                        return;
                      }
                      if (state.transcriptReady) {
                        router.push(workflowHref("/review-transcript", savedState));
                      }
                    }}
                    disabled={!canStartTranscriptReview}
                  >
                    Start Transcript Review
                  </ActionButton>
                </div>
              </div>
            </GlassCard>
          ) : null}

          {state.transcriptReady && !isTranscriptUnlocked(state) ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900" role="alert">
              Feature extraction requires a saved, reviewed, and attested transcript.
            </div>
          ) : null}

          <GradientButton
            icon={Sparkles}
            className="w-full text-xl"
            onClick={handleAnalyze}
            disabled={
              busy ||
              state.workflowLoading ||
              !isTranscriptUnlocked(state) ||
              !state.backendTranscriptId ||
              !(state.backendTranscriptSessionId ?? state.backendSessionId)
            }
            aria-label="Extract language-sample features"
            data-testid="extract-features-button"
          >
            {busy ? "Extracting..." : "Extract language-sample features"}
          </GradientButton>

          <GlassCard className="p-5">
            <h2 className="mb-4 font-bold text-ink">What happens next</h2>
            <div className="flex gap-2">
              <WorkflowStep icon={FileText} title="Transcript ready" helper={state.transcriptReady ? "Available" : "After source material is prepared"} tone="purple" />
              <WorkflowStep icon={CheckCircle2} title="Features extracted" helper={state.featuresExtracted ? "Complete" : "After review gate"} tone="green" />
              <WorkflowStep icon={Wand2} title="Suggested next step" helper="Therapist transcript review" tone="orange" />
            </div>
          </GlassCard>
          <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
          <SafetyNote>Decision-support only. Not diagnostic. Transcript must be reviewed before report use.</SafetyNote>
        </div>

        <div className="space-y-6">
          <ReviewSummaryCard title="Current intake" rows={[
            { label: "Step", value: sessionIntakeStepLabels.find((item) => item.id === intakeStep)?.title ?? "Session Details" },
            { label: "Source", value: sourceSummaryLabel(selectedSource) },
            { label: "Transcript status", value: state.transcriptReady ? "Ready for review" : "Pending" }
          ]} />
          <SessionResultsPreview state={state} onGenerateReport={handleGenerateReport} busy={busy} />
        </div>
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
      featureSignals: [],
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

function createSessionDetailsDraft(state: WorkflowState) {
  const now = new Date();
  const sessionDate = state.sessionCreatedAt?.slice(0, 10) ?? now.toISOString().slice(0, 10);
  const sessionTime = state.sessionCreatedAt
    ? state.sessionCreatedAt.slice(11, 16)
    : `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  return {
    childClient: state.childName,
    sessionDate,
    sessionTime,
    setting: "clinic",
    durationMinutes: "45",
    clinician: "",
    sessionGoals: state.therapyGoals.join("\n")
  };
}

function createTranscriptSetupDraft() {
  return {
    speakerLabels: "THER = Therapist\nCHI = Child",
    sessionMetadata: "",
    language: "eng",
    sampleType: "conversation",
    reviewSpeakerLabels: false,
    reviewFeatureLock: false
  };
}

function sourceFromMode(mode?: string): SessionIntakeSource {
  if (mode === "audio") return "audio";
  if (mode === "cha") return "cha";
  if (mode === "paste") return "paste";
  return "recording";
}

function workflowSourceFromSelection(source: SessionIntakeSource): WorkflowSource {
  if (source === "audio") return "audio-upload";
  if (source === "cha") return "cha-upload";
  if (source === "paste") return "paste-transcript";
  return "recording";
}

function buildTherapyGoals(goals: string): string[] {
  return goals
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildSessionIntakeNotes(
  sessionDetails: ReturnType<typeof createSessionDetailsDraft>,
  transcriptSetup: ReturnType<typeof createTranscriptSetupDraft>,
  selectedSource: SessionIntakeSource
): string {
  return [
    `Session intake summary`,
    `Date: ${sessionDetails.sessionDate || "not set"} ${sessionDetails.sessionTime || ""}`.trim(),
    `Setting: ${sessionDetails.setting}`,
    `Duration: ${sessionDetails.durationMinutes} minutes`,
    `Clinician: ${sessionDetails.clinician || "not set"}`,
    `Source: ${sourceSummaryLabel(selectedSource)}`,
    `Language: ${transcriptSetup.language}`,
    `Sample type: ${transcriptSetup.sampleType}`,
    `Session metadata: ${transcriptSetup.sessionMetadata || "not provided"}`
  ].join("\n");
}

function sourceSummaryLabel(source: SessionIntakeSource): string {
  if (source === "audio") return "Uploaded audio (experimental)";
  if (source === "cha") return ".cha transcript";
  if (source === "paste") return "Pasted transcript";
  return "Browser recording";
}

function capitalizeWord(value: string) {
  return value ? `${value.slice(0, 1).toUpperCase()}${value.slice(1)}` : "";
}

function Field({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`.trim()}>
      {children}
    </div>
  );
}

function SourceChoiceButton({
  label,
  active,
  icon: Icon,
  onClick
}: {
  label: string;
  active: boolean;
  icon: LucideIcon;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex min-h-24 flex-col items-start justify-between rounded-[var(--radius-card)] border px-4 py-4 text-left transition motion-reduce:transition-none ${
        active
          ? "border-[color:var(--color-accent-subtle)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)] shadow-soft"
          : "border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)]"
      }`}
      aria-pressed={active}
    >
      <Icon size={20} aria-hidden="true" />
      <span className="text-sm font-semibold">{label}</span>
    </button>
  );
}

function ReviewSummaryCard({
  title,
  rows
}: {
  title: string;
  rows: Array<{ label: string; value: string }>;
}) {
  return (
    <GlassCard className="p-5">
      <h3 className="font-bold text-ink">{title}</h3>
      <dl className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={`${title}-${row.label}`} className="grid gap-1 border-b border-line/70 pb-3 last:border-b-0 last:pb-0">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{row.label}</dt>
            <dd className="text-sm text-slate-700">{row.value}</dd>
          </div>
        ))}
      </dl>
    </GlassCard>
  );
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

async function createBackendAudioObjectUrl(audioFileId: string): Promise<string> {
  const blob = await apiBlob(`/audio/${audioFileId}/file`);
  return URL.createObjectURL(blob);
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
        <textarea
          className="min-h-44 w-full rounded-2xl border border-line bg-white/70 p-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
          value={draftTranscript}
          onChange={(event) => onDraftChange(event.target.value)}
          aria-label={mode === "cha" ? "CHA transcript text" : "Pasted transcript text"}
          data-testid="transcript-input"
        />
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
        <GradientButton
          icon={CheckCircle2}
          className="mt-3 w-full"
          onClick={() => onTranscriptSubmit(source)}
          disabled={busy || Boolean(error)}
          data-testid="save-transcript-button"
        >
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
  onProfileEvidenceReview,
  backendUnavailable,
  isHydrated,
  hasLocator
}: {
  state: WorkflowState;
  busy: boolean;
  onGenerateReport: () => void;
  onGenerateMlDecisionSupport: () => void;
  onProfileEvidenceReview: (
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote?: string
  ) => void;
  backendUnavailable?: boolean;
  isHydrated: boolean;
  hasLocator: boolean;
}) {
  const [showEvidenceDetails, setShowEvidenceDetails] = useState(false);
  const [disagreementProfile, setDisagreementProfile] = useState<string>();
  const [disagreementNote, setDisagreementNote] = useState("");
  const [interpretationDraft, setInterpretationDraft] = useState(() =>
    createInterpretationDraft(state.featureSignals, state.featureSummary, state.mlDecisionSupport)
  );
  const [reviewedCuesApproved, setReviewedCuesApproved] = useState(false);
  const signalCards = useMemo(() => buildLinguisticSignalCards(state), [state]);
  const recommendedReviewPoints = useMemo(() => buildRecommendedReviewPoints(state), [state]);
  const interpretationDraftSeed = useMemo(
    () => createInterpretationDraft(state.featureSignals, state.featureSummary, state.mlDecisionSupport),
    [state.featureSignals, state.featureSummary, state.mlDecisionSupport]
  );
  const reportReady = isResultsReportReady(state);
  const missingReferenceData = hasMissingReferenceData(state);

  useEffect(() => {
    setInterpretationDraft(interpretationDraftSeed);
    setReviewedCuesApproved(false);
  }, [interpretationDraftSeed, state.backendSessionId, state.reportId]);

  let initialEvidenceCueCount = 0;
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
  if (hasLocator && isHydrated && state.featuresExtracted && !state.mlDecisionSupport) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <GlassCard className="p-8 text-center space-y-5">
          <Loader2 className="mx-auto text-clinical animate-spin" size={38} aria-hidden="true" />
          <h1 className="text-2xl font-bold text-ink">Analyzing linguistic observations...</h1>
          <p className="text-sm leading-6 text-slate-600">
            ระบบสนับสนุนการตัดสินใจทางคลินิก (ML) กำลังประมวลผลคำแนะนำสนับสนุนการวิเคราะห์ข้อสังเกต โดยอ้างอิงสัญญาณทางภาษาที่สกัดได้
          </p>
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-xs text-blue-900 leading-5">
            ⚠️ <strong>ข้อควรระวังทางคลินิก:</strong> ข้อมูลวิเคราะห์จาก AI/ML เป็นเพียงข้อมูลเพื่อสนับสนุนการตัดสินใจและสนับสนุนทางคลินิกเท่านั้น (Decision-Support Only) ไม่ใช่ผลการวินิจฉัยโรคอัตโนมัติหรือแทนที่การประเมินโดยนักบำบัด
          </div>
          <div className="flex justify-center gap-3">
            <GradientButton
              onClick={onGenerateReport}
              disabled={busy}
              icon={ShieldCheck}
            >
              Skip to Draft Report
            </GradientButton>
          </div>
        </GlassCard>
      </div>
    );
  }
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-6">
        <header className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-6 shadow-soft backdrop-blur-xl">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[color:var(--color-accent-strong)]">Evidence Review</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)]">Session Results</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--color-text-muted)]">
                Review descriptive transcript cues, backend-derived features, and therapist-editable draft language before generating a report draft.
              </p>
            </div>
            <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm text-[color:var(--color-text-muted)]">
              <p className="font-semibold text-[color:var(--color-text-strong)]">{state.childName}</p>
              <p>Session workspace · {state.backendTranscriptSessionId ?? state.backendSessionId ?? "local preview"}</p>
            </div>
          </div>
        </header>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--color-text-muted)]">Summary cards</h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Transcript quality"
              value={transcriptQualityLabel(state)}
              helper={state.qaSummary ?? "Therapist review remains required before report use."}
              icon={FileText}
              tone={state.qaStatus === "pass" ? "success" : "warning"}
            />
            <StatCard
              label="Features extracted"
              value={state.featuresExtracted ? `${signalCards.length} signals` : "Pending"}
              helper={state.featuresExtracted ? "Backend feature values are available for review." : "Extract reviewed transcript features to populate the signal grid."}
              icon={Sparkles}
              tone={state.featuresExtracted ? "success" : "warning"}
            />
            <StatCard
              label="Review flags"
              value={String(totalReviewFlags(state))}
              helper={totalReviewFlags(state) > 0 ? "Review flagged items before generating a draft report." : "No additional review flags are currently open."}
              icon={AlertTriangle}
              tone={totalReviewFlags(state) > 0 ? "warning" : "accent"}
            />
            <StatCard
              label="Report readiness"
              value={reportReady ? "Ready" : "Blocked"}
              helper={reportReady ? "Transcript and feature gates passed for a draft report." : "Therapist-reviewed transcript and feature extraction are required before generating a draft report. ML evidence review remains optional."}
              icon={ShieldCheck}
              tone={reportReady ? "success" : "warning"}
            />
          </div>
        </section>

        <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-6 shadow-soft backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold tracking-[-0.02em] text-[color:var(--color-text-strong)]">Linguistic Signals</h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
                Backend feature values are shown as descriptive cues only. Therapist interpretation is required for any clinical use.
              </p>
            </div>
            {state.featuresExtracted && !state.mlDecisionSupport ? (
              <GradientButton
                icon={Wand2}
                onClick={onGenerateMlDecisionSupport}
                disabled={busy || backendUnavailable || state.mlReadiness?.ready === false}
                data-testid="generate-evidence-review-button"
              >
                {busy ? "Generating..." : "Generate evidence review"}
              </GradientButton>
            ) : null}
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {signalCards.length ? signalCards.map((signal) => (
              <article key={signal.featureName} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-[color:var(--color-text-strong)]">{signal.displayName}</h3>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">{signal.description}</p>
                  </div>
                  <span className="rounded-full bg-[color:var(--color-accent-soft)] px-3 py-1 text-sm font-semibold text-[color:var(--color-accent-strong)]">
                    {signal.value}
                  </span>
                </div>
                <dl className="mt-4 space-y-2 text-sm text-[color:var(--color-text-muted)]">
                  <div>
                    <dt className="font-semibold text-[color:var(--color-text-strong)]">Method</dt>
                    <dd>{signal.calculationMethod}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-[color:var(--color-text-strong)]">Reference</dt>
                    <dd>{signal.referenceText}</dd>
                  </div>
                </dl>
                <p className="mt-4 text-xs font-medium uppercase tracking-[0.18em] text-[color:var(--color-text-muted)]">Safety note</p>
                <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">{signal.clinicalInterpretationCaution}</p>
              </article>
            )) : (
              <div className="rounded-[var(--radius-panel)] border border-dashed border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-5 text-sm text-[color:var(--color-text-muted)]">
                Feature extraction has not been completed yet. Extract reviewed transcript features to populate this grid.
              </div>
            )}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-6 shadow-soft backdrop-blur-xl">
            <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Recommended review points</h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-[color:var(--color-text-muted)]">
              {recommendedReviewPoints.map((point) => (
                <li key={point} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3">
                  {point}
                </li>
              ))}
            </ul>
            {state.mlDecisionSupport ? (
              <div className="mt-5 space-y-3" data-testid="evidence-review-panel">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--color-text-muted)]">Evidence review</h3>
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">Not diagnostic</span>
                </div>
                <p className="text-sm text-[color:var(--color-text-muted)]">
                  {state.mlDecisionSupport.providerName} v{state.mlDecisionSupport.providerVersion} · schema {state.mlDecisionSupport.featureSchemaVersion}
                </p>
                {state.mlDecisionSupport.patternEvidence ? (
                  <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
                    <p className="font-semibold text-[color:var(--color-text-strong)]">{patternEvidenceTitle(state.mlDecisionSupport.patternEvidence.status)}</p>
                    <EvidenceAvailabilityView availability={state.mlDecisionSupport.patternEvidence.availability} />
                  </div>
                ) : null}
                {(state.mlDecisionSupport.profileEvidence ?? []).map((profile) => {
                  const visibleFeatures = showEvidenceDetails
                    ? profile.associatedFeatures
                    : profile.associatedFeatures.slice(0, Math.max(0, 3 - initialEvidenceCueCount));
                  initialEvidenceCueCount += visibleFeatures.length;
                  return (
                    <article key={profile.profileCode} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="font-semibold text-[color:var(--color-text-strong)]">{profile.profileCode} profile</p>
                          <p className="text-xs text-[color:var(--color-text-muted)]">Presentation group: {profile.presentationGroup}</p>
                        </div>
                        <span className="rounded-full bg-[color:var(--color-surface-muted)] px-3 py-1 text-xs font-semibold text-[color:var(--color-text-strong)]">
                          {profileStatusTitle(profile.status)}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
                        Reference support: {profile.participantCount} participants · {profile.corpusCount} corpora
                      </p>
                      <EvidenceAvailabilityView availability={profile.availability} />
                      {profile.availability.state === "insufficient_reference_data" ? (
                        <p className="mt-3 rounded-[var(--radius-pill)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-medium text-[color:var(--color-warning-text)]">
                          Reference comparison unavailable
                        </p>
                      ) : null}
                      {visibleFeatures.map((feature) => (
                        <div key={feature.featureName} className="mt-3 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-3" data-testid={showEvidenceDetails ? "evidence-detail" : "evidence-cue"}>
                          <p className="text-sm font-semibold text-[color:var(--color-text-strong)]">{featureLabel(feature.featureName)}</p>
                          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                            Observed {String(feature.observedValue)} · {positionTitle(feature.position)}
                          </p>
                          {showEvidenceDetails ? (
                            <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">
                              Reference distribution Q1 {String(feature.q1)} · median {String(feature.median)} · Q3 {String(feature.q3)}
                            </p>
                          ) : null}
                          <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">{feature.caveat}</p>
                        </div>
                      ))}
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm font-semibold text-[color:var(--color-accent-strong)]"
                          onClick={() => onProfileEvidenceReview(profile.profileCode, "reviewed")}
                          disabled={busy}
                        >
                          Reviewed
                        </button>
                        <button
                          type="button"
                          className="rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm font-semibold text-[color:var(--color-text-strong)]"
                          onClick={() => {
                            setDisagreementProfile(profile.profileCode);
                            setDisagreementNote(profile.reviewState.therapistNote);
                          }}
                          disabled={busy}
                        >
                          Record disagreement
                        </button>
                      </div>
                      {disagreementProfile === profile.profileCode ? (
                        <div className="mt-3 rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-3">
                          <p className="text-xs text-amber-900">
                            This records clinical disagreement and preserves the original provider output.
                          </p>
                          <textarea
                            aria-label={`Disagreement note for ${profile.profileCode}`}
                            className="mt-2 min-h-24 w-full rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-white p-3 text-sm"
                            value={disagreementNote}
                            onChange={(event) => setDisagreementNote(event.target.value)}
                          />
                          <div className="mt-2 flex gap-2">
                            <button
                              type="button"
                              className="rounded-[var(--radius-pill)] bg-[color:var(--color-accent-strong)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                              disabled={busy || !disagreementNote.trim()}
                              onClick={() => {
                                onProfileEvidenceReview(profile.profileCode, "disagreement", disagreementNote.trim());
                                setDisagreementProfile(undefined);
                                setDisagreementNote("");
                              }}
                            >
                              Save disagreement
                            </button>
                            <button
                              type="button"
                              className="rounded-[var(--radius-pill)] px-3 py-2 text-sm font-semibold text-[color:var(--color-text-strong)]"
                              onClick={() => {
                                setDisagreementProfile(undefined);
                                setDisagreementNote("");
                              }}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </article>
                  );
                })}
                {(state.mlDecisionSupport.profileEvidence ?? []).some((profile) => profile.associatedFeatures.length > 0) ? (
                  <button
                    type="button"
                    className="text-sm font-semibold text-[color:var(--color-accent-strong)] underline"
                    onClick={() => setShowEvidenceDetails((value) => !value)}
                  >
                    {showEvidenceDetails ? "Hide supporting evidence" : "View supporting evidence"}
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="space-y-6">
            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-6 shadow-soft backdrop-blur-xl">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Action panel</h2>
              <div className="mt-4 space-y-3">
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm font-semibold text-[color:var(--color-text-strong)] disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => setReviewedCuesApproved(true)}
                  disabled={busy || (!state.mlDecisionSupport && signalCards.length === 0)}
                >
                  Approve reviewed cues
                </button>
                <GradientButton href="/review-transcript" icon={FileText} className="w-full justify-center">
                  Revise transcript
                </GradientButton>
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-[var(--radius-pill)] bg-[color:var(--color-accent-strong)] px-4 py-3 text-sm font-semibold text-white shadow-soft disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={onGenerateReport}
                  disabled={busy || !reportReady}
                  data-testid="generate-report-button"
                >
                  {busy ? "Generating..." : "Generate report draft"}
                </button>
              </div>
              {!reportReady ? (
                <p className="mt-4 text-sm text-[color:var(--color-warning-text)]">
                  Therapist-reviewed transcript and feature extraction are required before generating a draft report. ML evidence review remains optional.
                </p>
              ) : null}
              {reviewedCuesApproved ? (
                <p className="mt-3 text-sm text-[color:var(--color-success-text)]">
                  Reviewed cues marked as acknowledged in the current workspace. Therapist sign-off is still required.
                </p>
              ) : null}
            </section>

            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-6 shadow-soft backdrop-blur-xl">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Therapist-editable interpretation draft</h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
                Draft wording only. Edit this text before using it in any report or clinical documentation.
              </p>
              <textarea
                aria-label="Therapist-editable interpretation draft"
                className="mt-4 min-h-48 w-full rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 text-sm leading-6 text-[color:var(--color-text-strong)]"
                value={interpretationDraft}
                onChange={(event) => setInterpretationDraft(event.target.value)}
              />
            </section>
          </div>
        </section>

        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
        <SessionResultsPreview state={state} onGenerateReport={onGenerateReport} busy={busy} />
      </div>

      <RightRail
        title="Safety & limitations"
        description="Evidence review is descriptive. Therapist interpretation, editing, and sign-off remain required."
      >
        <SafetyNotice>Decision-support only. Therapist interpretation and sign-off remain required.</SafetyNotice>
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
          <h3 className="text-sm font-semibold text-[color:var(--color-text-strong)]">Review readiness</h3>
          <ul className="mt-3 space-y-2 text-sm text-[color:var(--color-text-muted)]">
            <li>{state.transcriptAttested ? "Transcript attested" : "Transcript attestation required"}</li>
            <li>{state.featuresExtracted ? "Feature extraction complete" : "Feature extraction pending"}</li>
            <li>{state.mlReadiness?.ready === false ? "Evidence readiness check still blocked" : "Evidence readiness check can proceed"}</li>
          </ul>
        </div>
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
          <h3 className="text-sm font-semibold text-[color:var(--color-text-strong)]">Reference status</h3>
          <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
            {missingReferenceData ? "Reference comparison unavailable" : "Reference comparisons are shown only when the backend provides supporting data."}
          </p>
        </div>
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
          <h3 className="text-sm font-semibold text-[color:var(--color-text-strong)]">Limitations</h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[color:var(--color-text-muted)]">
            {(state.mlDecisionSupport?.limitations.length
              ? state.mlDecisionSupport.limitations
              : [
                  "Feature definitions describe how backend values are computed; they do not provide diagnostic conclusions.",
                  "If reference data is unavailable, compare within therapist context rather than inferred norms."
                ]).map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        </div>
      </RightRail>
    </div>
  );
}

function buildLinguisticSignalCards(state: WorkflowState) {
  if (state.featureSignals.length) return state.featureSignals;
  return state.featureSummary.map((item) => ({
    featureName: item.label.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
    displayName: item.label,
    description: "Descriptive language-sample cue from the current workflow.",
    valueType: "string",
    unit: "",
    value: item.value,
    rawValue: item.value,
    calculationMethod: "Derived from the reviewed transcript workflow.",
    requiredInputs: ["reviewed transcript"],
    limitations: [],
    clinicalInterpretationCaution: "Therapist interpretation required.",
    interpretationHint: "Therapist-editable descriptive draft. Do not treat as a diagnosis or final conclusion.",
    referenceText: "Reference comparison unavailable"
  }));
}

function transcriptQualityLabel(state: WorkflowState) {
  if (state.qaStatus === "pass") return `Pass · ${state.transcriptCompleteness || 100}%`;
  if (state.qaStatus === "warning") return `Warning · ${state.transcriptCompleteness || 0}%`;
  if (state.qaStatus === "fail") return "Blocked";
  return "Pending";
}

function totalReviewFlags(state: WorkflowState) {
  return state.reviewNeededCount
    + state.qaIssues.length
    + (state.mlDecisionSupport?.cues.length ?? 0)
    + (state.mlDecisionSupport?.profileEvidence.filter((profile) => profile.reviewState.status === "unreviewed").length ?? 0);
}

function buildRecommendedReviewPoints(state: WorkflowState) {
  const points = new Set<string>();
  if (state.qaIssues.length) {
    for (const issue of state.qaIssues) points.add(issue);
  }
  if (state.mlDecisionSupport?.cues.length) {
    for (const cue of state.mlDecisionSupport.cues) {
      points.add(cue.recommendedNextReviewStep);
    }
  }
  if (!state.transcriptAttested) {
    points.add("Therapist attestation is required before feature extraction and report drafting.");
  }
  if (!state.featuresExtracted) {
    points.add("Complete feature extraction after transcript review to populate report-ready evidence.");
  }
  if (!points.size) {
    points.add("Confirm transcript wording, feature context, and therapist-edited draft text before generating the report.");
  }
  return [...points];
}

function createInterpretationDraft(
  featureSignals: WorkflowState["featureSignals"],
  featureSummary: WorkflowState["featureSummary"],
  mlDecisionSupport?: WorkflowState["mlDecisionSupport"]
) {
  const signalSummary = featureSignals.length
    ? featureSignals.slice(0, 3).map((signal) => `${signal.displayName}: ${signal.value}`).join("; ")
    : featureSummary.slice(0, 3).map((item) => `${item.label}: ${item.value}`).join("; ");
  const cueSummary = mlDecisionSupport?.cues.slice(0, 2).map((cue) => cue.title).join("; ");
  return [
    "Therapist-editable draft text:",
    signalSummary ? `Observed cues: ${signalSummary}.` : "Observed cues: feature review pending.",
    cueSummary ? `Review focus: ${cueSummary}.` : "Review focus: confirm transcript context and therapist notes.",
    "Edit this draft before using it in any report. Decision-support only."
  ].join("\n\n");
}

function hasMissingReferenceData(state: WorkflowState) {
  if (state.featureSignals.some((signal) => signal.referenceText === "Reference comparison unavailable")) return true;
  if (state.mlDecisionSupport?.patternEvidence?.availability.state === "insufficient_reference_data") return true;
  return (state.mlDecisionSupport?.profileEvidence ?? []).some((profile) => profile.availability.state === "insufficient_reference_data");
}

function isResultsReportReady(state: WorkflowState) {
  return isTranscriptUnlocked(state) && state.featuresExtracted;
}

const evidenceStateTitle = {
  input_action_required: "Input action required",
  unsupported_scope: "Outside the supported evidence scope",
  insufficient_reference_data: "Insufficient reference data",
  system_unavailable: "Evidence service unavailable",
  available: "Evidence available"
} as const;

function EvidenceAvailabilityView({ availability }: { availability: NonNullable<WorkflowState["mlDecisionSupport"]>["profileEvidence"][number]["availability"] }) {
  return (
    <div className="mt-2 text-sm text-slate-700">
      <p className="font-semibold">{evidenceStateTitle[availability.state]}</p>
      <p>{availability.message}</p>
      <p className="mt-1 text-xs font-semibold">
        {availability.workflowCanContinue ? "Feature and report workflow can continue." : "Workflow action is required before continuing."}
      </p>
      {availability.nextStep ? <p className="mt-1 text-xs text-slate-600">Next: {availability.nextStep}</p> : null}
    </div>
  );
}

function patternEvidenceTitle(status: "no_additional_pattern_cue" | "additional_evidence_review_suggested" | "not_available") {
  if (status === "no_additional_pattern_cue") return "No additional pattern cue";
  if (status === "additional_evidence_review_suggested") return "Additional evidence review suggested";
  return "Pattern evidence not available";
}

function profileStatusTitle(status: "comparable_patterns_observed" | "limited_comparison" | "not_available") {
  if (status === "comparable_patterns_observed") return "Comparable patterns observed";
  if (status === "limited_comparison") return "Limited comparison";
  return "Not available";
}

function positionTitle(position: "below_iqr" | "within_iqr" | "above_iqr" | "missing") {
  if (position === "below_iqr") return "below the reference IQR";
  if (position === "above_iqr") return "above the reference IQR";
  if (position === "within_iqr") return "within the reference IQR";
  return "value unavailable";
}

function featureLabel(value: string) {
  return value.replaceAll("_", " ");
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
  onExport,
  backendUnavailable,
  audioUrl
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
  backendUnavailable?: boolean;
  audioUrl?: string;
}) {
  const transcriptCompleteness = state.transcriptCompleteness || estimateTranscriptCompleteness(lines);
  const reviewChecklist = [
    { label: "Draft saved", complete: state.transcriptSaveStatus === "saved" },
    { label: "QA completed", complete: state.qaStatus !== "not_run" && state.qaStatus !== "fail" },
    { label: "Therapist attested", complete: state.transcriptAttested }
  ];

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <header>
        <h1 className="text-3xl font-bold text-ink">Review Transcript</h1>
        <p className="mt-2 text-slate-600">Confirm speaker labels and transcript quality before report generation.</p>
      </header>
      <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
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
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          <GlassCard className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-bold text-ink">Transcript review</h2>
              <span
                className={`rounded-full px-3 py-1 text-sm font-bold ${state.transcriptAttested ? "bg-emerald-100 text-emerald-700" : "bg-orange-100 text-orange-700"}`}
                data-testid="transcript-attestation-badge"
              >
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
              backendUnavailable={backendUnavailable}
              onRunQa={onRunQa}
              onAttest={onAttest}
              onExport={onExport}
              audioUrl={audioUrl}
            />
          </GlassCard>
          <GradientButton icon={ShieldCheck} className="w-full text-xl" onClick={onGenerateReport} disabled={busy || !isTranscriptUnlocked(state)}>
            Generate Report
          </GradientButton>
          <SafetyNote>Transcript must be reviewed before report use. Decision-support only. Not diagnostic.</SafetyNote>
        </div>
        <RightRail title="Review Summary" description="Keep therapist review visible before any downstream report or feature workflow continues.">
          <div className="grid gap-3">
            <StatCard label="Transcript completeness" value={`${transcriptCompleteness}%`} helper="Descriptive completeness estimate for therapist review." icon={FileText} tone="accent" />
            <StatCard label="QA status" value={state.qaStatus === "not_run" ? "Not checked" : state.qaStatus === "pass" ? "Pass" : state.qaStatus === "warning" ? "Warning" : "Needs changes"} helper="QA informs review but does not replace therapist judgment." icon={CheckCircle2} tone={state.qaStatus === "pass" ? "success" : "warning"} />
          </div>
          <section className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
            <h3 className="font-semibold text-[color:var(--color-text-strong)]">Review checklist</h3>
            <ul className="mt-3 space-y-2 text-sm text-[color:var(--color-text-muted)]">
              {reviewChecklist.map((item) => (
                <li key={item.label} className="flex items-start gap-3">
                  <span className={`mt-0.5 grid h-5 w-5 place-items-center rounded-full text-xs font-bold ${item.complete ? "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]" : "bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]"}`}>
                    {item.complete ? "✓" : "•"}
                  </span>
                  <span>{item.label}</span>
                </li>
              ))}
            </ul>
          </section>
          <SafetyNotice>
            Before You Continue: therapist review is required. Editing after attestation invalidates attestation until the transcript is saved, QA is run again, and attestation is re-recorded. Feature extraction and report generation stay blocked until review is complete.
          </SafetyNotice>
        </RightRail>
      </div>
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
        <GradientButton icon={ShieldCheck} onClick={onGenerateReport} disabled={busy || !isResultsReportReady(state)}>Generate Report</GradientButton>
      </div>
    </GlassCard>
  );
}

function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  if (!state.statusMessage && !state.error) {
    return null;
  }
  const isError = Boolean(state.error);
  const isSuccess = Boolean(state.statusMessage && !isError);
  if (isSuccess && backendUnavailable) {
    return null;
  }
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

function estimateTranscriptCompleteness(lines: TranscriptLine[]) {
  if (lines.length === 0) return 0;
  const populated = lines.filter((line) => line.text.trim().length > 0).length / lines.length;
  const speakers = lines.filter((line) => line.speaker && line.speaker !== "UNK").length / lines.length;
  const timings = lines.filter((line) => line.startMs !== undefined && line.endMs !== undefined).length / lines.length;
  return Math.max(0, Math.min(100, Math.round((populated * 0.5 + speakers * 0.3 + timings * 0.2) * 100)));
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
