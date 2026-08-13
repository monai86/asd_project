"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { SettingsWorkspace } from "@/features/settings/components/settings-workspace";
import {
  isAdminSettingsSection,
  resolveAuthorizedSection,
  type SettingsRole,
  type SettingsSection,
} from "@/features/settings/services/settings-access";
import { useConfirmedRuntimeSettings } from "@/lib/confirmed-runtime-settings";
import { useMockAccessSession } from "@/lib/use-mock-access-session";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

type LegacySettingsScope = "therapist" | "admin";

type SettingsWorkspaceClientProps = {
  initialScope?: LegacySettingsScope;
  initialSection?: SettingsSection;
  initialSectionExplicit?: boolean;
  role?: SettingsRole | null;
  organizationId?: string | null;
  caseId?: string | null;
  notice?: "not-authorized";
  confirmedAuthMode?: "mock" | "supabase";
};

export function SettingsWorkspaceClient({
  ...props
}: SettingsWorkspaceClientProps) {
  if (props.confirmedAuthMode !== undefined) {
    return <SettingsWorkspaceClientIdentity {...props} runtimeAuthMode={props.confirmedAuthMode} />;
  }
  return <RuntimeResolvedSettingsWorkspaceClient {...props} />;
}

function RuntimeResolvedSettingsWorkspaceClient(props: SettingsWorkspaceClientProps) {
  const runtimeSettings = useConfirmedRuntimeSettings();
  const runtimeAuthMode = runtimeSettings?.auth_mode ?? null;
  return <SettingsWorkspaceClientIdentity {...props} runtimeAuthMode={runtimeAuthMode} />;
}

function SettingsWorkspaceClientIdentity({
  initialScope = "therapist",
  initialSection,
  initialSectionExplicit,
  role,
  organizationId,
  caseId,
  notice,
  runtimeAuthMode,
}: SettingsWorkspaceClientProps & { runtimeAuthMode: "mock" | "supabase" | null }) {
  const router = useRouter();
  const mockSession = useMockAccessSession();
  const supabaseSession = useSupabaseAccessSession();
  const [browserIdentityHydrated, setBrowserIdentityHydrated] = useState(false);
  useEffect(() => {
    setBrowserIdentityHydrated(true);
  }, []);
  const authenticatedSupabaseSession = supabaseSession?.stage === "authenticated"
    && supabaseSession.aal === "aal2"
    && supabaseSession.organizationId
      ? supabaseSession
      : null;
  const browserRole = runtimeAuthMode === "mock"
    ? mockSession?.role ?? null
    : runtimeAuthMode === "supabase"
      ? authenticatedSupabaseSession?.role ?? null
      : null;
  const browserOrganizationId = runtimeAuthMode === "mock"
    ? mockSession?.organizationId ?? null
    : runtimeAuthMode === "supabase"
      ? authenticatedSupabaseSession?.organizationId ?? null
      : null;
  const resolvedRole = role !== undefined
    ? role
    : browserRole;
  const resolvedOrganizationId = organizationId !== undefined
    ? organizationId
    : browserOrganizationId;
  const requestedSection = initialSection ?? (initialScope === "admin" ? "team" : "account");
  const requestedSectionExplicit = initialSectionExplicit ?? (initialSection !== undefined || initialScope === "admin");
  const identityResolved = role !== undefined
    || (runtimeAuthMode !== null && (
      (runtimeAuthMode === "mock" && mockSession !== null)
      || (runtimeAuthMode === "supabase" && authenticatedSupabaseSession !== null)
      || browserIdentityHydrated
    ));
  const resolution = resolveAuthorizedSection(resolvedRole, requestedSection);
  const adminSectionRequested = isAdminSettingsSection(requestedSection);
  const unauthorizedAdminRequest = identityResolved && adminSectionRequested && !resolution.authorized;

  useEffect(() => {
    if (unauthorizedAdminRequest) {
      router.replace("/settings?section=account&notice=not-authorized");
    }
  }, [router, unauthorizedAdminRequest]);

  return (
    <div className="grid gap-4">
      {notice === "not-authorized" || unauthorizedAdminRequest ? (
        <p role="status" className="rounded-md border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm text-slate-700">
          You do not have access to that settings section. Account settings are shown instead.
        </p>
      ) : null}
      <SettingsWorkspace
        role={resolvedRole}
        requestedSection={requestedSection}
        requestedSectionExplicit={requestedSectionExplicit}
        organizationId={resolvedOrganizationId}
        caseId={caseId}
      />
    </div>
  );
}
