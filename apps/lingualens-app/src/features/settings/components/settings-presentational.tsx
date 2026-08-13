import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { CheckCircle2, LockKeyhole, UserX } from "lucide-react";

import type {
  OrganizationInvitation,
  OrganizationMembership,
  OrganizationReadiness,
  OrganizationReadinessItem,
} from "@/lib/workflow";

export function SettingRows({ rows }: { rows: string[][] }) {
  return (
    <div className="clinical-card rounded-md">
      {rows.map(([label, value]) => (
        <div key={label} className="grid gap-1 border-b border-line px-4 py-3 text-sm last:border-b-0 md:grid-cols-[240px_1fr]">
          <div className="font-medium text-ink">{label}</div>
          <div className="text-slate-700">{value}</div>
        </div>
      ))}
    </div>
  );
}

export function ReadinessCockpit({
  activeCount,
  pendingCount,
  readiness,
}: {
  activeCount: number;
  pendingCount: number;
  readiness: OrganizationReadiness | null;
}) {
  const summaryLabel = readiness
    ? readiness.production_ready
      ? "Production SaaS ready"
      : readiness.pilot_ready
        ? "Pilot-ready, production blocked"
        : "Pilot readiness needs attention"
    : "Readiness source unavailable";
  const summaryTone = readiness?.production_ready ? "green" : readiness?.pilot_ready ? "amber" : "slate";
  const visibleItems = readiness?.items ?? [
    {
      key: "backend_readiness",
      label: "Backend readiness",
      status: "attention",
      detail: "The app could not load the readiness endpoint; no lifecycle state is inferred locally.",
      evidence: ["readiness_endpoint=unavailable"],
      next_action: "Restore the backend readiness endpoint before making rollout decisions.",
    } satisfies OrganizationReadinessItem,
  ];

  return (
    <section className="clinical-card rounded-md p-4" aria-label="SaaS readiness">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-700">SaaS readiness</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-bold text-ink">Organization readiness cockpit</h2>
            <Badge tone={summaryTone === "green" ? "green" : summaryTone === "amber" ? "amber" : "slate"}>{summaryLabel}</Badge>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
            Backend-derived status for the active organization. This does not claim production compliance; blocked items must be cleared before real SaaS rollout.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:min-w-[520px]">
          <StatusPill label="Active members" value={readiness?.active_memberships ?? activeCount} />
          <StatusPill label="Pending invites" value={readiness?.pending_invitations ?? pendingCount} />
          <ReadinessMetric label="Environment" value={formatReadinessValue(readiness?.environment ?? "unknown")} />
          <ReadinessMetric label="Checked role" value={formatReadinessValue(readiness?.role ?? "unknown")} />
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {visibleItems.map((item) => (
          <ReadinessItemCard key={item.key} item={item} />
        ))}
      </div>
    </section>
  );
}

function ReadinessMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-line bg-field px-3 py-2">
      <p className="text-xs text-slate-600">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-ink" title={value}>{value}</p>
    </div>
  );
}

function ReadinessItemCard({ item }: { item: OrganizationReadinessItem }) {
  const evidence = item.evidence ?? [];
  const tone = item.status === "ready"
    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
    : item.status === "blocked"
      ? "border-red-200 bg-red-50 text-red-900"
      : "border-amber-200 bg-amber-50 text-amber-950";
  return (
    <article className={`rounded-md border p-3 ${tone}`}>
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold">{item.label}</h3>
        <span className="shrink-0 rounded-md bg-[color:var(--color-surface-reading)] px-2 py-1 text-xs font-semibold capitalize">{item.status}</span>
      </div>
      <p className="mt-2 text-xs leading-5">{item.detail}</p>
      {evidence.length > 0 ? (
        <div className="mt-3">
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.12em] opacity-80">Evidence</p>
          <ul className="mt-1 space-y-1">
            {evidence.slice(0, 4).map((entry) => (
              <li key={entry} className="break-words text-xs leading-5">{entry}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {item.next_action ? (
        <p className="mt-3 rounded-md bg-[color:var(--color-surface-reading)] p-2 text-xs font-medium leading-5">
          Next action: {item.next_action}
        </p>
      ) : null}
    </article>
  );
}

export function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-field p-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink">{value}</p>
    </div>
  );
}

export function StatusPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-20 rounded-md border border-line bg-[color:var(--color-surface-reading)] px-3 py-2">
      <p className="text-lg font-semibold text-ink">{value}</p>
      <p className="text-xs text-slate-600">{label}</p>
    </div>
  );
}

