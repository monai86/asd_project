import type { MlReadiness, TranscriptQaStatus, WorkflowState } from "@/lib/workflow";

/**
 * Shared, pure helpers that explain why a workflow action is currently
 * disabled. Each returns undefined when the action is not blocked, and a
 * human-readable reason otherwise. Views render the reason inline next to the
 * disabled button and link it through aria-describedby so assistive tech can
 * announce why the action is unavailable.
 */

export type IntakeSourceChoice = "recording" | "audio" | "cha" | "paste";

/**
 * Why "Start Transcript Review" is blocked on the Review & Start intake step.
 */
export function startTranscriptReviewBlockedReason({
  sessionDetailsComplete,
  transcriptSetupComplete,
  sourceReadyForReview,
  selectedSource,
}: {
  sessionDetailsComplete: boolean;
  transcriptSetupComplete: boolean;
  sourceReadyForReview: boolean;
  selectedSource: IntakeSourceChoice;
}): string | undefined {
  if (!sessionDetailsComplete) {
    return "Complete the session details (child/client, date, time, and clinician) before starting transcript review.";
  }
  if (!transcriptSetupComplete) {
    return "Complete the transcript setup fields and confirm both review requirements before starting transcript review.";
  }
  if (!sourceReadyForReview) {
    if (selectedSource === "paste" || selectedSource === "cha") {
      return "Add transcript text in Source Material before starting transcript review.";
    }
    return "Wait until a draft transcript is available before starting transcript review.";
  }
  return undefined;
}

/**
 * Why "Continue to Source Material" is blocked on the Session Details intake step.
 */
export function continueToSourceMaterialBlockedReason({
  sessionDetailsComplete,
}: {
  sessionDetailsComplete: boolean;
}): string | undefined {
  if (!sessionDetailsComplete) {
    return "Complete the session details (child/client, date, time, and clinician) before continuing to source material.";
  }
  return undefined;
}

/**
 * Why "Verify and Grant Consent" is blocked on the consent gate. The busy state
 * is transient and the button label ("Verifying...") already communicates it.
 */
export function grantConsentBlockedReason({
  checked,
  busy,
}: {
  checked: boolean;
  busy: boolean;
}): string | undefined {
  if (busy) return undefined;
  if (!checked) {
    return "Check the confirmation box to verify caregiver consent was obtained.";
  }
  return undefined;
}

/**
 * Why "Extract language-sample features" is blocked on the intake page.
 * Transient states (loading / in-flight extraction) are not blockers, so they
 * return undefined and the button label already communicates them.
 */
export function extractFeaturesBlockedReason(state: WorkflowState): string | undefined {
  if (state.workflowLoading) return undefined;
  if (!state.backendTranscriptId && !state.transcriptReady) {
    return "Save a transcript and review it before extracting features.";
  }
  if (!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed") {
    return "Feature extraction requires a saved, reviewed, and attested transcript.";
  }
  if (!state.backendTranscriptId) {
    return "Save the transcript to the session before extracting features.";
  }
  if (!(state.backendTranscriptSessionId ?? state.backendSessionId)) {
    return "A persisted session is required before extracting features.";
  }
  return undefined;
}

/**
 * Why "Export reviewed .cha" is blocked in the transcript review controls.
 * The busy state is transient, so it returns undefined.
 */
export function exportTranscriptBlockedReason({
  busy,
  linesCount,
}: {
  busy: boolean;
  linesCount: number;
}): string | undefined {
  if (busy) return undefined;
  if (linesCount === 0) {
    return "Add transcript lines before exporting.";
  }
  return undefined;
}

/**
 * Why "Regenerate findings" is blocked on the stale-findings banner. The busy
 * state is transient (the label becomes "Regenerating..."), so it returns
 * undefined.
 */
export function regenerateFindingsBlockedReason(state: WorkflowState): string | undefined {
  if (!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed") {
    return "Complete transcript review and attestation before regenerating findings.";
  }
  return undefined;
}

/**
 * Why "Generate evidence review" is blocked next to the linguistic signals.
 * The busy state is transient (the label becomes "Generating..."), so it
 * returns undefined. When the backend's readiness check is blocked, prefer the
 * backend's own human-readable reasons when present.
 */
export function generateEvidenceReviewBlockedReason({
  backendUnavailable,
  readiness,
}: {
  backendUnavailable?: boolean;
  readiness?: MlReadiness;
}): string | undefined {
  if (backendUnavailable) {
    return "The backend is unavailable; evidence review cannot be generated until the connection is restored.";
  }
  if (readiness?.ready === false) {
    const backendReason = readiness.reasons?.find((reason) => Boolean(reason.trim()));
    if (backendReason) {
      return `Evidence readiness check is blocked: ${backendReason}`;
    }
    return "The evidence readiness check is blocked; resolve the blocking condition before generating evidence review.";
  }
  return undefined;
}

/**
 * Why "Generate AI-assisted review" is blocked in the findings view. The busy
 * state is transient (the label becomes "Generating..."), so it returns
 * undefined.
 */
export function generateAiReviewBlockedReason(state: WorkflowState): string | undefined {
  if (state.workflowLoading) return undefined;
  if (!state.featuresExtracted) {
    return "AI-assisted review requires extracted features from a reviewed, attested transcript.";
  }
  if (!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed") {
    return "AI-assisted review requires a saved, reviewed, and attested transcript.";
  }
  if (state.analysisStatus === "stale") {
    return "Regenerate findings from the current attested transcript before generating AI-assisted review.";
  }
  return undefined;
}

/**
 * Why "Approve reviewed cues" is blocked in the findings action panel. The
 * busy state is transient, so it returns undefined.
 */
export function approveReviewedCuesBlockedReason({
  busy,
  findingsStale,
  hasReviewableCues,
}: {
  busy: boolean;
  findingsStale: boolean;
  hasReviewableCues: boolean;
}): string | undefined {
  if (busy) return undefined;
  if (findingsStale) {
    return "Regenerate findings from the current attested transcript before approving reviewed cues.";
  }
  if (!hasReviewableCues) {
    return "Approve reviewed cues requires extracted signals or an evidence review. Review and attest the transcript, then extract features.";
  }
  return undefined;
}

/**
 * Why "Attest transcript" is blocked in the transcript review controls.
 * Already-attested transcripts and transient busy states return undefined: the
 * button label ("Transcript attested") and the surrounding status text already
 * communicate those, so a separate reason would be noise.
 */
export function attestTranscriptBlockedReason({
  busy,
  attested,
  linesCount,
  qaStatus,
}: {
  busy: boolean;
  attested: boolean;
  linesCount: number;
  qaStatus: TranscriptQaStatus;
}): string | undefined {
  if (attested || busy) return undefined;
  if (linesCount === 0) {
    return "Add transcript lines before attesting.";
  }
  if (qaStatus === "not_run") {
    return "Run transcript QA before attesting.";
  }
  if (qaStatus === "fail") {
    return "Resolve the QA failures before attesting.";
  }
  return undefined;
}
