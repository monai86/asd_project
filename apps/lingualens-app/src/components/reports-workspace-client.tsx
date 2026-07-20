"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { GlassCard, SafetyNote } from "@/components/liquid-ui";
import { ReportsLibrary } from "@/features/reports/components/reports-library";
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
    <div className="space-y-5">
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <header className="workspace-panel flex flex-col gap-4 p-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-ink">Reports</h1>
          <p className="mt-2 max-w-[70ch] text-[color:var(--color-text-muted)]">
            Find persisted drafts and signed snapshots, then continue work in the canonical Session Report workspace.
          </p>
        </div>
        <Link href="/cases?intent=start-session" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 text-sm font-semibold text-clinical">
          Start session
          <ExternalLink size={16} aria-hidden="true" />
        </Link>
      </header>

      {loading && !backendUnavailable ? (
        <GlassCard className="p-5">
          <p className="text-slate-600" role="status">Loading persisted reports...</p>
        </GlassCard>
      ) : null}

      {!loading && !backendUnavailable && reports.length === 0 ? (
        <GlassCard className="p-5">
          <p className="font-semibold text-ink">No persisted reports yet.</p>
          <p className="mt-2 text-sm text-slate-600">Create or open a session, review the transcript, and generate a draft report from Session Workspace.</p>
          <Link href="/cases?intent=start-session" className="mt-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-clinical">
            Choose a case
            <ExternalLink size={16} aria-hidden="true" />
          </Link>
        </GlassCard>
      ) : null}

      {!loading && !backendUnavailable && reports.length > 0 ? <ReportsLibrary reports={reports} /> : null}

      <SafetyNote>Reports remain export-eligible only after therapist review and sign-off. Stale drafts require regeneration.</SafetyNote>
    </div>
  );
}
