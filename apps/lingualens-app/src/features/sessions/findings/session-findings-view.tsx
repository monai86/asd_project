"use client";

import { useEffect, useMemo, useState } from "react";
import { FileText, ShieldCheck, Sparkles, Wand2 } from "lucide-react";

import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";
import { RightRail } from "@/components/right-rail";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import { FindingsFeatureGroups } from "@/features/sessions/findings/findings-feature-groups";
import {
  EvidenceAvailabilityView,
  ProvenanceItem,
  WorkflowStatus,
  analysisDispositionLabel,
  buildLinguisticSignalCards,
  buildRecommendedReviewPoints,
  createInterpretationDraft,
  evidenceDisposition,
  featureLabel,
  hasMissingReferenceData,
  isResultsReportReady,
  isTranscriptUnlocked,
  patternEvidenceTitle,
  positionTitle,
  profileStatusTitle,
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
  onProfileEvidenceReview: (
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote?: string
  ) => void;
  onApproveReviewedCues: () => void | Promise<void>;
  backendUnavailable?: boolean;
}) {
  const [showEvidenceDetails, setShowEvidenceDetails] = useState(false);
  const [disagreementProfile, setDisagreementProfile] = useState<string>();
  const [disagreementNote, setDisagreementNote] = useState("");
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

  let initialEvidenceCueCount = 0;
  if (!state.transcriptReady && !state.featuresExtracted) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <SessionContextHeader
          title="Session Results"
          description="Review descriptive transcript cues and therapist-owned next steps."
          context={sessionContext}
        />
        <WorkspacePanel className="p-8 text-center">
          <Sparkles className="mx-auto text-clinical" size={38} aria-hidden="true" />
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
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-6">
        {findingsStale ? (
          <div className="rounded-[var(--radius-panel)] border border-amber-300 bg-amber-50 p-5 text-amber-950" role="alert">
            <p className="font-semibold">These findings are stale because the transcript changed.</p>
            <p className="mt-1 text-sm">Prior derived values are hidden and cannot be used for a report until findings are regenerated from the current attested transcript.</p>
            <PrimaryActionButton
              className="mt-3"
              icon={Sparkles}
              onClick={onRegenerateFindings}
              disabled={busy || !isTranscriptUnlocked(state)}
              aria-describedby={regenerateFindingsReason ? "regenerate-findings-reason" : undefined}
            >
              {busy ? "Regenerating..." : "Regenerate findings"}
            </PrimaryActionButton>
            {regenerateFindingsReason ? (
              <p id="regenerate-findings-reason" role="status" className="mt-2 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900">
                {regenerateFindingsReason}
              </p>
            ) : null}
          </div>
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
          <FindingsFeatureGroups signals={signalCards} />
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
          <details className="responsive-details self-start rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)]">
            <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 px-5 py-3">
              <span className="font-semibold text-[color:var(--color-text-strong)]">Review guidance and evidence</span>
              <span className="text-xs font-medium text-[color:var(--color-text-muted)]">{recommendedReviewPoints.length} review point{recommendedReviewPoints.length === 1 ? "" : "s"}</span>
            </summary>
            <div className="border-t border-[color:var(--color-border)] p-5">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Recommended review points</h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-[color:var(--color-text-muted)]">
              {recommendedReviewPoints.map((point) => (
                <li key={point} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3">
                  {point}
                </li>
              ))}
            </ul>
            {currentFindingsState.mlDecisionSupport ? (
              <div className="mt-5 space-y-3" data-testid="evidence-review-panel">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--color-text-muted)]">Evidence review</h3>
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">Not diagnostic</span>
                </div>
                <p className="text-sm text-[color:var(--color-text-muted)]">
                  {currentFindingsState.mlDecisionSupport.providerName} v{currentFindingsState.mlDecisionSupport.providerVersion} · schema {currentFindingsState.mlDecisionSupport.featureSchemaVersion}
                </p>
                {currentFindingsState.mlDecisionSupport.patternEvidence ? (
                  <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
                    <p className="font-semibold text-[color:var(--color-text-strong)]">{patternEvidenceTitle(currentFindingsState.mlDecisionSupport.patternEvidence.status)}</p>
                    <EvidenceAvailabilityView availability={currentFindingsState.mlDecisionSupport.patternEvidence.availability} />
                  </div>
                ) : null}
                {(currentFindingsState.mlDecisionSupport.profileEvidence ?? []).map((profile) => {
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
                        <p className="mt-3 rounded-[var(--radius-card)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-medium text-[color:var(--color-warning-text)]">
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
                          className="rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm font-semibold text-[color:var(--color-accent-strong)]"
                          onClick={() => onProfileEvidenceReview(profile.profileCode, "reviewed")}
                          disabled={busy}
                        >
                          Reviewed
                        </button>
                        <button
                          type="button"
                          className="rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm font-semibold text-[color:var(--color-text-strong)]"
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
                            className="mt-2 min-h-24 w-full rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-3 text-sm"
                            value={disagreementNote}
                            onChange={(event) => setDisagreementNote(event.target.value)}
                          />
                          <div className="mt-2 flex gap-2">
                            <button
                              type="button"
                              className="rounded-[var(--radius-card)] bg-[color:var(--color-accent-strong)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
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
                              className="rounded-[var(--radius-card)] px-3 py-2 text-sm font-semibold text-[color:var(--color-text-strong)]"
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
                {(currentFindingsState.mlDecisionSupport.profileEvidence ?? []).some((profile) => profile.associatedFeatures.length > 0) ? (
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
          </details>

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
