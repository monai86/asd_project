"use client";

import dynamic from "next/dynamic";
import { resolveWorkspaceFeature, type SessionView } from "@/features/sessions/state/session-view";
import { SessionWorkflowWorkspace } from "@/features/sessions/components/session-workspace-model";

const SessionReportView = dynamic(
  () => import("@/features/sessions/report/session-report-view").then((module) => module.SessionReportView),
  { loading: SessionWorkspaceLoading },
);

export type SessionWorkspaceProps = {
  sessionId?: string;
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
  view?: SessionView;
  mode?: string;
};

export function SessionWorkspace({ view = "intake", ...props }: SessionWorkspaceProps) {
  if (view === "report") {
    return <SessionReportView {...props} />;
  }
  return <SessionWorkflowWorkspace {...props} view={view} />;
}

function SessionWorkspaceLoading() {
  return (
    <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6 text-sm text-[color:var(--color-text-muted)]" role="status" aria-live="polite">
      Loading session workspace…
    </div>
  );
}

export { resolveWorkspaceFeature };
