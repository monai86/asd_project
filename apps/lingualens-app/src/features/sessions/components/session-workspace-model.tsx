"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiBlob } from "@/lib/api";

import type { RecordingMetadata } from "@/components/browser-audio-recorder";
import { useBackendAvailability } from "@/components/backend-availability-banner";
import {
  backendTranscriptLines,
  buildBasicChatExport,
  buildFeatureSignals,
  createBackendSession,
  createBackendSessionForCase,
  ensureWorkflowSession,
  classifyWorkflowLoadFailure,
  createIdentityScopedWorkflowState,
  createInitialWorkflowState,
  defaultTranscript,
  evaluateTranscriptQa,
  exportReviewedCha,
  generateBackendMlDecisionSupport,
  getBackendFeatureDefinitions,
  getBackendMlDecisionSupport,
  getBackendMlReadiness,
  getBackendCase,
  getBackendSessionFeatures,
  getBackendSession,
  getBackendSessionTranscript,
  getBackendTranscript,
  loadWorkflowState,
  prepareTranscriptIntake,
  saveWorkflowState,
  summarizeAnalysis,
  type TranscriptLine,
  type WorkflowSource,
  type WorkflowState,
  updateProfileEvidenceReview,
  getSessionAudioFiles,
  type BackendTranscript,
} from "@/lib/workflow";
import { canApplyMlDecisionSupportSettlement, canApplyTranscriptSaveSettlement, canSettleWorkflowRequest, derivePipelineStatus, sessionWorkflowReducer } from "@/features/sessions/state/session-workflow-reducer";
import {
  audioLineage,
  describeAudioWorkflowFailure,
  describeFailedAudioJob,
  AudioWorkflowContractError,
  sessionWorkflowService,
  type AudioCapabilities,
  type AudioLineage,
  type AudioProcessingJob,
  type SpeakerMappingEntry,
  type SpeakerMappingResponse,
} from "@/features/sessions/services/session-workflow-service";
import { resolveSessionHref, resolveWorkspaceFeature, type SessionView } from "@/features/sessions/state/session-view";
import type { SessionIntakeSource, SessionIntakeStepId } from "@/features/sessions/intake/session-intake-view";
import type { AudioFileUploadState } from "@/features/sessions/intake/audio-file-upload-panel";
import type { SessionContext } from "@/features/sessions/components/session-context-header";
import { SessionWorkflowView, type SessionWorkflowViewModel } from "@/features/sessions/components/session-workspace-view";


export type SessionWorkspaceProps = {
  sessionId?: string;
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
  view?: SessionView;
  mode?: string;
};

type SessionWorkspaceIdentityProps = Omit<SessionWorkspaceProps, "view"> & {
  view?: "intake" | "transcript" | "findings";
};

const DEFAULT_AUDIO_CAPABILITIES: AudioCapabilities = {
  milestone: "v1.7.0-testbed",
  max_size_bytes: 100 * 1024 * 1024,
  max_duration_seconds: 15 * 60,
  supported_formats: ["wav", "mp3"],
  processing_state: "unavailable",
  unavailable_reason: "capabilities_loading",
  normalization: {
    channels: 1,
    sample_rate_hz: 16_000,
    format: "wav_pcm_s16le",
    source_min_sample_rate_hz: 8_000,
    source_max_sample_rate_hz: 192_000,
    source_max_channels: 8,
    max_rational_factor: 512,
    max_filter_taps: 262_144,
    max_working_bytes: 512 * 1024 * 1024,
  },
  browser_recording: {
    state: "experimental_unavailable",
    blocks_milestone: false,
  },
};

export function SessionWorkflowWorkspace(props: SessionWorkspaceProps) {
  const identityKey = JSON.stringify([
    props.sessionId ?? "",
    props.caseId ?? "",
    props.transcriptId ?? "",
    props.reportId ?? "",
    props.mode ?? "",
  ]);
  const view = resolveWorkspaceFeature(props.view);
  return <SessionWorkspaceIdentityScope key={identityKey} {...props} view={view} />;
}

function SessionWorkspaceIdentityScope({ sessionId, caseId, transcriptId, reportId, view = "intake", mode }: SessionWorkspaceIdentityProps) {
  const model = useSessionWorkspace({ sessionId, caseId, transcriptId, reportId, view, mode });
  return <SessionWorkflowView model={model} />;
}

/**
 * Identity-scoped workflow controller. It owns request sequencing, persistence,
 * and mutations; visual rendering stays in SessionWorkflowView and the feature
 * views so transport state cannot leak into layout components.
 */
