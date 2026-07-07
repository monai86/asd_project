"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock3,
  Download,
  FileCheck2,
  HelpCircle,
  LockKeyhole,
  MailPlus,
  ShieldCheck,
  SlidersHorizontal,
  UserRound,
  UserX
} from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { saveMockAccessSession, type MockRole } from "@/lib/mock-access-session";
import { useMockAccessSession } from "@/lib/use-mock-access-session";
import {
  acceptOrganizationInvitation,
  createOrganizationInvitation,
  getOrganizationReadiness,
  listOrganizationInvitations,
  listOrganizationMemberships,
  revokeOrganizationMembership,
  type OrganizationInvitation,
  type OrganizationMembership,
  type OrganizationReadiness,
  type OrganizationReadinessItem
} from "@/lib/workflow";

type Scope = "therapist" | "admin";

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
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
      <div className="grid gap-4 md:grid-cols-2">
        <SettingsCard icon={UserRound} title="Profile" description="Therapist workspace identity for the local pilot interface.">
          <SettingLine label="Name" value="Demo Therapist" />
          <SettingLine label="Role" value="Speech therapist / clinician" />
          <SettingLine label="Organization" value="Pilot organization workspace" />
          <SettingLine label="Data mode" value="Demo mode" />
        </SettingsCard>

        <SettingsCard icon={SlidersHorizontal} title="Preferences" description="Local interface defaults only; backend workflow records remain authoritative.">
          <SettingLine label="Workspace start page" value="Work Queue" />
          <SettingLine label="Sample data" value="Anonymized local demo data only" />
          <SettingLine label="Language sample workflow" value="Transcript review first" />
          <SettingLine label="Experimental audio" value="Clearly labeled" />
        </SettingsCard>

        <SettingsCard icon={Bell} title="Notification preferences" description="Operational notification support is intentionally limited in this prototype.">
          <SettingLine label="In-app reminders" value="Available" />
          <SettingLine label="Email delivery" value="Not configured" tone="muted" />
          <SettingLine label="Caregiver messages" value="Not configured" tone="muted" />
          <SettingLine label="Clinical content in alerts" value="Not allowed" tone="warning" />
        </SettingsCard>

        <SettingsCard icon={Download} title="Export/report preferences" description="Exports stay gated by transcript review, report validation, and sign-off.">
          <SettingLine label="Markdown export" value="Configured after sign-off" />
          <SettingLine label="HTML export" value="Configured after sign-off" />
          <SettingLine label="PDF export" value="Not configured" tone="muted" />
          <SettingLine label="Caregiver share status" value="Local/demo only" />
        </SettingsCard>

        <SettingsCard icon={LockKeyhole} title="Security" description="Shows actual configured state; no production compliance claims are made here.">
          <SettingLine label="Authentication" value="Demo workspace" />
          <SettingLine label="Production MFA" value="Not configured" tone="muted" />
          <SettingLine label="Secure messaging" value="Not configured" tone="muted" />
          <SettingLine label="Session storage" value="UI cache only" />
        </SettingsCard>

        <section className="rounded-[1.5rem] border border-amber-200 bg-amber-50 p-5 text-amber-950">
          <div className="flex items-start gap-3">
            <ShieldCheck size={22} aria-hidden="true" className="mt-0.5 shrink-0" />
            <div>
              <h2 className="text-lg font-bold">Privacy & consent reminder</h2>
              <p className="mt-2 text-sm leading-6">
                Consent status must be checked per case before transcript review, feature extraction, report drafting, or export.
              </p>
              <p className="mt-2 text-sm leading-6">
                No HIPAA compliance claim is made by this prototype workspace.
              </p>
            </div>
          </div>
        </section>
      </div>

      <aside className="space-y-4 xl:sticky xl:top-24 xl:self-start">
        <section className="clinical-card rounded-[1.5rem] p-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cyan-50 text-cyan-700">
            <HelpCircle size={22} aria-hidden="true" />
          </div>
          <h2 className="mt-4 text-lg font-bold text-ink">Help & guidance</h2>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Use the session intake, transcript review, results, and report screens in order. Backend records are the source of truth when IDs exist.
          </p>
          <div className="mt-4 grid gap-3">
            <StatusTile label="Transcript gate" value="Quality attestation required" />
            <StatusTile label="Report export" value="Sign-off required" />
            <StatusTile label="Clinical boundary" value="Decision-support only" />
          </div>
        </section>

        <section className="rounded-[1.5rem] border border-cyan-100 bg-cyan-50 p-5">
          <h2 className="text-base font-bold text-cyan-950">Therapist pilot workspace</h2>
          <p className="mt-2 text-sm leading-6 text-cyan-950">
            This local path is for exploring the workspace with anonymized demo data. It does not create production accounts or production delivery channels.
          </p>
        </section>
      </aside>
    </section>
  );
}

