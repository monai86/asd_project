import { AppShell } from "@/components/app-shell";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";

export default function ResultsPage({ searchParams }: {
  searchParams?: { case_id?: string; session_id?: string; transcript_id?: string; report_id?: string };
}) {
  return (
    <AppShell active="Sessions">
      <SessionWorkspaceClient
        sessionId={searchParams?.session_id}
        caseId={searchParams?.case_id}
        transcriptId={searchParams?.transcript_id}
        reportId={searchParams?.report_id}
        view="results"
      />
    </AppShell>
  );
}
