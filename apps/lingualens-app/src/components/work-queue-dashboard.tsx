import Link from "next/link";
import { AlertTriangle, CalendarDays, ClipboardPaste, FileText, Mic, ShieldCheck, UploadCloud } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { AppShell } from "@/components/app-shell";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { SafetyNotice } from "@/components/safety-notice";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import {
  cases,
  reports,
  workQueue
} from "@/lib/mock-data";
import type { ShellActive } from "@/components/sidebar";

const priorityTasks = [
  {
    id: "task-review-transcript",
    title: "Transcript review pending",
    detail: "C-1024 · reviewed transcript needed before feature extraction",
    href: "/review-transcript",
    status: "Needs Review" as const
  },
  {
    id: "task-report-signoff",
    title: "Report draft awaiting sign-off",
    detail: "C-1031 · therapist review required before export",
    href: "/reports",
    status: "Ready" as const
  },
  {
    id: "task-audio-processing",
    title: "Experimental audio job needs follow-up",
    detail: "Non-identifying demo item · verify transcript wording after upload",
    href: "/record?mode=audio",
    status: "Processing" as const
  }
];

const agendaItems = [
  { id: "agenda-1", child: "Ava M.", time: "10:30 AM", focus: "Language sample review", href: "/today" },
  { id: "agenda-2", child: "Ethan L.", time: "1:00 PM", focus: "Articulation therapy session", href: "/record" },
  { id: "agenda-3", child: "Jacob W.", time: "3:30 PM", focus: "Fluency follow-up", href: "/today" }
];

const recentUploads = [
  { id: "upload-1", source: "Upload .cha", item: "C-1024 · June sample", status: "Needs Review" },
  { id: "upload-2", source: "Upload audio", item: "Demo recording · therapist review required", status: "Processing" },
  { id: "upload-3", source: "Paste transcript", item: "Follow-up sample · draft saved", status: "Draft" }
];

const recentResults = [
  { id: "result-1", title: "Ethan L.", detail: "Transcript review · 92% complete · 2:28", href: "/review-transcript" },
  { id: "result-2", title: "Ava M.", detail: "Feature summary ready · therapist review needed", href: "/results" },
  { id: "result-3", title: "Jacob W.", detail: "Report draft ready · therapist review required", href: "/reports" }
];

