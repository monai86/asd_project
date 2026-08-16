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
  return (
    <div className="space-y-6">
      <header className="workspace-panel flex flex-col gap-4 p-5 sm:p-6 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)]">Work Queue</h1>
          <p className="mt-2 max-w-[70ch] text-sm leading-6 text-[color:var(--color-text-muted)]">
            What needs your decision next, in one prioritized list. Queue status is operational, not a clinical conclusion.
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
          <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">We couldn’t load your work queue</h2>
          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
            Check your connection and try again.
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
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">Start a session or review a case when you’re ready.</p>
        <ActionButton href="/cases?intent=start-session" className="mt-5">
          Start a session
        </ActionButton>
      </section>
    );
  }

  return (
    <div data-testid="today-primary-workbench" className="space-y-5">
      <dl
        className="flex snap-x snap-proximity gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-3 sm:gap-3 sm:overflow-visible sm:pb-0"
        aria-label="Work queue summary"
      >
        <QueueMetric label="Needs action" value={model.summary.needsAction} />
        <QueueMetric label="Ready for review" value={model.summary.readyForReview} />
        <QueueMetric label="Ready for sign-off" value={model.summary.readyForSignoff} />
      </dl>

      <section className="workspace-panel overflow-hidden" aria-labelledby="prioritized-queue-title">
        <div className="px-4 py-3 sm:px-5">
          <h2 id="prioritized-queue-title" className="text-xl font-semibold text-[color:var(--color-text-strong)]">Prioritized queue</h2>
        </div>

        <div className="border-t border-[color:var(--color-border)]">
          {todayQueueGroups.map((group) => {
            const items = model.items.filter((item) => item.group === group.key);
            if (!items.length) return null;
            return (
              <section
                key={group.key}
                aria-labelledby={`today-group-${group.key}`}
                className="border-b border-[color:var(--color-border)] last:border-b-0"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2 bg-[color:var(--color-surface-strong)] px-4 py-2.5 sm:px-5">
                  <div>
                    <h3 id={`today-group-${group.key}`} className="text-base font-semibold text-[color:var(--color-text-strong)]">{group.label}</h3>
                    <p className="mt-0.5 hidden text-xs leading-5 text-[color:var(--color-text-muted)] sm:block">{group.description}</p>
                  </div>
                  <span className="text-xs font-semibold text-[color:var(--color-text-muted)]">{items.length} {items.length === 1 ? "item" : "items"}</span>
                </div>
                <div className="grid gap-3 p-3 sm:grid-cols-2 sm:p-4 lg:grid-cols-1 lg:gap-0 lg:p-0 lg:divide-y lg:divide-[color:var(--color-border)]">
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
    <article
      data-testid="today-queue-row"
      className="flex flex-col gap-3 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 sm:px-5 lg:flex-row lg:items-center lg:gap-4 lg:rounded-none lg:border-0 lg:bg-transparent lg:px-4 lg:py-3"
    >
      <div className="min-w-0 lg:w-48">
        <h4 className="truncate font-semibold text-[color:var(--color-text-strong)]">{item.caseLabel}</h4>
        <p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">{formatDate(item.sessionDate)}</p>
      </div>
      <div className="min-w-0 lg:w-56">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={item.workflowStatus} />
          <span className="text-xs font-medium text-[color:var(--color-text-muted)]">{item.reviewPriority}</span>
        </div>
        <p className="mt-1 truncate text-sm text-[color:var(--color-text-strong)]">{item.taskType}</p>
      </div>
      <p className="min-w-0 flex-1 text-sm leading-5 text-[color:var(--color-text-strong)] lg:line-clamp-2">{item.reason}</p>
      <Link
        href={item.href}
        className="inline-flex min-h-11 w-full shrink-0 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-[color:var(--color-accent)] px-4 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)] lg:w-auto"
      >
        {item.actionLabel}
      </Link>
    </article>
  );
}

function QueueMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-0 flex-1 snap-start rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-3 sm:min-w-0 sm:flex-none sm:p-4">
      <dt className="text-[10px] font-semibold uppercase leading-4 tracking-[0.04em] text-[color:var(--color-text-muted)] sm:text-xs sm:tracking-[0.06em]">{label}</dt>
      <dd className="mt-1 text-xl font-semibold text-[color:var(--color-text-strong)] sm:text-2xl">{value}</dd>
    </div>
  );
}

function formatDate(value?: string) {
  if (!value) return "Not scheduled";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? "Unavailable" : parsed.toLocaleDateString();
}
