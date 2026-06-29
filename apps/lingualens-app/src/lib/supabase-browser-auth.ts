"use client";

import {
  loadSupabaseOrganizationHint,
  saveSupabaseAccessSession,
  saveSupabaseOrganizationHint,
  type SupabaseAccessSession,
  type SupabaseOrganizationHint,
  type SupabaseOrganizationOption,
  type SupabaseSessionRole,
} from "@/lib/supabase-access-session";
import { saveSupabaseSessionToken } from "@/lib/supabase-session-token";

export const SUPABASE_BROWSER_AUTH_KEY = "lingualens.supabase-browser-auth.v1";
export const SUPABASE_BROWSER_AUTH_EVENT = "lingualens:supabase-browser-auth-changed";

export type SupabaseBrowserAuthSnapshot = {
  userId: string;
  email: string;
  displayName?: string;
  aal: "aal1" | "aal2";
  appMetadata: {
    role: SupabaseSessionRole;
    membership_active: boolean;
    invitation_status: "pending" | "accepted" | "revoked" | "expired";
    organization_id?: string;
    organizations?: SupabaseOrganizationOption[];
  };
};

type SupabaseSessionLike = {
  aal?: string | null;
  access_token?: string | null;
  user?: {
    id?: string | null;
    email?: string | null;
    app_metadata?: {
      role?: unknown;
      membership_active?: unknown;
      invitation_status?: unknown;
      organization_id?: unknown;
      organizations?: unknown;
      organization_memberships?: unknown;
    } | null;
    user_metadata?: {
      display_name?: unknown;
      full_name?: unknown;
      name?: unknown;
    } | null;
  } | null;
} | null;

export function loadSupabaseBrowserAuthSnapshot(): SupabaseBrowserAuthSnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SUPABASE_BROWSER_AUTH_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SupabaseBrowserAuthSnapshot>;
    if (!isValidSnapshot(parsed)) return null;
    return {
      userId: parsed.userId,
      email: parsed.email,
      displayName: parsed.displayName,
      aal: parsed.aal,
      appMetadata: {
        role: parsed.appMetadata.role,
        membership_active: parsed.appMetadata.membership_active,
        invitation_status: parsed.appMetadata.invitation_status,
        organization_id: parsed.appMetadata.organization_id,
        organizations: parsed.appMetadata.organizations,
      },
    };
  } catch {
    return null;
  }
}

export function saveSupabaseBrowserAuthSnapshot(snapshot: SupabaseBrowserAuthSnapshot | null): void {
  if (typeof window === "undefined") return;
  if (snapshot) {
    window.sessionStorage.setItem(SUPABASE_BROWSER_AUTH_KEY, JSON.stringify(snapshot));
  } else {
    window.sessionStorage.removeItem(SUPABASE_BROWSER_AUTH_KEY);
    saveSupabaseOrganizationHint(null);
  }
  window.dispatchEvent(new CustomEvent(SUPABASE_BROWSER_AUTH_EVENT, { detail: snapshot }));
}

export function buildSupabaseBrowserAuthSnapshotFromSession(
  session: SupabaseSessionLike,
): SupabaseBrowserAuthSnapshot | null {
  if (!session?.user?.id || !session.user.email || (session.aal !== "aal1" && session.aal !== "aal2")) {
    return null;
  }

  const appMetadata = session.user.app_metadata ?? {};
  const role = isValidRole(appMetadata.role) ? appMetadata.role : null;
  const invitationStatus = isValidInvitationStatus(appMetadata.invitation_status)
    ? appMetadata.invitation_status
    : null;
  const organizations = normalizeOrganizations(
    appMetadata.organizations ?? appMetadata.organization_memberships,
  );
  const organizationId = typeof appMetadata.organization_id === "string"
    ? appMetadata.organization_id
    : undefined;
  const displayName = extractDisplayName(session.user.user_metadata);

  if (!role || invitationStatus == null || typeof appMetadata.membership_active !== "boolean") {
    return null;
  }

  if (organizations && organizationId && !organizations.some((option) => option.organizationId === organizationId)) {
    return null;
  }

  return {
    userId: session.user.id,
    email: session.user.email,
    displayName,
    aal: session.aal,
    appMetadata: {
      role,
      membership_active: appMetadata.membership_active,
      invitation_status: invitationStatus,
      organization_id: organizationId,
      organizations,
    },
  };
}