export function WorkQueueDashboard({ active }: { active: ShellActive }) {
  const caseActivityRows = cases.map((row) => ({
    id: row.id,
    case: (
      <Link href={`/cases/${row.id}`} className="font-semibold text-[color:var(--color-text-strong)] hover:text-[color:var(--color-accent-strong)]">
        {row.childCode}
      </Link>
    ),
    child: row.nickname,
    session: row.latestSessionDate,
    status: <StatusBadge status={row.latestSessionStatus} />
  }));

  const uploadRows = recentUploads.map((row) => ({
    id: row.id,
    source: row.source,
    item: row.item,
    status: <StatusBadge status={row.status} />
  }));

  return (
    <AppShell
      active={active}
      rightRail={
        <>
          <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-4">
            <h2 className="text-base font-semibold text-[color:var(--color-warning-text)]">Safety &amp; Clinical Reminders</h2>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-[color:var(--color-warning-text)]">
              <li>Decision-support only. Therapist review and sign-off remain required.</li>
              <li>Experimental audio and ASR output remain draft-only and must be reviewed manually.</li>
              <li>No notifications or sharing actions on this page imply real delivery or secure messaging.</li>
            </ul>
          </div>
          <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
            <h2 className="text-base font-semibold text-[color:var(--color-text-strong)]">Quick Actions</h2>
            <div className="mt-4 grid gap-3">
              <ActionButton href="/record" icon={<Mic size={18} aria-hidden="true" />} className="w-full justify-start">Start Recording</ActionButton>
              <ActionButton href="/record?mode=audio" tone="secondary" icon={<UploadCloud size={18} aria-hidden="true" />} className="w-full justify-start">Upload audio</ActionButton>
              <ActionButton href="/record?mode=cha" tone="secondary" icon={<FileText size={18} aria-hidden="true" />} className="w-full justify-start">Upload .cha</ActionButton>
              <ActionButton href="/record?mode=paste" tone="secondary" icon={<ClipboardPaste size={18} aria-hidden="true" />} className="w-full justify-start">Paste transcript</ActionButton>
            </div>
          </div>
        </>
      }
    >
      <div className="space-y-6">
        <PageHeader
          title="Work Queue"
          description="Review what needs attention next, keep session intake moving, and preserve the manual-first therapist workflow."
          meta={["Local clinician workspace", "Non-identifying demo fallback data"]}
          actions={<ActionButton href="/record" icon={<Mic size={18} aria-hidden="true" />}>Start Recording</ActionButton>}
        />

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(22rem,0.75fr)]">
          <div className="space-y-6">
            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Priority Tasks</h2>
                  <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">Operational queue only. Review states do not imply diagnosis.</p>
                </div>
                <span className="inline-flex min-h-8 items-center rounded-full bg-[color:var(--color-accent-soft)] px-3 text-xs font-semibold text-[color:var(--color-accent-strong)]">
                  {priorityTasks.length} active
                </span>
              </div>
              <div className="mt-4 grid gap-3">
                {priorityTasks.map((task) => (
                  <Link
                    key={task.id}
                    href={task.href}
                    className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft transition hover:border-[color:var(--color-accent-subtle)] motion-reduce:transition-none"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-[color:var(--color-text-strong)]">{task.title}</h3>
                        <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">{task.detail}</p>
                      </div>
                      <StatusBadge status={task.status} />
                    </div>
                  </Link>
                ))}
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
                <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Today&apos;s Agenda</h2>
                <div className="mt-4 space-y-3">
                  {agendaItems.map((item) => (
                    <Link
                      key={item.id}
                      href={item.href}
                      className="flex min-h-11 items-start gap-3 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft"
                    >
                      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]">
                        <CalendarDays size={18} aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <p className="font-semibold text-[color:var(--color-text-strong)]">{item.child}</p>
                        <p className="text-sm text-[color:var(--color-text-muted)]">{item.time}</p>
                        <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">{item.focus}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>

              <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
                <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Workload Overview</h2>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {workQueue.slice(0, 4).map((item) => (
                    <StatCard
                      key={item.label}
                      label={item.label}
                      value={String(item.count)}
                      helper={`Status: ${item.status}`}
                      tone={item.status === "Failed" ? "warning" : item.status === "Ready" ? "success" : "accent"}
                    />
                  ))}
                </div>
              </div>
            </section>

            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Recent Case Activity</h2>
              <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">Uses existing non-identifying case records or local demo fallback data.</p>
              <div className="mt-4">
                {caseActivityRows.length ? (
                  <DataTable
                    caption="Recent case activity"
                    columns={[
                      { key: "case", header: "Case" },
                      { key: "child", header: "Label" },
                      { key: "session", header: "Latest session" },
                      { key: "status", header: "Status", align: "right" }
                    ]}
                    rows={caseActivityRows}
                  />
                ) : (
                  <EmptyState title="No recent case activity" description="Open or create a case to populate this queue." />
                )}
              </div>
            </section>

            <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Recent Uploads</h2>
              <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">Demo rows are clearly labeled when backend upload history is unavailable.</p>
              <div className="mt-4">
                <DataTable
                  caption="Recent uploads"
                  columns={[
                    { key: "source", header: "Source" },
                    { key: "item", header: "Item" },
                    { key: "status", header: "Status", align: "right" }
                  ]}
                  rows={uploadRows}
                />
              </div>
            </section>
          </div>

          <div className="space-y-6 xl:hidden">
            <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Safety &amp; Clinical Reminders</h2>
              <SafetyNotice className="mt-4">
                Decision-support only. Therapist review and sign-off remain required.
              </SafetyNotice>
              <div className="mt-4 rounded-[var(--radius-panel)] border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-4 text-sm leading-6 text-[color:var(--color-warning-text)]">
                Experimental audio uploads remain draft-only and must be reviewed manually.
              </div>
            </div>

            <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Quick Actions</h2>
              <div className="mt-4 grid gap-3">
                <ActionButton href="/record" icon={<Mic size={18} aria-hidden="true" />} className="w-full justify-start">Start Recording</ActionButton>
                <ActionButton href="/record?mode=audio" tone="secondary" icon={<UploadCloud size={18} aria-hidden="true" />} className="w-full justify-start">Upload audio</ActionButton>
                <ActionButton href="/record?mode=cha" tone="secondary" icon={<FileText size={18} aria-hidden="true" />} className="w-full justify-start">Upload .cha</ActionButton>
                <ActionButton href="/record?mode=paste" tone="secondary" icon={<ClipboardPaste size={18} aria-hidden="true" />} className="w-full justify-start">Paste transcript</ActionButton>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:hidden">
          <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-2xl font-semibold text-[color:var(--color-text-strong)]">Start Recording</h2>
            <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">Keep the one-tap workflow for fast session intake.</p>
            <div className="mt-4 grid gap-3">
              <ActionButton href="/record" icon={<Mic size={18} aria-hidden="true" />} size="lg" className="w-full">Start Recording</ActionButton>
              <div className="grid grid-cols-3 gap-3">
                <ActionButton href="/record?mode=audio" tone="secondary" icon={<UploadCloud size={18} aria-hidden="true" />} className="w-full text-center">Upload audio</ActionButton>
                <ActionButton href="/record?mode=cha" tone="secondary" icon={<FileText size={18} aria-hidden="true" />} className="w-full text-center">Upload .cha</ActionButton>
                <ActionButton href="/record?mode=paste" tone="secondary" icon={<ClipboardPaste size={18} aria-hidden="true" />} className="w-full text-center">Paste transcript</ActionButton>
              </div>
            </div>
          </div>

          <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Today&apos;s sessions</h2>
            <div className="mt-4 space-y-3">
              {agendaItems.map((item) => (
                <Link key={item.id} href={item.href} className="flex items-start gap-3 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]">
                    <CalendarDays size={18} aria-hidden="true" />
                  </span>
                  <div>
                    <p className="font-semibold text-[color:var(--color-text-strong)]">{item.child}</p>
                    <p className="text-sm text-[color:var(--color-text-muted)]">{item.time}</p>
                    <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">{item.focus}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Recent results</h2>
            <div className="mt-4 space-y-3">
              {recentResults.map((item) => (
                <Link key={item.id} href={item.href} className="flex items-start gap-3 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]">
                    <FileText size={18} aria-hidden="true" />
                  </span>
                  <div>
                    <p className="font-semibold text-[color:var(--color-text-strong)]">{item.title}</p>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">{item.detail}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-6">
          <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Safety &amp; Clinical Reminders</h2>
            <div className="mt-4 grid gap-3">
              <SafetyNotice>
                Decision-support only. Therapist review and sign-off remain required.
              </SafetyNotice>
              <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-4 text-sm leading-6 text-[color:var(--color-warning-text)]">
                <div className="flex items-start gap-3">
                  <AlertTriangle size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
                  <p>Do not treat quick-start uploads, AI review cues, or draft reports as final clinical output.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Quick Actions</h2>
            <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">Routes into the existing intake workflows without changing report or transcript gates.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <ActionButton href="/record" icon={<Mic size={18} aria-hidden="true" />} className="w-full justify-start">Start Recording</ActionButton>
              <ActionButton href="/record?mode=audio" tone="secondary" icon={<UploadCloud size={18} aria-hidden="true" />} className="w-full justify-start">Upload audio</ActionButton>
              <ActionButton href="/record?mode=cha" tone="secondary" icon={<FileText size={18} aria-hidden="true" />} className="w-full justify-start">Upload .cha</ActionButton>
              <ActionButton href="/record?mode=paste" tone="secondary" icon={<ClipboardPaste size={18} aria-hidden="true" />} className="w-full justify-start">Paste transcript</ActionButton>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
