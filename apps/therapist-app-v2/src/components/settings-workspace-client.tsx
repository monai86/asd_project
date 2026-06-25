"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, Clock3, MailPlus, ShieldCheck, UserRound, UserX } from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import {
  createOrganizationInvitation,
  listOrganizationInvitations,
  listOrganizationMemberships,
  revokeOrganizationMembership,
  type OrganizationInvitation,
  type OrganizationMembership
} from "@/lib/workflow";

type Scope = "therapist" | "admin";

const therapistSettings = [
  ["Profile", "Demo Therapist"],
  ["Credentials", "Speech therapist / clinician"],
  ["Organization", "Pilot organization workspace"],
  ["Sample data mode", "Anonymized local demo data only"],
  ["Owned privacy requests", "Case export and consent withdrawal requests for owned cases"],
  ["Consent policy", "Visible per case with withdrawal workflow"]
];

const adminSettings = [
  ["Auth lifecycle", "Invitation-only onboarding, MFA guard, membership revocation"],
  ["Production auth mode", "Supabase Auth contract required before real accounts"],
  ["Mock headers", "Allowed only in local pilot mode; ignored in Supabase auth mode"],
  ["Break-glass", "Scoped platform-operator workflow with backend audit events"],
  ["Runtime diagnostics", "Repository, job queue, storage, and auth mode remain server-owned"],
  ["Pipeline settings", "Audio automation is experimental and asynchronous"]
];

const fallbackMemberships: OrganizationMembership[] = [
  {
    membership_id: "local-admin",
    organization_id: "pilot_org_001",
    user_id: "admin-demo",
    display_name: "Pilot Org Admin",
    role: "org_admin",
    active: true,
    created_at: "2026-06-25T08:00:00Z"
  },
  {
    membership_id: "local-therapist",
    organization_id: "pilot_org_001",
    user_id: "therapist-demo",
    display_name: "Demo Therapist",
    role: "therapist",
    active: true,
    created_at: "2026-06-25T08:00:00Z"
  }
];

const fallbackInvitations: OrganizationInvitation[] = [
  {
    invitation_id: "local-invite",
    organization_id: "pilot_org_001",
    email: "pilot.clinician@example.test",
    display_name: "Pilot Clinician",
    role: "therapist",
    status: "pending",
    invited_by: "admin-demo",
    expires_at: "2026-07-02T08:00:00Z",
    created_at: "2026-06-25T08:00:00Z"
  }
];

export function SettingsWorkspaceClient({ initialScope = "therapist" }: { initialScope?: Scope }) {
  const [scope, setScope] = useState<Scope>(initialScope);

  return (
    <section className="grid gap-5">
      <div className="inline-flex w-fit rounded-md border border-line bg-white p-1 shadow-soft" aria-label="Settings scope">
        <ScopeButton active={scope === "therapist"} icon={UserRound} label="Therapist" onClick={() => setScope("therapist")} />
        <ScopeButton active={scope === "admin"} icon={ShieldCheck} label="Admin" onClick={() => setScope("admin")} />
      </div>

      {scope === "therapist" ? <TherapistSettings /> : <AdminSettings />}
    </section>
  );
}

