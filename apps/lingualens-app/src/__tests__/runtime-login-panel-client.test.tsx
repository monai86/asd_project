import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";

test("does not expose mock login when runtime settings are malformed", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    mock_mode: true,
    auth_mode: "mock",
    capabilities: { cases: "maybe" },
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  })));

  render(<RuntimeLoginPanelClient />);

  expect(await screen.findByRole("heading", { name: "Runtime settings unavailable" })).toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Mock login form" })).not.toBeInTheDocument();
});

test("does not expose mock login for an unknown runtime auth mode", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    ...validRuntimeSettings,
    auth_mode: "oidc",
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  })));

  render(<RuntimeLoginPanelClient />);

  expect(await screen.findByRole("heading", { name: "Runtime settings unavailable" })).toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Mock login form" })).not.toBeInTheDocument();
});

const validRuntimeSettings = {
  mock_mode: false,
  auth_mode: "supabase",
  model_version: "v2-mock",
  feature_schema: "lingualens-app.1",
  guideline_mapping: "review-support-only",
  user_roles: ["therapist"],
  data_retention: "configured",
  consent_policy: "required",
  capabilities: {
    cases: "available",
    audio_upload: "unavailable",
    transcription: "unavailable",
    transcript_qa: "available",
    feature_extraction: "available",
    ai_review: "disabled",
    report_drafting: "disabled",
    pdf_export: "unavailable",
  },
  pipeline_settings: {
    audio_processing: "experimental_async",
    job_queue_mode: "redis",
    repository_mode: "sql",
    storage_mode: "supabase_private",
  },
};
