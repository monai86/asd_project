"use client";

import type { Dispatch, SetStateAction } from "react";
import type { LucideIcon } from "lucide-react";
import { CheckCircle2, ClipboardPaste, FileText, Mic, ShieldCheck, Sparkles, UploadCloud, Wand2 } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { AudioUploadConfirmPanel } from "@/components/audio-upload-confirm-panel";
import { BrowserAudioRecorder, type RecordingMetadata } from "@/components/browser-audio-recorder";
import { GlassCard, GradientButton, SafetyNote, WorkflowStep } from "@/components/liquid-ui";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
import { SafetyNotice } from "@/components/safety-notice";
import { TranscriptionJobStatusPanel, type TranscriptionJobDisplayStatus } from "@/components/transcription-job-status-panel";
import { WorkflowStepper } from "@/components/workflow-stepper";
import { SessionContextHeader } from "@/features/sessions/components/session-context-header";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import {
  prepareTranscriptIntake,
  updateBackendCase,
  type WorkflowSource,
  type WorkflowState,
} from "@/lib/workflow";

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
  pipelineStatusValue: string;
  intakeStep: SessionIntakeStepId;
  setIntakeStep: Dispatch<SetStateAction<SessionIntakeStepId>>;
  caseConsent: string;
  setCaseConsent: Dispatch<SetStateAction<string>>;
  intakeError: string;
  setIntakeError: Dispatch<SetStateAction<string>>;
  consentChecked: boolean;
  setConsentChecked: Dispatch<SetStateAction<boolean>>;
  consentSigner: string;
  setConsentSigner: Dispatch<SetStateAction<string>>;
  caseId?: string;
  busy: boolean;
  setBusy: Dispatch<SetStateAction<boolean>>;
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
    pipelineStatusValue, intakeStep, setIntakeStep, caseConsent, setCaseConsent,
    intakeError, setIntakeError, consentChecked, setConsentChecked, consentSigner,
    setConsentSigner, caseId, busy, setBusy, sessionDetails, setSessionDetails,
    sessionDetailsComplete, selectedSource, setSelectedSource, state, setState,
    recordedAudio, setRecordedAudio, uploadStep, setUploadStep, handleRecordingMetadata,
    handleRecordingReady, handleUploadForTranscription, transJobStatus, transJobMessage,
    transJobRequestedProvider, transJobActualProvider, backendUnavailable, draftTranscript,
    setDraftTranscript, setSourceFilename, intakeWarnings, setIntakeWarnings,
    intakeValidationIssues, setIntakeValidationIssues, handleAudioUpload,
    handleTranscriptSubmit, transcriptLines, transcriptSetup, setTranscriptSetup,
    sourceReadyForReview, canStartTranscriptReview, saveSessionIntakeDraft,
    handleAnalyze, handleGenerateReport, router,
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
      <div className="space-y-6">
        <SessionContextHeader
          title="Session Intake"
          description="Capture session context, prepare source material, and route the workflow into therapist transcript review without weakening the existing review and attestation gates."
          meta={["Decision-support only", "Audio upload requires explicit confirmation", "ASR remains experimental"]}
        />
        <PipelineProgressBar currentStatus={pipelineStatusValue} />
        <WorkflowStepper steps={steps} />
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
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none"
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
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-clinician" className="text-sm font-semibold text-ink">Clinician</label>
                  <input
                    id="session-clinician"
                    type="text"
                    value={sessionDetails.clinician}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, clinician: event.target.value }))}
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-date" className="text-sm font-semibold text-ink">Session date</label>
                  <input
                    id="session-date"
                    type="date"
                    value={sessionDetails.sessionDate}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, sessionDate: event.target.value }))}
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-time" className="text-sm font-semibold text-ink">Session time</label>
                  <input
                    id="session-time"
                    type="time"
                    value={sessionDetails.sessionTime}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, sessionTime: event.target.value }))}
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="session-setting" className="text-sm font-semibold text-ink">Setting</label>
                  <select
                    id="session-setting"
                    value={sessionDetails.setting}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, setting: event.target.value }))}
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
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
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
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
                  className="min-h-32 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
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

                  {uploadStep === "confirm" && recordedAudio ? (
                    <AudioUploadConfirmPanel
                      blob={recordedAudio.blob}
                      durationSeconds={recordedAudio.metadata.durationSeconds}
                      onUpload={handleUploadForTranscription}
                      onCancel={() => setUploadStep("idle")}
                      backendAvailable={!backendUnavailable}
                      uploading={busy}
                    />
                  ) : null}

                  {["polling", "done", "error"].includes(uploadStep) ? (
                    <TranscriptionJobStatusPanel
                      status={transJobStatus as TranscriptionJobDisplayStatus}
                      message={transJobMessage}
                      requestedProvider={transJobRequestedProvider}
                      actualProvider={transJobActualProvider}
                      onOpenTranscript={
                        uploadStep === "done" && state.backendTranscriptId && state.sessionId
                          ? () => {
                              router.push(workflowSessionHref("transcript", state));
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

                  {uploadStep === "idle" && recordedAudio ? (
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
                        <div className="rounded-[var(--radius-card)] border border-dashed border-line bg-[color:var(--color-surface-muted)] p-4 text-center">
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
                    className="min-h-28 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field className="md:col-span-2">
                  <label htmlFor="session-metadata" className="text-sm font-semibold text-ink">Session metadata</label>
                  <textarea
                    id="session-metadata"
                    value={transcriptSetup.sessionMetadata}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, sessionMetadata: event.target.value }))}
                    className="min-h-28 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </Field>
                <Field>
                  <label htmlFor="transcript-language" className="text-sm font-semibold text-ink">Language</label>
                  <select
                    id="transcript-language"
                    value={transcriptSetup.language}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, language: event.target.value }))}
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
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
                    className="min-h-11 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
                  >
                    <option value="conversation">Conversation</option>
                    <option value="play">Play-based interaction</option>
                    <option value="narrative">Narrative sample</option>
                  </select>
                </Field>
              </div>
              <div className="space-y-3 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4">
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
                <div className="rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
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
                        router.push(workflowSessionHref("transcript", savedState));
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
            <div className="rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900" role="alert">
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
          { label: "Transcript status", value: state.transcriptReady ? "Ready for review" : "Pending" },
        ]} />
        <SessionResultsPreview state={state} onGenerateReport={handleGenerateReport} busy={busy} />
      </div>
    </div>
  );
}

