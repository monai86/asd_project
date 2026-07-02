import { AppShell } from "@/components/app-shell";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";

type ReviewTranscriptSearchParams = {
  case_id?: string;
  session_id?: string;
  transcript_id?: string;
};

export default async function ReviewTranscriptPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as ReviewTranscriptSearchParams | undefined);

  return (
    <AppShell active="Sessions">
      <SessionWorkspaceClient
        sessionId={resolvedSearchParams?.session_id}
        caseId={resolvedSearchParams?.case_id}
        transcriptId={resolvedSearchParams?.transcript_id}
        view="transcript"
      />
    </AppShell>
  );
}
