"use client";

import { CaseDetail } from "@/features/cases/components/case-detail";
import { CaseList } from "@/features/cases/components/case-list";
import { useCasesWorkspace } from "@/features/cases/hooks/use-cases-workspace";

type CasesWorkspaceClientProps = {
  caseId?: string;
};

export function CasesWorkspaceClient({ caseId }: CasesWorkspaceClientProps) {
  const model = useCasesWorkspace(caseId);

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

  return <CaseList model={model.list} />;
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
