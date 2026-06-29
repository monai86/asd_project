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
    <form className="clinical-card self-start rounded-md p-5" aria-label="Mock login form">
      <div className="mb-5 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-md bg-clinical text-white">
          <ShieldCheck size={20} aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-semibold">Mock login</h2>
          <p className="text-xs text-slate-600">Therapist, supervisor, and org-admin demo roles are available for local exploration.</p>
        </div>
      </div>
      <label className="mb-4 block text-sm font-medium">
        Email
        <input className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2" defaultValue="therapist@example.test" type="email" />
      </label>
      <label className="mb-3 block text-sm font-medium">
        Role
        <select
          className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2"
          value={role}
          onChange={(event) => setRole(event.target.value as MockRole)}
        >
          <option value="therapist">Therapist</option>
          <option value="clinical_supervisor">Clinical supervisor</option>
          <option value="org_admin">Org admin</option>
        </select>
      </label>
      <label className="mb-3 block text-sm font-medium">
        Active organization session
        <select
          className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2"
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
      <label className="mb-3 block text-sm font-medium">
        Session assurance
        <select
          className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2"
          value={aal}
          onChange={(event) => setAal(event.target.value as "aal1" | "aal2")}
        >
          <option value="aal2">AAL2</option>
          <option value="aal1">AAL1</option>
        </select>
      </label>
      <p className="mb-4 text-xs text-slate-600" aria-live="polite">
        {role === "org_admin"
          ? "Org admin opens assignment-safe runtime controls."
          : role === "clinical_supervisor"
            ? "Clinical supervisor opens the work queue with org-wide oversight."
            : "Therapist opens Today / Work Queue."}
      </p>
      <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
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
      <div className="mb-4 rounded-md border border-cyan-100 bg-cyan-50 p-3 text-xs text-cyan-950">
        <div className="flex items-start gap-2">
          <LockKeyhole size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Production access boundary</p>
            <p className="mt-1">
              {runtimeSettings?.access_model?.invitation_only === false
                ? "Runtime settings do not currently enforce invitation-only onboarding."
                : "Production access stays invitation-only and requires AAL2 before app access."}
            </p>
            <p className="mt-1 text-cyan-900/80">
              Mock mode is for local exploration only and does not provision real clinic accounts or real organization sessions.
            </p>
          </div>
        </div>
      </div>
      <Link
        href={destination}
        onClick={() => saveMockAccessSession({ role, organizationId, aal })}
        className="inline-flex w-full justify-center rounded-md bg-clinical px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-clinical"
      >
        Enter workspace
      </Link>
    </form>
  );
}
