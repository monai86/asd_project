"use client";

export const SUPABASE_ACCESS_SESSION_KEY = "lingualens.supabase-access-session.v1";
export const SUPABASE_ACCESS_SESSION_EVENT = "lingualens:supabase-access-session-changed";
export const SUPABASE_ORGANIZATION_HINT_KEY = "lingualens.supabase-organization-hint.v1";

export type SupabaseSessionRole = "therapist" | "clinical_supervisor" | "org_admin" | "platform_operator";

export type SupabaseOrganizationOption = {
  organizationId: string;
  label: string;
  role?: SupabaseSessionRole;
};

export type SupabaseAccessStage =
  | "signed_out"
  | "mfa_required"
  | "org_selection_required"
  | "authenticated";

export type SupabaseAccessSession = {
  stage: SupabaseAccessStage;
  userId?: string;
  email?: string;
  displayName?: string;
  role?: SupabaseSessionRole;
  aal?: "aal1" | "aal2";
  organizationId?: string;
  availableOrganizations?: SupabaseOrganizationOption[];
  suggestedOrganizationId?: string;
};

export type SupabaseOrganizationHint = {
  userId: string;
  email: string;
  organizationId: string;
};

export function loadSupabaseAccessSession(): SupabaseAccessSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SUPABASE_ACCESS_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SupabaseAccessSession>;
    if (!isValidStage(parsed.stage)) return null;
    return {
      stage: parsed.stage,
      userId: typeof parsed.userId === "string" ? parsed.userId : undefined,
      email: typeof parsed.email === "string" ? parsed.email : undefined,
      displayName: typeof parsed.displayName === "string" ? parsed.displayName : undefined,
      role: isValidRole(parsed.role) ? parsed.role : undefined,
      aal: parsed.aal === "aal1" || parsed.aal === "aal2" ? parsed.aal : undefined,
      organizationId: typeof parsed.organizationId === "string" ? parsed.organizationId : undefined,
      suggestedOrganizationId: typeof parsed.suggestedOrganizationId === "string"
        ? parsed.suggestedOrganizationId
        : undefined,
      availableOrganizations: Array.isArray(parsed.availableOrganizations)
        ? parsed.availableOrganizations
            .filter(isValidOrganizationOption)
            .map((option) => ({
              organizationId: option.organizationId,
              label: option.label,
              role: isValidRole(option.role) ? option.role : undefined,
            }))
        : undefined,
    };
  } catch {
    return null;
  }
}

export function saveSupabaseAccessSession(session: SupabaseAccessSession): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(SUPABASE_ACCESS_SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new CustomEvent(SUPABASE_ACCESS_SESSION_EVENT, { detail: session }));
}

export function loadSupabaseOrganizationHint(): SupabaseOrganizationHint | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(SUPABASE_ORGANIZATION_HINT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SupabaseOrganizationHint>;
    if (
      typeof parsed.userId !== "string"
      || !parsed.userId.trim()
      || typeof parsed.email !== "string"
      || !parsed.email.trim()
      || typeof parsed.organizationId !== "string"
      || !parsed.organizationId.trim()
    ) {
      return null;
    }
    return {
      userId: parsed.userId,
      email: parsed.email,
      organizationId: parsed.organizationId,
    };
  } catch {
    return null;
  }
}

export function saveSupabaseOrganizationHint(hint: SupabaseOrganizationHint | null): void {
  if (typeof window === "undefined") return;
  if (!hint) {
    window.localStorage.removeItem(SUPABASE_ORGANIZATION_HINT_KEY);
    return;
  }
  window.localStorage.setItem(SUPABASE_ORGANIZATION_HINT_KEY, JSON.stringify(hint));
}

export function updateSupabaseOrganizationSelection(organizationId: string): void {
  const current = loadSupabaseAccessSession();
  if (!current) return;
  const selected = current.availableOrganizations?.find((option) => option.organizationId === organizationId);
  saveSupabaseAccessSession({
    ...current,
    stage: "authenticated",
    organizationId,
    availableOrganizations: current.availableOrganizations ?? (selected ? [selected] : undefined),
    aal: current.aal ?? "aal2",
  });
}

export function beginSupabaseOrganizationSwitch(): void {
  const current = loadSupabaseAccessSession();
  if (!current || !current.availableOrganizations?.length) return;
  saveSupabaseAccessSession({
    ...current,
    stage: "org_selection_required",
    organizationId: undefined,
    aal: current.aal ?? "aal2",
  });
}

function isValidStage(value: unknown): value is SupabaseAccessStage {
  return value === "signed_out" || value === "mfa_required" || value === "org_selection_required" || value === "authenticated";
}

function isValidRole(value: unknown): value is SupabaseSessionRole {
  return value === "therapist" || value === "clinical_supervisor" || value === "org_admin" || value === "platform_operator";
}

function isValidOrganizationOption(value: unknown): value is SupabaseOrganizationOption {
  if (!value || typeof value !== "object") return false;
  const option = value as Partial<SupabaseOrganizationOption>;
  return typeof option.organizationId === "string" && Boolean(option.organizationId.trim())
    && typeof option.label === "string" && Boolean(option.label.trim());
}
