import { createTranscript } from "@shared/models";
import {
  PROCESSING_API_BASE_URL,
  PROCESSING_MODE,
  normalizeProcessingMode
} from "../constants.js";

export const AUDIO_PROCESSING_ROUTES = [
  "POST /api/sessions/:sessionId/process-audio",
  "GET /api/jobs/:jobId/status",
  "GET /api/sessions/:sessionId/transcript",
  "GET /api/sessions/:sessionId/features",
  "GET /api/sessions/:sessionId/qa"
];

export class BackendAudioProcessingUnavailableError extends Error {
  constructor(message) {
    super(message);
    this.name = "BackendAudioProcessingUnavailableError";
  }
}

function endpoint(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function requestJson(path, { method = "GET", body, fetchImpl, apiBaseUrl } = {}) {
  if (!apiBaseUrl) {
    throw new BackendAudioProcessingUnavailableError(
      "Backend audio processing API is not configured. Use PROCESSING_MODE=mock to run the mock transcription workflow."
    );
  }

  const response = await fetchImpl(endpoint(apiBaseUrl, path), {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    throw new Error(`Audio processing API request failed with status ${response.status}.`);
  }
  return response.json();
}

function resolveFetch(fetchImpl) {
  if (fetchImpl) return fetchImpl;
  if (typeof fetch !== "undefined") return fetch;
  throw new BackendAudioProcessingUnavailableError("Fetch is unavailable in this runtime.");
}

function notConfiguredResult(mode) {
  return {
    job_id: null,
    status: "not_configured",
    mode,
    message: "Backend audio processing adapter is not configured yet. Use PROCESSING_MODE=mock for mock transcription.",
    suggested_routes: AUDIO_PROCESSING_ROUTES
  };
}

export async function submitAudioProcessingJob(sessionId, audioFileId, options = {}) {
  const mode = normalizeProcessingMode(options.processingMode || PROCESSING_MODE);
  const apiBaseUrl = options.apiBaseUrl ?? PROCESSING_API_BASE_URL;
  if (mode === "mock" || mode === "api_placeholder" || !apiBaseUrl) {
    return notConfiguredResult(mode);
  }

  return requestJson(`/api/sessions/${sessionId}/process-audio`, {
    method: "POST",
    body: { audio_file_id: audioFileId },
    fetchImpl: resolveFetch(options.fetchImpl),
    apiBaseUrl
  });
}

export async function getProcessingJobStatus(jobId, options = {}) {
  return requestJson(`/api/jobs/${jobId}/status`, {
    fetchImpl: resolveFetch(options.fetchImpl),
    apiBaseUrl: options.apiBaseUrl ?? PROCESSING_API_BASE_URL
  });
}

export async function getSessionTranscript(sessionId, options = {}) {
  return requestJson(`/api/sessions/${sessionId}/transcript`, {
    fetchImpl: resolveFetch(options.fetchImpl),
    apiBaseUrl: options.apiBaseUrl ?? PROCESSING_API_BASE_URL
  });
}

export async function getSessionFeatures(sessionId, options = {}) {
  return requestJson(`/api/sessions/${sessionId}/features`, {
    fetchImpl: resolveFetch(options.fetchImpl),
    apiBaseUrl: options.apiBaseUrl ?? PROCESSING_API_BASE_URL
  });
}

export async function getSessionQaResult(sessionId, options = {}) {
  return requestJson(`/api/sessions/${sessionId}/qa`, {
    fetchImpl: resolveFetch(options.fetchImpl),
    apiBaseUrl: options.apiBaseUrl ?? PROCESSING_API_BASE_URL
  });
}

function toTranscriptSpeakerLabel(item) {
  const raw = (item.speaker || item.speaker_code || item.speaker_label || "INV").toUpperCase();
  if (raw === "CHILD") return "CHI";
  if (raw === "CAREGIVER" || raw === "MOTHER" || raw === "MOT") return "MOT";
  if (raw === "THERAPIST" || raw === "INV") return "INV";
  return raw.length <= 4 ? raw : "INV";
}

export function mapBackendLinesToTranscriptLines(payload = {}) {
  const rows = payload.transcript_lines || payload.lines || payload.utterances || [];
  return rows.map((item, index) => ({
    line_number: item.line_number || index + 1,
    speaker: toTranscriptSpeakerLabel(item),
    text: item.text || item.transcript || "",
    confidence: item.confidence ?? null,
    timing: item.start_time || item.end_time || item.start || item.end
      ? {
          start_time: item.start_time ?? item.start ?? null,
          end_time: item.end_time ?? item.end ?? null
        }
      : null,
    start_time: item.start_time ?? item.start ?? null,
    end_time: item.end_time ?? item.end ?? null,
    clinical_flags: item.clinical_flags || [],
    review_status: "needs_review",
    reviewed: false,
    interpretation_note: ""
  }));
}

export function mapBackendProcessingResultToFrontend(payload, { session, childCase, currentUser, transcriptCount = 0 } = {}) {
  const now = new Date().toISOString();
  const transcriptPayload = payload.transcript || payload;
  const qaPayload = payload.qa || payload.qa_result || transcriptPayload.qa || {};
  const featuresPayload = payload.features || payload.extracted_features || {};
  const aiPayload = payload.ai_screening_output || payload.ai_decision_support || null;
  const ownerUserId = session?.owner_user_id || currentUser?.user_id;
  const transcriptId =
    transcriptPayload.transcript_id ||
    `TRANSCRIPT-${String(transcriptCount + 1).padStart(3, "0")}`;

  const transcriptRecord = {
    ...createTranscript({
      transcript_id: transcriptId,
      session_id: session.session_id,
      case_id: session.case_id,
      owner_user_id: ownerUserId,
      original_filename: transcriptPayload.original_filename || "backend_generated.cha",
      transcript_text: transcriptPayload.chat_text || transcriptPayload.transcript_text || payload.chat_text || "",
      review_status: "awaiting_review",
      qa_status: qaPayload.status || qaPayload.qa_status || "needs_review",
      qa_score: qaPayload.score ?? qaPayload.qa_score ?? null,
      qa_issues: qaPayload.issues || qaPayload.qa_issues || [],
      reviewer_notes: "Backend ASR-generated transcript requires therapist review before interpretation.",
      created_at: now,
      updated_at: now
    }),
    review_required: true,
    generated_by: "backend_audio_pipeline"
  };

  const featureRows = featuresPayload.features || featuresPayload.core_14_features || featuresPayload;
  const featuresSet = {
    feature_id: featuresPayload.feature_id || `FEATURE-${String(transcriptCount + 1).padStart(3, "0")}`,
    session_id: session.session_id,
    case_id: session.case_id,
    owner_user_id: ownerUserId,
    feature_schema_version: featuresPayload.feature_schema_version || "14-feature-schema",
    features: {
      ...(featureRows || {}),
      ...(featuresPayload.interaction_indicators || {}),
      ...(featuresPayload.acoustic_indicators || {})
    },
    extraction_status: "preliminary",
    review_status: "preliminary",
    created_at: now
  };

  const aiOutput = aiPayload
    ? {
        ...aiPayload,
        session_id: session.session_id,
        case_id: session.case_id,
        owner_user_id: ownerUserId,
        therapist_review_status: "requires_transcript_review",
        explanation:
          aiPayload.explanation ||
          "AI-assisted explanation requires transcript review before clinical interpretation.",
        created_at: aiPayload.created_at || now
      }
    : null;

  return {
    transcriptRecord,
    transcriptLines: mapBackendLinesToTranscriptLines(payload),
    featuresSet,
    aiOutput,
    qaResult: qaPayload,
    sessionUpdates: {
      transcript_id: transcriptId,
      processing_status: "transcript_ready",
      feature_extraction_status: "preliminary",
      ai_analysis_status: aiOutput ? "requires_transcript_review" : "not_started",
      therapist_review_status: "awaiting_review"
    },
    childCase
  };
}
