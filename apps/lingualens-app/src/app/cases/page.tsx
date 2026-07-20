import { AppShell } from "@/components/app-shell";
import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

type CasesPageProps = {
  searchParams?: Promise<{ intent?: string | string[] }>;
};

export default async function CasesPage({ searchParams }: CasesPageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const intent = resolvedSearchParams?.intent === "start-session" ? "start-session" : undefined;

  return (
    <AppShell active="Cases">
      <CasesWorkspaceClient intent={intent} />
    </AppShell>
  );
}
