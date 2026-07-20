"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  MailPlus,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { CareTeamAdministration } from "@/features/settings/components/care-team-administration";
import {
  Guardrail,
  InvitationRow,
  LifecycleList,
  MembershipRow,
  ReadinessCockpit,
  SettingRows,
  StatusPill,
  StatusTile,
} from "@/features/settings/components/settings-presentational";
import { TherapistSettings } from "@/features/settings/components/therapist-settings";
import {
  allowedSettingsSections,
  resolveAuthorizedSection,
  type SettingsRole,
  type SettingsSection,
} from "@/features/settings/services/settings-access";
import { saveMockAccessSession, type MockRole } from "@/lib/mock-access-session";
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
} from "@/lib/workflow";

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

type SettingsWorkspaceProps = {
  role: SettingsRole | null;
  requestedSection?: unknown;
  organizationId?: string | null;
  caseId?: string | null;
};

export function SettingsWorkspace({
  role,
  requestedSection = "profile",
  organizationId,
  caseId,
}: SettingsWorkspaceProps) {
  const initialResolution = resolveAuthorizedSection(role, requestedSection);
  const [section, setSection] = useState<SettingsSection>(initialResolution.section);
  const canAccessAdmin = allowedSettingsSections(role).includes("team") && role === "org_admin";

  useEffect(() => {
    setSection(resolveAuthorizedSection(role, requestedSection).section);
  }, [requestedSection, role]);

  const adminSectionSelected = section === "team" || section === "audit";

  return (
    <section className="grid min-w-0 gap-5">
      {canAccessAdmin ? (
        <div className="inline-flex w-fit rounded-md border border-line bg-[color:var(--color-surface-reading)] p-1" aria-label="Settings scope">
          <button
            type="button"
            className={`inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-medium transition ${
              !adminSectionSelected ? "bg-clinical text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
            onClick={() => setSection(resolveAuthorizedSection(role, "profile").section)}
            aria-pressed={!adminSectionSelected}
          >
            <UserRound size={16} aria-hidden="true" />
            Therapist
          </button>
          <button
            type="button"
            className={`inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-medium transition ${
              adminSectionSelected ? "bg-clinical text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
            onClick={() => setSection(resolveAuthorizedSection(role, "team").section)}
            aria-pressed={adminSectionSelected}
          >
            <ShieldCheck size={16} aria-hidden="true" />
            Admin
          </button>
        </div>
      ) : null}

      {adminSectionSelected && canAccessAdmin
        ? <AdminSettings organizationId={organizationId ?? null} initialCaseId={caseId ?? null} />
        : <TherapistSettings />}
    </section>
  );
}


function AdminSettings({ organizationId, initialCaseId }: { organizationId: string | null; initialCaseId: string | null }) {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const organizationIdRef = useRef(organizationId);
  organizationIdRef.current = organizationId;
  const renderedOrganizationIdRef = useRef(organizationId);
  const mutationRequestIdRef = useRef(0);
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
    const organizationChanged = renderedOrganizationIdRef.current !== organizationId;
    renderedOrganizationIdRef.current = organizationId;
    mutationRequestIdRef.current += 1;
    setLoading(true);
    setBusy(false);
    setMessage("");
    if (organizationChanged) {
      setMemberships([]);
      setInvitations([]);
      setReadiness(null);
    }
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
  }, [organizationId, setBackendUnavailable]);

  const activeCount = useMemo(() => memberships.filter((member) => member.active).length, [memberships]);
  const pendingCount = useMemo(() => invitations.filter((invite) => invite.status === "pending").length, [invitations]);

  async function handleInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!inviteEmail.trim() || !inviteName.trim()) return;
    setBusy(true);
    setMessage("");
    const request = beginMutationRequest();
    try {
      const created = await createOrganizationInvitation({
        email: inviteEmail.trim(),
        display_name: inviteName.trim(),
        role: inviteRole
      });
      if (!isCurrentMutationRequest(request)) return;
      setInvitations((current) => [created, ...current]);
      setInviteEmail("");
      setInviteName("");
      setInviteRole("therapist");
      setMessage(`Invitation created for ${created.display_name}.`);
      setBackendUnavailable(false);
    } catch {
      if (!isCurrentMutationRequest(request)) return;
      setBackendUnavailable(true);
      setMessage("Could not create invitation. The local API workspace is unavailable.");
    } finally {
      if (isCurrentMutationRequest(request)) setBusy(false);
    }
  }

  async function handleRevoke(member: OrganizationMembership) {
    setBusy(true);
    setMessage("");
    const request = beginMutationRequest();
    try {
      const revoked = await revokeOrganizationMembership(member.membership_id);
      if (!isCurrentMutationRequest(request)) return;
      setMemberships((current) => current.map((item) => item.membership_id === revoked.membership_id ? revoked : item));
      setMessage(`Membership revoked for ${revoked.display_name}. Care-team assignments are deactivated by the backend.`);
      setBackendUnavailable(false);
    } catch {
      if (!isCurrentMutationRequest(request)) return;
      setBackendUnavailable(true);
      setMessage("Could not revoke membership. Check backend availability and org-admin role.");
    } finally {
      if (isCurrentMutationRequest(request)) setBusy(false);
    }
  }

  async function refreshLifecycleState(request: AdminMutationRequest) {
    const [loadedMemberships, loadedInvitations] = await Promise.all([
      listOrganizationMemberships(),
      listOrganizationInvitations()
    ]);
    if (!isCurrentMutationRequest(request)) return false;
    setMemberships(loadedMemberships);
    setInvitations(loadedInvitations);
    return true;
  }

  async function handleAcceptInvitation(invitation: OrganizationInvitation) {
    setBusy(true);
    setMessage("");
    setPreparedInviteSessionId(null);
    const request = beginMutationRequest();
    try {
      const accepted = await acceptOrganizationInvitation(invitation.invitation_id, {
        user_id: buildInvitedUserId(invitation.email)
      });
      if (!await refreshLifecycleState(request)) return;
      setMessage(`Invitation accepted for ${accepted.display_name}. Membership is active and MFA enrollment is required before app access.`);
      setBackendUnavailable(false);
    } catch {
      if (!isCurrentMutationRequest(request)) return;
      setBackendUnavailable(true);
      setMessage("Could not accept invitation. Expired invitations require a newly issued invitation.");
    } finally {
      if (isCurrentMutationRequest(request)) setBusy(false);
    }
  }

  type AdminMutationRequest = {
    organizationId: string | null;
    requestId: number;
  };

  function beginMutationRequest(): AdminMutationRequest {
    return {
      organizationId: organizationIdRef.current,
      requestId: ++mutationRequestIdRef.current,
    };
  }

  function isCurrentMutationRequest(request: AdminMutationRequest): boolean {
    return organizationIdRef.current === request.organizationId
      && mutationRequestIdRef.current === request.requestId;
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
      <CareTeamAdministration memberships={memberships} initialCaseId={initialCaseId} />

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

          <form className="mt-5 grid min-w-0 gap-3 rounded-md border border-line bg-field p-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_150px_auto]" onSubmit={handleInvite}>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Invite email
              <input
                className="min-h-11 rounded-md border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm text-ink outline-none focus:border-clinical"
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
                className="min-h-11 rounded-md border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm text-ink outline-none focus:border-clinical"
                value={inviteName}
                onChange={(event) => setInviteName(event.target.value)}
                placeholder="Pilot Clinician"
                required
              />
            </label>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Role
              <select
                className="min-h-11 rounded-md border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm text-ink outline-none focus:border-clinical"
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
