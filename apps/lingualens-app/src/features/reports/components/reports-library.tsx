import Link from "next/link";
import { ExternalLink, FileText, Lock, RefreshCw, ShieldCheck } from "lucide-react";

import { WorkspacePanel } from "@/components/workbench-ui";
import { StatusBadge } from "@/components/status-badge";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import type { BackendReport } from "@/lib/workflow";

type ReportGroup = {
  key: "review" | "regenerate" | "signed";
  title: string;
  description: string;
  reports: BackendReport[];
  icon: typeof FileText;
};

export function ReportsLibrary({ reports }: { reports: BackendReport[] }) {
  const groups: ReportGroup[] = [
    {
      key: "review",
      title: "Needs review",
      description: "Editable drafts and blocked drafts that require therapist action.",
      reports: reports.filter((report) => !isSignedReport(report) && !isStaleReport(report)),
      icon: FileText,
    },
    {
      key: "regenerate",
      title: "Needs regeneration",
      description: "Drafts invalidated by a newer transcript. Regenerate them in Session Workspace.",
      reports: reports.filter(isStaleReport),
      icon: RefreshCw,
    },
    {
      key: "signed",
      title: "Signed reports",
      description: "Immutable signed snapshots available for review and gated export.",
      reports: reports.filter(isSignedReport),
      icon: Lock,
    },
  ];

  return (
    <div className="space-y-5" aria-label="Reports Library">
      <WorkspacePanel className="p-5">
        <h2 className="text-lg font-bold text-ink">Library status</h2>
        <dl className="mt-4 grid gap-3 sm:grid-cols-3">
          <LibraryMetric label="Needs review" value={groups[0].reports.length} />
          <LibraryMetric label="Needs regeneration" value={groups[1].reports.length} />
          <LibraryMetric label="Signed" value={groups[2].reports.length} />
        </dl>
        <p className="mt-4 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-950">
          Status counts describe workflow progress only. They are not clinical outcome scores.
        </p>
      </WorkspacePanel>

      {groups.map((group) => {
        const Icon = group.icon;
        return (
          <section key={group.key} aria-labelledby={`report-group-${group.key}`} className="workspace-panel min-w-0 p-5">
            <div className="flex items-start gap-3">
              <Icon className="mt-0.5 shrink-0 text-clinical" size={22} aria-hidden="true" />
              <div>
                <h2 id={`report-group-${group.key}`} className="text-xl font-bold text-ink">{group.title}</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">{group.description}</p>
              </div>
            </div>

            {group.reports.length ? (
              <ul className="mt-4 grid min-w-0 gap-3 lg:grid-cols-2">
                {group.reports.map((report) => (
                  <li className="min-w-0" key={report.report_id ?? `${report.session_id}-${report.title}`}>
                    <ReportLibraryRow report={report} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 rounded-[var(--radius-panel)] border border-dashed border-line bg-[color:var(--color-surface-muted)] p-4 text-sm text-slate-600">
                No reports in this group.
              </p>
            )}
          </section>
        );
      })}
    </div>
  );
}

function ReportLibraryRow({ report }: { report: BackendReport }) {
  const href = reportHref(report);
  const actionLabel = reportActionLabel(report);
  const signed = isSignedReport(report);
  const stale = isStaleReport(report);
  return (
    <article data-testid="report-library-row" className="h-full min-w-0 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate font-bold text-ink">{report.title ?? report.report_type ?? report.report_id ?? "Untitled report"}</h3>
          <p className="mt-1 [overflow-wrap:anywhere] text-xs text-slate-600">
            Case {report.case_id ?? "Unavailable"} · Session {report.session_id ?? "Unavailable"}
          </p>
        </div>
        <StatusBadge status={signed ? "Signed Off" : stale ? "Stale" : report.status ?? "Draft"} />
      </div>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold text-slate-500">Updated</dt>
          <dd className="mt-1 [overflow-wrap:anywhere] text-slate-700">{formatDate(report.updated_at)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold text-slate-500">Report version</dt>
          <dd className="mt-1 [overflow-wrap:anywhere] text-slate-700">{report.version == null ? "Unavailable" : `Version ${report.version}`}</dd>
        </div>
      </dl>
      <Link
        href={href}
        className="mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-card)] bg-clinical px-4 text-sm font-semibold text-white"
      >
        {actionLabel}
        <ExternalLink size={16} aria-hidden="true" />
      </Link>
    </article>
  );
}

function LibraryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-muted)] p-3">
      <dt className="text-xs font-semibold text-slate-500">{label}</dt>
      <dd className="mt-1 flex items-center gap-2 text-xl font-bold text-ink">
        {label === "Signed" ? <ShieldCheck size={18} aria-hidden="true" /> : null}
        {value}
      </dd>
    </div>
  );
}

function isSignedReport(report: BackendReport) {
  const status = `${report.status ?? ""} ${report.therapist_signoff_status ?? ""}`.toLowerCase();
  return status.includes("signed") || status.includes("final");
}

function isStaleReport(report: BackendReport) {
  return `${report.status ?? ""}`.trim().toLowerCase() === "stale";
}

function reportHref(report: BackendReport) {
  return resolveSessionHref("report", report.session_id?.trim(), {
    caseId: report.case_id,
    reportId: report.report_id,
  });
}

function reportActionLabel(report: BackendReport) {
  if (!report.session_id?.trim()) return "Find session";
  if (isSignedReport(report)) return "View signed report";
  if (isStaleReport(report)) return "Regenerate report";
  if (`${report.status ?? ""}`.toLowerCase().includes("failed")) return "Review blocked report";
  return "Review draft";
}

function formatDate(value?: string) {
  if (!value) return "Unavailable";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Unavailable" : date.toLocaleDateString();
}