function SettingsCard({
  children,
  description,
  icon: Icon,
  title
}: {
  children: React.ReactNode;
  description: string;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <section className="clinical-card rounded-[1.5rem] p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-cyan-50 text-cyan-700">
          <Icon size={21} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-lg font-bold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>
      <div className="mt-4 divide-y divide-line/70 rounded-2xl border border-line bg-white/70">
        {children}
      </div>
    </section>
  );
}

function SettingLine({ label, tone = "default", value }: { label: string; tone?: "default" | "muted" | "warning"; value: string }) {
  const valueClassName = tone === "warning" ? "text-amber-800" : tone === "muted" ? "text-slate-600" : "text-ink";
  return (
    <div className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[150px_1fr]">
      <span className="font-semibold text-slate-600">{label}</span>
      <span className={`font-bold ${valueClassName}`}>{value}</span>
    </div>
  );
}

function AdminSettings() {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const session = useMockAccessSession();
  const [memberships, setMemberships] = useState<OrganizationMembership[]>(fallbackMemberships);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>(fallbackInvitations);
  const [readiness, setReadiness] = useState<OrganizationReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [preparedInviteSessionId, setPreparedInviteSessionId] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("therapist");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void (async () => {
      try {
        const [loadedMemberships, loadedInvitations, loadedReadiness] = await Promise.all([
          listOrganizationMemberships(),
          listOrganizationInvitations(),
          getOrganizationReadiness().catch(() => null)
        ]);
        if (!Array.isArray(loadedMemberships) || !Array.isArray(loadedInvitations)) {
          throw new Error("Malformed admin lifecycle payload.");
        }
        if (cancelled) return;
        setMemberships(loadedMemberships);
        setInvitations(loadedInvitations);
        setReadiness(isOrganizationReadiness(loadedReadiness) ? loadedReadiness : null);
        setBackendUnavailable(false);
      } catch {
        if (cancelled) return;
        setBackendUnavailable(true);
        setReadiness(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session?.organizationId, setBackendUnavailable]);

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

  async function refreshLifecycleState() {
    const [loadedMemberships, loadedInvitations] = await Promise.all([
      listOrganizationMemberships(),
      listOrganizationInvitations()
    ]);
    setMemberships(loadedMemberships);
    setInvitations(loadedInvitations);
  }

  async function handleAcceptInvitation(invitation: OrganizationInvitation) {
    setBusy(true);
    setMessage("");
    setPreparedInviteSessionId(null);
    try {
      const accepted = await acceptOrganizationInvitation(invitation.invitation_id, {
        user_id: buildInvitedUserId(invitation.email)
      });
      await refreshLifecycleState();
      setMessage(`Invitation accepted for ${accepted.display_name}. Membership is active and MFA enrollment is required before app access.`);
      setBackendUnavailable(false);
    } catch {
      setBackendUnavailable(true);
      setMessage("Could not accept invitation. Expired invitations require a newly issued invitation.");
    } finally {
      setBusy(false);
    }
  }

  function handlePrepareAcceptedSession(invitation: OrganizationInvitation) {
    if (!isMockRole(invitation.role)) {
      setMessage("Only clinic roles can open a mock invited session.");
      return;
    }
    saveMockAccessSession({
      role: invitation.role,
      organizationId: invitation.organization_id,
      aal: "aal1",
    });
    setPreparedInviteSessionId(invitation.invitation_id);
    setMessage(`Prepared an AAL1 invited session for ${invitation.display_name}. The next app page will stop at the MFA gate until promoted to AAL2.`);
  }

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <section className="clinical-card rounded-[1.5rem] p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-700">Admin scope</p>
            <h2 className="mt-2 text-2xl font-bold text-ink">Pilot admin controls</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              These controls are pilot/admin lifecycle tools, not production account management.
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3 lg:min-w-[360px]">
            <StatusTile label="Invitations" value="Available" />
            <StatusTile label="Audit trail" value="Available" />
            <StatusTile label="Real MFA" value="Not configured" />
          </div>
        </div>
      </section>
      <SettingRows rows={adminSettings} />
      <ReadinessCockpit readiness={readiness} activeCount={activeCount} pendingCount={pendingCount} />

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

          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
            <p className="font-semibold">Pilot-only boundary</p>
            <p className="mt-1">
              This panel does not send real invitation emails, does not represent the production Supabase acceptance
              path, and cannot provision production MFA enrollment on its own.
            </p>
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
                <InvitationRow
                  key={invite.invitation_id}
                  invitation={invite}
                  busy={busy || loading}
                  prepared={preparedInviteSessionId === invite.invitation_id}
                  onAccept={() => void handleAcceptInvitation(invite)}
                  onPrepareSession={() => void handlePrepareAcceptedSession(invite)}
                />
              ))}
            </LifecycleList>
            <LifecycleList title="Memberships" empty="No memberships returned by the backend.">
              {memberships.map((member) => (
                <MembershipRow key={member.membership_id} member={member} busy={busy || loading} onRevoke={() => void handleRevoke(member)} />
              ))}
            </LifecycleList>
          </div>
        </div>

        <aside className="space-y-4">
        <section className="clinical-card rounded-[1.5rem] p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-cyan-50 text-cyan-700">
            <ShieldCheck size={22} aria-hidden="true" />
          </div>
          <h2 className="mt-4 text-base font-semibold text-ink">Admin safety boundaries</h2>
          <div className="mt-4 grid gap-3">
            <Guardrail icon={CheckCircle2} label="Invitation backend" value="Implemented locally" />
            <Guardrail icon={CheckCircle2} label="Membership revocation" value="Audited backend action" />
            <Guardrail icon={Clock3} label="Real MFA enrollment" value="Not configured" />
            <Guardrail icon={AlertTriangle} label="Real clinic rollout" value="Blocked on legal/vendor decisions" />
          </div>
          <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
            Production invitation delivery and acceptance stay outside this panel. This pilot UI exists only to exercise
            local lifecycle scaffolding and backend guard behavior.
          </p>
        </section>

        <section className="clinical-card rounded-[1.5rem] p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-amber-50 text-amber-700">
            <FileCheck2 size={22} aria-hidden="true" />
          </div>
          <h2 className="mt-4 text-base font-semibold text-ink">Audit & break-glass</h2>
          <div className="mt-4 grid gap-3">
            <Guardrail icon={ShieldCheck} label="Break-glass access" value="Scoped backend workflow with audit events" />
            <Guardrail icon={CheckCircle2} label="Audit trail available" value="Backend records actor, target, outcome, and timestamp" />
            <Guardrail icon={AlertTriangle} label="Clinical data in logs" value="Not allowed" />
          </div>
        </section>
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