export function saveSupabaseBrowserAuthSnapshotFromSession(session: SupabaseSessionLike): SupabaseBrowserAuthSnapshot | null {
  const snapshot = buildSupabaseBrowserAuthSnapshotFromSession(session);
  saveSupabaseSessionToken(snapshot ? (session?.access_token ?? null) : null);
  saveSupabaseBrowserAuthSnapshot(snapshot);
  return snapshot;
}

export function beginSupabaseBrowserOrganizationSwitch(): SupabaseAccessSession {
  const snapshot = loadSupabaseBrowserAuthSnapshot();
  if (!snapshot) {
    return syncSupabaseAccessSessionFromBrowserAuth();
  }

  saveSupabaseBrowserAuthSnapshot({
    ...snapshot,
    appMetadata: {
      ...snapshot.appMetadata,
      organization_id: undefined,
    },
  });

  return syncSupabaseAccessSessionFromBrowserAuth();
}

export function selectSupabaseBrowserOrganization(organizationId: string): SupabaseAccessSession {
  const snapshot = loadSupabaseBrowserAuthSnapshot();
  if (!snapshot) {
    return syncSupabaseAccessSessionFromBrowserAuth();
  }

  const selectedOrganization = snapshot.appMetadata.organizations?.find(
    (option) => option.organizationId === organizationId,
  );
  if (!selectedOrganization) {
    return syncSupabaseAccessSessionFromBrowserAuth();
  }

  saveSupabaseBrowserAuthSnapshot({
    ...snapshot,
    appMetadata: {
      ...snapshot.appMetadata,
      organization_id: organizationId,
      organizations: snapshot.appMetadata.organizations ?? [selectedOrganization],
    },
  });
  saveSupabaseOrganizationHint({
    userId: snapshot.userId,
    email: snapshot.email,
    organizationId: selectedOrganization.organizationId,
  });

  return syncSupabaseAccessSessionFromBrowserAuth();
}

export function syncSupabaseAccessSessionFromBrowserAuth(): SupabaseAccessSession {
  const snapshot = loadSupabaseBrowserAuthSnapshot();
  const accessSession = deriveSupabaseAccessSession(snapshot, loadSupabaseOrganizationHint());
  saveSupabaseAccessSession(accessSession);
  return accessSession;
}

export function syncSupabaseAccessSessionFromSession(session: SupabaseSessionLike): SupabaseAccessSession {
  saveSupabaseBrowserAuthSnapshotFromSession(session);
  return syncSupabaseAccessSessionFromBrowserAuth();
}

export function deriveSupabaseAccessSession(
  snapshot: SupabaseBrowserAuthSnapshot | null,
  organizationHint?: SupabaseOrganizationHint | null,
): SupabaseAccessSession {
  if (!snapshot) {
    return { stage: "signed_out" };
  }

  const organizations = snapshot.appMetadata.organizations ?? [];
  const selectedOrganizationId = snapshot.appMetadata.organization_id;
  const organizationMatch = selectedOrganizationId
    ? organizations.find((option) => option.organizationId === selectedOrganizationId)
    : undefined;
  const soleOrganization = organizations.length === 1 ? organizations[0] : undefined;
  const resolvedOrganizationId = selectedOrganizationId
    ?? soleOrganization?.organizationId;
  const resolvedRole = organizationMatch?.role
    ?? soleOrganization?.role
    ?? snapshot.appMetadata.role;
  const suggestedOrganizationId = selectedOrganizationId || organizations.length <= 1
    ? undefined
    : organizationHint?.userId === snapshot.userId
        && organizationHint.email === snapshot.email
        && organizations.some((option) => option.organizationId === organizationHint.organizationId)
      ? organizationHint.organizationId
      : undefined;

  if (
    !snapshot.appMetadata.membership_active
    || snapshot.appMetadata.invitation_status !== "accepted"
  ) {
    return {
      stage: "signed_out",
      email: snapshot.email,
      displayName: snapshot.displayName,
      role: snapshot.appMetadata.role,
    };
  }

  if (snapshot.aal !== "aal2") {
    return {
      stage: "mfa_required",
      userId: snapshot.userId,
      email: snapshot.email,
      displayName: snapshot.displayName,
      role: snapshot.appMetadata.role,
      aal: snapshot.aal,
      organizationId: selectedOrganizationId,
      availableOrganizations: organizations,
      suggestedOrganizationId,
    };
  }

  if (!resolvedOrganizationId) {
    return {
      stage: "org_selection_required",
      userId: snapshot.userId,
      email: snapshot.email,
      displayName: snapshot.displayName,
      role: snapshot.appMetadata.role,
      aal: snapshot.aal,
      availableOrganizations: organizations,
      suggestedOrganizationId,
    };
  }

  if (selectedOrganizationId && organizations.length > 0 && !organizationMatch) {
    return {
      stage: "org_selection_required",
      userId: snapshot.userId,
      email: snapshot.email,
      displayName: snapshot.displayName,
      role: snapshot.appMetadata.role,
      aal: snapshot.aal,
      availableOrganizations: organizations,
      suggestedOrganizationId,
    };
  }

  return {
    stage: "authenticated",
    userId: snapshot.userId,
    email: snapshot.email,
    displayName: snapshot.displayName,
    role: resolvedRole,
    aal: snapshot.aal,
    organizationId: resolvedOrganizationId,
    availableOrganizations: organizations,
    suggestedOrganizationId: undefined,
  };
}

