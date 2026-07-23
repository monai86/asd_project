"use client";

import type { Dispatch, SetStateAction } from "react";
import { CheckCircle2, FileText, Sparkles, Wand2 } from "lucide-react";

import type { RecordingMetadata } from "@/components/browser-audio-recorder";
import { PrimaryActionButton, SafetyNote, WorkflowStep, WorkspacePanel } from "@/components/workbench-ui";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
import { WorkflowStepper } from "@/components/workflow-stepper";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import {
  isTranscriptUnlocked,
  ReviewSummaryCard,
  SessionResultsPreview,
  sourceSummaryLabel,
  WorkflowStatus,
} from "@/features/sessions/intake/session-intake-components";
import { SessionIntakeSteps } from "@/features/sessions/intake/session-intake-steps";
import type { WorkflowSource, WorkflowState } from "@/lib/workflow";

export type SessionIntakeStepId = "details" | "source" | "setup" | "review";
export type SessionIntakeSource = "recording" | "audio" | "cha" | "paste";

type SessionDetailsDraft = {
  childClient: string;
  sessionDate: string;
  sessionTime: string;
  setting: string;
  durationMinutes: string;
  clinician: string;
  sessionGoals: string;
};

type TranscriptSetupDraft = {
  speakerLabels: string;
  sessionMetadata: string;
  language: string;
  sampleType: string;
  reviewSpeakerLabels: boolean;
  reviewFeatureLock: boolean;
};

type RecordedAudio = { blob: Blob; metadata: RecordingMetadata } | null;
type UploadStep = "idle" | "confirm" | "uploading" | "polling" | "done" | "error";

export type SessionIntakeViewModel = {
  sessionContext: SessionContext;
  pipelineStatusValue: string;
  intakeStep: SessionIntakeStepId;
  setIntakeStep: Dispatch<SetStateAction<SessionIntakeStepId>>;
  caseConsent: string;
  intakeError: string;
  setIntakeError: Dispatch<SetStateAction<string>>;
  consentChecked: boolean;
  setConsentChecked: Dispatch<SetStateAction<boolean>>;
  consentSigner: string;
  setConsentSigner: Dispatch<SetStateAction<string>>;
  busy: boolean;
  handleGrantConsent: () => void | Promise<void>;
  sessionDetails: SessionDetailsDraft;
  setSessionDetails: Dispatch<SetStateAction<SessionDetailsDraft>>;
  sessionDetailsComplete: boolean;
  selectedSource: SessionIntakeSource;
  setSelectedSource: Dispatch<SetStateAction<SessionIntakeSource>>;
  state: WorkflowState;
  setState: Dispatch<SetStateAction<WorkflowState>>;
  recordedAudio: RecordedAudio;
  setRecordedAudio: Dispatch<SetStateAction<RecordedAudio>>;
  uploadStep: UploadStep;
  setUploadStep: Dispatch<SetStateAction<UploadStep>>;
  handleRecordingMetadata: (metadata: RecordingMetadata) => void;
  handleRecordingReady: (blob: Blob, metadata: RecordingMetadata) => void;
  handleUploadForTranscription: () => void | Promise<void>;
  transJobStatus: string;
  transJobMessage: string;
  transJobRequestedProvider?: string;
  transJobActualProvider?: string;
  backendUnavailable: boolean;
  draftTranscript: string;
  setDraftTranscript: Dispatch<SetStateAction<string>>;
  setSourceFilename: Dispatch<SetStateAction<string | undefined>>;
  intakeWarnings: string[];
  setIntakeWarnings: Dispatch<SetStateAction<string[]>>;
  intakeValidationIssues: string[];
  setIntakeValidationIssues: Dispatch<SetStateAction<string[]>>;
  handleAudioUpload: () => void | Promise<void>;
  handleTranscriptSubmit: (source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">) => void | Promise<void>;
  transcriptLines: string[];
  transcriptSetup: TranscriptSetupDraft;
  setTranscriptSetup: Dispatch<SetStateAction<TranscriptSetupDraft>>;
  sourceReadyForReview: boolean;
  canStartTranscriptReview: boolean;
  saveSessionIntakeDraft: () => WorkflowState;
  handleAnalyze: () => void | Promise<void>;
  handleGenerateReport: () => void | Promise<void>;
  router: { push: (href: string) => void };
};

const sessionIntakeStepLabels: Array<{ id: SessionIntakeStepId; title: string; helper: string }> = [
  { id: "details", title: "Session Details", helper: "Set the session context before adding source material." },
  { id: "source", title: "Source Material", helper: "Record, upload, or paste the material for therapist review." },
  { id: "setup", title: "Transcript Setup", helper: "Define labels, metadata, and review requirements." },
  { id: "review", title: "Review & Start", helper: "Confirm safety notices before opening transcript review." },
];

export function SessionIntakeView({ model }: { model: SessionIntakeViewModel }) {
  const {
    sessionContext,
    pipelineStatusValue,
    intakeStep,
    selectedSource,
    state,
    busy,
    backendUnavailable,
    handleAnalyze,
    handleGenerateReport,
  } = model;
  const steps = sessionIntakeStepLabels.map((step) => ({
    id: step.id,
    title: step.title,
    helper: step.helper,
    status: step.id === intakeStep
      ? "current" as const
      : sessionIntakeStepLabels.findIndex((item) => item.id === step.id) < sessionIntakeStepLabels.findIndex((item) => item.id === intakeStep)
        ? "complete" as const
        : "pending" as const,
  }));

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-6">
        <SessionContextHeader
          title="Session Intake"
          description="Capture session context, prepare source material, and route the workflow into therapist transcript review without weakening the existing review and attestation gates."
          meta={["Audio upload requires explicit confirmation", "ASR remains experimental"]}
          context={sessionContext}
        />
        <PipelineProgressBar currentStatus={pipelineStatusValue} />
        <WorkflowStepper steps={steps} />
          <SessionIntakeSteps model={model} />

          {state.transcriptReady && !isTranscriptUnlocked(state) ? (
            <div className="rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900" role="alert">
              Feature extraction requires a saved, reviewed, and attested transcript.
            </div>
          ) : null}

          <PrimaryActionButton
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
          </PrimaryActionButton>

          <WorkspacePanel className="p-5">
            <h2 className="mb-4 font-bold text-ink">What happens next</h2>
            <div className="flex gap-2">
              <WorkflowStep icon={FileText} title="Transcript ready" helper={state.transcriptReady ? "Available" : "After source material is prepared"} tone="purple" />
              <WorkflowStep icon={CheckCircle2} title="Features extracted" helper={state.featuresExtracted ? "Complete" : "After review gate"} tone="green" />
              <WorkflowStep icon={Wand2} title="Suggested next step" helper="Therapist transcript review" tone="orange" />
            </div>
          </WorkspacePanel>
          <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
          <SafetyNote>Decision-support only. Not diagnostic. Transcript must be reviewed before report use.</SafetyNote>
      </div>
      <div className="space-y-6">
        <ReviewSummaryCard title="Current intake" rows={[
          { label: "Step", value: sessionIntakeStepLabels.find((item) => item.id === intakeStep)?.title ?? "Session Details" },
          { label: "Source", value: sourceSummaryLabel(selectedSource) },
          { label: "Transcript status", value: state.transcriptReady ? "Ready for review" : "Pending" },
        ]} />
        <SessionResultsPreview state={state} onGenerateReport={handleGenerateReport} busy={busy} />
      </div>
    </div>
  );
}
