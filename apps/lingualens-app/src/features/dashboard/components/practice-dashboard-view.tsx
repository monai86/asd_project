"use client";

import Link from "next/link";
import { Activity, FileCheck2, FileCode, FolderOpen, ListChecks, MessagesSquare, Sparkles } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { LanguageProgressChart } from "@/features/dashboard/components/language-progress-chart";
import type { DashboardSummary } from "@/lib/workflow";

function consentLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function sessionStage(session: DashboardSummary["recent_sessions"][number]) {
  if (session.has_report) return "Report drafted";
  if (session.has_ml_review) return "Evidence review";
  if (session.has_features) return "Findings extracted";
  if (session.has_transcript) return "Transcript ready";
  return "Intake only";
}

export function PracticeDashboardView({ summary }: { summary: DashboardSummary }) {
  const consentCounts = Object.entries(summary.cases.consent_counts).sort((a, b) => b[1] - a[1]);
  const reviewedSessions = summary.cases.with_latest_reviewed_session;

  return (
    <div className="min-w-0 space-y-6">
      <PageHeader
        eyebrow="Clinical Decision Support Workbench"
        title="Dashboard"
        description="A unified clinical overview across child caseloads, TalkBank transcript review, 15+ speech-language features, Spider Diagram norm comparisons, and SHA-256 attested reports."
        meta={[
          `Organization ${summary.organization_id}`,
          summary.generated_at ? `Updated ${new Date(summary.generated_at).toLocaleDateString()}` : "",
        ].filter(Boolean)}
      />

      {/* Quick Launchpad Hero */}
      <div className="rounded-xl border border-slate-200 bg-gradient-to-r from-slate-50 via-white to-teal-50/50 p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="inline-flex items-center gap-1 rounded-md bg-teal-50 border border-teal-200 px-2.5 py-0.5 text-xs font-semibold text-teal-800">
              <Sparkles className="h-3 w-3 text-teal-600" />
              LinguaLens Clinical Suite v1.6.3
            </span>
            <h2 className="mt-2 text-base font-bold text-slate-900">
              Speech-Language Assessment & Decision Support
            </h2>
            <p className="mt-1 text-xs text-slate-600 max-w-2xl leading-relaxed">
              รองรับการนำเข้าไฟล์เสียง (.wav/.mp3), ไฟล์ TalkBank (.cha), สตูดิโอตรวจคำพูด Dual-Mode, กราฟใยแมงมุม (Spider Diagram) เทียบเกณฑ์สมวัย 100%, และร่างรายงานคลินิกอ้างอิงข้อมูลจริง
            </p>
          </div>
          <div className="flex flex-wrap gap-2.5">
            <Link
              href="/sessions/session_demo_001?view=transcript"
              className="flex min-h-11 items-center gap-1.5 rounded-lg bg-[color:var(--color-accent)] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[color:var(--color-accent-strong)] transition-all"
            >
              <FileCode className="h-3.5 w-3.5" />
              <span>Open TalkBank Studio</span>
            </Link>
            <Link
              href="/sessions/session_demo_001?view=findings"
              className="flex min-h-11 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 shadow-xs hover:bg-slate-50 transition-all"
            >
              <Activity className="h-3.5 w-3.5 text-slate-600" />
              <span>View Spider Diagram</span>
            </Link>
          </div>
        </div>
      </div>

      <section aria-labelledby="dashboard-stats" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <h2 id="dashboard-stats" className="sr-only">
          Caseload summary
        </h2>
        <StatCard
          label="Active cases"
          value={String(summary.cases.total)}
          helper={`${reviewedSessions} with a reviewed latest session`}
          icon={FolderOpen}
          tone="accent"
        />
        <StatCard
          label="Sessions"
          value={String(summary.sessions.total)}
          helper={`${summary.sessions.with_transcript} transcript · ${summary.sessions.with_features} features extracted`}
          icon={MessagesSquare}
          tone="neutral"
        />
        <StatCard
          label="Evidence review"
          value={String(summary.sessions.with_ml_review)}
          helper="Sessions with an ML decision-support review"
          icon={ListChecks}
          tone="neutral"
        />
        <StatCard
          label="Reports"
          value={String(summary.reports.total)}
          helper={summary.reports.signoff_counts["Signed Off"]
            ? `${summary.reports.signoff_counts["Signed Off"]} signed off`
            : "None signed off yet"}
          icon={FileCheck2}
          tone={summary.reports.signoff_counts["Signed Off"] ? "success" : "neutral"}
        />
      </section>

      <section aria-labelledby="progress-heading" className="workspace-panel mt-6 p-5">
        <h2 id="progress-heading" className="text-base font-semibold text-[color:var(--color-text-strong)]">
          Language progress
        </h2>
        <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
          Track a language-sample feature across each case&apos;s sessions over time.
        </p>
        <LanguageProgressChart trends={summary.feature_trends} />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section aria-labelledby="consent-heading" className="workspace-panel p-5">
          <h2 id="consent-heading" className="text-base font-semibold text-[color:var(--color-text-strong)]">
            Consent status
          </h2>
          {consentCounts.length ? (
            <ul className="mt-4 space-y-3">
              {consentCounts.map(([status, count]) => (
                <li key={status} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-[color:var(--color-text-muted)]">{consentLabel(status)}</span>
                  <span className="font-semibold text-[color:var(--color-text-strong)]">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-[color:var(--color-text-muted)]">No cases yet.</p>
          )}
        </section>

        <section aria-labelledby="pipeline-heading" className="workspace-panel p-5">
          <h2 id="pipeline-heading" className="text-base font-semibold text-[color:var(--color-text-strong)]">
            Pipeline progress
          </h2>
          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
            Sessions that reached each stage of the analysis pipeline.
          </p>
          <ul className="mt-4 space-y-3 text-sm">
            <li className="flex items-center justify-between gap-3">
              <span className="text-[color:var(--color-text-muted)]">Transcript recorded</span>
              <span className="font-semibold text-[color:var(--color-text-strong)]">{summary.sessions.with_transcript}</span>
            </li>
            <li className="flex items-center justify-between gap-3">
              <span className="text-[color:var(--color-text-muted)]">Features extracted</span>
              <span className="font-semibold text-[color:var(--color-text-strong)]">{summary.sessions.with_features}</span>
            </li>
            <li className="flex items-center justify-between gap-3">
              <span className="text-[color:var(--color-text-muted)]">ML decision support</span>
              <span className="font-semibold text-[color:var(--color-text-strong)]">{summary.sessions.with_ml_review}</span>
            </li>
            <li className="flex items-center justify-between gap-3">
              <span className="text-[color:var(--color-text-muted)]">Report drafted</span>
              <span className="font-semibold text-[color:var(--color-text-strong)]">{summary.sessions.with_report}</span>
            </li>
          </ul>
        </section>

        <section aria-labelledby="report-heading" className="workspace-panel p-5">
          <h2 id="report-heading" className="text-base font-semibold text-[color:var(--color-text-strong)]">
            Report sign-off
          </h2>
          {summary.reports.total ? (
            <ul className="mt-4 space-y-3 text-sm">
              {Object.entries(summary.reports.signoff_counts)
                .sort((a, b) => b[1] - a[1])
                .map(([status, count]) => (
                  <li key={status} className="flex items-center justify-between gap-3">
                    <StatusBadge status={status} />
                    <span className="font-semibold text-[color:var(--color-text-strong)]">{count}</span>
                  </li>
                ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-[color:var(--color-text-muted)]">No reports yet.</p>
          )}
        </section>
      </div>

      <section aria-labelledby="recent-heading" className="mt-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 id="recent-heading" className="text-base font-semibold text-[color:var(--color-text-strong)]">
            Recent sessions
          </h2>
          <Link
            href="/cases"
            className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-semibold text-[color:var(--color-accent-strong)] transition hover:bg-[color:var(--color-accent-soft)]"
          >
            View all cases
          </Link>
        </div>
        {summary.recent_sessions.length ? (
          <>
            <div className="workspace-panel hidden md:block">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--color-border)] text-left">
                    <th scope="col" className="px-4 py-3 font-medium text-[color:var(--color-text-muted)]">
                      Case
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium text-[color:var(--color-text-muted)]">
                      Date
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium text-[color:var(--color-text-muted)]">
                      Stage
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium text-[color:var(--color-text-muted)]">
                      Status
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium text-[color:var(--color-text-muted)]">
                      <span className="sr-only">Open</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {summary.recent_sessions.map((session) => (
                    <tr key={session.session_id} className="border-b border-[color:var(--color-border)] last:border-b-0">
                      <td className="px-4 py-3">
                        <Link
                          href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                          className="inline-flex min-h-11 items-center rounded-lg px-1 font-semibold text-[color:var(--color-accent-strong)] transition hover:bg-[color:var(--color-accent-soft)]"
                        >
                          {session.case_label}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-[color:var(--color-text-muted)]">{session.session_date}</td>
                      <td className="px-4 py-3 text-[color:var(--color-text-muted)]">{sessionStage(session)}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={session.status} />
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                          className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-semibold text-[color:var(--color-accent-strong)] transition hover:bg-[color:var(--color-accent-soft)]"
                        >
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="space-y-3 md:hidden">
              {summary.recent_sessions.map((session) => (
                <li key={session.session_id} className="workspace-panel p-4">
                  <div className="flex items-center justify-between gap-3">
                    <Link
                      href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                      className="inline-flex min-h-11 items-center rounded-lg px-1 font-semibold text-[color:var(--color-accent-strong)] transition hover:bg-[color:var(--color-accent-soft)]"
                    >
                      {session.case_label}
                    </Link>
                    <StatusBadge status={session.status} />
                  </div>
                  <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
                    {session.session_date} · {sessionStage(session)}
                  </p>
                  <Link
                    href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                    className="mt-3 inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-semibold text-[color:var(--color-accent-strong)] transition hover:bg-[color:var(--color-accent-soft)]"
                  >
                    Open session
                  </Link>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <div className="workspace-panel p-6 text-sm text-[color:var(--color-text-muted)]">
            No sessions yet. Start a session from the Cases list to populate the pipeline.
          </div>
        )}
      </section>
    </div>
  );
}
