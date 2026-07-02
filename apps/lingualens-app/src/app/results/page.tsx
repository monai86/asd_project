import { AppShell } from "@/components/app-shell";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";

type ResultsSearchParams = {
  case_id?: string;
  session_id?: string;
  transcript_id?: string;
  report_id?: string;
};

export default async function ResultsPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as ResultsSearchParams | undefined);

  return (
    <AppShell active="Sessions">
      <SessionWorkspaceClient
        sessionId={resolvedSearchParams?.session_id}
        caseId={resolvedSearchParams?.case_id}
        transcriptId={resolvedSearchParams?.transcript_id}
        reportId={resolvedSearchParams?.report_id}
        view="results"
      />
    </AppShell>
  );
}
