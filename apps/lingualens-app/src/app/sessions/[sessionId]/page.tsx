import { AppShell } from "@/components/app-shell";
import { SessionWorkspace } from "@/features/sessions/components/session-workspace";
import { resolveSessionView } from "@/features/sessions/state/session-view";

type SessionWorkspaceParams = { sessionId?: string };
type SessionWorkspaceSearchParams = {
  view?: string;
  mode?: string;
  case_id?: string;
  transcript_id?: string;
  report_id?: string;
};

export default async function SessionWorkspacePage({
  params,
  searchParams
}: {
  params?: any;
  searchParams?: any;
}) {
  const resolvedParams = await Promise.resolve(params as SessionWorkspaceParams | undefined);
  const resolvedSearchParams = await Promise.resolve(searchParams as SessionWorkspaceSearchParams | undefined);
  const view = resolveSessionView(resolvedSearchParams?.view);

  return (
    <AppShell active="Session" activeSessionId={resolvedParams?.sessionId}>
      <SessionWorkspace
        sessionId={resolvedParams?.sessionId}
        caseId={resolvedSearchParams?.case_id}
        transcriptId={resolvedSearchParams?.transcript_id}
        reportId={resolvedSearchParams?.report_id}
        view={view}
        mode={resolvedSearchParams?.mode}
      />
    </AppShell>
  );
}
