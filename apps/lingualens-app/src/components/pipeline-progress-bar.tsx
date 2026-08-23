"use client";

import { Check } from "lucide-react";

import { EVIDENCE_REVIEW_NOUN } from "@/lib/workflow-glossary";

export type PipelineState =
  | "awaiting_consent"
  | "ready_for_audio"
  | "uploading"
  | "transcribing"
  | "cha_generating"
  | "review_required"
  | "ml_pending"
  | "report_ready";

/** The source path chosen in Session Intake; narrows which pipeline stages apply. */
export type PipelinePath = "recording" | "audio" | "cha" | "paste";

const pipelineStages: Array<{ id: PipelineState; label: string }> = [
  { id: "awaiting_consent", label: "Consent" },
  { id: "ready_for_audio", label: "Ready" },
  { id: "uploading", label: "Upload" },
  { id: "transcribing", label: "ASR" },
  { id: "cha_generating", label: "CHA" },
  { id: "review_required", label: "Review" },
  { id: "ml_pending", label: EVIDENCE_REVIEW_NOUN },
  { id: "report_ready", label: "Report" }
];

/**
 * Ordered, source-relevant subsets of the full pipeline. Paste and CHA inputs
 * never upload audio or run ASR, so those stages are omitted; the recording
 * path keeps Upload and ASR; the audio path keeps Upload (ASR remains a
 * separate experimental step). Omitting `path` renders the full pipeline.
 */
const pathStageIds: Record<PipelinePath, PipelineState[]> = {
  recording: [
    "awaiting_consent",
    "ready_for_audio",
    "uploading",
    "transcribing",
    "review_required",
    "ml_pending",
    "report_ready"
  ],
  audio: [
    "awaiting_consent",
    "ready_for_audio",
    "uploading",
    "review_required",
    "ml_pending",
    "report_ready"
  ],
  cha: [
    "awaiting_consent",
    "ready_for_audio",
    "review_required",
    "ml_pending",
    "report_ready"
  ],
  paste: [
    "awaiting_consent",
    "ready_for_audio",
    "review_required",
    "ml_pending",
    "report_ready"
  ]
};

export function canonicalPipelineStageForStatus(statusLower: string): PipelineState {
  if (statusLower === "awaiting consent") return "awaiting_consent";
  if (statusLower === "ready for audio") return "ready_for_audio";
  if (statusLower === "recording" || statusLower === "uploading") return "uploading";
  if (statusLower === "transcribing") return "transcribing";
  if (statusLower === "cha generating") return "cha_generating";
  if (statusLower === "needs review" || statusLower === "review required" || statusLower === "in review") {
    return "review_required";
  }
  if (statusLower === "ml pending" || statusLower === "attested") return "ml_pending";
  if (statusLower === "report ready" || statusLower === "ready" || statusLower === "signed off") return "report_ready";
  return "awaiting_consent";
}

type PipelineProgressBarProps = {
  currentStatus: string;
  path?: PipelinePath;
};

export function PipelineProgressBar({ currentStatus, path }: PipelineProgressBarProps) {
  const stages = path
    ? pathStageIds[path]
        .map((id) => pipelineStages.find((stage) => stage.id === id))
        .filter((stage): stage is { id: PipelineState; label: string } => Boolean(stage))
    : pipelineStages;
  const statusLower = (currentStatus || "").toLowerCase().replace(/_/g, " ").trim();
  const canonicalStage = canonicalPipelineStageForStatus(statusLower);

  let activeIndex = stages.findIndex((stage) => stage.id === canonicalStage);
  if (activeIndex === -1) {
    // The status refers to a stage that does not exist on this path; highlight
    // the nearest preceding stage that does, falling back to the first stage.
    const canonicalIndex = pipelineStages.findIndex((stage) => stage.id === canonicalStage);
    activeIndex = stages.reduce((nearest, stage, idx) => (
      pipelineStages.findIndex((full) => full.id === stage.id) <= canonicalIndex ? idx : nearest
    ), -1);
    if (activeIndex === -1) activeIndex = 0;
  }

  return (
    <section className="grid gap-4 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">
          Pipeline Status
        </h2>
        <p className="text-xs font-medium text-[color:var(--color-accent-strong)]">
          Stage {activeIndex + 1} of {stages.length}: {stages[activeIndex].label}
        </p>
      </div>
      <div
        className="relative grid grid-cols-2 gap-3 sm:flex sm:items-start sm:justify-between sm:gap-0"
        role="img"
        aria-label={`Pipeline Progress: ${stages[activeIndex].label}`}
      >
        {/* Progress bar line background */}
        <div className="absolute left-0 top-4 hidden h-0.5 w-full bg-[color:var(--color-border)] sm:block" />
        {/* Active progress bar line */}
        <div
          className="motion-panel absolute left-0 top-4 hidden h-0.5 bg-[color:var(--color-accent-strong)] transition-all sm:block"
          style={{ width: `${(activeIndex / (stages.length - 1)) * 100}%` }}
        />

        {stages.map((stage, idx) => {
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
