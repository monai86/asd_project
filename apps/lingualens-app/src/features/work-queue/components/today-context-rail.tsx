import Link from "next/link";

import type { TodayWorkbenchViewState } from "@/features/work-queue/components/today-workbench-view";

export function TodayContextRail({ state, titleId }: { state: TodayWorkbenchViewState; titleId: string }) {
  return (
    <section className="workspace-panel p-4" aria-labelledby={titleId}>
      <div>
        <h2 id={titleId} className="text-base font-semibold text-[color:var(--color-text-strong)]">Today context</h2>
      </div>
      <p className="mt-3 text-sm leading-6 text-[color:var(--color-text-muted)]">
        Decision-support only. Therapist review and sign-off remain required.
      </p>

      {state.status === "loading" ? <p className="mt-4 text-sm text-[color:var(--color-text-muted)]">Recent cases will appear after backend confirmation.</p> : null}
      {state.status === "error" ? <p className="mt-4 rounded-[var(--radius-card)] border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]">Backend status: unavailable</p> : null}
      {state.status === "ready" ? (
        <div className="mt-5">
          <h3 className="text-sm font-semibold text-[color:var(--color-text-strong)]">Recent cases</h3>
          {state.model.recentCases.length ? (
            <ul className="mt-2 divide-y divide-[color:var(--color-border)]">
              {state.model.recentCases.map((caseItem) => (
                <li key={caseItem.caseId}>
                  <Link href={`/cases/${encodeURIComponent(caseItem.caseId)}`} className="flex min-h-11 items-center justify-between gap-3 py-3 text-sm">
                    <span className="min-w-0">
                      <span className="block font-semibold text-[color:var(--color-text-strong)]">{caseItem.caseLabel}</span>
                      <span className="block text-xs text-[color:var(--color-text-muted)]">{caseItem.workflowStatus}</span>
                    </span>
                    <span aria-hidden="true" className="shrink-0 text-[color:var(--color-accent)]">→</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">No recent cases were returned.</p>}
        </div>
      ) : null}
    </section>
  );
}
