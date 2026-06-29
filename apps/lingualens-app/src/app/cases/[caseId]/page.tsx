import { AppShell } from "@/components/app-shell";
import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  return (
    <AppShell active="Cases">
      <CasesWorkspaceClient caseId={params.caseId} />
    </AppShell>
  );
}