function isValidSnapshot(value: Partial<SupabaseBrowserAuthSnapshot> | undefined): value is SupabaseBrowserAuthSnapshot {
  return Boolean(
    value
    && typeof value.userId === "string"
    && typeof value.email === "string"
    && (value.aal === "aal1" || value.aal === "aal2")
    && value.appMetadata
    && isValidRole(value.appMetadata.role)
    && typeof value.appMetadata.membership_active === "boolean"
    && isValidInvitationStatus(value.appMetadata.invitation_status)
    && (value.appMetadata.organization_id == null || typeof value.appMetadata.organization_id === "string")
    && (value.appMetadata.organizations == null || value.appMetadata.organizations.every(isValidOrganizationOption))
  );
}

function isValidRole(value: unknown): value is SupabaseSessionRole {
  return value === "therapist" || value === "clinical_supervisor" || value === "org_admin" || value === "platform_operator";
}

function isValidInvitationStatus(value: unknown): value is SupabaseBrowserAuthSnapshot["appMetadata"]["invitation_status"] {
  return value === "pending" || value === "accepted" || value === "revoked" || value === "expired";
}

function isValidOrganizationOption(value: unknown): value is SupabaseOrganizationOption {
  if (!value || typeof value !== "object") return false;
  const option = value as Partial<SupabaseOrganizationOption>;
  return typeof option.organizationId === "string"
    && typeof option.label === "string"
    && Boolean(option.organizationId.trim())
    && Boolean(option.label.trim())
    && (option.role == null || isValidRole(option.role));
}

function normalizeOrganizations(value: unknown): SupabaseOrganizationOption[] | undefined {
  if (!Array.isArray(value)) return undefined;

  const organizations = value.flatMap((item) => {
    if (typeof item === "string" && item.trim()) {
      return [{ organizationId: item, label: item }];
    }

    if (!item || typeof item !== "object") {
      return [];
    }

    const option = item as {
      organizationId?: unknown;
      organization_id?: unknown;
      label?: unknown;
      name?: unknown;
      role?: unknown;
    };
    const organizationId = typeof option.organizationId === "string"
      ? option.organizationId
      : typeof option.organization_id === "string"
        ? option.organization_id
        : null;
    const label = typeof option.label === "string"
      ? option.label
      : typeof option.name === "string"
        ? option.name
        : organizationId;
    const role = isValidRole(option.role) ? option.role : undefined;

    return organizationId && label ? [{ organizationId, label, role }] : [];
  });

  return organizations.length ? organizations : undefined;
}

function extractDisplayName(
  metadata: {
    display_name?: unknown;
    full_name?: unknown;
    name?: unknown;
  } | null | undefined,
): string | undefined {
  if (!metadata || typeof metadata !== "object") return undefined;
  if (typeof metadata.display_name === "string" && metadata.display_name.trim()) return metadata.display_name;
  if (typeof metadata.full_name === "string" && metadata.full_name.trim()) return metadata.full_name;
  if (typeof metadata.name === "string" && metadata.name.trim()) return metadata.name;
  return undefined;
}
