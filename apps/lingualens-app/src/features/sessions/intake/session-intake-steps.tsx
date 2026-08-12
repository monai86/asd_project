import { ClipboardPaste, FileText, Mic, UploadCloud } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { BrowserAudioRecorder } from "@/components/browser-audio-recorder";
import { WorkspacePanel } from "@/components/workbench-ui";
import { SafetyNotice } from "@/components/safety-notice";
import { AudioFileUploadPanel } from "@/features/sessions/intake/audio-file-upload-panel";
import {
  capitalizeWord,
  Field,
  ReviewSummaryCard,
  sourceSummaryLabel,
  SourceChoiceButton,
  SourceInputPanel,
  workflowSessionHref,
} from "@/features/sessions/intake/session-intake-components";
import type { SessionIntakeViewModel } from "@/features/sessions/intake/session-intake-view";
import { prepareTranscriptIntake } from "@/lib/workflow";

export function SessionIntakeSteps({ model }: { model: SessionIntakeViewModel }) {
  const {
    intakeStep, setIntakeStep, caseConsent, intakeError, setIntakeError,
    consentChecked, setConsentChecked, consentSigner, setConsentSigner, busy,
    handleGrantConsent, sessionDetails, setSessionDetails, sessionDetailsComplete,
    selectedSource, selectSource, state, recordedAudio, setRecordedAudio,
    handleRecordingMetadata, handleRecordingReady, browserRecordingEnabled,
    audioCapabilities, audioFileUploadState, handleAudioFileSelected,
    handleAudioFileUpload, handleAudioJobRetry, resetAudioFileUpload,
    openAudioDraftTranscript, draftTranscript, setDraftTranscript,
    setSourceFilename, intakeWarnings, setIntakeWarnings, intakeValidationIssues,
    setIntakeValidationIssues, handleTranscriptSubmit, transcriptLines,
    transcriptSetup, setTranscriptSetup, sourceReadyForReview, canStartTranscriptReview,
    saveSessionIntakeDraft, router,
  } = model;

  return (
    <>
          {intakeStep === "details" && caseConsent !== "granted" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6" role="region" aria-label="Consent Intake Gate">
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
                await handleGrantConsent();
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
            </WorkspacePanel>
          ) : intakeStep === "details" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
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
            </WorkspacePanel>
          ) : null}

          {intakeStep === "source" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">Source Material</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Upload synthetic audio through the verified backend lifecycle. Browser recording remains a separate follow-up capability.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <SourceChoiceButton label="Record in browser" active={selectedSource === "recording"} icon={Mic} onClick={() => selectSource("recording")} />
                <SourceChoiceButton label="Upload audio" active={selectedSource === "audio"} icon={UploadCloud} onClick={() => selectSource("audio")} />
                <SourceChoiceButton label="Upload .cha" active={selectedSource === "cha"} icon={FileText} onClick={() => selectSource("cha")} />
                <SourceChoiceButton label="Paste transcript" active={selectedSource === "paste"} icon={ClipboardPaste} onClick={() => selectSource("paste")} />
              </div>

              {selectedSource === "recording" ? (
                browserRecordingEnabled ? (
                  <WorkspacePanel className="p-5 text-center">
                    <BrowserAudioRecorder
                      initialDurationSeconds={state.recordingSeconds}
                      hadUnsavedRecording={state.recordingClearedForPrivacy}
                      onMetadataChange={handleRecordingMetadata}
                      onRecordingReady={handleRecordingReady}
                      onRecordingCleared={() => setRecordedAudio(null)}
                    />
                    {recordedAudio ? (
                      <div className="mt-4 flex flex-col items-center gap-3">
                        <ActionButton
                          type="button"
                          onClick={() => {
                            let ext = "wav";
                            const mime = recordedAudio.metadata.mimeType || recordedAudio.blob.type || "";
                            if (mime.includes("webm")) ext = "webm";
                            else if (mime.includes("mp3") || mime.includes("mpeg")) ext = "mp3";
                            else if (mime.includes("wav")) ext = "wav";

                            if (!audioCapabilities.supported_formats.includes(ext) && audioCapabilities.supported_formats.length > 0) {
                              ext = audioCapabilities.supported_formats.includes("wav")
                                ? "wav"
                                : audioCapabilities.supported_formats[0];
                            }

                            const file = new File(
                              [recordedAudio.blob],
                              `recording.${ext}`,
                              { type: recordedAudio.blob.type || recordedAudio.metadata.mimeType || "audio/wav" }
                            );

                            const selected = handleAudioFileSelected(file);
                            if (selected !== false) {
                              void handleAudioFileUpload(file);
                            }
                          }}
                          disabled={
                            busy ||
                            audioFileUploadState.state === "uploading" ||
                            audioFileUploadState.state === "verifying" ||
                            audioFileUploadState.state === "normalizing" ||
                            audioFileUploadState.state === "transcribing"
                          }
                        >
                          {audioFileUploadState.state === "uploading" ||
                          audioFileUploadState.state === "verifying" ||
                          audioFileUploadState.state === "normalizing" ||
                          audioFileUploadState.state === "transcribing"
                            ? "กำลังส่งวิเคราะห์..."
                            : "ส่งวิเคราะห์ด้วย ASR Pipeline"}
                        </ActionButton>
                        {audioFileUploadState.state === "failed" ? (
                          <p className="text-sm font-medium text-rose-600">{audioFileUploadState.message}</p>
                        ) : null}
                      </div>
                    ) : (
                      <p className="mt-4 text-sm text-amber-800">
                        Local development capture only. Browser recordings cannot enter the v1.7.0 transcription milestone.
                      </p>
                    )}
                  </WorkspacePanel>
                ) : (
                  <WorkspacePanel className="border-amber-200 bg-amber-50 p-5" role="status">
                    <h2 className="font-bold text-amber-950">Browser recording — Experimental</h2>
                    <p className="mt-2 text-sm leading-6 text-amber-900">
                      Experimental — unavailable in v1.7.0 testbed. Upload a versioned synthetic audio file to complete the milestone workflow.
                    </p>
                  </WorkspacePanel>
                )
              ) : selectedSource === "audio" ? (
                <AudioFileUploadPanel
                  capabilities={audioCapabilities}
                  state={audioFileUploadState}
                  onSelectFile={handleAudioFileSelected}
                  onConfirmUpload={handleAudioFileUpload}
                  onRetry={handleAudioJobRetry}
                  onReset={resetAudioFileUpload}
                  onOpenTranscript={openAudioDraftTranscript}
                />
              ) : (
                <SourceInputPanel
                  mode={selectedSource === "cha" ? "cha" : "paste"}
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
                  onTranscriptSubmit={handleTranscriptSubmit}
                />
              )}

              <WorkspacePanel className="p-5">
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
              </WorkspacePanel>

              <div className="flex flex-wrap justify-between gap-3">
                <ActionButton type="button" tone="ghost" onClick={() => setIntakeStep("details")}>
                  Back to Session Details
                </ActionButton>
                <ActionButton type="button" onClick={() => setIntakeStep("setup")}>
                  Continue to Transcript Setup
                </ActionButton>
              </div>
            </WorkspacePanel>
          ) : null}

          {intakeStep === "setup" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
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
            </WorkspacePanel>
          ) : null}

          {intakeStep === "review" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
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
            </WorkspacePanel>
          ) : null}
    </>
  );
}
