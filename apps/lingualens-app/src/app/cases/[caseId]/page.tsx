import { AppShell } from "@/components/app-shell";
import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

export default async function CaseDetailPage({ params }: { params: any }) {
  const { caseId } = await Promise.resolve(params as { caseId: string });

  return (
    <AppShell active="Cases">
      <CasesWorkspaceClient caseId={caseId} />
    </AppShell>
  );
}
