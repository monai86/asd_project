"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowRight, CalendarDays, FolderOpen, ShieldCheck } from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { GlassCard, SafetyNote } from "@/components/liquid-ui";
import { StatusBadge } from "@/components/status-badge";
import { cases as fallbackCases } from "@/lib/mock-data";
import {
  getBackendCase,
  getBackendCaseTimeline,
  listBackendCases,
  type BackendCase,
  type BackendTimelineEvent
} from "@/lib/workflow";

type CasesWorkspaceClientProps = {
  caseId?: string;
};

function mapFallbackCase(row: typeof fallbackCases[number]): BackendCase {
  return {
    case_id: row.id,
    child_code: row.childCode,
    nickname: row.nickname,
    age_months: Number.parseInt(row.age, 10) * 12 || undefined,
    language: row.language,
    consent_status: row.consentStatus.toLowerCase(),
    latest_session_date: row.latestSessionDate,
    latest_session_status: row.latestSessionStatus,
    latest_report_status: row.latestReportStatus,
    review_priority: row.reviewPriority
  };
}

function ageLabel(caseItem: BackendCase) {
  return caseItem.age_months != null ? `${Math.floor(caseItem.age_months / 12)}y ${caseItem.age_months % 12}m` : "Age not recorded";
}

function caseLabel(caseItem: BackendCase) {
  return caseItem.nickname ?? caseItem.child_code ?? caseItem.display_label ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function codeLabel(caseItem: BackendCase) {
  return caseItem.child_code ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function languageLabel(caseItem: BackendCase) {
  return caseItem.language ?? "Language not recorded";
}

export function CasesWorkspaceClient({ caseId }: CasesWorkspaceClientProps) {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const [cases, setCases] = useState<BackendCase[]>(() => fallbackCases.map(mapFallbackCase));
  const [timeline, setTimeline] = useState<BackendTimelineEvent[]>([]);
  const [selectedCase, setSelectedCase] = useState<BackendCase | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const loadedCases = await listBackendCases();
        if (cancelled) return;
        setCases(loadedCases);

        if (caseId) {
          const [detail, detailTimeline] = await Promise.all([
            getBackendCase(caseId),
            getBackendCaseTimeline(caseId).catch(() => [])
          ]);
          if (cancelled) return;
          setSelectedCase(detail);
          setTimeline(detailTimeline);
        }
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
  }, [caseId, setBackendUnavailable]);

  const currentCase = useMemo(() => {
    if (selectedCase) return selectedCase;
    if (!caseId) return null;
    return cases.find((item) => item.case_id === caseId) ?? mapFallbackCase(fallbackCases.find((item) => item.id === caseId) ?? fallbackCases[0]);
  }, [caseId, cases, selectedCase]);

  if (caseId && currentCase) {
    return (
      <>
        <BackendAvailabilityBanner unavailable={backendUnavailable} />
        <CaseDetailContent caseItem={currentCase} timeline={timeline} />
      </>
    );
  }

  if (backendUnavailable && !caseId) {
    return (
      <>
        <BackendAvailabilityBanner unavailable />
        <CaseListFallback />
      </>
    );
  }

  if (loading && !caseId) {
    return (
      <>
        <BackendAvailabilityBanner unavailable={backendUnavailable} />
        <CaseListFallback />
      </>
    );
  }

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <div className="mx-auto max-w-3xl space-y-5">
        <header>
          <h1 className="text-3xl font-bold text-ink">Cases</h1>
          <p className="mt-2 text-slate-600">Open a persisted child record when you need session context, consent status, and current workflow state.</p>
        </header>
        <div className="space-y-4">
          {cases.map((row) => (
            <Link key={row.case_id} href={`/cases/${row.case_id}`}>
              <GlassCard className="p-4 transition hover:-translate-y-0.5 hover:shadow-lift">
                <div className="flex items-center gap-3">
                  <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-[#efeaff] font-bold text-clinical">
                    {codeLabel(row).slice(-2)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h2 className="font-bold text-ink">{caseLabel(row)}</h2>
                    <p className="text-sm text-slate-600">{codeLabel(row)} · {ageLabel(row)} · {languageLabel(row)}</p>
                  </div>
                  <ArrowRight size={20} aria-hidden="true" className="text-slate-400" />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                  <MiniStatus icon={ShieldCheck} label="Consent" value={row.consent_status ?? "Unknown"} />
                  <MiniStatus icon={CalendarDays} label="Latest" value={row.latest_session_date ?? "No session"} />
                  <MiniStatus icon={FolderOpen} label="Next" value={row.latest_session_status ?? "Draft"} />
                </div>
              </GlassCard>
            </Link>
          ))}
        </div>
        <SafetyNote>Backend records are the source of truth when case or session IDs exist.</SafetyNote>
      </div>
    </>
  );
}

function CaseListFallback() {
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <h1 className="text-3xl font-bold text-ink">Cases</h1>
        <p className="mt-2 text-slate-600">Showing local seeded demo content because the API workspace is unavailable.</p>
      </header>
      <div className="space-y-4">
        {fallbackCases.map((row) => (
          <GlassCard key={row.id} className="p-4">
            <div className="flex items-center gap-3">
              <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-[#efeaff] font-bold text-clinical">
                {row.childCode.slice(-2)}
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="font-bold text-ink">{row.nickname}</h2>
                <p className="text-sm text-slate-600">{row.childCode} · {row.age} · {row.language}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <MiniStatus icon={ShieldCheck} label="Consent" value={row.consentStatus} />
              <MiniStatus icon={CalendarDays} label="Latest" value={row.latestSessionDate} />
              <MiniStatus icon={FolderOpen} label="Next" value={row.latestSessionStatus} />
            </div>
          </GlassCard>
        ))}
      </div>
      <SafetyNote>Seeded fallback data is for local demo continuity only.</SafetyNote>
    </div>
  );
}

function CaseDetailContent({
  caseItem,
  timeline
}: {
  caseItem: BackendCase;
  timeline: BackendTimelineEvent[];
}) {
  return (
    <div className="space-y-6">
      <header className="border-b border-line pb-5">
        <p className="mb-3 inline-flex rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-safety">
          Backend-backed case record
        </p>
        <h1 className="text-2xl font-semibold tracking-normal text-ink sm:text-3xl">
          Case {codeLabel(caseItem)}
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          This view reads the persisted case record, current consent status, and timeline from the active Therapist App v2 API.
        </p>
      </header>
      <section className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <aside className="clinical-card rounded-md p-4">
          <h2 className="font-semibold">Child profile summary</h2>
          <dl className="mt-4 grid gap-3 text-sm">
            <div><dt className="text-slate-600">Display label</dt><dd>{caseLabel(caseItem)}</dd></div>
            <div><dt className="text-slate-600">Case code</dt><dd>{codeLabel(caseItem)}</dd></div>
            <div><dt className="text-slate-600">Age</dt><dd>{ageLabel(caseItem)}</dd></div>
            <div><dt className="text-slate-600">Language</dt><dd>{languageLabel(caseItem)}</dd></div>
            <div><dt className="text-slate-600">Consent status</dt><dd>{caseItem.consent_status ?? "Unknown"}</dd></div>
            <div><dt className="text-slate-600">Review priority</dt><dd className="capitalize">{caseItem.review_priority ?? "low"}</dd></div>
          </dl>
          <Link href={`/record?case_id=${caseItem.case_id}`} className="mt-5 inline-flex w-full justify-center rounded-md bg-clinical px-4 py-2 text-sm font-semibold text-white">
            Create new session
          </Link>
        </aside>
        <div className="grid gap-4">
          <section className="clinical-card rounded-md p-4">
            <h2 className="font-semibold">Session timeline</h2>
            <div className="mt-4 border-l border-line pl-4">
              {timeline.length ? timeline.map((event) => (
                <div key={event.event_id} className="mb-4">
                  <p className="font-medium">{event.label}</p>
                  <p className="text-sm text-slate-600">{new Date(event.occurred_at).toLocaleString()}</p>
                  <div className="mt-2"><StatusBadge status={event.status} /></div>
                </div>
              )) : (
                <p className="text-sm text-slate-600">No persisted session events yet for this case.</p>
              )}
            </div>
          </section>
          <section className="grid gap-4 lg:grid-cols-3">
            <div className="clinical-card rounded-md p-4">
              <p className="text-xs text-slate-600">Latest session date</p>
              <p className="mt-2 text-lg font-semibold text-ink">{caseItem.latest_session_date ?? "No session"}</p>
            </div>
            <div className="clinical-card rounded-md p-4">
              <p className="text-xs text-slate-600">Latest session status</p>
              <div className="mt-2"><StatusBadge status={caseItem.latest_session_status ?? "Draft"} /></div>
            </div>
            <div className="clinical-card rounded-md p-4">
              <p className="text-xs text-slate-600">Latest report status</p>
              <div className="mt-2"><StatusBadge status={caseItem.latest_report_status ?? "Draft"} /></div>
            </div>
          </section>
        </div>
      </section>
      <SafetyNote>Case detail stays descriptive and workflow-oriented; it is not a diagnostic summary.</SafetyNote>
    </div>
  );
}

function MiniStatus({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white/55 p-3">
      <Icon className="mx-auto mb-1 text-clinical" size={18} aria-hidden="true" />
      <p className="text-slate-500">{label}</p>
      <p className="mt-1 truncate font-semibold text-ink">{value}</p>
    </div>
  );
}
