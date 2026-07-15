"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ExternalLink, FileText, Lock, Send, TrendingUp } from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { GlassCard, SafetyNote } from "@/components/liquid-ui";
import { StatusBadge } from "@/components/status-badge";
import { listBackendReports, type BackendReport } from "@/lib/workflow";
import { resolveSessionHref } from "@/features/sessions/state/session-view";

export function ReportsWorkspaceClient() {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const [reports, setReports] = useState<BackendReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"drafts" | "signed" | "progress">("drafts");
  const [selectedReportId, setSelectedReportId] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const loaded = await listBackendReports();
        if (cancelled) return;
        setReports(loaded);
        setBackendUnavailable(false);
      } catch {
        if (cancelled) return;
        setBackendUnavailable(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setBackendUnavailable]);

  const signedReports = useMemo(() => reports.filter(isSignedReport), [reports]);
  const draftReports = useMemo(() => reports.filter((report) => !isSignedReport(report)), [reports]);
  const visibleReports = activeTab === "drafts" ? draftReports : activeTab === "signed" ? signedReports : reports;
  const selectedReport = visibleReports.find((report) => report.report_id === selectedReportId) ?? visibleReports[0] ?? reports[0];
  const selectedHref = selectedReport ? reportHref(selectedReport) : "/cases?intent=start-session";
  const selectedActionLabel = reportActionLabel(selectedReport);
  const completion = calculateCompletion(selectedReport);
  const progressRows = [
    { label: "Transcript reviewed", value: selectedReport ? 100 : 0 },
    { label: "Draft prepared", value: selectedReport?.markdown || selectedReport?.content_markdown ? 100 : selectedReport ? 70 : 0 },
    { label: "Safety validation", value: selectedReport?.safety_validation_result?.status === "failed" ? 35 : selectedReport ? 85 : 0 },
    { label: "Sign-off", value: isSignedReport(selectedReport) ? 100 : 45 }
  ];

  return (
    <div className="space-y-5">
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <header className="workspace-panel flex flex-col gap-4 p-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-ink">Reports</h1>
          <p className="mt-2 max-w-[70ch] text-[color:var(--color-text-muted)]">
            Review persisted therapist-editable drafts, finalized reports, and progress tracking from the active API workspace.
          </p>
        </div>
        <Link href="/record" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 text-sm font-semibold text-clinical">
          New session
          <ExternalLink size={16} aria-hidden="true" />
        </Link>
      </header>

      {loading && !backendUnavailable ? (
        <GlassCard className="p-5">
          <p className="text-slate-600">Loading persisted reports...</p>
        </GlassCard>
      ) : null}

      {!loading && !backendUnavailable && reports.length === 0 ? (
        <GlassCard className="p-5">
          <p className="font-semibold text-ink">No persisted reports yet.</p>
          <p className="mt-2 text-sm text-slate-600">Create or open a session, review the transcript, and generate a draft report from the session workspace.</p>
          <Link href="/record" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-clinical">
            Go to session workspace
            <ExternalLink size={16} aria-hidden="true" />
          </Link>
        </GlassCard>
      ) : null}

      {!loading && !backendUnavailable && reports.length > 0 ? (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_var(--rail-width)]">
          <div className="space-y-5">
            <GlassCard className="p-3">
              <div className="grid gap-2 sm:grid-cols-3" role="tablist" aria-label="Report workspace sections">
                <ReportTab
                  active={activeTab === "drafts"}
                  count={draftReports.length}
                  label="Drafts"
                  onClick={() => {
                    setActiveTab("drafts");
                    setSelectedReportId(undefined);
                  }}
                />
                <ReportTab
                  active={activeTab === "signed"}
                  count={signedReports.length}
                  label="Signed-off"
                  onClick={() => {
                    setActiveTab("signed");
                    setSelectedReportId(undefined);
                  }}
                />
                <ReportTab
                  active={activeTab === "progress"}
                  count={reports.length}
                  label="Progress Tracking"
                  onClick={() => {
                    setActiveTab("progress");
                    setSelectedReportId(undefined);
                  }}
                />
              </div>
            </GlassCard>

            <div className="grid gap-5 lg:grid-cols-[330px_minmax(0,1fr)]">
              <GlassCard className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-lg font-bold text-ink">Report list</h2>
                  <span className="rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)] px-3 py-1 text-xs font-bold text-[color:var(--color-text-muted)]">{visibleReports.length} shown</span>
                </div>
                {visibleReports.length ? (
                  <div className="mt-4 space-y-3">
                    {visibleReports.map((report) => {
                      const selected = selectedReport?.report_id === report.report_id;
                      return (
                        <button
                          key={report.report_id}
                          className={`w-full rounded-[var(--radius-card)] border p-3 text-left transition ${
                            selected ? "border-clinical bg-[color:var(--color-accent-soft)]" : "border-line bg-[color:var(--color-surface-reading)] hover:border-clinical/50"
                          }`}
                          onClick={() => setSelectedReportId(report.report_id)}
                        >
                          <div className="flex items-start gap-3">
                            <span className="flex h-9 w-9 shrink-0 items-center justify-center text-clinical">
                              <FileText size={20} aria-hidden="true" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate font-bold text-ink">{report.title ?? report.report_type ?? report.report_id}</span>
                              <span className="mt-1 block text-xs text-slate-600">Case {report.case_id ?? "Unknown"} · Session {report.session_id ?? "Unknown"}</span>
                              <span className="mt-2 inline-flex">
                                <StatusBadge status={isSignedReport(report) ? "Signed Off" : report.status ?? "Draft"} />
                              </span>
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <p className="mt-4 rounded-[var(--radius-panel)] border border-line bg-slate-50 p-4 text-sm text-slate-600">
                    No reports match this workspace tab yet.
                  </p>
                )}
              </GlassCard>

              <div className="space-y-5">
                <GlassCard className="p-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h2 className="sr-only">Report detail</h2>
                      <h3 className="text-2xl font-bold text-ink">{selectedReport?.title ?? selectedReport?.report_type ?? "Selected report"}</h3>
                      <p className="mt-2 text-sm text-slate-600">
                        {selectedReport ? `${selectedReport.report_type ?? "Report"} · Case ${selectedReport.case_id ?? "Unknown"} · Session ${selectedReport.session_id ?? "Unknown"}` : "Select a report to review details."}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {selectedReport ? <StatusBadge status={isSignedReport(selectedReport) ? "Signed Off" : selectedReport.status ?? "Draft"} /> : null}
                      {isSignedReport(selectedReport) ? (
                        <span className="inline-flex min-h-9 items-center gap-2 rounded-[var(--radius-card)] bg-emerald-100 px-3 text-sm font-bold text-emerald-800">
                          <Lock size={15} aria-hidden="true" />
                          Finalized / locked
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <dl className="mt-5 grid gap-3 sm:grid-cols-3">
                    <ReportMetric label="Provider" value={selectedReport?.actual_provider ?? selectedReport?.requested_provider ?? "Template"} />
                    <ReportMetric label="Updated" value={selectedReport?.updated_at ? new Date(selectedReport.updated_at).toLocaleDateString() : "Unavailable"} />
                    <ReportMetric label="Safety validator" value={selectedReport?.validator_version ?? selectedReport?.rule_set_version ?? "Unavailable"} />
                  </dl>

                  <div className="mt-5 reading-surface p-4">
                    <h3 className="font-bold text-ink">Draft preview</h3>
                    <p className="mt-2 line-clamp-6 whitespace-pre-line text-sm leading-6 text-slate-700">
                      {selectedReport?.markdown ?? selectedReport?.content_markdown ?? "No draft content returned by the API for this report."}
                    </p>
                    <Link href={selectedHref} className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-clinical px-4 text-sm font-semibold text-white">
                      {selectedActionLabel}
                      <ExternalLink size={16} aria-hidden="true" />
                    </Link>
                  </div>
                </GlassCard>

                <GlassCard className="p-5">
                  <div className="flex items-start gap-3">
                    <TrendingUp size={22} aria-hidden="true" className="mt-1 shrink-0 text-[color:var(--color-success-text)]" />
                    <div>
                      <h2 className="text-xl font-bold text-ink">Progress Tracking</h2>
                      <p className="mt-1 text-sm text-slate-600">Accessible progress summary based on backend report status and available report metadata.</p>
                    </div>
                  </div>
                  <div className="mt-5 space-y-4" role="img" aria-label="Report progress overview">
                    {progressRows.map((row) => (
                      <div key={row.label}>
                        <div className="flex items-center justify-between gap-3 text-sm">
                          <span className="font-semibold text-ink">{row.label}</span>
                          <span className="font-bold text-clinical">{row.value}%</span>
                        </div>
                        <div className="mt-2 h-2 overflow-hidden rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]">
                          <div className="h-full rounded-[var(--radius-card)] bg-[color:var(--color-accent)]" style={{ width: `${row.value}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </GlassCard>

                <GlassCard className="p-5">
                  <h2 className="text-xl font-bold text-ink">Goal progress overview</h2>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <ReportMetric label="Overall progress" value={`${completion}%`} />
                    <ReportMetric label="Reports finalized" value={`${signedReports.length}/${reports.length}`} />
                    <ReportMetric label="Open drafts" value={String(draftReports.length)} />
                  </div>
                  <p className="mt-4 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-950">
                    Progress is workflow status only. It is not a clinical outcome score.
                  </p>
                </GlassCard>
              </div>
            </div>
          </div>

          <aside className="space-y-5 xl:sticky xl:top-24 xl:self-start">
            <GlassCard className="p-5">
              <h2 className="text-xl font-bold text-ink">Report actions</h2>
              <div className="mt-4 space-y-3">
                <Link href={selectedHref} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-card)] bg-clinical px-4 text-sm font-semibold text-white">
                  {selectedReport?.session_id?.trim() ? "Open report workspace" : "Find session"}
                  <ExternalLink size={16} aria-hidden="true" />
                </Link>
                {selectedReport?.session_id?.trim() ? (
                  <button disabled className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-card)] border border-line bg-slate-100 px-4 text-sm font-semibold text-slate-500 disabled:opacity-70">
                    <Send size={17} aria-hidden="true" />
                    Sharing available after gated review
                  </button>
                ) : null}
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-600">
                Export and sign-off use the existing report summary gates. Caregiver sharing is local/demo status only and does not send a message.
              </p>
            </GlassCard>

            <GlassCard className="p-5">
              <h2 className="text-lg font-bold text-ink">Safety reminders</h2>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                <li>• Decision-support only; therapist review is required.</li>
                <li>• Finalization remains blocked by safety validation failures.</li>
                <li>• PDF export remains unavailable here unless supported by the gated summary flow.</li>
              </ul>
            </GlassCard>
          </aside>
        </div>
      ) : null}

      <SafetyNote>Reports remain export-eligible only after therapist review and sign-off.</SafetyNote>
    </div>
  );
}

function ReportTab({ active, count, label, onClick }: {
  active: boolean;
  count: number;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      aria-selected={active}
      className={`min-h-11 rounded-[var(--radius-card)] px-4 py-3 text-left font-semibold transition ${
        active ? "bg-[color:var(--color-accent)] text-white" : "border border-line bg-[color:var(--color-surface-reading)] text-ink hover:bg-[color:var(--color-surface-muted)]"
      }`}
      onClick={onClick}
      role="tab"
      type="button"
    >
      <span>{label}</span>
      <span className={`ml-2 rounded-[var(--radius-card)] px-2 py-0.5 text-xs ${active ? "bg-white/20 text-white" : "bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]"}`}>{count}</span>
    </button>
  );
}

function ReportMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-muted)] p-3">
      <dt className="text-xs font-semibold text-slate-500">{label}</dt>
      <dd className="mt-1 font-bold text-ink">{value}</dd>
    </div>
  );
}

function isSignedReport(report?: BackendReport) {
  if (!report) return false;
  const status = `${report.status ?? ""} ${report.therapist_signoff_status ?? ""}`.toLowerCase();
  return status.includes("signed") || status.includes("final");
}

function reportHref(report: BackendReport) {
  const sessionId = report.session_id?.trim();
  return resolveSessionHref("report", sessionId, {
    caseId: report.case_id,
    reportId: report.report_id,
  });
}

function reportActionLabel(report?: BackendReport) {
  if (!report?.session_id?.trim()) return "Find session";
  if (isSignedReport(report)) return "View signed report";
  const status = `${report.status ?? ""}`.toLowerCase();
  if (status.includes("stale")) return "Review stale report";
  if (status.includes("failed")) return "Review blocked report";
  return "Review draft";
}

function calculateCompletion(report?: BackendReport) {
  if (!report) return 0;
  if (isSignedReport(report)) return 100;
  if (report.safety_validation_result?.status === "failed" || report.finalization_blocked) return 55;
  if (report.markdown || report.content_markdown) return 75;
  return 40;
}
