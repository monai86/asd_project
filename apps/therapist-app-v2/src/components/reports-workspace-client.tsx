"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ExternalLink, FileText } from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { GlassCard, SafetyNote } from "@/components/liquid-ui";
import { StatusBadge } from "@/components/status-badge";
import { listBackendReports, type BackendReport } from "@/lib/workflow";

export function ReportsWorkspaceClient() {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const [reports, setReports] = useState<BackendReport[]>([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <header>
        <h1 className="text-3xl font-bold text-ink">Reports</h1>
        <p className="mt-2 text-slate-600">Open persisted therapist-editable drafts and finalized reports from the active API workspace.</p>
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

      <div className="space-y-4">
        {reports.map((report) => (
          <Link
            key={report.report_id}
            href={`/report-summary?report_id=${report.report_id ?? ""}&session_id=${report.session_id ?? ""}&case_id=${report.case_id ?? ""}`}
          >
            <GlassCard className="p-4 transition hover:-translate-y-0.5 hover:shadow-lift">
              <div className="flex items-start gap-3">
                <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#efeaff] text-clinical">
                  <FileText size={22} aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="font-bold text-ink">{report.title ?? report.report_type ?? report.report_id}</h2>
                  <p className="text-sm text-slate-600">
                    {report.report_type ?? "Report"} · Case {report.case_id ?? "Unknown"} · Session {report.session_id ?? "Unknown"}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    Provider: {report.actual_provider ?? report.requested_provider ?? "template"} · Updated {report.updated_at ? new Date(report.updated_at).toLocaleString() : "unknown"}
                  </p>
                </div>
                <div className="shrink-0">
                  <StatusBadge status={report.status ?? "Draft"} />
                </div>
              </div>
            </GlassCard>
          </Link>
        ))}
      </div>

      <SafetyNote>Reports remain export-eligible only after therapist review and sign-off.</SafetyNote>
    </div>
  );
}
