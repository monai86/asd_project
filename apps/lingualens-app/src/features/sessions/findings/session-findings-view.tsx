"use client";

import { useEffect, useMemo, useState } from "react";
import { FileSearch, FileText, ShieldCheck, Wand2 } from "lucide-react";

import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";
import { RightRail } from "@/components/right-rail";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import { SessionGuide, type SessionGuideAction } from "@/features/sessions/components/session-guide";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import { EvidenceReviewSection } from "@/features/sessions/findings/evidence-review-section";
import { FeatureDecisionGrid } from "@/features/sessions/findings/feature-decision-grid";
import { ProgressSummaryCard } from "@/features/sessions/findings/progress-summary-card";
import {
  ProvenanceItem,
  WorkflowStatus,
  analysisDispositionLabel,
  buildLinguisticSignalCards,
  buildRecommendedReviewPoints,
  createInterpretationDraft,
  evidenceDisposition,
  hasMissingReferenceData,
  isResultsReportReady,
  isTranscriptUnlocked,
  totalReviewFlags,
  transcriptQualityLabel,
  versionLabel,
  workflowSessionHref,
} from "@/features/sessions/findings/session-findings-support";
import { approveReviewedCuesBlockedReason, generateEvidenceReviewBlockedReason, regenerateFindingsBlockedReason } from "@/lib/workflow-gates";
import { EXTRACT_FEATURES_ACTION, GENERATE_EVIDENCE_REVIEW_ACTION, GENERATE_REPORT_ACTION } from "@/lib/workflow-glossary";
import type { WorkflowState } from "@/lib/workflow";

