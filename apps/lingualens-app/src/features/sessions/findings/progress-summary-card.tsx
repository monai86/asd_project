"use client";

import type { AiAssistanceArea, AiReview, WorkflowState } from "@/lib/workflow";
import { generateAiReviewBlockedReason } from "@/lib/workflow-gates";

/**
 * AI-assisted Progress Summary card for the Findings view. Surfaces the same
 * longitudinal context (previous-session deltas plus the typical-development
 * reference band when available) that the printed report and the dashboard
 * chart carry, so the therapist sees it without opening a report. When no
 * AI-assisted review exists yet, it offers generation with an inline
 * workflow-gate reason (aria-describedby) when blocked.
 */
export function ProgressSummaryCard({
  state,
  aiReview,
  busy,
  onGenerateAiReview,
}: {
  state: WorkflowState;
  aiReview?: AiReview;
  busy: boolean;
  onGenerateAiReview: () => void;
}) {
  const progressSummaryArea: AiAssistanceArea | undefined = aiReview?.assistanceAreas.find(
    (area) => area.area === "Progress Summary"
  );
  const aiReviewReason = generateAiReviewBlockedReason(state);

  return (
    <section aria-labelledby="findings-progress-summary-title" className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="findings-progress-summary-title" className="text-lg font-semibold text-[color:var(--color-text-strong)]">Progress Summary</h2>
          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
            AI-assisted longitudinal context for this case, including the typical-development reference band when available.
          </p>
        </div>
        {progressSummaryArea ? (
          <span className="rounded-full bg-[color:var(--color-surface-muted)] px-3 py-1 text-xs font-semibold text-[color:var(--color-text-strong)]">
            AI-assisted review
          </span>
        ) : null}
      </div>
      {progressSummaryArea ? (
        <div className="mt-4 space-y-3">
          <p className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm leading-6 text-[color:var(--color-text-strong)]">
            {progressSummaryArea.summary}
          </p>
          {progressSummaryArea.contributingFactors.length > 0 ? (
            <ul className="space-y-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
              {progressSummaryArea.contributingFactors.map((factor) => (
                <li key={factor} className="flex gap-2">
                  <span aria-hidden="true" className="text-[color:var(--color-text-subtle)]">•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <div className="mt-4">
          <button
            type="button"
            className="flex min-h-11 items-center justify-center rounded-[var(--radius-card)] bg-[color:var(--color-accent-strong)] px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => onGenerateAiReview()}
            disabled={busy || Boolean(aiReviewReason)}
            aria-describedby={aiReviewReason ? "generate-ai-review-reason" : undefined}
            data-testid="generate-ai-review-button"
          >
            {busy ? "Generating..." : "Generate AI-assisted review"}
          </button>
          {aiReviewReason ? (
            <p id="generate-ai-review-reason" role="status" className="mt-2 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900">
              {aiReviewReason}
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
