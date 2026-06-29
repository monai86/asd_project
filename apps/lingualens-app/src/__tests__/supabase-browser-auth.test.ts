import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  beginSupabaseBrowserOrganizationSwitch,
  buildSupabaseBrowserAuthSnapshotFromSession,
  deriveSupabaseAccessSession,
  selectSupabaseBrowserOrganization,
  syncSupabaseAccessSessionFromSession,
  syncSupabaseAccessSessionFromBrowserAuth,
} from "@/lib/supabase-browser-auth";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";

beforeEach(() => {
  window.sessionStorage.clear();
});

describe("supabase browser auth bridge", () => {
  it("derives a signed-out access state when no browser auth snapshot exists", () => {
    expect(deriveSupabaseAccessSession(null)).toEqual({ stage: "signed_out" });
  });

  it("derives an MFA-required access state for an aal1 accepted membership", () => {
    expect(deriveSupabaseAccessSession({
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      aal: "aal1",
      appMetadata: {
        role: "therapist",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
        ],
      },
    })).toMatchObject({
      stage: "mfa_required",
      email: "clinician@clinic.example",
      aal: "aal1",
      organizationId: "clinic_001",
    });
  });

  it("derives an org-selection-required state when aal2 claims do not carry an active organization", () => {
    expect(deriveSupabaseAccessSession({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "clinical_supervisor",
        membership_active: true,
        invitation_status: "accepted",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
          { organizationId: "clinic_002", label: "North Review Clinic" },
        ],
      },
    })).toMatchObject({
      stage: "org_selection_required",
      email: "supervisor@clinic.example",
      aal: "aal2",
    });
  });

  it("derives an authenticated state when aal2 claims carry exactly one organization membership", () => {
    expect(deriveSupabaseAccessSession({
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "therapist",
        membership_active: true,
        invitation_status: "accepted",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
        ],
      },
    })).toMatchObject({
      stage: "authenticated",
      email: "clinician@clinic.example",
      aal: "aal2",
      organizationId: "clinic_001",
    });
  });

  it("derives an authenticated state when aal2 claims carry an explicit organization without membership list", () => {
    expect(deriveSupabaseAccessSession({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "clinical_supervisor",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
      },
    })).toMatchObject({
      stage: "authenticated",
      email: "supervisor@clinic.example",
      aal: "aal2",
      organizationId: "clinic_001",
    });
  });

  it("syncs an authenticated access session from accepted aal2 browser auth claims", () => {
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_org_admin_001",
      email: "admin@clinic.example",
      displayName: "Clinic Admin",
      aal: "aal2",
      appMetadata: {
        role: "org_admin",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
        ],
      },
    }));

    const accessSession = syncSupabaseAccessSessionFromBrowserAuth();

    expect(accessSession).toMatchObject({
      stage: "authenticated",
      email: "admin@clinic.example",
      displayName: "Clinic Admin",
      aal: "aal2",
      organizationId: "clinic_001",
    });
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"organizationId\":\"clinic_001\"");
  });

  it("builds a browser-auth snapshot from a Supabase-like session payload", () => {
    expect(buildSupabaseBrowserAuthSnapshotFromSession({
      aal: "aal2",
      user: {
        id: "user_org_admin_001",
        email: "admin@clinic.example",
        app_metadata: {
          role: "org_admin",
          membership_active: true,
          invitation_status: "accepted",
          organization_id: "clinic_001",
          organization_memberships: [
            { organization_id: "clinic_001", name: "LinguaLens Clinic", role: "org_admin" },
            { organization_id: "clinic_002", name: "North Review Clinic", role: "clinical_supervisor" },
          ],
        },
        user_metadata: {
          full_name: "Clinic Admin",
        },
      },
    })).toEqual({
      userId: "user_org_admin_001",
      email: "admin@clinic.example",
      displayName: "Clinic Admin",
      aal: "aal2",
      appMetadata: {
        role: "org_admin",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic", role: "org_admin" },
          { organizationId: "clinic_002", label: "North Review Clinic", role: "clinical_supervisor" },
        ],
      },
    });
  });

  it("syncs access state directly from a Supabase-like session payload", () => {
    const accessSession = syncSupabaseAccessSessionFromSession({
      aal: "aal2",
      access_token: "supabase-access-token",
      user: {
        id: "user_org_admin_001",
        email: "admin@clinic.example",
        app_metadata: {
          role: "org_admin",
          membership_active: true,
          invitation_status: "accepted",
          organization_id: "clinic_001",
          organizations: [
            { organizationId: "clinic_001", label: "LinguaLens Clinic" },
          ],
        },
        user_metadata: {
          display_name: "Clinic Admin",
        },
      },
    });

    expect(accessSession).toMatchObject({
      stage: "authenticated",
      email: "admin@clinic.example",
      organizationId: "clinic_001",
    });
    expect(window.sessionStorage.getItem("lingualens.supabase-browser-auth.v1")).toContain("\"Clinic Admin\"");
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    expect(window.sessionStorage.getItem("lingualens.supabase-session-token.v1")).toBe("supabase-access-token");
  });

  it("fails closed when the Supabase session aal claim is missing", () => {
    const accessSession = syncSupabaseAccessSessionFromSession({
      access_token: "stale-access-token",
      user: {
        id: "user_org_admin_001",
        email: "admin@clinic.example",
        app_metadata: {
          role: "org_admin",
          membership_active: true,
          invitation_status: "accepted",
          organization_id: "clinic_001",
        },
      },
    });

    expect(accessSession).toEqual({ stage: "signed_out" });
    expect(window.sessionStorage.getItem("lingualens.supabase-browser-auth.v1")).toBeNull();
    expect(window.sessionStorage.getItem("lingualens.supabase-session-token.v1")).toBeNull();
  });

  it("fails closed and clears cached token when required claims downgrade to malformed state", () => {
    syncSupabaseAccessSessionFromSession({
      aal: "aal2",
      access_token: "valid-access-token",
      user: {
        id: "user_org_admin_001",
        email: "admin@clinic.example",
        app_metadata: {
          role: "org_admin",
          membership_active: true,
          invitation_status: "accepted",
          organization_id: "clinic_001",
        },
      },
    });

    const downgraded = syncSupabaseAccessSessionFromSession({
      aal: "aal2",
      access_token: "invalid-access-token",
      user: {
        id: "user_org_admin_001",
        email: "admin@clinic.example",
        app_metadata: {
          role: "org_admin",
          membership_active: "true",
          invitation_status: "accepted",
          organization_id: "clinic_001",
        },
      },
    });

    expect(downgraded).toEqual({ stage: "signed_out" });
    expect(window.sessionStorage.getItem("lingualens.supabase-browser-auth.v1")).toBeNull();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"signed_out\"");
    expect(window.sessionStorage.getItem("lingualens.supabase-session-token.v1")).toBeNull();
  });

  it("persists explicit organization selection back into the browser auth snapshot", () => {
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "clinical_supervisor",
        membership_active: true,
        invitation_status: "accepted",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic", role: "clinical_supervisor" },
          { organizationId: "clinic_002", label: "North Review Clinic", role: "org_admin" },
        ],
      },
    }));

    const accessSession = selectSupabaseBrowserOrganization("clinic_002");

    expect(accessSession).toMatchObject({
      stage: "authenticated",
      organizationId: "clinic_002",
      role: "org_admin",
    });
    expect(window.sessionStorage.getItem("lingualens.supabase-browser-auth.v1")).toContain("\"organization_id\":\"clinic_002\"");
    expect(window.localStorage.getItem("lingualens.supabase-organization-hint.v1")).toContain("\"organizationId\":\"clinic_002\"");
  });

  it("uses the last active organization as a hint only for ambiguous aal2 sessions", () => {
    window.localStorage.setItem("lingualens.supabase-organization-hint.v1", JSON.stringify({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      organizationId: "clinic_002",
    }));

    expect(deriveSupabaseAccessSession({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "clinical_supervisor",
        membership_active: true,
        invitation_status: "accepted",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
          { organizationId: "clinic_002", label: "North Review Clinic" },
        ],
      },
    }, {
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      organizationId: "clinic_002",
    })).toMatchObject({
      stage: "org_selection_required",
      suggestedOrganizationId: "clinic_002",
    });
  });

  it("clears the selected organization from the browser auth snapshot when switching orgs", () => {
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "clinical_supervisor",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
          { organizationId: "clinic_002", label: "North Review Clinic" },
        ],
      },
    }));

    const accessSession = beginSupabaseBrowserOrganizationSwitch();

    expect(accessSession).toMatchObject({
      stage: "org_selection_required",
    });
    expect(window.sessionStorage.getItem("lingualens.supabase-browser-auth.v1")).not.toContain("\"organization_id\":\"clinic_001\"");
  });

  it("publishes a Supabase session payload event for the runtime bridge to consume", () => {
    const listener = vi.fn();
    window.addEventListener("lingualens:supabase-session-source", listener as EventListener);

    publishSupabaseSessionPayload({
      user: { id: "user_therapist_001", email: "clinician@clinic.example" },
      aal: "aal2",
    });

    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener("lingualens:supabase-session-source", listener as EventListener);
  });

  it("clears the organization hint when browser auth is removed", () => {
    window.localStorage.setItem("lingualens.supabase-organization-hint.v1", JSON.stringify({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      organizationId: "clinic_002",
    }));

    syncSupabaseAccessSessionFromSession(null);

    expect(window.localStorage.getItem("lingualens.supabase-organization-hint.v1")).toBeNull();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"signed_out\"");
  });
});
