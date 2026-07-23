import { describe, expect, it } from "vitest";

import {
  allowedSettingsSections,
  resolveAuthorizedSection,
} from "@/features/settings/services/settings-access";

describe("settings access", () => {
  it("gives therapists only the shared settings sections", () => {
    expect(allowedSettingsSections("therapist")).toEqual([
      "account",
      "organization",
      "accessibility",
      "notifications",
      "privacy",
      "export",
      "help",
    ]);
  });

  it("gives organization admins the shared sections plus every admin category", () => {
    expect(allowedSettingsSections("org_admin")).toEqual([
      "account",
      "organization",
      "accessibility",
      "notifications",
      "privacy",
      "export",
      "help",
      "team",
      "invitations",
      "audit",
      "privacy_operations",
      "integration_status",
    ]);
  });

  it.each(["team", "invitations", "audit", "privacy_operations", "integration_status"])(
    "fails closed for an unauthorized admin deep link (%s)",
    (section) => {
      expect(resolveAuthorizedSection("therapist", section)).toEqual({
        authorized: false,
        section: "account",
      });
    },
  );

  it("preserves an authorized organization-admin deep link", () => {
    expect(resolveAuthorizedSection("org_admin", "audit")).toEqual({
      authorized: true,
      section: "audit",
    });
  });

  it("uses account as the safe default when no section is requested", () => {
    expect(resolveAuthorizedSection("therapist", undefined)).toEqual({
      authorized: true,
      section: "account",
    });
  });

  it("normalizes legacy profile and credentials deep links", () => {
    expect(resolveAuthorizedSection("therapist", "profile")).toEqual({
      authorized: true,
      section: "account",
    });
    expect(resolveAuthorizedSection("therapist", "credentials")).toEqual({
      authorized: true,
      section: "privacy",
    });
  });

  it.each([null, "unknown", "admin"])(
    "fails closed for an invalid section (%s)",
    (section) => {
      expect(resolveAuthorizedSection("org_admin", section)).toEqual({
        authorized: false,
        section: "account",
      });
    },
  );

  it("fails closed when the role is unavailable or unsupported", () => {
    expect(resolveAuthorizedSection(null, "team")).toEqual({
      authorized: false,
      section: "account",
    });
    expect(resolveAuthorizedSection("platform_operator", "team")).toEqual({
      authorized: false,
      section: "account",
    });
  });
});
