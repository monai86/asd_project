import { describe, expect, it } from "vitest";

import {
  allowedSettingsSections,
  resolveAuthorizedSection,
} from "@/features/settings/services/settings-access";

describe("settings access", () => {
  it("gives therapists only the shared settings sections", () => {
    expect(allowedSettingsSections("therapist")).toEqual([
      "profile",
      "organization",
      "credentials",
      "accessibility",
      "privacy",
    ]);
  });

  it("gives organization admins the shared sections plus team and audit", () => {
    expect(allowedSettingsSections("org_admin")).toEqual([
      "profile",
      "organization",
      "credentials",
      "accessibility",
      "privacy",
      "team",
      "audit",
    ]);
  });

  it("fails closed for an unauthorized admin deep link", () => {
    expect(resolveAuthorizedSection("therapist", "team")).toEqual({
      authorized: false,
      section: "profile",
    });
  });

  it("preserves an authorized organization-admin deep link", () => {
    expect(resolveAuthorizedSection("org_admin", "audit")).toEqual({
      authorized: true,
      section: "audit",
    });
  });

  it("uses profile as the safe default when no section is requested", () => {
    expect(resolveAuthorizedSection("therapist", undefined)).toEqual({
      authorized: true,
      section: "profile",
    });
  });

  it.each([null, "unknown", "admin"])(
    "fails closed for an invalid section (%s)",
    (section) => {
      expect(resolveAuthorizedSection("org_admin", section)).toEqual({
        authorized: false,
        section: "profile",
      });
    },
  );

  it("fails closed when the role is unavailable or unsupported", () => {
    expect(resolveAuthorizedSection(null, "team")).toEqual({
      authorized: false,
      section: "profile",
    });
    expect(resolveAuthorizedSection("platform_operator", "team")).toEqual({
      authorized: false,
      section: "profile",
    });
  });
});
