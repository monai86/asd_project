"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  MailPlus,
  ShieldCheck,
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
} from "@/features/settings/components/settings-presentational";
import { TherapistSettings } from "@/features/settings/components/therapist-settings";
import { SettingsNavigation } from "@/features/settings/components/settings-navigation";
import {
  allowedSettingsSections,
  isAdminSettingsSection,
  isSharedSettingsSection,
  resolveAuthorizedSection,
  type AdminSettingsSection,
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

type SettingsWorkspaceProps = {
  role: SettingsRole | null;
  requestedSection?: unknown;
  requestedSectionExplicit?: boolean;
  organizationId?: string | null;
  caseId?: string | null;
};

export function SettingsWorkspace({
  role,
  requestedSection = "account",
  requestedSectionExplicit = false,
  organizationId,
  caseId,
}: SettingsWorkspaceProps) {
  const initialResolution = resolveAuthorizedSection(role, requestedSection);
  const [section, setSection] = useState<SettingsSection>(initialResolution.section);
  const [mobileIndexOpen, setMobileIndexOpen] = useState(!requestedSectionExplicit);
  const sections = allowedSettingsSections(role);
  const canAccessAdmin = role === "org_admin";

  useEffect(() => {
    setSection(resolveAuthorizedSection(role, requestedSection).section);
    setMobileIndexOpen(!requestedSectionExplicit);
  }, [requestedSection, requestedSectionExplicit, role]);

  useEffect(() => {
    function restoreSectionFromHistory() {
      const requested = new URLSearchParams(window.location.search).get("section");
      setSection(resolveAuthorizedSection(role, requested).section);
      setMobileIndexOpen(requested === null);
    }
    window.addEventListener("popstate", restoreSectionFromHistory);
    return () => window.removeEventListener("popstate", restoreSectionFromHistory);
  }, [role]);

  function selectSection(nextSection: SettingsSection) {
    const resolution = resolveAuthorizedSection(role, nextSection);
    setSection(resolution.section);
    setMobileIndexOpen(false);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("section", resolution.section);
      url.searchParams.delete("scope");
      url.searchParams.delete("notice");
      window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
    }
  }

  const adminSectionSelected = isAdminSettingsSection(section) && canAccessAdmin;
  const therapistSection = isSharedSettingsSection(section) ? section : "account";

  return (
    <section
      className="grid min-w-0 gap-4 md:grid-cols-[220px_minmax(0,1fr)] md:items-start"
      data-testid="settings-workspace"
      data-mobile-view={mobileIndexOpen ? "categories" : "detail"}
    >
      <SettingsNavigation
        sections={sections}
        selected={section}
        onSelect={selectSection}
        mobileIndexOpen={mobileIndexOpen}
        onOpenMobileIndex={() => setMobileIndexOpen(true)}
      />
      <div className={`${mobileIndexOpen ? "hidden md:block" : "block"} min-w-0`}>
        {adminSectionSelected
          ? <AdminSettings section={section} organizationId={organizationId ?? null} initialCaseId={caseId ?? null} />
          : <TherapistSettings section={therapistSection} />}
      </div>
    </section>
  );
}


