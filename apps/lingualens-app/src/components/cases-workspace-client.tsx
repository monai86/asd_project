"use client";

import { CaseDetail } from "@/features/cases/components/case-detail";
import { CaseList } from "@/features/cases/components/case-list";
import { StartSessionSelector } from "@/features/cases/components/start-session-selector";
import { useCasesWorkspace } from "@/features/cases/hooks/use-cases-workspace";
import { useConfirmedRuntimeSettings } from "@/lib/confirmed-runtime-settings";
import { useMockAccessSession } from "@/lib/use-mock-access-session";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

type CasesWorkspaceClientProps = {
  caseId?: string;
  intent?: "start-session";
  preselectedCaseId?: string;
};

export function CasesWorkspaceClient({ caseId, intent, preselectedCaseId }: CasesWorkspaceClientProps) {
  const model = useCasesWorkspace(caseId);
  const runtimeSettings = useConfirmedRuntimeSettings();
  const mockSession = useMockAccessSession();
  const supabaseSession = useSupabaseAccessSession();
  const confirmedRole = runtimeSettings?.auth_mode === "mock"
    ? mockSession?.role
    : runtimeSettings?.auth_mode === "supabase"
      && supabaseSession?.stage === "authenticated"
      && supabaseSession.aal === "aal2"
      ? supabaseSession.role
      : undefined;
  const canFilterByClinician = confirmedRole === "org_admin" || confirmedRole === "clinical_supervisor";
  const canCreateCase = confirmedRole === "therapist";

  if (model.status === "loading") {
    return <CaseListSkeleton />;
  }

  if (model.status === "unavailable") {
    return (
      <section className="workspace-panel p-5" role="alert">
        <h1 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Cases are unavailable</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          The backend cases service could not be reached. Try again when the service is available.
        </p>
      </section>
    );
  }

  if (model.status === "error") {
    return (
      <section className="workspace-panel p-5" role="alert">
        <h1 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Case could not be loaded</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          The requested backend case was not returned. Check the case link or try again.
        </p>
      </section>
    );
  }

  if (model.status === "detail") {
    return <CaseDetail key={model.detail.caseItem.case_id} model={model.detail} />;
  }

  if (intent === "start-session") {
    return <StartSessionSelector cases={model.list.cases} preselectedCaseId={preselectedCaseId} />;
  }

  return <CaseList model={model.list} canFilterByClinician={canFilterByClinician} canCreateCase={canCreateCase} />;
}

function CaseListSkeleton() {
  return (
    <section className="workspace-panel p-4">
      <div className="space-y-3 animate-pulse motion-reduce:animate-none">
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
      </div>
    </section>
  );
}
