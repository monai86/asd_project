import { AppShell } from "@/components/app-shell";
import { ReportsWorkspaceClient } from "@/components/reports-workspace-client";

export default function ReportsPage() {
  return (
    <AppShell active="Reports">
      <ReportsWorkspaceClient />
    </AppShell>
  );
}
