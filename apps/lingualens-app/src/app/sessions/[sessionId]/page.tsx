import { AppShell } from "@/components/app-shell";
import { ReportSummaryClient } from "@/components/report-summary-client";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";
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
    <AppShell active="Sessions">
      {view === "report" ? (
        <ReportSummaryClient
          sessionId={resolvedParams?.sessionId}
          caseId={resolvedSearchParams?.case_id}
          transcriptId={resolvedSearchParams?.transcript_id}
          reportId={resolvedSearchParams?.report_id}
        />
      ) : (
        <SessionWorkspaceClient
          sessionId={resolvedParams?.sessionId}
          caseId={resolvedSearchParams?.case_id}
          transcriptId={resolvedSearchParams?.transcript_id}
          reportId={resolvedSearchParams?.report_id}
          view={view === "intake" ? "record" : view === "findings" ? "results" : view}
          mode={resolvedSearchParams?.mode}
        />
      )}
    </AppShell>
  );
}
