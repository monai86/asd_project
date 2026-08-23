"use client";

import { useState } from "react";

import type { WorkflowState } from "@/lib/workflow";
import {
  EvidenceAvailabilityView,
  featureLabel,
  patternEvidenceTitle,
  positionTitle,
  profileStatusTitle,
} from "@/features/sessions/findings/session-findings-support";

export function EvidenceReviewSection({
  mlDecisionSupport,
  recommendedReviewPoints,
  busy,
  onProfileEvidenceReview,
}: {
  mlDecisionSupport?: WorkflowState["mlDecisionSupport"];
  recommendedReviewPoints: string[];
  busy: boolean;
  onProfileEvidenceReview: (
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote?: string
  ) => void;
}) {
  const [showEvidenceDetails, setShowEvidenceDetails] = useState(false);
  const [disagreementProfile, setDisagreementProfile] = useState<string>();
  const [disagreementNote, setDisagreementNote] = useState("");

  let initialEvidenceCueCount = 0;

  return (
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
      {mlDecisionSupport ? (
        <div className="mt-5 space-y-3" data-testid="evidence-review-panel">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--color-text-muted)]">Evidence review</h3>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">Not diagnostic</span>
          </div>
          <p className="text-sm text-[color:var(--color-text-muted)]">
            {mlDecisionSupport.providerName} v{mlDecisionSupport.providerVersion} · schema {mlDecisionSupport.featureSchemaVersion}
          </p>
          {mlDecisionSupport.patternEvidence ? (
            <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
              <p className="font-semibold text-[color:var(--color-text-strong)]">{patternEvidenceTitle(mlDecisionSupport.patternEvidence.status)}</p>
              <EvidenceAvailabilityView availability={mlDecisionSupport.patternEvidence.availability} />
            </div>
          ) : null}
          {(mlDecisionSupport.profileEvidence ?? []).map((profile) => {
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
          {(mlDecisionSupport.profileEvidence ?? []).some((profile) => profile.associatedFeatures.length > 0) ? (
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
  );
}
