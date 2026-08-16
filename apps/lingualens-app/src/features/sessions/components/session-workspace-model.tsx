"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiBlob, apiRequest, apiGet } from "@/lib/api";

import type { RecordingMetadata } from "@/components/browser-audio-recorder";
import { useBackendAvailability } from "@/components/backend-availability-banner";
import {
  createExperimentalTranscriptionJob,
  getExperimentalTranscriptionJob,
  releaseExperimentalAudioUpload,
  uploadRecordedAudio
} from "@/lib/experimental-transcription-service";
import {
  backendTranscriptLines,
  buildBasicChatExport,
  buildFeatureSignals,
  createBackendSession,
  ensureWorkflowSession,
  classifyWorkflowLoadFailure,
  createIdentityScopedWorkflowState,
  createInitialWorkflowState,
  defaultTranscript,
  acknowledgeSessionCues,
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
  uploadAudioFileBytes,
  getSessionAudioFiles,
  uploadAudioBlobToBackend,
  startBackendTranscriptionJob,
  pollTranscriptionJob
} from "@/lib/workflow";
import { canApplyMlDecisionSupportSettlement, canApplyTranscriptSaveSettlement, canSettleWorkflowRequest, derivePipelineStatus, sessionWorkflowReducer } from "@/features/sessions/state/session-workflow-reducer";
import { sessionWorkflowService } from "@/features/sessions/services/session-workflow-service";
import { resolveSessionHref, resolveWorkspaceFeature, type SessionView } from "@/features/sessions/state/session-view";
import type { SessionIntakeSource, SessionIntakeStepId } from "@/features/sessions/intake/session-intake-view";
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

export function SessionWorkflowWorkspace(props: SessionWorkspaceProps) {
  const identityKey = JSON.stringify([
    props.sessionId ?? "",
    props.caseId ?? "",
    props.transcriptId ?? "",
    props.reportId ?? "",
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

  useEffect(() => () => {
    workflowRevisionRef.current += 1;
    activeTranscriptSaveRevisionRef.current = null;
  }, []);

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
  const [sessionDetails, setSessionDetails] = useState(() => createSessionDetailsDraft(
    hasLocator ? createIdentityScopedWorkflowState() : createInitialWorkflowState(),
  ));
  const [transcriptSetup, setTranscriptSetup] = useState(createTranscriptSetupDraft());
  const [caseConsent, setCaseConsent] = useState<string>("granted");
  const [consentSigner, setConsentSigner] = useState("Parent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentDate, setConsentDate] = useState(() => new Date().toISOString().slice(0, 10));
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
    return derivePipelineStatus(state, caseConsent, uploadStep);
  }, [caseConsent, state, uploadStep]);

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

  async function handleGrantConsent() {
    if (!consentChecked || !caseId) return;
    setBusy(true);
    setIntakeError("");
    try {
      const caseRecord = await getBackendCase(caseId).catch(() => undefined);
      await sessionWorkflowService.grantCaseConsent(caseId, {
        signer: consentSigner,
        date: consentDate,
        notes: consentNotes,
        existingNotes: caseRecord?.notes,
      });
      setCaseConsent("granted");
    } catch {
      setIntakeError("Could not update case consent on the backend.");
    } finally {
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
          reportStatus: "not_started",
          reportMarkdown: undefined,
          statusMessage: job.message,
          error: undefined
        }));
        setBusy(false);
        router.push(workflowSessionHref("transcript", {
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
      reportStatus: "not_started",
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
        transcriptId: localSession.backendTranscriptId,
        source,
        originalText: draftTranscript,
        normalizedText: intake.transcriptText,
        sourceFilename,
      });
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
        statusMessage: "Evidence review requires extracted features from a reviewed transcript.",
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

  async function handleApproveReviewedCues() {
    const resolvedSessionId = state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId;
    if (!resolvedSessionId || busy) return;
    setBusy(true);
    try {
      const acknowledgement = await acknowledgeSessionCues(resolvedSessionId);
      persist({
        ...state,
        cuesAcknowledgedAt: acknowledgement.acknowledgedAt,
        cuesAcknowledgedBy: acknowledgement.acknowledgedBy,
        statusMessage: "Reviewed cues acknowledged and recorded server-side.",
        error: undefined,
      });
    } catch {
      persist({
        ...state,
        statusMessage: "Reviewed cues acknowledgement was not recorded.",
        error: undefined,
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

  const sessionContext: SessionContext = {
    sessionId: state.backendSessionId ?? state.sessionId ?? sessionId,
    caseId: state.caseId || caseId,
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
        onApproveReviewedCues: handleApproveReviewedCues,
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
        onLinesChange: (lines) => {
          workflowRevisionRef.current += 1;
          activeTranscriptSaveRevisionRef.current = null;
          setBusy(false);
          setEditorLines(lines);
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
          consentDate,
          setConsentDate,
          consentNotes,
          setConsentNotes,
          busy,
          handleGrantConsent,
          sessionDetails,
          setSessionDetails,
          sessionDetailsComplete,
          transcriptSetupComplete,
          selectedSource,
          setSelectedSource,
          state,
          setState,
          recordedAudio,
          setRecordedAudio,
          uploadStep,
          setUploadStep,
          handleRecordingMetadata,
          handleRecordingReady,
          handleUploadForTranscription,
          transJobStatus,
          transJobMessage,
          transJobRequestedProvider,
          transJobActualProvider,
          backendUnavailable,
          draftTranscript,
          setDraftTranscript,
          setSourceFilename,
          intakeWarnings,
          setIntakeWarnings,
          intakeValidationIssues,
          setIntakeValidationIssues,
          handleAudioUpload,
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
      setEditorLines(savedLines.length ? savedLines : lines);
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
  return "recording";
}

function workflowSourceFromSelection(source: SessionIntakeSource): WorkflowSource {
  if (source === "audio") return "audio-upload";
  if (source === "cha") return "cha-upload";
  if (source === "paste") return "paste-transcript";
  return "recording";
}

function workflowSourceLabel(source?: WorkflowSource): string | undefined {
  if (source === "audio-upload") return "Uploaded audio (experimental)";
  if (source === "cha-upload") return ".cha transcript";
  if (source === "paste-transcript") return "Pasted transcript";
  if (source === "recording") return "Browser recording";
  return undefined;
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
