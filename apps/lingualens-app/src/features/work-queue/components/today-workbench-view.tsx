import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { StatusBadge } from "@/components/status-badge";
import {
  todayQueueGroups,
  type TodayWorkbenchModel,
} from "@/features/work-queue/today-workbench-model";

export type TodayWorkbenchViewState =
  | { status: "loading" }
  | { status: "error"; retry: () => void }
  | { status: "ready"; model: TodayWorkbenchModel };

export function TodayWorkbenchView({
  state,
  compactContext,
}: {
  state: TodayWorkbenchViewState;
  compactContext?: React.ReactNode;
}) {
  const backendLabel = state.status === "ready"
    ? "Backend confirmed"
    : state.status === "error"
      ? "Backend unavailable"
      : "Backend verification pending";
  return (
    <div className="space-y-6">
      <header className="workspace-panel flex flex-col gap-4 p-5 sm:p-6 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[color:var(--color-text-muted)]">
            Today <span aria-hidden="true">·</span> <span>{backendLabel}</span>
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)]">Work Queue</h1>
          <p className="mt-2 max-w-[70ch] text-sm leading-6 text-[color:var(--color-text-muted)]">
            One prioritized queue for the next therapist decision. Workflow status is operational and does not imply a clinical conclusion.
          </p>
        </div>
        <ActionButton href="/cases?intent=start-session" className="w-full shrink-0 sm:w-auto">
          Start session
        </ActionButton>
      </header>

      {state.status === "loading" ? <TodayLoadingState /> : null}
      {state.status === "error" ? <TodayErrorState retry={state.retry} /> : null}
      {state.status === "ready" ? <TodayReadyState model={state.model} /> : null}
      {compactContext ? <div className="xl:hidden">{compactContext}</div> : null}
    </div>
  );
}

function TodayLoadingState() {
  return (
    <section className="workspace-panel p-5" role="status" aria-live="polite">
      <p className="font-semibold text-[color:var(--color-text-strong)]">Loading today’s work queue…</p>
      <div className="mt-4 grid gap-3" aria-hidden="true">
        {[0, 1, 2].map((item) => <div key={item} className="h-24 animate-pulse rounded-[var(--radius-panel)] bg-[color:var(--color-surface-muted)] motion-reduce:animate-none" />)}
      </div>
    </section>
  );
}

function TodayErrorState({ retry }: { retry: () => void }) {
  return (
    <section className="workspace-panel border-[color:var(--color-danger-border)] p-5" role="alert">
      <div className="flex items-start gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Today’s queue is unavailable</h2>
          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
            Cases and reports could not be confirmed by the backend. No sample work or success state has been substituted.
          </p>
          <button type="button" onClick={retry} className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm font-semibold text-[color:var(--color-accent-strong)]">
            Retry work queue
          </button>
        </div>
      </div>
    </section>
  );
}

function TodayReadyState({ model }: { model: TodayWorkbenchModel }) {
  if (model.items.length === 0) {
    return (
      <section className="workspace-panel p-6 text-center" aria-live="polite">
        <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">No work requires attention right now.</h2>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">The backend returned no cases or report tasks for this workspace.</p>
      </section>
    );
  }

  return (
    <div data-testid="today-primary-workbench" className="space-y-5">
      <dl className="grid gap-3 sm:grid-cols-3" aria-label="Work queue summary">
        <QueueMetric label="Needs action" value={model.summary.needsAction} />
        <QueueMetric label="Ready for review" value={model.summary.readyForReview} />
        <QueueMetric label="Ready for sign-off" value={model.summary.readyForSignoff} />
      </dl>

      <section className="workspace-panel p-5" aria-labelledby="prioritized-queue-title">
        <div>
            <h2 id="prioritized-queue-title" className="text-xl font-semibold text-[color:var(--color-text-strong)]">Prioritized queue</h2>
            <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">Status grouping stays inside one queue; each row has one next action.</p>
        </div>

        <div className="mt-5 space-y-6">
          {todayQueueGroups.map((group) => {
            const items = model.items.filter((item) => item.group === group.key);
            if (!items.length) return null;
            return (
              <section key={group.key} aria-labelledby={`today-group-${group.key}`}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <h3 id={`today-group-${group.key}`} className="text-base font-semibold text-[color:var(--color-text-strong)]">{group.label}</h3>
                    <p className="mt-1 text-xs leading-5 text-[color:var(--color-text-muted)]">{group.description}</p>
                  </div>
                  <span className="text-xs font-semibold text-[color:var(--color-text-muted)]">{items.length} {items.length === 1 ? "item" : "items"}</span>
                </div>
                <div className="mt-3 grid gap-3">
                  {items.map((item) => <TodayQueueRow key={item.id} item={item} />)}
                </div>
              </section>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function TodayQueueRow({ item }: { item: TodayWorkbenchModel["items"][number] }) {
  return (
    <article data-testid="today-queue-row" className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-semibold text-[color:var(--color-text-strong)]">{item.caseLabel}</h4>
            <StatusBadge status={item.workflowStatus} />
            <span className="text-xs font-semibold text-[color:var(--color-text-muted)]">{item.reviewPriority} priority</span>
          </div>
          <dl className="mt-3 grid gap-x-5 gap-y-2 text-sm sm:grid-cols-[minmax(8rem,0.65fr)_minmax(9rem,0.8fr)_minmax(0,1.8fr)]">
            <QueueDetail label="Session date" value={formatDate(item.sessionDate)} />
            <QueueDetail label="Task" value={item.taskType} />
            <QueueDetail label="Why now" value={item.reason} />
          </dl>
        </div>
        <Link href={item.href} className="inline-flex min-h-11 w-full shrink-0 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-[color:var(--color-accent)] px-4 text-sm font-semibold text-white sm:w-auto">
          {item.actionLabel}
        </Link>
      </div>
    </article>
  );
}

function QueueMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4">
      <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-[color:var(--color-text-muted)]">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold text-[color:var(--color-text-strong)]">{value}</dd>
    </div>
  );
}

function QueueDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold text-[color:var(--color-text-muted)]">{label}</dt>
      <dd className="mt-0.5 [overflow-wrap:anywhere] text-[color:var(--color-text-strong)]">{value}</dd>
    </div>
  );
}

function formatDate(value?: string) {
  if (!value) return "Not scheduled";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? "Unavailable" : parsed.toLocaleDateString();
}
