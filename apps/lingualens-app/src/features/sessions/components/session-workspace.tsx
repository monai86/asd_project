"use client";

import { SessionWorkflowWorkspace } from "@/features/sessions/components/session-workspace-model";
import { SessionReportView } from "@/features/sessions/report/session-report-view";
import type { SessionView } from "@/features/sessions/state/session-view";

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

export { resolveWorkspaceFeature } from "@/features/sessions/components/session-workspace-model";
