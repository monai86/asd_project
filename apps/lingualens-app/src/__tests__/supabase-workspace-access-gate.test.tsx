import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SupabaseWorkspaceAccessGate } from "@/components/supabase-workspace-access-gate";

const listFactors = vi.fn();
const enroll = vi.fn();
const challengeAndVerify = vi.fn();
const getSession = vi.fn();

vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession,
      mfa: {
        listFactors,
        enroll,
        challengeAndVerify,
      },
    },
  }),
}));

describe("SupabaseWorkspaceAccessGate", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    listFactors.mockReset();
    enroll.mockReset();
    challengeAndVerify.mockReset();
    getSession.mockReset();
  });

  it("enrolls and verifies TOTP to unlock workspace access from an aal1 session", async () => {
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "mfa_required",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "therapist",
      aal: "aal1",
      organizationId: "clinic_001",
      availableOrganizations: [
        { organizationId: "clinic_001", label: "LinguaLens Clinic" },
      ],
    }));

    listFactors
      .mockResolvedValueOnce({
        data: {
          all: [],
          totp: [],
          phone: [],
          webauthn: [],
        },
        error: null,
      })
      .mockResolvedValueOnce({
        data: {
          all: [{
            id: "factor_totp_001",
            factor_type: "totp",
            status: "unverified",
            friendly_name: "LinguaLens Authenticator",
          }],
          totp: [],
          phone: [],
          webauthn: [],
        },
        error: null,
      })
      .mockResolvedValueOnce({
        data: {
          all: [{
            id: "factor_totp_001",
            factor_type: "totp",
            status: "verified",
            friendly_name: "LinguaLens Authenticator",
          }],
          totp: [{
            id: "factor_totp_001",
            factor_type: "totp",
            status: "verified",
            friendly_name: "LinguaLens Authenticator",
          }],
          phone: [],
          webauthn: [],
        },
        error: null,
      });

    enroll.mockResolvedValue({
      data: {
        id: "factor_totp_001",
        type: "totp",
        friendly_name: "LinguaLens Authenticator",
        totp: {
          qr_code: "<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>",
          secret: "SECRET-CODE",
          uri: "otpauth://totp/LinguaLens",
        },
      },
      error: null,
    });

    challengeAndVerify.mockResolvedValue({
      data: {
        access_token: "access-token",
        token_type: "bearer",
        expires_in: 3600,
        refresh_token: "refresh-token",
        user: {
          id: "user_therapist_001",
          email: "clinician@clinic.example",
          app_metadata: {
            role: "therapist",
            membership_active: true,
            invitation_status: "accepted",
            organization_id: "clinic_001",
            organizations: [
              { organizationId: "clinic_001", label: "LinguaLens Clinic" },
            ],
          },
          user_metadata: {
            display_name: "Pilot Clinician",
          },
        },
      },
      error: null,
    });

    getSession.mockResolvedValue({
      data: {
        session: {
          aal: "aal2",
          user: {
            id: "user_therapist_001",
            email: "clinician@clinic.example",
            app_metadata: {
              role: "therapist",
              membership_active: true,
              invitation_status: "accepted",
              organization_id: "clinic_001",
              organizations: [
                { organizationId: "clinic_001", label: "LinguaLens Clinic" },
              ],
            },
            user_metadata: {
              display_name: "Pilot Clinician",
            },
          },
        },
      },
    });

    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    expect(await screen.findByRole("heading", { name: "Additional verification required" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start TOTP enrollment" }));

    expect(await screen.findByText("TOTP enrollment started. Scan the QR code or enter the secret, then verify with a current code.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("SECRET-CODE")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Authenticator code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Complete TOTP enrollment" }));

    await waitFor(() => {
      expect(challengeAndVerify).toHaveBeenCalledWith({
        factorId: "factor_totp_001",
        code: "123456",
      });
    });

    expect(await screen.findByText("Unlocked workspace")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"aal\":\"aal2\"");
  });

  it("treats the last active organization as a hint only until the user confirms it", async () => {
    window.localStorage.setItem("lingualens.supabase-organization-hint.v1", JSON.stringify({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      organizationId: "clinic_002",
    }));
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
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "org_selection_required",
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      role: "clinical_supervisor",
      aal: "aal2",
      availableOrganizations: [
        { organizationId: "clinic_001", label: "LinguaLens Clinic", role: "clinical_supervisor" },
        { organizationId: "clinic_002", label: "North Review Clinic", role: "org_admin" },
      ],
      suggestedOrganizationId: "clinic_002",
    }));

    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    expect(await screen.findByRole("heading", { name: "Choose an active organization" })).toBeInTheDocument();
    expect(screen.getByText(/The previous session used/)).toBeInTheDocument();
    expect(screen.queryByText("Unlocked workspace")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Continue with selected organization" }));

    expect(await screen.findByText("Unlocked workspace")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"organizationId\":\"clinic_002\"");
  });

  it("restores workspace access from Supabase localStorage when the access-session cache is stale signed_out", async () => {
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "signed_out",
    }));
    window.localStorage.setItem("sb-cbhwxklvcpgizeqriqxi-auth-token", JSON.stringify({
      access_token: createUnsignedJwt({ aal: "aal2" }),
      aal: "aal2",
      user: {
        id: "user_admin_001",
        email: "org.admin@clinic.example",
        app_metadata: {
          role: "org_admin",
          membership_active: true,
          invitation_status: "accepted",
          organization_id: "clinic_001",
          organizations: [
            { organizationId: "clinic_001", label: "LinguaLens Clinic", role: "org_admin" },
          ],
        },
      },
    }));

    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    expect(await screen.findByText("Unlocked workspace")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    expect(window.sessionStorage.getItem("lingualens.supabase-session-token.v1")).toBeTruthy();
  });
});

function createUnsignedJwt(payload: Record<string, unknown>): string {
  return [
    btoa(JSON.stringify({ alg: "none", typ: "JWT" })),
    btoa(JSON.stringify(payload)),
    "",
  ].join(".");
}