export function LifecycleList({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const hasItems = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return (
    <section aria-label={title}>
      <h3 className="mb-2 text-sm font-semibold text-ink">{title}</h3>
      <div className="grid gap-2">
        {hasItems ? children : <p className="rounded-md border border-line bg-field p-3 text-sm text-slate-600">{empty}</p>}
      </div>
    </section>
  );
}

export function InvitationRow({
  invitation,
  busy,
  prepared,
  onAccept,
  onPrepareSession,
}: {
  invitation: OrganizationInvitation;
  busy: boolean;
  prepared: boolean;
  onAccept: () => void;
  onPrepareSession: () => void;
}) {
  return (
    <article className="rounded-md border border-line bg-field p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-ink">{invitation.display_name}</h4>
          <p className="mt-1 text-xs text-slate-600">{invitation.email}</p>
        </div>
        <Badge>{capitalize(invitation.status)}</Badge>
      </div>
      <p className="mt-2 text-xs text-slate-600">
        {invitation.role} · expires {formatDate(invitation.expires_at)}
      </p>
      {invitation.status === "pending" ? (
        <button
          type="button"
          className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-md border border-cyan-200 bg-[color:var(--color-surface-reading)] px-3 text-sm font-semibold text-cyan-800 transition hover:bg-cyan-50 disabled:opacity-50"
          disabled={busy}
          onClick={onAccept}
        >
          <CheckCircle2 size={16} aria-hidden="true" />
          Accept invite locally
        </button>
      ) : null}
      {invitation.status === "accepted" ? (
        <div className="mt-3 space-y-2">
          <p className="text-xs leading-5 text-slate-600">
            Membership is active. Prepare an AAL1 invited session to validate the post-acceptance MFA gate.
          </p>
          <button
            type="button"
            className="inline-flex min-h-10 items-center gap-2 rounded-md border border-amber-200 bg-[color:var(--color-surface-reading)] px-3 text-sm font-semibold text-amber-900 transition hover:bg-amber-50 disabled:opacity-50"
            disabled={busy}
            onClick={onPrepareSession}
          >
            <LockKeyhole size={16} aria-hidden="true" />
            {prepared ? "AAL1 session prepared" : "Prepare mock MFA session"}
          </button>
        </div>
      ) : null}
    </article>
  );
}

export function MembershipRow({ member, busy, onRevoke }: { member: OrganizationMembership; busy: boolean; onRevoke: () => void }) {
  return (
    <article className="rounded-md border border-line bg-field p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-ink">{member.display_name}</h4>
          <p className="mt-1 text-xs text-slate-600">{member.user_id} · {member.role}</p>
        </div>
        <Badge tone={member.active ? "green" : "slate"}>{member.active ? "Active" : "Inactive"}</Badge>
      </div>
      <button
        type="button"
        className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-md border border-red-200 bg-[color:var(--color-surface-reading)] px-3 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:opacity-50"
        disabled={busy || !member.active}
        onClick={onRevoke}
      >
        <UserX size={16} aria-hidden="true" />
        Revoke {member.display_name}
      </button>
    </article>
  );
}

export function Guardrail({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex gap-3 rounded-md border border-line bg-field p-3">
      <Icon size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-cyan-700" />
      <div>
        <p className="text-sm font-semibold text-ink">{label}</p>
        <p className="mt-0.5 text-xs leading-5 text-slate-600">{value}</p>
      </div>
    </div>
  );
}

function Badge({ children, tone = "cyan" }: { children: ReactNode; tone?: "cyan" | "green" | "slate" | "amber" }) {
  const className = tone === "green"
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : tone === "amber"
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : tone === "slate"
        ? "border-slate-200 bg-slate-50 text-slate-700"
        : "border-cyan-200 bg-cyan-50 text-cyan-800";
  return <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${className}`}>{children}</span>;
}

function formatDate(value?: string) {
  if (!value) return "unknown";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatReadinessValue(value: string) {
  return value.replace(/_/g, " ");
}
