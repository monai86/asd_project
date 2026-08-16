import Link from "next/link";

import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageHeader } from "@/components/page-header";
import {
  resolveSessionHref,
  sessionViews,
  type SessionView,
} from "@/features/sessions/state/session-view";

export type SessionDataMode = "backend" | "local_draft" | "unavailable";

export type SessionContext = {
  sessionId?: string;
  caseId?: string;
  caseLabel?: string;
  sourceLabel?: string;
  consentStatus?: string;
  workflowStatus?: string;
  dataMode: SessionDataMode;
  activeView: SessionView;
};

export type SessionContextHeaderProps = {
  title: string;
  description: string;
  meta?: string[];
  context: SessionContext;
  density?: "default" | "compact";
};

const viewLabels: Record<SessionView, string> = {
  intake: "Intake",
  transcript: "Transcript",
  findings: "Findings",
  report: "Report",
};

const modeLabels: Record<SessionDataMode, string> = {
  backend: "Connected",
  local_draft: "Offline draft",
  unavailable: "Offline",
};

function displayValue(value?: string): string {
  return value?.trim() || "Unavailable";
}

function consentLabel(value?: string): string {
  return value?.trim() ? `Consent ${value.trim().toLowerCase()}` : "Unavailable";
}

export function SessionContextHeader({
  title,
  description,
  meta,
  context,
  density = "default",
}: SessionContextHeaderProps) {
  const details = [
    { label: "Case", value: displayValue(context.caseLabel) },
    { label: "Session", value: displayValue(context.sessionId) },
    { label: "Source", value: displayValue(context.sourceLabel) },
    { label: "Consent", value: consentLabel(context.consentStatus) },
    { label: "Status", value: displayValue(context.workflowStatus) },
    { label: "Connection", value: modeLabels[context.dataMode] },
  ];

  const breadcrumbs = [
    { label: "Cases", href: "/cases" },
    ...(context.caseLabel
      ? [{ label: context.caseLabel, href: context.caseId ? `/cases/${encodeURIComponent(context.caseId)}` : undefined }]
      : []),
    { label: viewLabels[context.activeView] },
  ];

  if (density === "compact") {
    return (
      <section aria-label="Session context" data-density="compact">
        <Breadcrumbs items={breadcrumbs} />
        <div className="grid gap-2 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 py-2 sm:gap-3 sm:px-4 sm:py-3 xl:grid-cols-[minmax(14rem,0.7fr)_minmax(0,1.3fr)] xl:items-center">
          <div className="min-w-0">
            <h1 className="text-lg font-semibold leading-tight text-[color:var(--color-text-strong)] sm:text-xl">{title}</h1>
            <p className="sr-only mt-1 text-sm leading-5 text-[color:var(--color-text-muted)] sm:not-sr-only sm:block">{description}</p>
          </div>
          <dl className="hidden min-w-0 gap-x-4 gap-y-2 md:grid md:grid-cols-2 lg:grid-cols-3 xl:flex xl:flex-wrap xl:justify-end">
            {details.map((detail) => (
              <div key={detail.label} className="min-w-0 text-sm">
                <dt className="inline text-xs font-semibold uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">
                  {detail.label}
                  <span aria-hidden="true"> · </span>
                </dt>
                <dd className="inline break-words font-medium text-[color:var(--color-text-strong)]">{detail.value}</dd>
              </div>
            ))}
          </dl>
          <details className="responsive-details min-w-0 rounded-[var(--radius-card)] border border-[color:var(--color-border)] md:hidden">
            <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-3 py-2 marker:content-none">
              <span className="flex min-w-0 items-baseline gap-1 overflow-hidden text-sm font-medium text-[color:var(--color-text-strong)]">
                <span className="shrink-0 text-xs font-semibold uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Case</span>
                <span className="min-w-0 truncate">{displayValue(context.caseLabel)}</span>
              </span>
              <span className="shrink-0 text-xs font-semibold text-[color:var(--color-accent-strong)]">Details</span>
            </summary>
            <dl className="grid grid-cols-2 gap-3 border-t border-[color:var(--color-border)] p-3">
              {details.map((detail) => (
                <div key={detail.label} className="min-w-0 text-sm">
                  <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">{detail.label}</dt>
                  <dd className="mt-0.5 break-words font-medium text-[color:var(--color-text-strong)]">{detail.value}</dd>
                </div>
              ))}
            </dl>
          </details>
        </div>
        <SessionViewNavigation context={context} compact />
      </section>
    );
  }

  return (
    <section aria-label="Session context" className="space-y-4" data-density="default">
      <Breadcrumbs items={breadcrumbs} />
      <PageHeader title={title} description={description} meta={meta} />
      <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 sm:p-5">
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {details.map((detail) => (
            <div key={detail.label} className="min-w-0">
              <dt className="text-xs font-semibold uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">
                {detail.label}
              </dt>
              <dd className="mt-1 break-words text-sm font-medium leading-5 text-[color:var(--color-text-strong)]">
                {detail.value}
              </dd>
            </div>
          ))}
        </dl>
        <SessionViewNavigation context={context} />
      </div>
    </section>
  );
}

function SessionViewNavigation({ context, compact = false }: { context: SessionContext; compact?: boolean }) {
  return (
    <nav
      aria-label="Session views"
      className={`${compact ? "border-t px-2 py-1" : "mt-4 border-t pt-4"} grid grid-cols-4 gap-1 border-[color:var(--color-border)] sm:flex sm:gap-2`}
    >
      {sessionViews.map((view) => {
        const active = view === context.activeView;
        return (
          <Link
            key={view}
            href={resolveSessionHref(view, context.sessionId)}
            aria-current={active ? "page" : undefined}
            className={`inline-flex min-h-11 min-w-0 items-center justify-center rounded-[var(--radius-card)] px-2 text-sm font-semibold transition-colors motion-reduce:transition-none sm:px-4 ${
              active
                ? "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
                : compact
                  ? "text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text-strong)]"
                  : "border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-strong)]"
            }`}
          >
            {viewLabels[view]}
          </Link>
        );
      })}
    </nav>
  );
}
