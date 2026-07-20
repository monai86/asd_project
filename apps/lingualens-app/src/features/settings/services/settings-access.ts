import type { MockRole } from "@/lib/mock-access-session";
import type { SupabaseSessionRole } from "@/lib/supabase-access-session";

export type SettingsRole = MockRole | SupabaseSessionRole;
export type SettingsSection =
  | "profile"
  | "organization"
  | "credentials"
  | "accessibility"
  | "privacy"
  | "team"
  | "audit";

const SHARED_SETTINGS_SECTIONS = Object.freeze([
  "profile",
  "organization",
  "credentials",
  "accessibility",
  "privacy",
] as const satisfies readonly SettingsSection[]);

const ADMIN_SETTINGS_SECTIONS = Object.freeze([
  ...SHARED_SETTINGS_SECTIONS,
  "team",
  "audit",
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
  return section === "profile"
    || section === "organization"
    || section === "credentials"
    || section === "accessibility"
    || section === "privacy"
    || section === "team"
    || section === "audit";
}

export function allowedSettingsSections(role: unknown): readonly SettingsSection[] {
  return isSettingsRole(role) ? SETTINGS_ROLE_MATRIX[role] : SHARED_SETTINGS_SECTIONS;
}

export function resolveAuthorizedSection(
  role: unknown,
  requestedSection: unknown,
): AuthorizedSettingsSection {
  if (requestedSection === undefined || requestedSection === "") {
    return { authorized: isSettingsRole(role), section: "profile" };
  }
  if (!isSettingsRole(role) || !isSettingsSection(requestedSection)) {
    return { authorized: false, section: "profile" };
  }

  const allowed: readonly SettingsSection[] = allowedSettingsSections(role);
  return allowed.includes(requestedSection)
    ? { authorized: true, section: requestedSection }
    : { authorized: false, section: "profile" };
}