export function useSessionWorkspace({ sessionId, caseId, transcriptId, reportId, view = "intake", mode }: SessionWorkspaceIdentityProps): SessionWorkflowViewModel {
  const hasLocator = Boolean(sessionId || transcriptId || caseId || reportId);
  const [state, setState] = useState<WorkflowState>(() => hasLocator
    ? createIdentityScopedWorkflowState({ workflowLoading: true, statusMessage: "Loading persisted workflow..." })
    : createInitialWorkflowState());
  const workflowRevisionRef = useRef(0);
  const activeTranscriptSaveRevisionRef = useRef<number | null>(null);
  const workflowStateRef = useRef(state);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    workflowStateRef.current = state;
  }, [state]);
  const [draftTranscript, setDraftTranscript] = useState(hasLocator ? "" : defaultTranscript);
  const [editorLines, setEditorLines] = useState<TranscriptLine[]>([]);
  const [sourceFilename, setSourceFilename] = useState<string | undefined>();
  const [intakeError, setIntakeError] = useState("");
  const [intakeWarnings, setIntakeWarnings] = useState<string[]>([]);
  const [intakeValidationIssues, setIntakeValidationIssues] = useState<string[]>([]);
  const [recordedAudio, setRecordedAudio] = useState<{ blob: Blob; metadata: RecordingMetadata } | null>(null);
  const [audioCapabilities, setAudioCapabilities] = useState<AudioCapabilities>(DEFAULT_AUDIO_CAPABILITIES);
  const [audioFileUploadState, setAudioFileUploadState] = useState<AudioFileUploadState>({ state: "idle" });
  const [speakerMapping, setSpeakerMapping] = useState<SpeakerMappingResponse | undefined>(undefined);
  const audioWorkflowGenerationRef = useRef(0);
  const audioLifecycleAbortRef = useRef<AbortController | null>(null);
  const audioJobIdRef = useRef<string | undefined>(undefined);
  const audioFileIdRef = useRef<string | undefined>(undefined);
  const audioLineageRef = useRef<AudioLineage | undefined>(undefined);
  const [intakeStep, setIntakeStep] = useState<SessionIntakeStepId>(mode ? "source" : "details");
  const [selectedSource, setSelectedSource] = useState<SessionIntakeSource>(sourceFromMode(mode));
  const [sessionDetails, setSessionDetails] = useState(() => createSessionDetailsDraft(
    hasLocator ? createIdentityScopedWorkflowState() : createInitialWorkflowState(),
  ));
  const [transcriptSetup, setTranscriptSetup] = useState(createTranscriptSetupDraft());
  const [caseConsent, setCaseConsent] = useState<string>("granted");
  const [consentSigner, setConsentSigner] = useState("Parent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentNotes, setConsentNotes] = useState("");
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => () => {
    workflowRevisionRef.current += 1;
    activeTranscriptSaveRevisionRef.current = null;
    audioWorkflowGenerationRef.current += 1;
    audioLifecycleAbortRef.current?.abort();
    audioLifecycleAbortRef.current = null;
  }, []);

  const handleRecordingReady = (blob: Blob, metadata: RecordingMetadata) => {
    setRecordedAudio({ blob, metadata });
  };

  const [audioUrl, setAudioUrl] = useState<string | undefined>(undefined);
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const router = useRouter();
  const browserRecordingEnabled = process.env.NODE_ENV === "development"
    && process.env.NEXT_PUBLIC_BROWSER_RECORDING_EXPERIMENTAL === "true";

  const pipelineStatusValue = useMemo(() => {
    return derivePipelineStatus(state, caseConsent, audioFileUploadState.state);
  }, [audioFileUploadState.state, caseConsent, state]);

  useEffect(() => {
    let cancelled = false;
    void sessionWorkflowService.getAudioCapabilities()
      .then((capabilities) => {
        if (!cancelled) setAudioCapabilities(capabilities);
      })
      .catch(() => {
        if (!cancelled) {
          setAudioCapabilities({
            ...DEFAULT_AUDIO_CAPABILITIES,
            unavailable_reason: "capabilities_unavailable",
          });
        }
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!hasLocator) {
      const stored = loadWorkflowState();
      setState((current) => sessionWorkflowReducer(current, { type: "session-identity-changed", state: stored }));
      setDraftTranscript(stored.transcriptText || (mode === "paste" || mode === "cha" ? "" : defaultTranscript));
      setEditorLines(stored.transcriptLines);
      setSourceFilename(stored.sourceFilename);
      setIntakeWarnings(stored.chatWarnings);
      setIntakeValidationIssues(stored.chatValidationIssues);
      setIsHydrated(true);
      return;
    }

    const loadingState = saveWorkflowState(sessionWorkflowReducer(
      createIdentityScopedWorkflowState(),
      { type: "request-started", message: "Loading persisted workflow..." },
    ));
    setBackendUnavailable(false);
    setState(loadingState);
    setAudioUrl(undefined);
    setDraftTranscript("");
    setEditorLines([]);
    setSourceFilename(undefined);
    setIntakeWarnings([]);
    setIntakeValidationIssues([]);
    void Promise.resolve().then(async () => {
      // React Strict Mode replays effects in development. Deferring the request
      // one microtask lets the replay cleanup cancel the discarded run before
      // it can issue duplicate clinical-workflow reads.
      if (cancelled) return;
      try {
        const loaded = sessionId
          ? await sessionWorkflowService.load({ sessionId, transcriptId, reportId })
          : undefined;
        const backendSession = loaded?.session;
        const backendReport = loaded?.report;
        const resolvedTranscriptId = transcriptId ?? backendSession?.transcript_id;
        const transcript = loaded?.transcript ?? (resolvedTranscriptId
          ? await getBackendTranscript(resolvedTranscriptId)
          : backendSession
            ? await getBackendSessionTranscript(backendSession.session_id).catch(() => undefined)
            : undefined);
        const resolvedCaseId = caseId ?? backendSession?.case_id ?? transcript?.case_id;
        const childCase = resolvedCaseId ? await getBackendCase(resolvedCaseId) : undefined;
        if (childCase && !cancelled) {
          setCaseConsent(childCase.consent_status ?? "pending");
        }
        const lines = transcript ? backendTranscriptLines(transcript) : [];
        const parsed = transcript?.raw_text ? prepareTranscriptIntake("cha-upload", transcript.raw_text) : undefined;
        const resolvedSpeakerMapping = await loadSpeakerMappingForTranscript(transcript).catch(() => undefined);

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
        const findingsAreStale = backendFeatures?.review_status === "stale";

        if (cancelled) {
          if (resolvedAudioUrl?.startsWith("blob:")) {
            URL.revokeObjectURL(resolvedAudioUrl);
          }
          return;
        }
        const emptyState = createIdentityScopedWorkflowState();
        const hydrated = saveWorkflowState({
          ...emptyState,
          sessionId: resolvedSessionId,
          caseId: resolvedCaseId,
          caseInfo: {
            caseId: resolvedCaseId,
            clientLabel: childCase?.nickname ?? childCase?.child_code ?? ""
          },
          childName: childCase?.nickname ?? childCase?.child_code ?? "",
          backendSessionId: backendSession?.session_id ?? sessionId,
          backendTranscriptSessionId: transcript?.session_id ?? backendSession?.session_id ?? sessionId,
          backendTranscriptId: transcript?.transcript_id,
          backendTranscriptVersion: transcript?.version,
          backendReportId: backendReport?.report_id ?? reportId ?? backendSession?.report_id,
          backendReportVersion: backendReport?.version,
          reportGeneratedFromVersions: backendReport?.generated_from_versions,
          reportId: backendReport?.report_id ?? reportId ?? backendSession?.report_id,
          featureSetId: backendFeatures?.feature_set_id ?? backendSession?.feature_set_id,
          featureTranscriptVersion: backendFeatures?.transcript_version,
          transcriptText: transcript?.raw_text ?? "",
          transcriptLines: lines,
          chatMetadata: parsed?.metadata ?? emptyState.chatMetadata,
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
          analysisStatus: findingsAreStale ? "stale" : backendFeatures ? "completed" : "not_started",
          featuresExtracted: Boolean(backendSession?.feature_set_id) && !findingsAreStale,
          featureSignals,
          mlReadiness,
          mlDecisionSupport,
          reportStatus: normalizeHydratedReportStatus(backendReport?.status),
          workflowLoading: false,
          statusMessage: transcript ? "Persisted transcript loaded." : "Persisted session loaded.",
          error: undefined
        });
        setAudioUrl(resolvedAudioUrl);
        setState(sessionWorkflowReducer(loadingState, { type: "hydration-succeeded", state: hydrated }));
        setDraftTranscript(hydrated.transcriptText);
        setEditorLines(hydrated.transcriptLines);
        setIntakeWarnings(hydrated.chatWarnings);
        setIntakeValidationIssues(hydrated.chatValidationIssues);
        setSpeakerMapping(resolvedSpeakerMapping);
        setIsHydrated(true);
      } catch (error) {
        if (cancelled) return;
        const failure = classifyWorkflowLoadFailure(error, "workflow");
        setBackendUnavailable(failure.backendUnavailable);
        const failedState = saveWorkflowState(sessionWorkflowReducer(
          createIdentityScopedWorkflowState(),
          { type: "request-failed", message: failure.statusMessage, error: failure.error },
        ));
        setAudioUrl(undefined);
        setState(failedState);
        setDraftTranscript("");
        setEditorLines([]);
        setSourceFilename(undefined);
        setIntakeWarnings([]);
        setIntakeValidationIssues([]);
        setIsHydrated(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [caseId, hasLocator, mode, reportId, sessionId, setBackendUnavailable, transcriptId]);

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
    workflowStateRef.current = saved;
    setState(saved);
    return saved;
  }

  function currentWorkflowRequestIdentity() {
    const current = workflowStateRef.current;
    return {
      revision: workflowRevisionRef.current,
      sessionId: current.backendTranscriptSessionId ?? current.backendSessionId,
      transcriptId: current.backendTranscriptId,
      transcriptVersion: current.backendTranscriptVersion,
    };
  }

  async function loadSpeakerMappingForTranscript(
    transcript: BackendTranscript | undefined,
    signal?: AbortSignal,
  ) {
    if (!transcript?.transcript_id || !transcriptRequiresSpeakerMapping(transcript)) {
      return undefined;
    }
    return sessionWorkflowService.getSpeakerMapping(transcript.transcript_id, signal);
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
        reportStatus: "not_started",
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

  async function handleGrantConsent() {
    if (!consentChecked || !caseId) return;
    setBusy(true);
    setIntakeError("");
    try {
      await sessionWorkflowService.grantCaseConsent(caseId);
      setCaseConsent("granted");
    } catch {
      setIntakeError("Could not update case consent on the backend.");
    } finally {
      setBusy(false);
    }
  }

  function cancelAudioLifecycle() {
    audioWorkflowGenerationRef.current += 1;
    audioLifecycleAbortRef.current?.abort();
    audioLifecycleAbortRef.current = null;
  }

  function clearPersistedAudioJob(nextSource?: SessionIntakeSource) {
    persist({
      ...workflowStateRef.current,
      source: nextSource ? workflowSourceFromSelection(nextSource) : workflowStateRef.current.source,
      transcriptionJobId: undefined,
      transcriptionJobStatus: undefined,
      transcriptionJobMessage: undefined,
      transcriptDraftLabel: undefined,
      statusMessage: nextSource
        ? "Audio processing was left behind when the source changed."
        : workflowStateRef.current.statusMessage,
      error: undefined,
    });
  }

  function abandonAudioJob(jobId?: string) {
    if (!jobId) return;
    void sessionWorkflowService.cancelAudioProcessingJob(jobId).catch(() => undefined);
  }

  function handleSelectedSourceChange(nextSource: SessionIntakeSource) {
    if (nextSource !== selectedSource) {
      const abandonedJobId = audioJobIdRef.current;
      cancelAudioLifecycle();
      abandonAudioJob(abandonedJobId);
      audioJobIdRef.current = undefined;
      audioFileIdRef.current = undefined;
      audioLineageRef.current = undefined;
      setSpeakerMapping(undefined);
      if (hasCurrentTranscriptLineage(workflowStateRef.current)) {
        persist(resetTranscriptForSourceReplacement(
          workflowStateRef.current,
          workflowSourceFromSelection(nextSource),
        ));
        setDraftTranscript("");
        setEditorLines([]);
        setSourceFilename(undefined);
      } else {
        clearPersistedAudioJob(nextSource);
      }
      setAudioFileUploadState({ state: "idle" });
      setRecordedAudio(null);
      setBusy(false);
    }
    setSelectedSource(nextSource);
  }

  function handleAudioFileSelected(file: File) {
    const abandonedJobId = audioJobIdRef.current;
    cancelAudioLifecycle();
    abandonAudioJob(abandonedJobId);
    audioJobIdRef.current = undefined;
    audioFileIdRef.current = undefined;
    audioLineageRef.current = undefined;
    setSpeakerMapping(undefined);
    if (abandonedJobId) clearPersistedAudioJob();
    if (audioCapabilities.processing_state !== "available") {
      setAudioFileUploadState({
        state: "failed",
        code: audioCapabilities.unavailable_reason ?? "audio_capability_unavailable",
        message: "The verified audio capability is unavailable. Restore the pinned decoder runtime before selecting a file.",
        retryable: false,
      });
      return;
    }
    if (file.size > audioCapabilities.max_size_bytes) {
      setAudioFileUploadState({
        state: "failed",
        code: "client_audio_size_limit_exceeded",
        message: `This file is larger than ${formatLimitBytes(audioCapabilities.max_size_bytes)}. Choose a smaller file. The server will still verify the actual uploaded size, decoded duration, and format.`,
        retryable: false,
      });
      return;
    }
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!extension || !audioCapabilities.supported_formats.includes(extension)) {
      setAudioFileUploadState({
        state: "failed",
        code: "client_audio_format_unavailable",
        message: `Choose a supported format: ${audioCapabilities.supported_formats.map((item) => item.toUpperCase()).join(", ")}. The server will verify the decoded format.`,
        retryable: false,
      });
      return;
    }
    setAudioFileUploadState({ state: "selected", file });
  }

  function resetAudioFileUpload() {
    const abandonedJobId = audioJobIdRef.current;
    cancelAudioLifecycle();
    abandonAudioJob(abandonedJobId);
    audioJobIdRef.current = undefined;
    audioFileIdRef.current = undefined;
    audioLineageRef.current = undefined;
    clearPersistedAudioJob();
    setAudioFileUploadState({ state: "idle" });
    setBusy(false);
  }

  async function handleAudioFileUpload() {
    if (audioFileUploadState.state !== "selected") return;
    const file = audioFileUploadState.file;
    cancelAudioLifecycle();
    const generation = audioWorkflowGenerationRef.current;
    const controller = new AbortController();
    audioLifecycleAbortRef.current = controller;
    setBusy(true);
    setAudioFileUploadState({ state: "uploading", file, progress: 0 });
    try {
      let backendSessionId = workflowStateRef.current.backendSessionId
        ?? (sessionId && !sessionId.startsWith("local_") ? sessionId : undefined);
      let backendCaseId = workflowStateRef.current.caseId ?? caseId;
      if (!backendSessionId) {
        if (!backendCaseId) throw new Error("audio_session_required");
        const created = await createBackendSessionForCase(backendCaseId, "audio-upload");
        backendSessionId = created.session_id;
        backendCaseId = created.case_id;
      }
      if (generation !== audioWorkflowGenerationRef.current) return;
      const currentState = workflowStateRef.current;
      const uploadBaseState = hasCurrentTranscriptLineage(currentState)
        ? resetTranscriptForSourceReplacement(currentState, "audio-upload")
        : currentState;
      if (uploadBaseState !== currentState) {
        setDraftTranscript("");
        setEditorLines([]);
        setSourceFilename(undefined);
      }
      persist(ensureWorkflowSession(buildIntakeBackedState(uploadBaseState, "audio-upload"), "audio-upload", {
        backendSessionId,
        caseId: backendCaseId,
        caseInfo: {
          ...workflowStateRef.current.caseInfo,
          caseId: backendCaseId,
        },
        source: "audio-upload",
        mockAudioStored: false,
        transcriptReady: false,
        transcriptAttested: false,
        transcriptReviewStatus: "not_started",
        qaStatus: "not_run",
        analysisStatus: "not_started",
        reportStatus: "not_started",
        statusMessage: "Uploading a synthetic source asset for server verification.",
        error: undefined,
      }));
      const intent = await sessionWorkflowService.createAudioUploadIntent(backendSessionId, file, controller.signal);
      if (generation !== audioWorkflowGenerationRef.current) return;
      audioFileIdRef.current = intent.audioFileId;
      setAudioFileUploadState({ state: "uploading", file, progress: 25 });
      await sessionWorkflowService.uploadAudioSource(intent, file, controller.signal);
      if (generation !== audioWorkflowGenerationRef.current) return;
      setAudioFileUploadState({ state: "uploading", file, progress: 100 });
      setAudioFileUploadState({ state: "verifying", audioFileId: intent.audioFileId });
      await sessionWorkflowService.completeAudioUpload(intent, file, controller.signal);
      if (generation !== audioWorkflowGenerationRef.current) return;
      setAudioFileUploadState({ state: "normalizing", audioFileId: intent.audioFileId });
      const normalized = await sessionWorkflowService.verifyAndNormalizeAudio(intent, controller.signal);
      if (generation !== audioWorkflowGenerationRef.current) return;
      const lineage = audioLineage(intent, normalized);
      audioLineageRef.current = lineage;
      const job = await sessionWorkflowService.startAudioTranscription(
        backendSessionId,
        intent,
        normalized,
        controller.signal,
      );
      if (generation !== audioWorkflowGenerationRef.current) return;
      audioJobIdRef.current = job.job_id;
      setAudioFileUploadState({ state: "transcribing", audioFileId: intent.audioFileId, jobId: job.job_id });
      const jobState = job.status === "failed" || job.status === "cancelled"
        ? workflowStateRef.current
        : resetTranscriptForSourceReplacement(workflowStateRef.current, "audio-upload");
      if (jobState !== workflowStateRef.current) {
        setDraftTranscript("");
        setEditorLines([]);
        setSourceFilename(undefined);
      }
      persist({
        ...jobState,
        transcriptionJobId: job.job_id,
        transcriptionJobStatus: persistedAudioJobStatus(job.status),
        transcriptionJobMessage: job.message,
        statusMessage: "Real transcription draft is processing.",
        error: undefined,
      });
      setBusy(false);
      startAudioJobMonitor(job, intent.audioFileId, backendSessionId, generation, controller, lineage);
    } catch (error) {
      if (generation !== audioWorkflowGenerationRef.current) return;
      const failure = describeAudioWorkflowFailure(error);
      setAudioFileUploadState({ state: "failed", ...failure });
      persist({
        ...workflowStateRef.current,
        transcriptionJobStatus: "failed",
        transcriptionJobMessage: failure.message,
        statusMessage: "Verified audio workflow stopped.",
        error: failure.message,
      });
      setBusy(false);
      audioLifecycleAbortRef.current = null;
    }
  }

  async function handleAudioJobRetry() {
    const failedJobId = audioJobIdRef.current;
    const audioFileId = audioFileIdRef.current;
    const lineage = audioLineageRef.current;
    const backendSessionId = workflowStateRef.current.backendSessionId;
    if (audioFileUploadState.state !== "failed" || !audioFileUploadState.retryable || !failedJobId || !audioFileId || !lineage || !backendSessionId) return;
    cancelAudioLifecycle();
    const generation = audioWorkflowGenerationRef.current;
    const controller = new AbortController();
    audioLifecycleAbortRef.current = controller;
    setBusy(true);
    try {
      const job = await sessionWorkflowService.retryAudioProcessingJob(
        failedJobId,
        backendSessionId,
        lineage,
        controller.signal,
      );
      if (generation !== audioWorkflowGenerationRef.current) return;
      audioJobIdRef.current = job.job_id;
      setAudioFileUploadState({ state: "transcribing", audioFileId, jobId: job.job_id });
      const jobState = job.status === "failed" || job.status === "cancelled"
        ? workflowStateRef.current
        : resetTranscriptForSourceReplacement(workflowStateRef.current, "audio-upload");
      if (jobState !== workflowStateRef.current) {
        setDraftTranscript("");
        setEditorLines([]);
        setSourceFilename(undefined);
      }
      persist({
        ...jobState,
        transcriptionJobId: job.job_id,
        transcriptionJobStatus: persistedAudioJobStatus(job.status),
        transcriptionJobMessage: job.message,
        statusMessage: "Real transcription retry is processing.",
        error: undefined,
      });
      setBusy(false);
      startAudioJobMonitor(job, audioFileId, backendSessionId, generation, controller, lineage);
    } catch (error) {
      if (generation !== audioWorkflowGenerationRef.current) return;
      const failure = describeAudioWorkflowFailure(error);
      setAudioFileUploadState({ state: "failed", ...failure });
      persistAudioFailure(failedJobId, failure, "Verified transcription retry stopped.");
      setBusy(false);
      audioLifecycleAbortRef.current = null;
    }
  }

  function startAudioJobMonitor(
    initialJob: AudioProcessingJob,
    audioFileId: string,
    backendSessionId: string,
    generation: number,
    controller: AbortController,
    lineage: AudioLineage,
  ) {
    void pollAudioProcessingJob(initialJob, audioFileId, backendSessionId, generation, controller, lineage);
  }

  async function pollAudioProcessingJob(
    initialJob: AudioProcessingJob,
    audioFileId: string,
    backendSessionId: string,
    generation: number,
    controller: AbortController,
    lineage: AudioLineage,
  ) {
    const jobId = initialJob.job_id;
    let consecutiveNetworkFailures = 0;
    let job: AudioProcessingJob | undefined = initialJob;
    while (generation === audioWorkflowGenerationRef.current) {
      if (!job) {
        await delay(process.env.NODE_ENV === "test" ? 10 : 2_000);
        if (generation !== audioWorkflowGenerationRef.current) return;
        try {
          job = await sessionWorkflowService.getAudioProcessingJob(
            jobId,
            controller.signal,
            backendSessionId,
            lineage,
          );
          consecutiveNetworkFailures = 0;
        } catch (error) {
          if (controller.signal.aborted || generation !== audioWorkflowGenerationRef.current) return;
          if (error instanceof AudioWorkflowContractError || error instanceof ApiError) {
            const failure = describeAudioWorkflowFailure(error);
            setAudioFileUploadState({ state: "failed", ...failure });
            persistAudioFailure(jobId, failure, "Transcription job monitoring stopped.");
            setBusy(false);
            audioLifecycleAbortRef.current = null;
            return;
          }
          consecutiveNetworkFailures += 1;
          if (consecutiveNetworkFailures < 3) continue;
          const failure = {
            code: "job_status_unavailable",
            message: "The backend job status could not be verified after repeated network failures. Reopen this session after connectivity is restored.",
            retryable: false,
          };
          setAudioFileUploadState({ state: "failed", ...failure });
          persistAudioFailure(jobId, failure, "Transcription job monitoring stopped.");
          setBusy(false);
          audioLifecycleAbortRef.current = null;
          return;
        }
      }
      if (generation !== audioWorkflowGenerationRef.current) return;
      if (job.status === "needs_review") {
        const transcriptId = job.details?.asr_draft?.transcript_id;
        if (!transcriptId) {
          setAudioFileUploadState({
            state: "failed",
            code: "asr_draft_missing",
            message: "The job completed without a linked transcription draft. Ask an administrator to inspect the job provenance.",
            retryable: false,
          });
          persistAudioFailure(jobId, {
            code: "asr_draft_missing",
            message: "The job completed without a linked transcription draft. Ask an administrator to inspect the job provenance.",
            retryable: false,
          }, "Transcription draft linkage failed.");
          audioLifecycleAbortRef.current = null;
          return;
        }
        try {
          const transcript = await getBackendTranscript(transcriptId, { signal: controller.signal });
          if (generation !== audioWorkflowGenerationRef.current) return;
          if (
            transcript.transcript_id !== transcriptId
            || transcript.session_id !== backendSessionId
            || (workflowStateRef.current.caseId
              && transcript.case_id !== workflowStateRef.current.caseId)
            || transcript.source !== "asr_draft:local_faster_whisper"
            || !transcriptAsrLineageMatches(transcript.asr_provenance, jobId, lineage)
            || typeof transcript.raw_text !== "string"
            || !Number.isSafeInteger(transcript.version)
            || (transcript.version ?? 0) < 1
            || !Array.isArray(transcript.utterances)
            || transcript.utterances.some((utterance) => (
              !utterance
              || typeof utterance.utterance_id !== "string"
              || typeof utterance.speaker !== "string"
              || typeof utterance.text !== "string"
            ))
          ) {
            throw new AudioWorkflowContractError("transcript_lineage_mismatch");
          }
          const resolvedSpeakerMapping = await loadSpeakerMappingForTranscript(transcript, controller.signal).catch(() => undefined);
          if (generation !== audioWorkflowGenerationRef.current) return;
          const lines = backendTranscriptLines(transcript);
          const saved = persist({
            ...workflowStateRef.current,
            backendSessionId,
            backendTranscriptSessionId: backendSessionId,
            backendTranscriptId: transcriptId,
            backendTranscriptVersion: transcript.version,
            transcriptReplacementRequired: undefined,
            replacementTranscriptId: undefined,
            replacementTranscriptVersion: undefined,
            transcriptText: transcript.raw_text ?? "",
            transcriptLines: lines,
            transcriptReady: true,
            transcriptAttested: false,
            transcriptionJobId: jobId,
            transcriptionJobStatus: "completed",
            transcriptionJobMessage: job.message,
            transcriptReviewStatus: "in_review",
            transcriptDraftLabel: "Draft ASR transcript — therapist review required.",
            statusMessage: "Real transcription draft is ready for therapist review.",
            error: undefined,
          });
          setEditorLines(lines);
          setDraftTranscript(transcript.raw_text ?? "");
          setSpeakerMapping(resolvedSpeakerMapping);
          setAudioFileUploadState({ state: "needs_review", transcriptId });
          setBusy(false);
          audioLifecycleAbortRef.current = null;
          router.push(workflowSessionHref("transcript", saved));
        } catch (error) {
          if (controller.signal.aborted || generation !== audioWorkflowGenerationRef.current) return;
          const failure = error instanceof AudioWorkflowContractError
            ? describeAudioWorkflowFailure(error)
            : {
                code: "transcript_load_failed",
                message: "The completed backend draft could not be loaded safely. Reopen this session after the backend is restored.",
                retryable: false,
              };
          setAudioFileUploadState({ state: "failed", ...failure });
          persistAudioFailure(jobId, failure, "Transcription draft validation failed.");
          setBusy(false);
          audioLifecycleAbortRef.current = null;
        }
        return;
      }
      if (job.status === "failed" || job.status === "cancelled") {
        const failure = job.status === "failed"
          ? describeFailedAudioJob(job)
          : {
              code: "transcription_cancelled",
              message: "Transcription was cancelled before a complete draft was created.",
              retryable: false,
            };
        setAudioFileUploadState({ state: "failed", ...failure });
        persist({
          ...workflowStateRef.current,
          transcriptionJobId: jobId,
          transcriptionJobStatus: "failed",
          transcriptionJobMessage: failure.message,
          statusMessage: "Verified transcription did not complete.",
          error: failure.message,
        });
        setBusy(false);
        audioLifecycleAbortRef.current = null;
        return;
      }
      setAudioFileUploadState({ state: "transcribing", audioFileId, jobId });
      job = undefined;
    }
  }

  function persistAudioFailure(
    jobId: string,
    failure: { code: string; message: string; retryable: boolean },
    statusMessage: string,
  ) {
    persist({
      ...workflowStateRef.current,
      transcriptionJobId: jobId,
      transcriptionJobStatus: "failed",
      transcriptionJobMessage: failure.message,
      statusMessage,
      error: failure.message,
    });
  }

  function openAudioDraftTranscript(transcriptId: string) {
    if (workflowStateRef.current.backendTranscriptId !== transcriptId) return;
    router.push(workflowSessionHref("transcript", workflowStateRef.current));
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
    const replacementRequired = workflowStateRef.current.transcriptReplacementRequired === true;
    const replacementTranscriptId = workflowStateRef.current.replacementTranscriptId;
    const replacementTranscriptVersion = workflowStateRef.current.replacementTranscriptVersion;
    if (
      replacementRequired
      && (!replacementTranscriptId || !Number.isSafeInteger(replacementTranscriptVersion))
    ) {
      setIntakeError("The existing transcript version cannot be replaced safely. Reload the session and try again.");
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
      reportStatus: "not_started",
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
      const updated = await sessionWorkflowService.saveTranscript({
        sessionId: backendSessionId,
        transcriptId: replacementRequired ? undefined : localSession.backendTranscriptId,
        source,
        originalText: draftTranscript,
        normalizedText: intake.transcriptText,
        sourceFilename,
        replaceExisting: replacementRequired,
        expectedExistingTranscriptId: replacementTranscriptId,
        expectedExistingTranscriptVersion: replacementTranscriptVersion,
      });
      const savedState = persist({
        ...localSession,
        backendSessionId,
        backendTranscriptId: updated.transcript_id,
        backendTranscriptSessionId: backendSessionId,
        backendTranscriptVersion: updated.version,
        transcriptReplacementRequired: undefined,
        replacementTranscriptId: undefined,
        replacementTranscriptVersion: undefined,
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
      setSpeakerMapping(undefined);
      router.push(workflowSessionHref("transcript", savedState));
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
    const analyzingState = persist(sessionWorkflowReducer(
      ensureWorkflowSession(state, state.source ?? "recording"),
      { type: "findings-started" },
    ));
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: analyzingState.backendTranscriptSessionId ?? analyzingState.backendSessionId,
      transcriptId: analyzingState.backendTranscriptId,
      transcriptVersion: analyzingState.backendTranscriptVersion,
    };
    try {
      const targetSession = analyzingState.backendTranscriptSessionId ?? analyzingState.backendSessionId;
      if (!targetSession || !analyzingState.backendTranscriptId) throw new Error("Persistent transcript unavailable.");
      const backendAnalysis = await sessionWorkflowService.extractFindings(targetSession, analyzingState.backendTranscriptId);
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      persist(sessionWorkflowReducer(analyzingState, { type: "findings-succeeded", findings: backendAnalysis }));
      router.push(workflowSessionHref("findings", analyzingState));
    } catch {
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist(sessionWorkflowReducer(analyzingState, { type: "findings-failed", error: "Backend unavailable. No feature result was recorded." }));
    } finally {
      if (canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
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
    if (!state.featuresExtracted) {
      persist({
        ...state,
        statusMessage: "Report generation is locked until language-sample features are extracted.",
        error: "Extract language-sample features from the attested transcript before generating a report."
      });
      return;
    }
    setBusy(true);
    const reportingState = persist(sessionWorkflowReducer(
      ensureWorkflowSession(state, state.source ?? "recording"),
      { type: "report-started" },
    ));
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: reportingState.backendTranscriptSessionId ?? reportingState.backendSessionId,
      transcriptId: reportingState.backendTranscriptId,
      transcriptVersion: reportingState.backendTranscriptVersion,
    };
    try {
      const targetSession = reportingState.backendTranscriptSessionId ?? reportingState.backendSessionId;
      if (!targetSession) throw new Error("Persistent session unavailable.");
      const report = await sessionWorkflowService.generateReport({ sessionId: targetSession });
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      if (!report.report_id) throw new Error("Report ID missing.");
      const savedState = persist(sessionWorkflowReducer(reportingState, {
        type: "report-succeeded",
        reportId: report.report_id,
        markdown: report.content_markdown ?? report.markdown ?? "",
        finalized: report.status === "Signed Off",
        version: report.version,
        generatedFromVersions: report.generated_from_versions,
      }));
      router.push(resolveSessionHref("report", savedState.backendSessionId ?? savedState.backendTranscriptSessionId, {
        caseId: savedState.caseId,
        transcriptId: savedState.backendTranscriptId,
        reportId: report.report_id,
      }));
    } catch {
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist(sessionWorkflowReducer(reportingState, { type: "report-failed", error: "Backend unavailable. No report draft was created." }));
    } finally {
      if (canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
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
    const mlState = state;
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: mlState.backendTranscriptSessionId ?? mlState.backendSessionId,
      transcriptId: mlState.backendTranscriptId,
      transcriptVersion: mlState.backendTranscriptVersion,
    };
    try {
      if (!mlState.backendTranscriptId) throw new Error("Persistent transcript unavailable.");
      const mlDecisionSupport = await generateBackendMlDecisionSupport(mlState.backendTranscriptId);
      if (!canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      persist({
        ...mlState,
        mlDecisionSupport,
        statusMessage: "Evidence review generated. Therapist interpretation is required.",
        error: undefined
      });
    } catch {
      if (!canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist({
        ...mlState,
        mlDecisionSupport: undefined,
        statusMessage: "ML review unavailable — backend verification required.",
        error: "Backend unavailable. No ML review result was generated or loaded."
      });
    } finally {
      if (canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
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

  const sessionContext: SessionContext = {
    sessionId: state.backendSessionId ?? state.sessionId ?? sessionId,
    caseLabel: state.childName || state.caseInfo.clientLabel || state.caseId || caseId,
    sourceLabel: workflowSourceLabel(state.source),
    consentStatus: caseConsent,
    workflowStatus: pipelineStatusValue.replaceAll("_", " "),
    dataMode: state.backendSessionId
      ? "backend"
      : backendUnavailable && hasLocator
        ? "unavailable"
        : "local_draft",
    activeView: view,
  };

  if (view === "findings") {
    return {
      view: "findings",
      backendUnavailable,
      viewProps: {
        sessionContext,
        state,
        busy,
        onRegenerateFindings: handleAnalyze,
        onGenerateReport: handleGenerateReport,
        onGenerateMlDecisionSupport: handleGenerateMlDecisionSupport,
        onProfileEvidenceReview: handleProfileEvidenceReview,
        backendUnavailable,
      },
    };
  }

  if (view === "transcript") {
    return {
      view: "transcript",
      backendUnavailable,
      viewProps: {
        sessionContext,
        state,
        lines: editorLines,
        busy,
        backendUnavailable,
        audioUrl,
        speakerMapping,
        onLinesChange: (lines) => {
          workflowRevisionRef.current += 1;
          activeTranscriptSaveRevisionRef.current = null;
          setBusy(false);
          setEditorLines(lines);
          setSpeakerMapping((current) => current ? markSpeakerMappingStale(current) : current);
          persist({
            ...sessionWorkflowReducer(state, { type: "transcript-edited", lines }),
            statusMessage: "Unsaved transcript edits.",
          });
        },
        onSaveDraft: () => handleSaveTranscriptDraft(editorLines),
        onRunQa: () => handleRunTranscriptQa(editorLines),
        onAttest: handleAttestTranscript,
        onExtractFeatures: handleAnalyze,
        onGenerateReport: handleGenerateReport,
        onExport: handleExportCha,
        onSaveSpeakerMappingDraft: handleSaveSpeakerMappingDraft,
        onConfirmSpeakerMapping: handleConfirmSpeakerMapping,
      },
    };
  }

  return {
    view: "intake",
    backendUnavailable,
    viewProps: {
      model: {
          sessionContext,
          pipelineStatusValue,
          intakeStep,
          setIntakeStep,
          caseConsent,
          intakeError,
          setIntakeError,
          consentChecked,
          setConsentChecked,
          consentSigner,
          setConsentSigner,
          busy,
          handleGrantConsent,
          sessionDetails,
          setSessionDetails,
          sessionDetailsComplete,
          selectedSource,
          selectSource: handleSelectedSourceChange,
          state,
          setState,
          recordedAudio,
          setRecordedAudio,
          handleRecordingMetadata,
          handleRecordingReady,
          browserRecordingEnabled,
          audioCapabilities,
          audioFileUploadState,
          handleAudioFileSelected,
          handleAudioFileUpload,
          handleAudioJobRetry,
          resetAudioFileUpload,
          openAudioDraftTranscript,
          backendUnavailable,
          draftTranscript,
          setDraftTranscript,
          setSourceFilename,
          intakeWarnings,
          setIntakeWarnings,
          intakeValidationIssues,
          setIntakeValidationIssues,
          handleTranscriptSubmit,
          transcriptLines,
          transcriptSetup,
          setTranscriptSetup,
          sourceReadyForReview,
          canStartTranscriptReview,
          saveSessionIntakeDraft,
          handleAnalyze,
          handleGenerateReport,
          router,
      },
    },
  };

  async function handleSaveSpeakerMappingDraft(entries: SpeakerMappingEntry[]) {
    const current = workflowStateRef.current;
    if (!speakerMapping || !current.backendTranscriptId || !current.backendTranscriptVersion) {
      persist({
        ...current,
        statusMessage: "Speaker mapping could not be saved.",
        error: "Reload the transcript before editing speaker roles.",
      });
      return;
    }
    setBusy(true);
    persist({ ...current, statusMessage: "Saving speaker mapping draft...", error: undefined });
    try {
      const updated = await sessionWorkflowService.saveSpeakerMappingDraft(current.backendTranscriptId, {
        transcriptVersion: current.backendTranscriptVersion,
        mappingVersion: speakerMapping.mapping_version,
        entries,
      });
      setSpeakerMapping(updated);
      persist({
        ...workflowStateRef.current,
        statusMessage: "Speaker mapping draft saved. Confirm it before QA, attestation, export, or role-dependent features.",
        error: undefined,
      });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status >= 500) {
        setBackendUnavailable(true);
      }
      persist({
        ...workflowStateRef.current,
        statusMessage: "Speaker mapping save failed.",
        error: getSpeakerMappingFailureCopy(error),
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmSpeakerMapping() {
    const current = workflowStateRef.current;
    if (!speakerMapping || !current.backendTranscriptId || !current.backendTranscriptVersion || speakerMapping.mapping_version < 1) {
      persist({
        ...current,
        statusMessage: "Speaker mapping could not be confirmed.",
        error: "Save a complete speaker mapping draft before confirmation.",
      });
      return;
    }
    setBusy(true);
    persist({ ...current, statusMessage: "Confirming speaker mapping...", error: undefined });
    try {
      const confirmed = await sessionWorkflowService.confirmSpeakerMapping(current.backendTranscriptId, {
        transcriptVersion: current.backendTranscriptVersion,
        mappingVersion: speakerMapping.mapping_version,
      });
      const refreshed = await getBackendTranscript(current.backendTranscriptId);
      const refreshedLines = backendTranscriptLines(refreshed);
      const parsed = refreshed.raw_text ? prepareTranscriptIntake("cha-upload", refreshed.raw_text) : undefined;
      const remapped = sessionWorkflowReducer({
        ...workflowStateRef.current,
        backendTranscriptVersion: refreshed.version ?? current.backendTranscriptVersion,
        transcriptText: refreshed.raw_text ?? workflowStateRef.current.transcriptText,
        transcriptLines: refreshedLines,
        chatMetadata: parsed?.metadata ?? workflowStateRef.current.chatMetadata,
        chatWarnings: parsed?.warnings ?? workflowStateRef.current.chatWarnings,
        chatValidationIssues: parsed?.validationIssues ?? workflowStateRef.current.chatValidationIssues,
      }, { type: "transcript-edited", lines: refreshedLines });
      setSpeakerMapping(confirmed);
      setEditorLines(refreshedLines);
      setDraftTranscript(refreshed.raw_text ?? workflowStateRef.current.transcriptText);
      persist({
        ...remapped,
        transcriptSaveStatus: "saved",
        statusMessage: "Speaker mapping confirmed. Re-run transcript QA before attestation or export.",
        error: undefined,
      });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status >= 500) {
        setBackendUnavailable(true);
      }
      persist({
        ...workflowStateRef.current,
        statusMessage: "Speaker mapping confirmation failed.",
        error: getSpeakerMappingFailureCopy(error),
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveTranscriptDraft(lines: TranscriptLine[]) {
    if (activeTranscriptSaveRevisionRef.current !== null) return;
    setBusy(true);
    const transcriptText = buildBasicChatExport({
      lines,
      metadata: state.chatMetadata,
      includeMedia: state.mockAudioStored || Boolean(state.chatMetadata.media),
      fallbackMediaName: `${state.sessionId ?? "local-session"}_audio`,
      allowInvalid: true
    }).trimEnd();
    const edited = sessionWorkflowReducer(state, { type: "transcript-edited", lines });
    const next = persist(sessionWorkflowReducer(
      ensureWorkflowSession(edited, state.source ?? "paste-transcript"),
      { type: "transcript-save-started", transcriptText },
    ));
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: next.backendTranscriptSessionId ?? next.backendSessionId,
      transcriptId: next.backendTranscriptId,
      transcriptVersion: next.backendTranscriptVersion,
    };
    activeTranscriptSaveRevisionRef.current = requestIdentity.revision;
    setDraftTranscript(transcriptText);
    try {
      if (!next.backendTranscriptId) throw new Error("No persistent transcript exists.");
      const updated = await sessionWorkflowService.saveTranscript({
        sessionId: next.backendTranscriptSessionId ?? next.backendSessionId ?? "",
        transcriptId: next.backendTranscriptId,
        source: next.source === "cha-upload" ? "cha-upload" : "paste-transcript",
        originalText: transcriptText,
        normalizedText: transcriptText,
        sourceFilename: next.sourceFilename,
      });
      if (!canApplyTranscriptSaveSettlement(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      setBusy(false);
      const savedLines = backendTranscriptLines(updated);
      const updatedSpeakerMapping = await loadSpeakerMappingForTranscript(updated).catch(() => undefined);
      if (!canApplyTranscriptSaveSettlement(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      setEditorLines(savedLines.length ? savedLines : lines);
      setSpeakerMapping(updatedSpeakerMapping);
      persist(sessionWorkflowReducer(next, {
        type: "transcript-save-succeeded",
        lines: savedLines.length ? savedLines : lines,
        backendTranscriptVersion: updated.version,
      }));
    } catch {
      if (!canApplyTranscriptSaveSettlement(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist(sessionWorkflowReducer(next, { type: "transcript-save-failed", error: "Backend unavailable. Edits remain unsaved and can be retried." }));
    } finally {
      if (activeTranscriptSaveRevisionRef.current === requestIdentity.revision) {
        activeTranscriptSaveRevisionRef.current = null;
      }
      if (canApplyTranscriptSaveSettlement(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
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
        const backendQa = await sessionWorkflowService.runQa(targetTranscriptId);
        next = persist(sessionWorkflowReducer(next, {
          type: "qa-succeeded",
          status: (backendQa.status ?? backendQa.qa_status ?? next.qaStatus) as any,
          issues: backendQa.issues ?? next.qaIssues,
          summary: backendQa.summary ?? localQa.summary,
        }));
      } catch {
        setBackendUnavailable(true);
        persist(sessionWorkflowReducer(next, { type: "qa-failed", error: "Backend QA was unavailable. Retry when the backend is available." }));
      }
    } else {
      persist(sessionWorkflowReducer(next, { type: "qa-failed", error: "No persistent transcript ID is available." }));
    }
    setBusy(false);
  }

  async function handleAttestTranscript() {
    if (state.qaStatus === "not_run" || state.qaStatus === "fail" || !state.backendTranscriptId || state.transcriptSaveStatus !== "saved") return;
    setBusy(true);
    persist({ ...state, statusMessage: "Recording transcript attestation...", error: undefined });
    try {
      await sessionWorkflowService.attest(state.backendTranscriptId);
      persist(sessionWorkflowReducer(state, { type: "attestation-succeeded" }));
    } catch (error) {
      if (!(error instanceof ApiError) || error.status >= 500) {
        setBackendUnavailable(true);
      }
      persist(sessionWorkflowReducer(state, { type: "attestation-failed", error: getAttestationFailureCopy(error) }));
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
  return "audio";
}

function workflowSourceFromSelection(source: SessionIntakeSource): WorkflowSource {
  if (source === "audio") return "audio-upload";
  if (source === "cha") return "cha-upload";
  if (source === "paste") return "paste-transcript";
  return "recording";
}

function workflowSourceLabel(source?: WorkflowSource): string | undefined {
  if (source === "audio-upload") return "Verified synthetic audio upload";
  if (source === "cha-upload") return ".cha transcript";
  if (source === "paste-transcript") return "Pasted transcript";
  if (source === "recording") return "Browser recording";
  return undefined;
}

function hasCurrentTranscriptLineage(state: WorkflowState): boolean {
  return Boolean(
    state.backendTranscriptId
      || state.replacementTranscriptId
      || state.transcriptReady,
  );
}

function resetTranscriptForSourceReplacement(
  state: WorkflowState,
  source: WorkflowSource,
): WorkflowState {
  const replacementTranscriptId = state.backendTranscriptId ?? state.replacementTranscriptId;
  const replacementTranscriptVersion = state.backendTranscriptVersion ?? state.replacementTranscriptVersion;
  return {
    ...state,
    source,
    backendTranscriptId: undefined,
    backendTranscriptVersion: undefined,
    backendTranscriptSessionId: undefined,
    transcriptReplacementRequired: Boolean(replacementTranscriptId),
    replacementTranscriptId,
    replacementTranscriptVersion,
    backendReportId: undefined,
    backendReportVersion: undefined,
    featureSetId: undefined,
    featureTranscriptVersion: undefined,
    featureSchemaVersion: undefined,
    reportGeneratedFromVersions: undefined,
    transcriptionJobId: undefined,
    transcriptionJobStatus: undefined,
    transcriptionJobMessage: undefined,
    transcriptDraftLabel: undefined,
    sourceFilename: undefined,
    transcriptText: "",
    transcriptLines: [],
    chatMetadata: createIdentityScopedWorkflowState().chatMetadata,
    chatWarnings: [],
    chatValidationIssues: [],
    transcriptReady: false,
    transcriptAttested: false,
    transcriptCompleteness: 0,
    transcriptReviewStatus: "not_started",
    qaStatus: "not_run",
    qaSummary: undefined,
    qaIssues: [],
    transcriptSaveStatus: "idle",
    analysisStatus: "not_started",
    featuresExtracted: false,
    featurePercent: 0,
    featureSummary: [],
    featureSignals: [],
    mlReadiness: undefined,
    mlDecisionSupport: undefined,
    reviewNeededCount: 0,
    insights: [],
    reportId: undefined,
    reportStatus: "not_started",
    reportMarkdown: undefined,
    reportSaveStatus: "idle",
    shareStatus: "Not shared",
    finalizeStatus: undefined,
    statusMessage: "The prior transcript was detached because the source changed.",
    error: undefined,
  };
}

function transcriptRequiresSpeakerMapping(transcript: BackendTranscript): boolean {
  return transcript.source?.startsWith("asr_draft:") === true;
}

function markSpeakerMappingStale(mapping: SpeakerMappingResponse): SpeakerMappingResponse {
  if (mapping.status === "stale") return mapping;
  const staleIssue = {
    code: "SPEAKER_MAPPING_STALE",
    severity: "error",
    message: "Speaker mapping belongs to an older transcript version.",
    blocking: true,
  };
  return {
    ...mapping,
    status: "stale",
    issues: mapping.issues.some((issue) => issue.code === staleIssue.code)
      ? mapping.issues
      : [staleIssue, ...mapping.issues],
  };
}

function persistedAudioJobStatus(
  status: AudioProcessingJob["status"],
): WorkflowState["transcriptionJobStatus"] {
  if (status === "failed" || status === "cancelled") return "failed";
  if (status === "processing" || status === "transcription_completed" || status === "needs_review") {
    return "processing";
  }
  return "queued";
}

function transcriptAsrLineageMatches(
  provenance: {
    job_id?: string;
    source_audio_file_id?: string;
    source_asset_version?: number;
    source_checksum_sha256?: string;
    normalized_asset_version?: number;
    normalized_checksum_sha256?: string;
    provider_id?: string;
  } | undefined,
  jobId: string,
  lineage: AudioLineage,
): boolean {
  return provenance?.job_id === jobId
    && provenance.source_audio_file_id === lineage.audioFileId
    && provenance.source_asset_version === lineage.sourceAssetVersion
    && provenance.source_checksum_sha256 === lineage.sourceChecksumSha256
    && provenance.normalized_asset_version === lineage.normalizedAssetVersion
    && provenance.normalized_checksum_sha256 === lineage.normalizedChecksumSha256
    && provenance.provider_id === lineage.providerId;
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function formatLimitBytes(bytes: number): string {
  const megabytes = bytes / (1024 * 1024);
  return `${Number.isInteger(megabytes) ? megabytes : megabytes.toFixed(1)} MB`;
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

function normalizeBackendQaStatus(status?: string): WorkflowState["qaStatus"] {
  const normalized = status?.toLowerCase();
  if (normalized === "pass") return "pass";
  if (normalized === "warning") return "warning";
  if (normalized === "fail") return "fail";
  return "not_run";
}

function workflowSessionHref(view: "intake" | "transcript" | "findings" | "report", state: WorkflowState, reportId?: string) {
  return resolveSessionHref(view, state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId, {
    caseId: state.caseId,
    transcriptId: state.backendTranscriptId,
    reportId: reportId ?? state.backendReportId ?? state.reportId,
  });
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

function normalizeHydratedReportStatus(status?: string): WorkflowState["reportStatus"] {
  const normalized = status?.trim().toLowerCase().replaceAll(" ", "_");
  if (normalized === "signed_off" || normalized === "finalized") return "finalized";
  if (normalized === "stale") return "stale";
  if (normalized === "reviewed" || normalized === "attested") return "reviewed";
  if (normalized === "draft" || normalized === "needs_review") return "draft";
  return "not_started";
}

function getAttestationFailureCopy(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your sign-in session expired before attestation was recorded. Log out, sign in again, then retry Attest transcript.";
    }
    if (error.status === 403) {
      return "This account is not allowed to attest this transcript for the active organization. Switch to the assigned therapist account or choose the correct organization, then retry.";
    }
    if (error.status === 404) {
      return "The saved transcript could not be found. Return to the session, save the transcript again, then retry attestation.";
    }
    if (error.status >= 500) {
      return "The backend could not record attestation right now. Your transcript is still saved; retry Attest transcript in a moment.";
    }
  }
  return "Attestation did not finish. Your transcript is still saved; retry Attest transcript before generating a report.";
}

function getSpeakerMappingFailureCopy(error: unknown) {
  if (error instanceof AudioWorkflowContractError) {
    return "The backend returned an invalid speaker-mapping contract. Reload the transcript before editing speaker roles.";
  }
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your sign-in session expired before speaker mapping was saved. Log out, sign in again, then retry.";
    }
    if (error.status === 403) {
      return "This account is not allowed to confirm speaker roles for the active organization.";
    }
    if (error.status === 404) {
      return "The saved transcript could not be found. Return to the session and reload the transcript.";
    }
    if (error.status >= 400 && error.status < 500) {
      return "The speaker mapping version is stale or incomplete. Reload the transcript and review the current mapping.";
    }
  }
  return "Speaker mapping did not finish. Reload the transcript and retry before QA, attestation, export, or feature extraction.";
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
