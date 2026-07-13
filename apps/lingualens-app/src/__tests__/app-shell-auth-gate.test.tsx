import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";
import { resetSupabaseAuthRuntimeSyncForTests } from "@/lib/supabase-auth-runtime";

const listFactors = vi.fn();
const enroll = vi.fn();
const challengeAndVerify = vi.fn();
const getSession = vi.fn();
const signOut = vi.fn();
const onAuthStateChange = vi.fn();

vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession,
      signOut,
      onAuthStateChange,
      mfa: {
        listFactors,
        enroll,
        challengeAndVerify,
      },
    },
  }),
}));

describe("AppShell auth gating", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    resetSupabaseAuthRuntimeSyncForTests();
    listFactors.mockReset();
    enroll.mockReset();
    challengeAndVerify.mockReset();
    getSession.mockReset();
    signOut.mockReset();
    onAuthStateChange.mockReset();
    getSession.mockResolvedValue({
      data: {
        session: null,
      },
    });
    onAuthStateChange.mockReturnValue({
      data: {
        subscription: {
          unsubscribe: vi.fn(),
        },
      },
    });
  });

  it("keeps aal1 supabase sessions on the MFA gate instead of rendering workspace content", async () => {
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
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
    }));
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

    listFactors.mockResolvedValue({
      data: {
        all: [],
        totp: [],
        phone: [],
        webauthn: [],
      },
      error: null,
    });
    getSession.mockResolvedValue({
      data: {
        session: {
          aal: "aal1",
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
          },
        },
      },
    });

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "configured",
          consent_policy: "required",
          capabilities: runtimeCapabilities,
          pipeline_settings: runtimePipelineSettings,
        });
      }
      return jsonResponse({});
    }));

    render(
      <AppShell active="Home">
        <div>Workspace payload</div>
      </AppShell>,
    );

    expect(await screen.findByRole("heading", { name: "Additional verification required" })).toBeInTheDocument();
    expect(screen.queryByText("Workspace payload")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /primary navigation/i })).not.toBeInTheDocument();
  });

  it("renders workspace chrome when the supabase session is already aal2 and organization-scoped", async () => {
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "therapist",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
        ],
      },
    }));
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "therapist",
      aal: "aal2",
      organizationId: "clinic_001",
      availableOrganizations: [
        { organizationId: "clinic_001", label: "LinguaLens Clinic" },
      ],
    }));
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
          },
        },
      },
    });

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "configured",
          consent_policy: "required",
          capabilities: runtimeCapabilities,
          pipeline_settings: runtimePipelineSettings,
        });
      }
      return jsonResponse({});
    }));

    render(
      <AppShell active="Cases">
        <div>Workspace payload</div>
      </AppShell>,
    );

    await waitFor(() => expect(screen.getByText("Workspace payload")).toBeInTheDocument());
    expect(screen.getByRole("navigation", { name: /primary navigation/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /log out/i }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Additional verification required" })).not.toBeInTheDocument();
  });

  it("blocks workspace access when runtime settings fail schema validation", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));

    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      mock_mode: true,
      auth_mode: "mock",
      capabilities: { cases: "maybe" },
    })));

    render(
      <AppShell active="Cases">
        <div>Workspace payload</div>
      </AppShell>,
    );

    expect(await screen.findByRole("heading", { name: "Workspace access is blocked" })).toBeInTheDocument();
    expect(screen.queryByText("Workspace payload")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /primary navigation/i })).not.toBeInTheDocument();
  });
});

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const runtimeCapabilities = {
  cases: "available",
  audio_upload: "experimental",
  transcription: "experimental",
  transcript_qa: "available",
  feature_extraction: "available",
  ai_review: "disabled",
  report_drafting: "disabled",
  pdf_export: "unavailable",
};

const runtimePipelineSettings = {
  audio_processing: "experimental_async",
  job_queue_mode: "redis",
  repository_mode: "sql",
  storage_mode: "supabase_private",
};
