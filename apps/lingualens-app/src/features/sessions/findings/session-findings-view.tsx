"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, FileText, ShieldCheck, Sparkles, Wand2 } from "lucide-react";

import { GlassCard, GradientButton } from "@/components/liquid-ui";
import { RightRail } from "@/components/right-rail";
import { SafetyNotice } from "@/components/safety-notice";
import { StatCard } from "@/components/stat-card";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
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
import type { WorkflowState } from "@/lib/workflow";

export function SessionFindingsView({
  sessionContext,
  state,
  busy,
  onRegenerateFindings,
  onGenerateReport,
  onGenerateMlDecisionSupport,
  onProfileEvidenceReview,
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
  const [reviewedCuesApproved, setReviewedCuesApproved] = useState(false);
  const signalCards = useMemo(() => buildLinguisticSignalCards(currentFindingsState), [currentFindingsState]);
  const recommendedReviewPoints = useMemo(() => buildRecommendedReviewPoints(currentFindingsState), [currentFindingsState]);
  const interpretationDraftSeed = useMemo(
    () => createInterpretationDraft(currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport),
    [currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport]
  );
  const reportReady = isResultsReportReady(state);
  const missingReferenceData = hasMissingReferenceData(currentFindingsState);

  useEffect(() => {
    setInterpretationDraft(interpretationDraftSeed);
    setReviewedCuesApproved(false);
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
        <GlassCard className="p-8 text-center">
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
            <GradientButton href={workflowSessionHref("intake", state)} icon={FileText}>Record or add a transcript</GradientButton>
            <GradientButton href={workflowSessionHref("transcript", state)} icon={FileText}>Review Transcript</GradientButton>
          </div>
          <GradientButton icon={ShieldCheck} className="mt-3" disabled>Generate Report</GradientButton>
        </GlassCard>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <SessionContextHeader
        title="Session Results"
        description="Review descriptive transcript cues, backend-derived features, and therapist-editable draft language before generating a report draft."
        context={sessionContext}
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-6">
        {findingsStale ? (
          <div className="rounded-[var(--radius-panel)] border border-amber-300 bg-amber-50 p-5 text-amber-950" role="alert">
            <p className="font-semibold">These findings are stale because the transcript changed.</p>
            <p className="mt-1 text-sm">Prior derived values are hidden and cannot be used for a report until findings are regenerated from the current attested transcript.</p>
            <GradientButton
              className="mt-3"
              icon={Sparkles}
              onClick={onRegenerateFindings}
              disabled={busy || !isTranscriptUnlocked(state)}
            >
              {busy ? "Regenerating..." : "Regenerate findings"}
            </GradientButton>
          </div>
        ) : null}

        <section
          aria-label="Findings provenance"
          className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-5"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Findings provenance</h2>
              <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
                Versions identify the reviewed inputs behind these descriptive cues. Missing metadata is never inferred.
              </p>
            </div>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${findingsCurrent ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-950"}`}>
              {analysisDispositionLabel(state.analysisStatus)}
            </span>
          </div>
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

        <section className="space-y-3">
          <h2 className="text-base font-semibold text-[color:var(--color-text-strong)]">Summary</h2>
          <span className="sr-only">Summary cards</span>
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
              value={currentFindingsState.featuresExtracted ? `${signalCards.length} signals` : "Pending"}
              helper={currentFindingsState.featuresExtracted ? "Backend feature values are available for review." : "Extract reviewed transcript features to populate the signal grid."}
              icon={Sparkles}
              tone={currentFindingsState.featuresExtracted ? "success" : "warning"}
            />
            <StatCard
              label="Review flags"
              value={String(totalReviewFlags(currentFindingsState))}
              helper={totalReviewFlags(currentFindingsState) > 0 ? "Review flagged items before generating a draft report." : "No additional review flags are currently open."}
              icon={AlertTriangle}
              tone={totalReviewFlags(currentFindingsState) > 0 ? "warning" : "accent"}
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

        <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold tracking-[-0.02em] text-[color:var(--color-text-strong)]">Linguistic Signals</h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
                {findingsStale
                  ? "Prior derived values are hidden until findings are regenerated from the current transcript."
                  : "Backend feature values are shown as descriptive cues only. Therapist interpretation is required for any clinical use."}
              </p>
            </div>
            {currentFindingsState.featuresExtracted && !currentFindingsState.mlDecisionSupport ? (
              <GradientButton
                icon={Wand2}
                onClick={onGenerateMlDecisionSupport}
                disabled={busy || backendUnavailable || currentFindingsState.mlReadiness?.ready === false}
                data-testid="generate-evidence-review-button"
              >
                {busy ? "Generating..." : "Generate evidence review"}
              </GradientButton>
            ) : null}
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {signalCards.length ? signalCards.map((signal) => (
              <article key={signal.featureName} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
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
          <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6">
            <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Recommended review points</h2>
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

          <div className="space-y-6">
            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Action panel</h2>
              <div className="mt-4 space-y-3">
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm font-semibold text-[color:var(--color-text-strong)] disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => setReviewedCuesApproved(true)}
                  disabled={busy || findingsStale || (!currentFindingsState.mlDecisionSupport && signalCards.length === 0)}
                >
                  Approve reviewed cues
                </button>
                <GradientButton href={workflowSessionHref("transcript", state)} icon={FileText} className="w-full justify-center">
                  Revise transcript
                </GradientButton>
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] bg-[color:var(--color-accent-strong)] px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
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
        description="Evidence review is descriptive. Therapist interpretation, editing, and sign-off remain required."
      >
        <SafetyNotice>Decision-support only. Therapist interpretation and sign-off remain required.</SafetyNotice>
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
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
          <h3 className="text-sm font-semibold text-[color:var(--color-text-strong)]">Limitations</h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[color:var(--color-text-muted)]">
            {(currentFindingsState.mlDecisionSupport?.limitations.length
              ? currentFindingsState.mlDecisionSupport.limitations
              : [
                  "Feature definitions describe how backend values are computed; they do not provide diagnostic conclusions.",
                  "If reference data is unavailable, compare within therapist context rather than inferred norms."
                ]).map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        </div>
      </RightRail>
      </div>
    </div>
  );
}
