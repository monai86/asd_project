"use client";

import { SettingsWorkspace } from "@/features/settings/components/settings-workspace";
import type { SettingsRole, SettingsSection } from "@/features/settings/services/settings-access";
import { useMockAccessSession } from "@/lib/use-mock-access-session";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

type LegacySettingsScope = "therapist" | "admin";

type SettingsWorkspaceClientProps = {
  initialScope?: LegacySettingsScope;
  initialSection?: SettingsSection;
  role?: SettingsRole | null;
  organizationId?: string | null;
};

export function SettingsWorkspaceClient({
  initialScope = "therapist",
  initialSection,
  role,
  organizationId,
}: SettingsWorkspaceClientProps) {
  const mockSession = useMockAccessSession();
  const supabaseSession = useSupabaseAccessSession();
  const authenticatedSupabaseSession = supabaseSession?.stage === "authenticated"
    && supabaseSession.aal === "aal2"
    && supabaseSession.organizationId
      ? supabaseSession
      : null;
  const resolvedRole = role !== undefined
    ? role
    : authenticatedSupabaseSession?.role ?? mockSession?.role ?? null;
  const resolvedOrganizationId = organizationId !== undefined
    ? organizationId
    : authenticatedSupabaseSession?.organizationId ?? mockSession?.organizationId ?? null;
  const requestedSection = initialSection ?? (initialScope === "admin" ? "team" : "profile");

  return (
    <SettingsWorkspace
      role={resolvedRole}
      requestedSection={requestedSection}
      organizationId={resolvedOrganizationId}
    />
  );
}
