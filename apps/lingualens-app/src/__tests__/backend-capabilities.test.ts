import { expect, test } from "vitest";

import { deriveBackendCapabilities } from "@/services/capabilities/backend-capabilities";

test("derives experimental and disabled capabilities from runtime settings", () => {
  expect(deriveBackendCapabilities({
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
      job_queue_mode: "redis",
      repository_mode: "sql",
      storage_mode: "supabase",
    },
  })).toMatchObject({ audioUpload: "experimental", aiReview: "disabled" });
});

test("rejects an unknown backend capability value", () => {
  expect(() => deriveBackendCapabilities({ capabilities: { cases: "maybe" } } as never)).toThrow();
});
