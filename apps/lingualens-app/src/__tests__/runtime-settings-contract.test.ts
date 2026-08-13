import { afterEach, describe, expect, it, vi } from "vitest";

import { getRuntimeSettings, type RuntimeSettings } from "@/lib/api";

const runtimeSettingsPayload: RuntimeSettings = {
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
  data_retention: "configured-by-deployment-policy",
  consent_policy: "explicit-consent-required-before-upload",
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
    audio_processing: "experimental_async",
    job_queue_mode: "in_process",
    repository_mode: "json",
    storage_mode: "local_private",
    ai_review_policy: "organization_opt_in_default_off",
    ai_report_drafting_enabled: false,
  },
};

describe("runtime settings contract", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("preserves Supabase auth and experimental async audio processing settings", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify(runtimeSettingsPayload),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    )));

    const settings = await getRuntimeSettings();

    expect(settings.auth_mode).toBe("supabase");
    expect(settings.pipeline_settings.audio_processing).toBe("experimental_async");
  });
});
