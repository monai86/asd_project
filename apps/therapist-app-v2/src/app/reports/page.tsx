import { AppShell } from "@/components/app-shell";
import { ReportSummaryClient } from "@/components/report-summary-client";

export default function ReportsPage() {
  return (
    <AppShell active="Reports">
      <ReportSummaryClient />
    </AppShell>
  );
}
