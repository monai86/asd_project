export const runtime = 'edge';

import { AppShell } from "@/components/app-shell";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";

export default function SessionWorkspacePage({
  params,
  searchParams
}: {
  params?: { sessionId?: string };
  searchParams?: { view?: string; mode?: string; case_id?: string; transcript_id?: string; report_id?: string };
}) {
  return (
    <AppShell active="Sessions">
      <SessionWorkspaceClient
        sessionId={params?.sessionId}
        caseId={searchParams?.case_id}
        transcriptId={searchParams?.transcript_id}
        reportId={searchParams?.report_id}
        view={searchParams?.view}
        mode={searchParams?.mode}
      />
    </AppShell>
  );
}
