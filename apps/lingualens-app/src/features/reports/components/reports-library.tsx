import Link from "next/link";
import { ExternalLink, FileText, Lock, RefreshCw, ShieldCheck } from "lucide-react";

import { DataTable } from "@/components/data-table";
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
              <>
                <div className="mt-4 hidden xl:block">
                  <DataTable
                    caption={`${group.title} reports`}
                    rowTestId="report-library-row"
                    columns={[
                      { key: "report", header: "Report" },
                      { key: "updated", header: "Updated" },
                      { key: "version", header: "Version" },
                      { key: "status", header: "Status" },
                      { key: "action", header: "Action" }
                    ]}
                    rows={group.reports.map((report) => {
                      const signed = isSignedReport(report);
                      const stale = isStaleReport(report);
                      return {
                        id: report.report_id ?? `${report.session_id}-${report.title}`,
                        report: (
                          <div className="min-w-0">
                            <p className="truncate font-medium text-[color:var(--color-text-strong)]">
                              {report.title ?? report.report_type ?? report.report_id ?? "Untitled report"}
                            </p>
                            <p className="mt-0.5 truncate text-xs text-[color:var(--color-text-muted)]">
                              Case {report.case_id ?? "Unavailable"} · Session {report.session_id ?? "Unavailable"}
                            </p>
                          </div>
                        ),
                        updated: formatDate(report.updated_at),
                        version: report.version == null ? "Unavailable" : `Version ${report.version}`,
                        status: <StatusBadge status={signed ? "Signed Off" : stale ? "Stale" : report.status ?? "Draft"} />,
                        action: <ReportActionLink report={report} />,
                      };
                    })}
                  />
                </div>
                <ul className="mt-4 space-y-0 xl:hidden" aria-label={group.title}>
                  {group.reports.map((report) => (
                    <li key={report.report_id ?? `${report.session_id}-${report.title}`} data-testid="report-library-row" className="border-b border-[color:var(--color-border)] py-3 last:border-b-0">
                      <ReportLibraryMobileRow report={report} />
                    </li>
                  ))}
                </ul>
              </>
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

function ReportActionLink({ report }: { report: BackendReport }) {
  return (
    <Link
      href={reportHref(report)}
      className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border)] px-4 py-2 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-accent-strong)] hover:bg-[color:var(--color-accent-soft)] hover:text-[color:var(--color-accent-strong)]"
    >
      {reportActionLabel(report)}
      <ExternalLink size={16} aria-hidden="true" />
    </Link>
  );
}

function ReportLibraryMobileRow({ report }: { report: BackendReport }) {
  const signed = isSignedReport(report);
  const stale = isStaleReport(report);
  return (
    <div className="flex items-center gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="min-w-0 truncate font-semibold text-[color:var(--color-text-strong)]">
            {report.title ?? report.report_type ?? report.report_id ?? "Untitled report"}
          </h3>
          <StatusBadge status={signed ? "Signed Off" : stale ? "Stale" : report.status ?? "Draft"} />
        </div>
        <p className="mt-0.5 truncate text-xs text-[color:var(--color-text-muted)]">
          Case {report.case_id ?? "Unavailable"} · {formatDate(report.updated_at)}
          {report.version == null ? "" : ` · Version ${report.version}`}
        </p>
      </div>
      <ReportActionLink report={report} />
    </div>
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
