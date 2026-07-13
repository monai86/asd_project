import {
  runtimeSettingsSchema,
  type RuntimeSettings,
} from "@/services/api/runtime-settings-schema";

export type BackendCapabilities = {
  cases: "available" | "unavailable";
  audioUpload: "available" | "experimental" | "unavailable";
  transcription: "available" | "experimental" | "unavailable";
  transcriptQa: "available" | "unavailable";
  featureExtraction: "available" | "unavailable";
  aiReview: "available" | "disabled" | "unavailable";
  reportDrafting: "available" | "disabled" | "unavailable";
  pdfExport: "available" | "unavailable";
};

export function deriveBackendCapabilities(input: RuntimeSettings): BackendCapabilities {
  const settings = runtimeSettingsSchema.parse(input);
  return {
    cases: settings.capabilities.cases,
    audioUpload: settings.capabilities.audio_upload,
    transcription: settings.capabilities.transcription,
    transcriptQa: settings.capabilities.transcript_qa,
    featureExtraction: settings.capabilities.feature_extraction,
    aiReview: settings.capabilities.ai_review,
    reportDrafting: settings.capabilities.report_drafting,
    pdfExport: settings.capabilities.pdf_export,
  };
}