export function SessionFindingsView({
  sessionContext,
  state,
  busy,
  onRegenerateFindings,
  onGenerateReport,
  onGenerateMlDecisionSupport,
  onGenerateAiReview,
  onProfileEvidenceReview,
  onApproveReviewedCues,
  backendUnavailable
}: {
  sessionContext: SessionContext;
  state: WorkflowState;
  busy: boolean;
  onRegenerateFindings: () => void;
  onGenerateReport: () => void;
  onGenerateMlDecisionSupport: () => void;
  onGenerateAiReview: () => void;
  onProfileEvidenceReview: (
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote?: string
  ) => void;
  onApproveReviewedCues: () => void | Promise<void>;
  backendUnavailable?: boolean;
}) {
  const findingsStale = state.analysisStatus === "stale";
  const findingsCurrent = state.analysisStatus === "completed";
  const currentFindingsState = useMemo(() => !findingsCurrent ? {
    ...state,
    featuresExtracted: false,
    featurePercent: 0,
    featureSummary: [],
    featureSignals: [],
    mlDecisionSupport: undefined,
    insights: [],
  } : state, [findingsCurrent, state]);
  const [interpretationDraft, setInterpretationDraft] = useState(() =>
    createInterpretationDraft(currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport)
  );
  const signalCards = useMemo(() => buildLinguisticSignalCards(currentFindingsState), [currentFindingsState]);
  const recommendedReviewPoints = useMemo(() => buildRecommendedReviewPoints(currentFindingsState), [currentFindingsState]);
  const interpretationDraftSeed = useMemo(
    () => createInterpretationDraft(currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport),
    [currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport]
  );
  const reportReady = isResultsReportReady(state);
  const missingReferenceData = hasMissingReferenceData(currentFindingsState);
  const regenerateFindingsReason = regenerateFindingsBlockedReason(state);
  const evidenceReviewReason = generateEvidenceReviewBlockedReason({
    backendUnavailable,
    readiness: currentFindingsState.mlReadiness,
  });
  const approveCuesReason = approveReviewedCuesBlockedReason({
    busy,
    findingsStale,
    hasReviewableCues: Boolean(currentFindingsState.mlDecisionSupport) || signalCards.length > 0,
  });

  useEffect(() => {
    setInterpretationDraft(interpretationDraftSeed);
  }, [interpretationDraftSeed, state.backendSessionId, state.reportId]);

  if (!state.transcriptReady && !state.featuresExtracted) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <SessionContextHeader
          title="Session Results"
          description="Review descriptive transcript cues and therapist-owned next steps."
          context={sessionContext}
        />
        <WorkspacePanel className="p-8 text-center">
          <FileSearch className="mx-auto text-clinical" size={38} aria-hidden="true" />
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
            <PrimaryActionButton href={workflowSessionHref("intake", state)} icon={FileText}>Record or add a transcript</PrimaryActionButton>
            <PrimaryActionButton href={workflowSessionHref("transcript", state)} icon={FileText}>Review Transcript</PrimaryActionButton>
          </div>
          <PrimaryActionButton icon={ShieldCheck} className="mt-3" disabled>{GENERATE_REPORT_ACTION}</PrimaryActionButton>
        </WorkspacePanel>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <SessionContextHeader
        title="Session Results"
        description="Review descriptive transcript cues and therapist-owned draft language."
        context={sessionContext}
        density="compact"
      />
      <SessionGuide
        testId="findings-guide"
        reasonId={findingsStale ? "regenerate-findings-reason" : undefined}
        prompt={
          findingsStale
            ? "The transcript changed, so these findings are out of date. Regenerate them before continuing."
            : reportReady
              ? "The session is ready for a draft. Review the signals below, then generate the report."
              : "Here are the language-sample signals for this session. Review them, then we'll prepare the report."
        }
        primaryAction={findingsGuidePrimary({
          findingsStale,
          busy,
          regenerateFindingsReason,
          onRegenerateFindings,
          state,
        })}
        quickReplies={
          findingsStale
            ? [
                { label: "Revise transcript", href: resolveSessionHref("transcript", sessionContext.sessionId) },
                { label: "Go to report", href: resolveSessionHref("report", sessionContext.sessionId) },
              ]
            : [
                { label: "Revise transcript", href: resolveSessionHref("transcript", sessionContext.sessionId) },
                { label: "Regenerate findings", onClick: onRegenerateFindings },
                { label: "Go to report", href: resolveSessionHref("report", sessionContext.sessionId) },
              ]
        }
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-6">
        {findingsStale ? (
          <p role="alert" className="text-sm leading-6 text-[color:var(--color-warning-text)]">
            These findings are stale because the transcript changed. Prior derived values are hidden and cannot be used for a report until findings are regenerated from the current attested transcript.
          </p>
        ) : null}

        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-[color:var(--color-text-strong)]">Linguistic Signals</h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
                {findingsStale
                  ? "Prior derived values are hidden until findings are regenerated from the current transcript."
                  : "Backend feature values are shown as descriptive cues only. Therapist interpretation is required for any clinical use."}
              </p>
            </div>
            {currentFindingsState.featuresExtracted && !currentFindingsState.mlDecisionSupport ? (
              <div className="space-y-2">
                <PrimaryActionButton
                  icon={Wand2}
                  onClick={onGenerateMlDecisionSupport}
                  disabled={busy || backendUnavailable || currentFindingsState.mlReadiness?.ready === false}
                  data-testid="generate-evidence-review-button"
                  aria-describedby={evidenceReviewReason ? "generate-evidence-review-reason" : undefined}
                >
                  {busy ? "Generating..." : GENERATE_EVIDENCE_REVIEW_ACTION}
                </PrimaryActionButton>
                {evidenceReviewReason ? (
                  <p id="generate-evidence-review-reason" role="status" className="rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900">
                    {evidenceReviewReason}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
          {currentFindingsState.featuresExtracted ? <FeatureDecisionGrid signals={signalCards} /> : null}
        </section>

        <section aria-labelledby="findings-workflow-summary-title" className="overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-border)]">
          <div className="bg-[color:var(--color-surface-reading)] px-4 py-3">
            <h2 id="findings-workflow-summary-title" className="text-sm font-semibold text-[color:var(--color-text-strong)]">Workflow summary</h2>
          </div>
          <dl className="grid gap-px sm:grid-cols-2 xl:grid-cols-4">
            <div className="bg-[color:var(--color-surface-strong)] px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Transcript quality</dt>
              <dd className="mt-1 font-semibold text-[color:var(--color-text-strong)]">{transcriptQualityLabel(state)}</dd>
              <p className="mt-1 text-xs leading-5 text-[color:var(--color-text-muted)]">{state.qaSummary ?? "Therapist review remains required."}</p>
            </div>
            <div className="bg-[color:var(--color-surface-strong)] px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Features extracted</dt>
              <dd className="mt-1 font-semibold text-[color:var(--color-text-strong)]">{currentFindingsState.featuresExtracted ? `${signalCards.length} signals` : "Pending"}</dd>
              <p className="mt-1 text-xs leading-5 text-[color:var(--color-text-muted)]">{currentFindingsState.featuresExtracted ? "Backend values available for review." : `Run ${EXTRACT_FEATURES_ACTION} on the reviewed transcript.`}</p>
            </div>
            <div className="bg-[color:var(--color-surface-strong)] px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Review flags</dt>
              <dd className="mt-1 font-semibold text-[color:var(--color-text-strong)]">{totalReviewFlags(currentFindingsState)}</dd>
              <p className="mt-1 text-xs leading-5 text-[color:var(--color-text-muted)]">{totalReviewFlags(currentFindingsState) > 0 ? "Review flagged items before drafting." : "No additional flags are open."}</p>
            </div>
            <div className="bg-[color:var(--color-surface-strong)] px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Report readiness</dt>
              <dd className="mt-1 font-semibold text-[color:var(--color-text-strong)]">{reportReady ? "Ready" : "Blocked"}</dd>
              <p className="mt-1 text-xs leading-5 text-[color:var(--color-text-muted)]">{reportReady ? "Workflow gates passed for a draft." : "Reviewed transcript and current findings required."}</p>
            </div>
          </dl>
        </section>

        <ProgressSummaryCard state={state} aiReview={state.aiReview} busy={busy} onGenerateAiReview={onGenerateAiReview} />

        <details className="responsive-details rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)]">
          <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 px-5 py-3">
            <span>
              <span className="block font-semibold text-[color:var(--color-text-strong)]">Technical provenance</span>
              <span className="mt-0.5 block text-sm text-[color:var(--color-text-muted)]">Versions and backend source identifiers</span>
            </span>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${findingsCurrent ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-950"}`}>
              {analysisDispositionLabel(state.analysisStatus)}
            </span>
          </summary>
          <section aria-label="Findings provenance" className="border-t border-[color:var(--color-border)] p-5">
            <p className="text-sm leading-6 text-[color:var(--color-text-muted)]">
              Versions identify the reviewed inputs behind these descriptive cues. Missing metadata is never inferred.
            </p>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <ProvenanceItem label="Reviewed transcript" value={versionLabel(state.backendTranscriptVersion)} />
              <ProvenanceItem label="Findings transcript" value={versionLabel(state.featureTranscriptVersion)} />
              <ProvenanceItem label="Feature result ID" value={state.featureSetId ?? "Unavailable"} />
              <ProvenanceItem
                label="Feature schema version"
                value={state.featureSchemaVersion ?? currentFindingsState.mlDecisionSupport?.featureSchemaVersion ?? "Unavailable"}
              />
              <ProvenanceItem
                label="AI disposition"
                value={findingsCurrent ? evidenceDisposition(currentFindingsState.mlDecisionSupport) : analysisDispositionLabel(state.analysisStatus)}
              />
            </dl>
          </section>
        </details>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <EvidenceReviewSection
            mlDecisionSupport={currentFindingsState.mlDecisionSupport}
            recommendedReviewPoints={recommendedReviewPoints}
            busy={busy}
            onProfileEvidenceReview={onProfileEvidenceReview}
          />

          <div className="space-y-6">
            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Action panel</h2>
              <div className="mt-4 space-y-3">
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm font-semibold text-[color:var(--color-text-strong)] disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => onApproveReviewedCues()}
                  disabled={busy || findingsStale || (!currentFindingsState.mlDecisionSupport && signalCards.length === 0)}
                  aria-describedby={approveCuesReason ? "approve-reviewed-cues-reason" : undefined}
                >
                  Approve reviewed cues
                </button>
                {approveCuesReason ? (
                  <p id="approve-reviewed-cues-reason" role="status" className="rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900">
                    {approveCuesReason}
                  </p>
                ) : null}
                <PrimaryActionButton href={workflowSessionHref("transcript", state)} icon={FileText} className="w-full justify-center">
                  Revise transcript
                </PrimaryActionButton>
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] bg-[color:var(--color-accent-strong)] px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={onGenerateReport}
                  disabled={busy || !reportReady}
                  data-testid="generate-report-button"
                >
                  {busy ? "Generating..." : GENERATE_REPORT_ACTION}
                </button>
              </div>
              {!reportReady ? (
                <p className="mt-4 text-sm text-[color:var(--color-warning-text)]">
                  Therapist-reviewed transcript and feature extraction are required before generating a draft report. Evidence review remains optional.
                </p>
              ) : null}
              {state.cuesAcknowledgedAt ? (
                <p className="mt-3 text-sm text-[color:var(--color-success-text)]">
                  Reviewed cues acknowledged and recorded{state.cuesAcknowledgedBy ? ` by ${state.cuesAcknowledgedBy}` : ""} on {new Date(state.cuesAcknowledgedAt).toLocaleDateString()}. Therapist sign-off is still required.
                </p>
              ) : null}
            </section>

            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Therapist-editable interpretation draft</h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
                Draft wording only. Edit this text before using it in any report or clinical documentation.
              </p>
              <textarea
                aria-label="Therapist-editable interpretation draft"
                className="mt-4 min-h-48 w-full rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 text-sm leading-6 text-[color:var(--color-text-strong)]"
                value={interpretationDraft}
                readOnly={findingsStale}
                onChange={(event) => setInterpretationDraft(event.target.value)}
              />
            </section>
          </div>
        </section>

        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
      </div>

      <RightRail
        title="Safety & limitations"
        description="Interpret descriptive cues in context; limitations remain attached to each feature."
      >
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
          <h3 className="text-sm font-semibold text-[color:var(--color-text-strong)]">Review readiness</h3>
          <ul className="mt-3 space-y-2 text-sm text-[color:var(--color-text-muted)]">
            <li>{state.transcriptAttested ? "Transcript attested" : "Transcript attestation required"}</li>
            <li>{currentFindingsState.featuresExtracted ? "Feature extraction complete" : "Feature extraction pending"}</li>
            <li>{currentFindingsState.mlReadiness?.ready === false ? "Evidence readiness check still blocked" : "Evidence readiness check can proceed"}</li>
          </ul>
        </div>
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
          <h3 className="text-sm font-semibold text-[color:var(--color-text-strong)]">Reference status</h3>
          <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
            {missingReferenceData ? "Reference comparison unavailable" : "Reference comparisons are shown only when the backend provides supporting data."}
          </p>
        </div>
        <details className="responsive-details rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)]">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-4 text-sm font-semibold text-[color:var(--color-text-strong)]">
            <span>Limitations</span>
            <span aria-hidden="true">›</span>
          </summary>
          <ul className="border-t border-[color:var(--color-border)] px-4 py-3 pl-9 text-sm text-[color:var(--color-text-muted)]">
            {(currentFindingsState.mlDecisionSupport?.limitations.length
              ? currentFindingsState.mlDecisionSupport.limitations
              : [
                  "Feature definitions describe how backend values are computed; they do not provide diagnostic conclusions.",
                  "If reference data is unavailable, compare within therapist context rather than inferred norms."
                ]).map((limitation) => <li className="list-disc" key={limitation}>{limitation}</li>)}
          </ul>
        </details>
      </RightRail>
      </div>
    </div>
  );
}

function findingsGuidePrimary({
  findingsStale,
  busy,
  regenerateFindingsReason,
  onRegenerateFindings,
  state,
}: {
  findingsStale: boolean;
  busy: boolean;
  regenerateFindingsReason?: string;
  onRegenerateFindings: () => void;
  state: WorkflowState;
}): SessionGuideAction | undefined {
  // The guide owns the regeneration affordance when findings are stale (it
  // replaced the old banner). In every other state the page's own action panel
  // already carries the primary action, so the guide only prompts and navigates.
  if (findingsStale) {
    return {
      label: "Regenerate findings",
      onClick: onRegenerateFindings,
      disabled: busy || !isTranscriptUnlocked(state),
      reason: regenerateFindingsReason,
    };
  }
  return undefined;
}
