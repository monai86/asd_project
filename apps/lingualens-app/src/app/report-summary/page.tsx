import { AppShell } from "@/components/app-shell";
import { ReportSummaryClient } from "@/components/report-summary-client";

type ReportSummarySearchParams = {
  case_id?: string;
  session_id?: string;
  transcript_id?: string;
  report_id?: string;
};

export default async function ReportSummaryPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as ReportSummarySearchParams | undefined);

  return (
    <AppShell active="Reports">
      <ReportSummaryClient
        caseId={resolvedSearchParams?.case_id}
        sessionId={resolvedSearchParams?.session_id}
        transcriptId={resolvedSearchParams?.transcript_id}
        reportId={resolvedSearchParams?.report_id}
      />
    </AppShell>
  );
}