function ScopeButton({
  active,
  icon: Icon,
  label,
  onClick
}: {
  active: boolean;
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-medium transition ${
        active ? "bg-clinical text-white" : "text-slate-600 hover:bg-slate-50"
      }`}
      onClick={onClick}
      aria-pressed={active}
    >
      <Icon size={16} aria-hidden="true" />
      {label}
    </button>
  );
}

function TherapistSettings() {
  return (
    <>
      <SettingRows rows={therapistSettings} />
      <section className="clinical-card rounded-md p-4">
        <h2 className="text-base font-semibold text-ink">Therapist pilot workspace</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
          This local path is for exploring the Session Workspace with anonymized demo data. Backend records remain the source of truth when workflow locators exist.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <StatusTile label="Transcript gate" value="Quality attestation required" />
          <StatusTile label="Report export" value="Sign-off required" />
          <StatusTile label="Clinical boundary" value="Not diagnostic" />
        </div>
      </section>
    </>
  );
}

function AdminSettings() {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const [memberships, setMemberships] = useState<OrganizationMembership[]>(fallbackMemberships);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>(fallbackInvitations);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("therapist");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [loadedMemberships, loadedInvitations] = await Promise.all([
          listOrganizationMemberships(),
          listOrganizationInvitations()
        ]);
        if (cancelled) return;
        setMemberships(loadedMemberships);
        setInvitations(loadedInvitations);
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

  const activeCount = useMemo(() => memberships.filter((member) => member.active).length, [memberships]);
  const pendingCount = useMemo(() => invitations.filter((invite) => invite.status === "pending").length, [invitations]);

  async function handleInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!inviteEmail.trim() || !inviteName.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const created = await createOrganizationInvitation({
        email: inviteEmail.trim(),
        display_name: inviteName.trim(),
        role: inviteRole
      });
      setInvitations((current) => [created, ...current]);
      setInviteEmail("");
      setInviteName("");
      setInviteRole("therapist");
      setMessage(`Invitation created for ${created.display_name}.`);
      setBackendUnavailable(false);
    } catch {
      setBackendUnavailable(true);
      setMessage("Could not create invitation. The local API workspace is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke(member: OrganizationMembership) {
    setBusy(true);
    setMessage("");
    try {
      const revoked = await revokeOrganizationMembership(member.membership_id);
      setMemberships((current) => current.map((item) => item.membership_id === revoked.membership_id ? revoked : item));
      setMessage(`Membership revoked for ${revoked.display_name}. Care-team assignments are deactivated by the backend.`);
      setBackendUnavailable(false);
    } catch {
      setBackendUnavailable(true);
      setMessage("Could not revoke membership. Check backend availability and org-admin role.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <SettingRows rows={adminSettings} />

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="clinical-card rounded-md p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">Pilot access lifecycle</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-700">
                Manage backend invitation records and active memberships for the local pilot path. Real delivery, MFA enrollment, and Supabase custom-claim sync remain external production work.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center">
              <StatusPill label="Active" value={activeCount} />
              <StatusPill label="Pending" value={pendingCount} />
            </div>
          </div>

          <form className="mt-5 grid gap-3 rounded-md border border-line bg-field p-3 md:grid-cols-[1fr_1fr_150px_auto]" onSubmit={handleInvite}>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Invite email
              <input
                className="min-h-11 rounded-md border border-line bg-white px-3 text-sm text-ink outline-none focus:border-clinical"
                type="email"
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
                placeholder="clinician@example.test"
                required
              />
            </label>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Display name
              <input
                className="min-h-11 rounded-md border border-line bg-white px-3 text-sm text-ink outline-none focus:border-clinical"
                value={inviteName}
                onChange={(event) => setInviteName(event.target.value)}
                placeholder="Pilot Clinician"
                required
              />
            </label>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Role
              <select
                className="min-h-11 rounded-md border border-line bg-white px-3 text-sm text-ink outline-none focus:border-clinical"
                value={inviteRole}
                onChange={(event) => setInviteRole(event.target.value)}
              >
                <option value="therapist">Therapist</option>
                <option value="clinical_supervisor">Supervisor</option>
                <option value="org_admin">Org admin</option>
              </select>
            </label>
            <button
              type="submit"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-clinical px-4 text-sm font-semibold text-white transition hover:bg-clinical-strong disabled:opacity-50"
              disabled={busy}
            >
              <MailPlus size={17} aria-hidden="true" />
              Create invitation
            </button>
          </form>

          {message ? (
            <p className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 px-3 py-2 text-sm font-medium text-cyan-900" role="status">
              {message}
            </p>
          ) : null}

          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            <LifecycleList title="Invitations" empty="No invitation records yet.">
              {invitations.map((invite) => (
                <InvitationRow key={invite.invitation_id} invitation={invite} />
              ))}
            </LifecycleList>
            <LifecycleList title="Memberships" empty="No memberships returned by the backend.">
              {memberships.map((member) => (
                <MembershipRow key={member.membership_id} member={member} busy={busy || loading} onRevoke={() => void handleRevoke(member)} />
              ))}
            </LifecycleList>
          </div>
        </div>

        <aside className="clinical-card rounded-md p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-cyan-50 text-cyan-700">
            <ShieldCheck size={22} aria-hidden="true" />
          </div>
          <h2 className="mt-4 text-base font-semibold text-ink">Production-path guardrails</h2>
          <div className="mt-4 grid gap-3">
            <Guardrail icon={CheckCircle2} label="Invitation backend" value="Implemented locally" />
            <Guardrail icon={CheckCircle2} label="Membership revocation" value="Audited backend action" />
            <Guardrail icon={Clock3} label="MFA enrollment UI" value="External Supabase setup required" />
            <Guardrail icon={AlertTriangle} label="Real clinic rollout" value="Blocked on legal/vendor decisions" />
          </div>
          <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
            Invitation and MFA are enforced by backend guards in production-capable auth mode.
          </p>
        </aside>
      </section>

      {loading ? <p className="text-sm text-slate-600">Loading pilot access lifecycle...</p> : null}
    </>
  );
}

function SettingRows({ rows }: { rows: string[][] }) {
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

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-field p-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink">{value}</p>
    </div>
  );
}

function StatusPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-20 rounded-md border border-line bg-white px-3 py-2">
      <p className="text-lg font-semibold text-ink">{value}</p>
      <p className="text-xs text-slate-600">{label}</p>
    </div>
  );
}

function LifecycleList({ title, empty, children }: { title: string; empty: string; children: React.ReactNode }) {
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

function InvitationRow({ invitation }: { invitation: OrganizationInvitation }) {
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
    </article>
  );
}

function MembershipRow({
  member,
  busy,
  onRevoke
}: {
  member: OrganizationMembership;
  busy: boolean;
  onRevoke: () => void;
}) {
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
        className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-md border border-red-200 bg-white px-3 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:opacity-50"
        disabled={busy || !member.active}
        onClick={onRevoke}
      >
        <UserX size={16} aria-hidden="true" />
        Revoke {member.display_name}
      </button>
    </article>
  );
}

function Guardrail({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
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

function Badge({ children, tone = "cyan" }: { children: React.ReactNode; tone?: "cyan" | "green" | "slate" }) {
  const className = tone === "green"
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
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
