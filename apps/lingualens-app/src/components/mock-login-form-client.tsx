"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Building2, LockKeyhole, ShieldCheck } from "lucide-react";

import { type RuntimeSettings } from "@/lib/api";
import {
  MOCK_ORGANIZATION_OPTIONS,
  type MockRole,
  saveMockAccessSession,
} from "@/lib/mock-access-session";

const roleDestinations: Record<MockRole, string> = {
  therapist: "/today?role=therapist",
  clinical_supervisor: "/today?role=clinical_supervisor",
  org_admin: "/settings?scope=admin&role=org_admin"
};

export function MockLoginFormClient({
  runtimeSettings,
}: {
  runtimeSettings: RuntimeSettings | null;
}) {
  const [role, setRole] = useState<MockRole>("therapist");
  const [organizationId, setOrganizationId] = useState(MOCK_ORGANIZATION_OPTIONS.therapist[0].organizationId);
  const [aal, setAal] = useState<"aal1" | "aal2">("aal2");
  const destination = roleDestinations[role];
  const organizationOptions = MOCK_ORGANIZATION_OPTIONS[role];
  const requiresExplicitOrganizationSelection = organizationOptions.length > 1;

  useEffect(() => {
    setOrganizationId(MOCK_ORGANIZATION_OPTIONS[role][0].organizationId);
  }, [role]);

  return (
    <form className="workspace-panel self-start p-5 sm:p-6" aria-label="Mock login form">
      <div className="mb-5 flex items-start gap-3">
        <ShieldCheck size={22} aria-hidden="true" className="mt-0.5 shrink-0 text-[color:var(--color-accent)]" />
        <div>
          <h2 className="font-semibold text-[color:var(--color-text-strong)]">Mock login</h2>
          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">Therapist, supervisor, and org-admin demo roles are available for local exploration.</p>
        </div>
      </div>
      <label className="mb-4 block text-sm font-medium text-[color:var(--color-text-strong)]">
        Email
        <input className="mt-1 min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 py-2 text-[color:var(--color-text-strong)]" defaultValue="therapist@example.test" type="email" />
      </label>
      <label className="mb-3 block text-sm font-medium text-[color:var(--color-text-strong)]">
        Role
        <select
          className="mt-1 min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 py-2 text-[color:var(--color-text-strong)]"
          value={role}
          onChange={(event) => setRole(event.target.value as MockRole)}
        >
          <option value="therapist">Therapist</option>
          <option value="clinical_supervisor">Clinical supervisor</option>
          <option value="org_admin">Org admin</option>
        </select>
      </label>
      <label className="mb-3 block text-sm font-medium text-[color:var(--color-text-strong)]">
        Active organization session
        <select
          className="mt-1 min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 py-2 text-[color:var(--color-text-strong)]"
          value={organizationId}
          onChange={(event) => setOrganizationId(event.target.value)}
        >
          {organizationOptions.map((option) => (
            <option key={option.organizationId} value={option.organizationId}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="mb-3 block text-sm font-medium text-[color:var(--color-text-strong)]">
        Session assurance
        <select
          className="mt-1 min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 py-2 text-[color:var(--color-text-strong)]"
          value={aal}
          onChange={(event) => setAal(event.target.value as "aal1" | "aal2")}
        >
          <option value="aal2">AAL2</option>
          <option value="aal1">AAL1</option>
        </select>
      </label>
      <p className="mb-4 text-sm leading-6 text-[color:var(--color-text-muted)]" aria-live="polite">
        {role === "org_admin"
          ? "Org admin opens assignment-safe runtime controls."
          : role === "clinical_supervisor"
            ? "Clinical supervisor opens the work queue with org-wide oversight."
            : "Therapist opens Today / Work Queue."}
      </p>
      <div className="mb-4 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-3 text-sm leading-6 text-[color:var(--color-text-muted)]">
        <div className="flex items-start gap-2">
          <Building2 size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Organization session selection</p>
            <p className="mt-1">
              {requiresExplicitOrganizationSelection
                ? "This mock role simulates multiple memberships, so the active organization must be selected explicitly before workspace access."
                : "This mock role has a single organization membership, so the active organization is preselected."}
            </p>
            <p className="mt-1">
              Selecting <strong>AAL1</strong> will stop at the MFA gate until the session is promoted to <strong>AAL2</strong>.
            </p>
          </div>
        </div>
      </div>
      <div className="mb-4 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-accent-soft)] p-3 text-sm leading-6 text-[color:var(--color-accent-strong)]">
        <div className="flex items-start gap-2">
          <LockKeyhole size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Production access boundary</p>
            <p className="mt-1">
              {runtimeSettings?.access_model?.invitation_only === false
                ? "Runtime settings do not currently enforce invitation-only onboarding."
                : "Production access stays invitation-only and requires AAL2 before app access."}
            </p>
            <p className="mt-1">
              Mock mode is for local exploration only and does not provision real clinic accounts or real organization sessions.
            </p>
          </div>
        </div>
      </div>
      <Link
        href={destination}
        onClick={() => saveMockAccessSession({ role, organizationId, aal })}
        className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] bg-[color:var(--color-accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)] motion-reduce:transition-none"
      >
        Enter workspace
      </Link>
    </form>
  );
}
