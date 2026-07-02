import { AppShell } from "@/components/app-shell";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";

type RecordSearchParams = {
  mode?: string;
  case_id?: string;
  session_id?: string;
  transcript_id?: string;
};

export default async function RecordPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as RecordSearchParams | undefined);

  return (
    <AppShell active="Sessions">
      <SessionWorkspaceClient
        sessionId={resolvedSearchParams?.session_id}
        caseId={resolvedSearchParams?.case_id}
        transcriptId={resolvedSearchParams?.transcript_id}
        view="record"
        mode={resolvedSearchParams?.mode}
      />
    </AppShell>
  );
}