function ReadinessCockpit({
  activeCount,
  pendingCount,
  readiness
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
      detail: "The app could not load the readiness endpoint; lifecycle data may be using local fallback state.",
      evidence: ["readiness_endpoint=unavailable"],
      next_action: "Restore the backend readiness endpoint before making rollout decisions."
    } satisfies OrganizationReadinessItem
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
        <span className="shrink-0 rounded-md bg-white/70 px-2 py-1 text-xs font-semibold capitalize">{item.status}</span>
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
        <p className="mt-3 rounded-md bg-white/65 p-2 text-xs font-medium leading-5">
          Next action: {item.next_action}
        </p>
      ) : null}
    </article>
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

function InvitationRow({
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
          className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-md border border-cyan-200 bg-white px-3 text-sm font-semibold text-cyan-800 transition hover:bg-cyan-50 disabled:opacity-50"
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
            className="inline-flex min-h-10 items-center gap-2 rounded-md border border-amber-200 bg-white px-3 text-sm font-semibold text-amber-900 transition hover:bg-amber-50 disabled:opacity-50"
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

function Badge({ children, tone = "cyan" }: { children: React.ReactNode; tone?: "cyan" | "green" | "slate" | "amber" }) {
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

function buildInvitedUserId(email: string) {
  return `invite_${email.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "member"}`;
}

function isMockRole(role: string): role is MockRole {
  return role === "therapist" || role === "clinical_supervisor" || role === "org_admin";
}

function isOrganizationReadiness(value: unknown): value is OrganizationReadiness {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<OrganizationReadiness>;
  return typeof candidate.organization_id === "string"
    && typeof candidate.pilot_ready === "boolean"
    && typeof candidate.production_ready === "boolean"
    && Array.isArray(candidate.items);
}

function formatReadinessValue(value: string) {
  return value.replace(/_/g, " ");
}
