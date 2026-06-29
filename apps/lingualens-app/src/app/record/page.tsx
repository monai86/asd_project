export const runtime = 'edge';

import { AppShell } from "@/components/app-shell";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";

export default function RecordPage({ searchParams }: {
  searchParams?: { mode?: string; case_id?: string; session_id?: string; transcript_id?: string };
}) {
  return (
    <AppShell active="Sessions">
      <SessionWorkspaceClient
        sessionId={searchParams?.session_id}
        caseId={searchParams?.case_id}
        transcriptId={searchParams?.transcript_id}
        view="record"
        mode={searchParams?.mode}
      />
    </AppShell>
  );
}