function sourceSummaryLabel(source: SessionIntakeSource): string {
  if (source === "recording") return "Browser recording";
  if (source === "audio") return "Audio upload";
  if (source === "cha") return "CHAT file upload";
  return "Pasted transcript";
}

function capitalizeWord(value: string) {
  return value ? value[0].toUpperCase() + value.slice(1) : value;
}

function workflowSessionHref(view: "intake" | "transcript" | "findings" | "report", state: WorkflowState, reportId?: string) {
  return resolveSessionHref(view, state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId, {
    caseId: state.caseId,
    transcriptId: state.backendTranscriptId,
    reportId: reportId ?? state.backendReportId ?? state.reportId,
  });
}

function isTranscriptUnlocked(state: WorkflowState) {
  return state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
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
          ? "border-[color:var(--color-accent-subtle)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
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
              className="mb-3 block w-full rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-3 py-3 text-sm"
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                if (file) void onChaFile(file);
              }}
            />
          </>
        ) : null}
        <textarea
          className="min-h-44 w-full rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
          value={draftTranscript}
          onChange={(event) => onDraftChange(event.target.value)}
          aria-label={mode === "cha" ? "CHA transcript text" : "Pasted transcript text"}
          data-testid="transcript-input"
        />
        {error ? (
          <p className="mt-3 rounded-[var(--radius-card)] border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-900 animate-fade-in" role="alert">
            {error}
          </p>
        ) : null}
        {warnings.length > 0 ? (
          <div className="mt-3 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
            <p className="font-semibold">Import warnings</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
          </div>
        ) : null}
        {validationIssues.length > 0 ? (
          <div className="mt-3 rounded-[var(--radius-card)] border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900" role="alert">
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
      <div className="mt-6 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4">
        <h3 className="font-bold text-ink">Key insights</h3>
        <ul className="mt-3 space-y-3 text-sm text-slate-700">
          {state.insights.map((insight) => <li key={insight.title}>{insight.title}: {insight.text}</li>)}
        </ul>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <GradientButton href={workflowSessionHref("transcript", state)} icon={FileText}>Review Transcript</GradientButton>
        <GradientButton icon={ShieldCheck} onClick={onGenerateReport} disabled={busy || !isResultsReportReady(state)}>Generate Report</GradientButton>
      </div>
    </GlassCard>
  );
}

function isResultsReportReady(state: WorkflowState) {
  if (state.analysisStatus === "stale") return false;
  return isTranscriptUnlocked(state) && state.featuresExtracted;
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
    ? "rounded-[var(--radius-panel)] border border-red-200 bg-red-50 p-4 text-sm text-red-950 animate-fade-in"
    : isSuccess
      ? "rounded-[var(--radius-panel)] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 animate-fade-in"
      : "demo-note rounded-[var(--radius-panel)] p-4 text-sm";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}

function MiniResult({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[1.25rem] border border-line bg-[color:var(--color-surface-reading)] p-4 text-center">
      <p className="text-3xl font-bold text-ink">{value}</p>
      <p className="mt-2 text-sm font-semibold text-slate-700">{label}</p>
    </div>
  );
}
