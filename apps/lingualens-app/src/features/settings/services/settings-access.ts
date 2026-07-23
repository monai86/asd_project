import type { MockRole } from "@/lib/mock-access-session";
import type { SupabaseSessionRole } from "@/lib/supabase-access-session";

export type SettingsRole = MockRole | SupabaseSessionRole;
export type SharedSettingsSection =
  | "account"
  | "organization"
  | "accessibility"
  | "notifications"
  | "privacy"
  | "export"
  | "help";
export type AdminSettingsSection =
  | "team"
  | "invitations"
  | "audit"
  | "privacy_operations"
  | "integration_status";
export type SettingsSection = SharedSettingsSection | AdminSettingsSection;

const SHARED_SETTINGS_SECTIONS = Object.freeze([
  "account",
  "organization",
  "accessibility",
  "notifications",
  "privacy",
  "export",
  "help",
] as const satisfies readonly SharedSettingsSection[]);

const ADMIN_ONLY_SETTINGS_SECTIONS = Object.freeze([
  "team",
  "invitations",
  "audit",
  "privacy_operations",
  "integration_status",
] as const satisfies readonly AdminSettingsSection[]);

const ADMIN_SETTINGS_SECTIONS = Object.freeze([
  ...SHARED_SETTINGS_SECTIONS,
  ...ADMIN_ONLY_SETTINGS_SECTIONS,
] as const satisfies readonly SettingsSection[]);

export const SETTINGS_ROLE_MATRIX = Object.freeze({
  therapist: SHARED_SETTINGS_SECTIONS,
  clinical_supervisor: SHARED_SETTINGS_SECTIONS,
  org_admin: ADMIN_SETTINGS_SECTIONS,
  platform_operator: SHARED_SETTINGS_SECTIONS,
} as const satisfies Readonly<Record<SettingsRole, readonly SettingsSection[]>>);

export type AuthorizedSettingsSection = {
  authorized: boolean;
  section: SettingsSection;
};

function isSettingsRole(role: unknown): role is SettingsRole {
  return role === "therapist"
    || role === "clinical_supervisor"
    || role === "org_admin"
    || role === "platform_operator";
}

export function isSettingsSection(section: unknown): section is SettingsSection {
  return SHARED_SETTINGS_SECTIONS.includes(section as SharedSettingsSection)
    || ADMIN_ONLY_SETTINGS_SECTIONS.includes(section as AdminSettingsSection);
}

export function parseSettingsSection(section: unknown): SettingsSection | null {
  if (section === "profile") return "account";
  if (section === "credentials") return "privacy";
  return isSettingsSection(section) ? section : null;
}

export function isAdminSettingsSection(section: SettingsSection): section is AdminSettingsSection {
  return ADMIN_ONLY_SETTINGS_SECTIONS.includes(section as AdminSettingsSection);
}

export function isSharedSettingsSection(section: SettingsSection): section is SharedSettingsSection {
  return SHARED_SETTINGS_SECTIONS.includes(section as SharedSettingsSection);
}

export function allowedSettingsSections(role: unknown): readonly SettingsSection[] {
  return isSettingsRole(role) ? SETTINGS_ROLE_MATRIX[role] : SHARED_SETTINGS_SECTIONS;
}

export function resolveAuthorizedSection(
  role: unknown,
  requestedSection: unknown,
): AuthorizedSettingsSection {
  if (requestedSection === undefined || requestedSection === "") {
    return { authorized: isSettingsRole(role), section: "account" };
  }
  const section = parseSettingsSection(requestedSection);
  if (!isSettingsRole(role) || !section) {
    return { authorized: false, section: "account" };
  }

  const allowed: readonly SettingsSection[] = allowedSettingsSections(role);
  return allowed.includes(section)
    ? { authorized: true, section }
    : { authorized: false, section: "account" };
}
