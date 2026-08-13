"use client";

import { Check } from "lucide-react";

export type PipelineState =
  | "awaiting_consent"
  | "ready_for_audio"
  | "uploading"
  | "transcribing"
  | "cha_generating"
  | "review_required"
  | "ml_pending"
  | "report_ready";

const pipelineStages: Array<{ id: PipelineState; label: string }> = [
  { id: "awaiting_consent", label: "Consent" },
  { id: "ready_for_audio", label: "Ready" },
  { id: "uploading", label: "Upload" },
  { id: "transcribing", label: "ASR" },
  { id: "cha_generating", label: "CHA" },
  { id: "review_required", label: "Review" },
  { id: "ml_pending", label: "ML Suggestions" },
  { id: "report_ready", label: "Report" }
];

type PipelineProgressBarProps = {
  currentStatus: string;
};

export function PipelineProgressBar({ currentStatus }: PipelineProgressBarProps) {
  // Map various session statuses to pipeline stages
  const statusLower = (currentStatus || "").toLowerCase().replace(/_/g, " ").trim();

  let activeIndex = 0;
  if (statusLower === "awaiting consent") {
    activeIndex = 0;
  } else if (statusLower === "ready for audio") {
    activeIndex = 1;
  } else if (statusLower === "recording" || statusLower === "uploading") {
    activeIndex = 2;
  } else if (statusLower === "transcribing") {
    activeIndex = 3;
  } else if (statusLower === "cha generating") {
    activeIndex = 4;
  } else if (statusLower === "needs review" || statusLower === "review required" || statusLower === "in review") {
    activeIndex = 5;
  } else if (statusLower === "ml pending" || statusLower === "attested") {
    activeIndex = 6;
  } else if (statusLower === "report ready" || statusLower === "ready" || statusLower === "signed off") {
    activeIndex = 7;
  }

  return (
    <section className="grid gap-4 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">
          Pipeline Status
        </h3>
        <p className="text-xs font-medium text-[color:var(--color-accent-strong)]">
          Stage {activeIndex + 1} of {pipelineStages.length}: {pipelineStages[activeIndex].label}
        </p>
      </div>
      <div
        className="relative grid grid-cols-2 gap-3 sm:flex sm:items-start sm:justify-between sm:gap-0"
        role="img"
        aria-label={`Pipeline Progress: ${pipelineStages[activeIndex].label}`}
      >
        {/* Progress bar line background */}
        <div className="absolute left-0 top-4 hidden h-0.5 w-full bg-[color:var(--color-border)] sm:block" />
        {/* Active progress bar line */}
        <div
          className="motion-panel absolute left-0 top-4 hidden h-0.5 bg-[color:var(--color-accent-strong)] transition-all sm:block"
          style={{ width: `${(activeIndex / (pipelineStages.length - 1)) * 100}%` }}
        />

        {pipelineStages.map((stage, idx) => {
          const isCompleted = idx < activeIndex;
          const isActive = idx === activeIndex;

          return (
            <div key={stage.id} className="relative z-10 flex flex-col items-center">
              <span
                className={`motion-panel rounded-full border-2 text-xs font-semibold transition-all ${
                  isCompleted
                    ? "border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-strong)] text-white"
                    : isActive
                    ? "border-[color:var(--color-accent-strong)] bg-white text-[color:var(--color-accent-strong)] ring-4 ring-[color:var(--color-accent-soft)]"
                    : "border-[color:var(--color-border)] bg-white text-[color:var(--color-text-muted)]"
                } grid h-8 w-8 place-items-center`}
              >
                {isCompleted ? <Check size={14} aria-hidden="true" /> : idx + 1}
              </span>
              <span
                className={`mt-2 text-center text-2xs font-semibold uppercase sm:max-w-20 ${
                  isActive
                    ? "text-[color:var(--color-text-strong)]"
                    : "text-[color:var(--color-text-muted)]"
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
