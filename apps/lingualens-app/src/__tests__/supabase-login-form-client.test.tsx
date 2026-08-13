import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { routerPush, routerRefresh } from "@/__tests__/setup";
import { SupabaseLoginFormClient } from "@/components/supabase-login-form-client";
import type { RuntimeSettings } from "@/lib/api";
import { resetSupabaseBrowserClientForTests } from "@/lib/supabase-browser-client";

const signInWithPassword = vi.fn();
const resetPasswordForEmail = vi.fn();

vi.mock("@/lib/supabase-browser-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/supabase-browser-client")>("@/lib/supabase-browser-client");

  return {
    ...actual,
    getSupabaseBrowserClient: () => ({
      auth: {
        signInWithPassword,
        resetPasswordForEmail,
      },
    }),
  };
});

const runtimeSettings: RuntimeSettings = {
  mock_mode: false,
  auth_mode: "supabase",
  model_version: "test-model",
  feature_schema: "test-schema",
  guideline_mapping: "test-guideline-map",
  user_roles: ["therapist", "clinical_supervisor", "org_admin"],
  access_model: {
    invitation_only: true,
    required_app_aal: "aal2",
    active_organization_session: "explicit_selection_when_ambiguous",
    production_mock_mode: "forbidden",
  },
  data_retention: "test-retention",
  consent_policy: "test-consent",
  capabilities: {
    cases: "available",
    audio_upload: "experimental",
    transcription: "experimental",
    transcript_qa: "available",
    feature_extraction: "available",
    ai_review: "disabled",
    report_drafting: "disabled",
    pdf_export: "unavailable",
  },
  pipeline_settings: {
    audio_processing: "test-audio",
    job_queue_mode: "test-queue",
    repository_mode: "test-repository",
    storage_mode: "test-storage",
  },
};

describe("SupabaseLoginFormClient", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    routerPush.mockClear();
    routerRefresh.mockClear();
    signInWithPassword.mockReset();
    resetPasswordForEmail.mockReset();
    resetSupabaseBrowserClientForTests();
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://lingualens.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "sb_publishable_test-key");
  });

  it("submits email/password sign-in and routes org admins to settings", async () => {
    const listener = vi.fn();
    signInWithPassword.mockResolvedValue({
      data: {
        session: {
          user: {
            app_metadata: {
              role: "org_admin",
            },
          },
        },
      },
      error: null,
    });
    window.addEventListener("lingualens:supabase-session-source", listener as EventListener);

    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@clinic.example" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in with Supabase" }));

    await waitFor(() => {
      expect(signInWithPassword).toHaveBeenCalledWith({
        email: "admin@clinic.example",
        password: "secret-password",
      });
    });
    await waitFor(() => {
      expect(listener).toHaveBeenCalledTimes(1);
      expect(routerPush).toHaveBeenCalledWith("/settings?scope=admin");
      expect(routerRefresh).toHaveBeenCalled();
    });

    window.removeEventListener("lingualens:supabase-session-source", listener as EventListener);
  });

  it("sends a Supabase password recovery email back to the login route", async () => {
    resetPasswordForEmail.mockResolvedValue({
      error: null,
    });

    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "clinician@clinic.example" } });
    fireEvent.click(screen.getByRole("button", { name: "Send recovery email" }));

    await waitFor(() => {
      expect(resetPasswordForEmail).toHaveBeenCalledWith("clinician@clinic.example", {
        redirectTo: "http://localhost:3000/login",
      });
    });
    expect(await screen.findByText("Recovery email sent. App access still requires accepted membership and AAL2 after reset.")).toBeInTheDocument();
  });

  it("fails closed with an explicit invalid-config status when the browser env is malformed", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://lingualens.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "bad-key");

    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    expect(screen.getByRole("button", { name: "Supabase browser config invalid" })).toBeDisabled();
    expect(
      screen.getByText((content) => content.includes(
        "NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is malformed for the launch contract.",
      )),
    ).toBeInTheDocument();
  });
});
