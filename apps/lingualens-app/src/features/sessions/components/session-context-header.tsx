import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import {
  resolveSessionHref,
  sessionViews,
  type SessionView,
} from "@/features/sessions/state/session-view";

export type SessionDataMode = "backend" | "local_draft" | "unavailable";

export type SessionContext = {
  sessionId?: string;
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
};

const viewLabels: Record<SessionView, string> = {
  intake: "Intake",
  transcript: "Transcript",
  findings: "Findings",
  report: "Report",
};

const modeLabels: Record<SessionDataMode, string> = {
  backend: "Backend mode",
  local_draft: "Local draft mode",
  unavailable: "Unavailable mode",
};

function displayValue(value?: string): string {
  return value?.trim() || "Unavailable";
}

function consentLabel(value?: string): string {
  return value?.trim() ? `Consent ${value.trim().toLowerCase()}` : "Unavailable";
}

export function SessionContextHeader({ title, description, meta, context }: SessionContextHeaderProps) {
  const details = [
    { label: "Case", value: displayValue(context.caseLabel) },
    { label: "Session", value: displayValue(context.sessionId) },
    { label: "Source", value: displayValue(context.sourceLabel) },
    { label: "Consent", value: consentLabel(context.consentStatus) },
    { label: "Status", value: displayValue(context.workflowStatus) },
    { label: "Data mode", value: modeLabels[context.dataMode] },
  ];

  return (
    <section aria-label="Session context" className="space-y-4">
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
        <nav aria-label="Session views" className="mt-4 grid grid-cols-4 gap-1 border-t border-[color:var(--color-border)] pt-4 sm:flex sm:gap-2">
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
                    : "border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-strong)]"
                }`}
              >
                {viewLabels[view]}
              </Link>
            );
          })}
        </nav>
      </div>
    </section>
  );
}
