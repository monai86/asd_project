import { AppShell } from "@/components/app-shell";
import { ReportSummaryClient } from "@/components/report-summary-client";

export default function ReportSummaryPage({ searchParams }: {
  searchParams?: { case_id?: string; session_id?: string; transcript_id?: string; report_id?: string };
}) {
  return (
    <AppShell active="Reports">
      <ReportSummaryClient
        caseId={searchParams?.case_id}
        sessionId={searchParams?.session_id}
        transcriptId={searchParams?.transcript_id}
        reportId={searchParams?.report_id}
      />
    </AppShell>
  );
}
