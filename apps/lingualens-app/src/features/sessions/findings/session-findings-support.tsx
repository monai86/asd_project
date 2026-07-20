import { resolveSessionHref } from "@/features/sessions/state/session-view";
import type { WorkflowState } from "@/lib/workflow";

export function buildLinguisticSignalCards(state: WorkflowState) {
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

export function transcriptQualityLabel(state: WorkflowState) {
  if (state.qaStatus === "pass") return `Pass · ${state.transcriptCompleteness || 100}%`;
  if (state.qaStatus === "warning") return `Warning · ${state.transcriptCompleteness || 0}%`;
  if (state.qaStatus === "fail") return "Blocked";
  return "Pending";
}

export function totalReviewFlags(state: WorkflowState) {
  return state.reviewNeededCount
    + state.qaIssues.length
    + (state.mlDecisionSupport?.cues.length ?? 0)
    + (state.mlDecisionSupport?.profileEvidence.filter((profile) => profile.reviewState.status === "unreviewed").length ?? 0);
}

export function buildRecommendedReviewPoints(state: WorkflowState) {
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

export function createInterpretationDraft(
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

export function hasMissingReferenceData(state: WorkflowState) {
  if (state.featureSignals.some((signal) => signal.referenceText === "Reference comparison unavailable")) return true;
  if (state.mlDecisionSupport?.patternEvidence?.availability.state === "insufficient_reference_data") return true;
  return (state.mlDecisionSupport?.profileEvidence ?? []).some((profile) => profile.availability.state === "insufficient_reference_data");
}

export function isTranscriptUnlocked(state: WorkflowState) {
  return state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
}

export function isResultsReportReady(state: WorkflowState) {
  return state.analysisStatus === "completed" && isTranscriptUnlocked(state) && state.featuresExtracted;
}

export function versionLabel(value?: number | string) {
  return value == null || value === "" ? "Unavailable" : `Version ${value}`;
}

export function analysisDispositionLabel(status: WorkflowState["analysisStatus"]) {
  if (status === "completed") return "Current findings";
  if (status === "stale") return "Stale · regeneration required";
  if (status === "processing") return "Processing";
  if (status === "failed") return "Failed";
  return "Not generated";
}

export function evidenceDisposition(decisionSupport?: WorkflowState["mlDecisionSupport"]) {
  if (!decisionSupport) return "Not generated";
  if (decisionSupport.status === "completed") return "Completed";
  if (decisionSupport.status === "insufficient_data") return "Insufficient data";
  if (decisionSupport.status === "unavailable") return "Unavailable";
  return "Failed";
}

export function ProvenanceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-[color:var(--color-text-strong)]">{value}</dd>
    </div>
  );
}

const evidenceStateTitle = {
  input_action_required: "Input action required",
  unsupported_scope: "Outside the supported evidence scope",
  insufficient_reference_data: "Insufficient reference data",
  system_unavailable: "Evidence service unavailable",
  available: "Evidence available"
} as const;

export function EvidenceAvailabilityView({ availability }: { availability: NonNullable<WorkflowState["mlDecisionSupport"]>["profileEvidence"][number]["availability"] }) {
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

export function patternEvidenceTitle(status: "no_additional_pattern_cue" | "additional_evidence_review_suggested" | "not_available") {
  if (status === "no_additional_pattern_cue") return "No additional pattern cue";
  if (status === "additional_evidence_review_suggested") return "Additional evidence review suggested";
  return "Pattern evidence not available";
}

export function profileStatusTitle(status: "comparable_patterns_observed" | "limited_comparison" | "not_available") {
  if (status === "comparable_patterns_observed") return "Comparable patterns observed";
  if (status === "limited_comparison") return "Limited comparison";
  return "Not available";
}

export function positionTitle(position: "below_iqr" | "within_iqr" | "above_iqr" | "missing") {
  if (position === "below_iqr") return "below the reference IQR";
  if (position === "above_iqr") return "above the reference IQR";
  if (position === "within_iqr") return "within the reference IQR";
  return "value unavailable";
}

export function featureLabel(value: string) {
  return value.replaceAll("_", " ");
}


export function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
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

export function workflowSessionHref(view: "intake" | "transcript" | "findings" | "report", state: WorkflowState, reportId?: string) {
  return resolveSessionHref(view, state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId, {
    caseId: state.caseId,
    transcriptId: state.backendTranscriptId,
    reportId: reportId ?? state.backendReportId ?? state.reportId,
  });
}
