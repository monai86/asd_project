import { AppShell } from "@/components/app-shell";
import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

export default function CasesPage() {
  return (
    <AppShell active="Cases">
      <CasesWorkspaceClient />
    </AppShell>
  );
}
