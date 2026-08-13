"use client";

import type { ComponentProps } from "react";
import dynamic from "next/dynamic";

import { BackendAvailabilityBanner } from "@/components/backend-availability-banner";
import type { SessionFindingsView as SessionFindingsViewComponent } from "@/features/sessions/findings/session-findings-view";
import type { SessionIntakeView as SessionIntakeViewComponent } from "@/features/sessions/intake/session-intake-view";
import type { SessionTranscriptView as SessionTranscriptViewComponent } from "@/features/sessions/transcript/session-transcript-view";

const SessionFindingsView = dynamic(
  () => import("@/features/sessions/findings/session-findings-view").then((module) => module.SessionFindingsView),
  { loading: SessionFeatureLoading },
);
const SessionIntakeView = dynamic(
  () => import("@/features/sessions/intake/session-intake-view").then((module) => module.SessionIntakeView),
  { loading: SessionFeatureLoading },
);
const SessionTranscriptView = dynamic(
  () => import("@/features/sessions/transcript/session-transcript-view").then((module) => module.SessionTranscriptView),
  { loading: SessionFeatureLoading },
);

type FindingsProps = ComponentProps<typeof SessionFindingsViewComponent>;
type IntakeProps = ComponentProps<typeof SessionIntakeViewComponent>;
type TranscriptProps = ComponentProps<typeof SessionTranscriptViewComponent>;

export type SessionWorkflowViewModel =
  | { view: "findings"; backendUnavailable: boolean; viewProps: FindingsProps }
  | { view: "transcript"; backendUnavailable: boolean; viewProps: TranscriptProps }
  | { view: "intake"; backendUnavailable: boolean; viewProps: IntakeProps };

/** Presentational dispatcher for the non-report Session views. */
export function SessionWorkflowView({ model }: { model: SessionWorkflowViewModel }) {
  return (
    <>
      <BackendAvailabilityBanner unavailable={model.backendUnavailable} />
      {model.view === "findings" ? <SessionFindingsView {...model.viewProps} /> : null}
      {model.view === "transcript" ? <SessionTranscriptView {...model.viewProps} /> : null}
      {model.view === "intake" ? <SessionIntakeView {...model.viewProps} /> : null}
    </>
  );
}

function SessionFeatureLoading() {
  return (
    <div
      className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6 text-sm text-[color:var(--color-text-muted)]"
      role="status"
      aria-live="polite"
    >
      Loading session view…
    </div>
  );
}