function AdminSettings({ section, organizationId, initialCaseId }: { section: AdminSettingsSection; organizationId: string | null; initialCaseId: string | null }) {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const organizationIdRef = useRef(organizationId);
  organizationIdRef.current = organizationId;
  const mutationRequestIdRef = useRef(0);
  const [memberships, setMemberships] = useState<OrganizationMembership[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
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
    mutationRequestIdRef.current += 1;
    setLoading(true);
    setBusy(false);
    setMessage("");
    setMemberships([]);
    setInvitations([]);
    setReadiness(null);
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
        setMemberships([]);
        setInvitations([]);
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

  let content;
  if (section === "team") {
    content = (
      <div className="grid gap-4">
        <AdminSectionHeader title="Team" description="Manage organization membership and care-team assignments through backend-authorized actions." />
        <CareTeamAdministration memberships={memberships} initialCaseId={initialCaseId} />
        <section className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-base font-semibold text-ink">Organization memberships</h3>
            <StatusPill label="Active" value={activeCount} />
          </div>
          <LifecycleList title="Memberships" empty="No memberships returned by the backend.">
            {memberships.map((member) => (
              <MembershipRow key={member.membership_id} member={member} busy={busy || loading} onRevoke={() => void handleRevoke(member)} />
            ))}
          </LifecycleList>
        </section>
      </div>
    );
  } else if (section === "invitations") {
    content = (
      <div className="grid gap-4">
        <AdminSectionHeader title="Invitations" description="Create and review invitation records for the local pilot lifecycle." />
        <section className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-ink">Pilot access lifecycle</h3>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-700">
                Real delivery, MFA enrollment, and Supabase custom-claim sync remain external production work.
              </p>
            </div>
            <StatusPill label="Pending" value={pendingCount} />
          </div>
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
            <p className="font-semibold">Pilot-only boundary</p>
            <p className="mt-1">This panel does not send real invitation emails or provision production MFA enrollment.</p>
          </div>
          <form className="mt-5 grid min-w-0 gap-3 rounded-md border border-line bg-field p-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_150px_auto]" onSubmit={handleInvite}>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Invite email
              <input className="min-h-11 rounded-md border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm text-ink outline-none focus:border-clinical" type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="clinician@example.test" required />
            </label>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Display name
              <input className="min-h-11 rounded-md border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm text-ink outline-none focus:border-clinical" value={inviteName} onChange={(event) => setInviteName(event.target.value)} placeholder="Pilot Clinician" required />
            </label>
            <label className="grid gap-1 text-sm font-medium text-ink">
              Role
              <select className="min-h-11 rounded-md border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm text-ink outline-none focus:border-clinical" value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}>
                <option value="therapist">Therapist</option>
                <option value="clinical_supervisor">Supervisor</option>
                <option value="org_admin">Org admin</option>
              </select>
            </label>
            <button type="submit" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-clinical px-4 text-sm font-semibold text-white transition hover:bg-clinical-strong disabled:opacity-50" disabled={busy}>
              <MailPlus size={17} aria-hidden="true" />
              Create invitation
            </button>
          </form>
          <div className="mt-5">
            <LifecycleList title="Invitations" empty="No invitation records returned by the backend.">
              {invitations.map((invite) => (
                <InvitationRow key={invite.invitation_id} invitation={invite} busy={busy || loading} prepared={preparedInviteSessionId === invite.invitation_id} onAccept={() => void handleAcceptInvitation(invite)} onPrepareSession={() => void handlePrepareAcceptedSession(invite)} />
              ))}
            </LifecycleList>
          </div>
        </section>
      </div>
    );
  } else if (section === "audit") {
    content = (
      <div className="grid gap-4">
        <AdminSectionHeader title="Audit" description="Review the scope and guarantees of backend audit records." />
        <section className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-amber-50 text-amber-700"><FileCheck2 size={22} aria-hidden="true" /></div>
          <h3 className="mt-4 text-base font-semibold text-ink">Audit & break-glass</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Guardrail icon={ShieldCheck} label="Break-glass access" value="Scoped backend workflow with audit events" />
            <Guardrail icon={CheckCircle2} label="Audit trail available" value="Backend records actor, target, outcome, and timestamp" />
            <Guardrail icon={CheckCircle2} label="Role and invitation actions" value="Recorded by backend organization-management routes" />
            <Guardrail icon={AlertTriangle} label="Clinical data in logs" value="Not allowed" />
          </div>
        </section>
      </div>
    );
  } else if (section === "privacy_operations") {
    content = (
      <div className="grid gap-4">
        <AdminSectionHeader title="Privacy Operations" description="Organization-level privacy workflows remain backend-authorized and auditable." />
        <section className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-5">
          <div className="grid gap-3 md:grid-cols-2">
            <Guardrail icon={ShieldCheck} label="Authorization" value="Organization-admin role required at the backend boundary" />
            <Guardrail icon={CheckCircle2} label="Audit logging" value="Privacy actions retain actor, target, outcome, and timestamp" />
            <Guardrail icon={Clock3} label="Request history" value="Backend-confirmed records only; no inferred empty history" />
            <Guardrail icon={AlertTriangle} label="Demo mode" value="Production privacy operations are unavailable" />
          </div>
        </section>
      </div>
    );
  } else {
    content = (
      <div className="grid gap-4">
        <AdminSectionHeader title="Integration Status" description="Backend-derived readiness and server-owned runtime boundaries." />
        <SettingRows rows={adminSettings} />
        <ReadinessCockpit readiness={readiness} activeCount={activeCount} pendingCount={pendingCount} />
        <section className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-4">
          <h3 className="text-base font-semibold text-ink">Admin safety boundaries</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Guardrail icon={CheckCircle2} label="Invitation backend" value="Implemented locally" />
            <Guardrail icon={CheckCircle2} label="Membership revocation" value="Audited backend action" />
            <Guardrail icon={Clock3} label="Real MFA enrollment" value="Not configured" />
            <Guardrail icon={AlertTriangle} label="Real clinic rollout" value="Blocked on legal/vendor decisions" />
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      {message ? <p className="rounded-md border border-cyan-100 bg-cyan-50 px-3 py-2 text-sm font-medium text-cyan-900" role="status">{message}</p> : null}
      {content}
      {loading ? <p className="text-sm text-slate-600">Loading organization settings...</p> : null}
    </div>
  );
}

function AdminSectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">Organization administration</p>
      <h2 className="mt-2 text-xl font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{description}</p>
    </section>
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
