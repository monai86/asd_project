import { z } from "zod";

const availability = z.enum(["available", "unavailable"]);
const experimentalAvailability = z.enum(["available", "experimental", "unavailable"]);
const optionalAvailability = z.enum(["available", "disabled", "unavailable"]);

export const runtimeSettingsSchema = z.object({
  mock_mode: z.boolean(),
  auth_mode: z.enum(["mock", "supabase"]),
  model_version: z.string(),
  feature_schema: z.string(),
  guideline_mapping: z.string(),
  user_roles: z.array(z.string()),
  access_model: z.object({
    invitation_only: z.boolean(),
    required_app_aal: z.enum(["aal1", "aal2"]),
    active_organization_session: z.string(),
    production_mock_mode: z.string(),
  }).optional(),
  data_retention: z.string(),
  consent_policy: z.string(),
  capabilities: z.object({
    cases: availability,
    audio_upload: experimentalAvailability,
    transcription: experimentalAvailability,
    transcript_qa: availability,
    feature_extraction: availability,
    ai_review: optionalAvailability,
    report_drafting: optionalAvailability,
    pdf_export: availability,
  }),
  pipeline_settings: z.object({
    audio_processing: z.string(),
    job_queue_mode: z.string(),
    repository_mode: z.string(),
    storage_mode: z.string(),
    ai_review_policy: z.string().optional(),
    ai_report_drafting_enabled: z.boolean().optional(),
  }),
});

export type RuntimeSettings = z.infer<typeof runtimeSettingsSchema>;
