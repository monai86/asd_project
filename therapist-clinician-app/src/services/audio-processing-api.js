import {
  createProcessingJob,
  normalizeProcessingJobStage,
  processingJobSessionStatus,
  createTranscript
} from "@shared/models";
import {
  PROCESSING_API_BASE_URL,
  PROCESSING_MODE,
  normalizeProcessingMode
} from "../constants.js";
import { CORE_14_FEATURE_KEYS, OPTIONAL_INDICATOR_KEYS, pickFeatureKeys } from "@shared/services/feature-extraction-service.js";

export const AUDIO_PROCESSING_ROUTES = [
  "POST /api/sessions/:sessionId/audio/upload-intent",
  "POST /api/sessions/:sessionId/process-audio",
  "GET /api/jobs/:jobId",
  "GET /api/sessions/:sessionId/transcript",
  "PATCH /api/transcripts/:transcriptId/lines/:lineId",
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

export async function createSecureAudioUploadIntent(sessionId, file, options = {}) {
  const mode = normalizeProcessingMode(options.processingMode || PROCESSING_MODE);
  const apiBaseUrl = options.apiBaseUrl ?? PROCESSING_API_BASE_URL;
  if (mode === "mock" || mode === "api_placeholder" || !apiBaseUrl) {
    return {
      status: "not_configured",
      mode,
      message: "Secure backend upload is not configured yet. Keep metadata-only mode for demos or configure PROCESSING_API_BASE_URL."
    };
  }

  return requestJson(`/api/sessions/${sessionId}/audio/upload-intent`, {
    method: "POST",
    body: buildSecureUploadIntentPayload(file, options),
    fetchImpl: resolveFetch(options.fetchImpl),
    apiBaseUrl
  });
}

export function buildSecureUploadIntentPayload(file, options = {}) {
  return {
    original_filename: file.name,
    file_size: file.size,
    mime_type: file.type || "application/octet-stream",
    checksum_sha256: options.checksumSha256 || file.checksum_sha256 || file.sha256 || null,
    retention_days: options.retentionDays || file.retention_days || 90,
    storage_provider: options.storageProvider || "supabase"
  };
}

export function mapUploadIntentToClientMetadata(intent = {}) {
  const fileObject = intent.file_object || {};
  const upload = intent.upload || {};
  return {
    audio_file_id: intent.audio_file?.audio_file_id || fileObject.audio_file_id || null,
    file_object_id: fileObject.file_object_id || upload.file_object_id || null,
    storage_mode: intent.audio_file?.storage_mode || "secure_private",
    encryption_status: fileObject.encryption_status || "required",
    retention_delete_after: fileObject.retention_delete_after || null,
    checksum_sha256: fileObject.checksum_sha256 || null,
    signed_upload_url: upload.signed_upload_url || upload.url || null,
    signed_upload_expires_in_seconds: upload.expires_in_seconds || null,
    storage_provider: upload.storage_provider || "supabase",
    exposes_permanent_storage_key: Boolean(fileObject.storage_key)
  };
}

export async function getProcessingJobStatus(jobId, options = {}) {
  return requestJson(`/api/jobs/${jobId}`, {
    fetchImpl: resolveFetch(options.fetchImpl),
    apiBaseUrl: options.apiBaseUrl ?? PROCESSING_API_BASE_URL
  });
}

export function mapBackendJobToProcessingJob(payload = {}) {
  const status = payload.status || "queued";
  const stage = normalizeProcessingJobStage(payload.stage, status);
  return createProcessingJob({
    job_id: payload.job_id,
    session_id: payload.session_id,
    case_id: payload.case_id,
    owner_user_id: payload.owner_user_id,
    audio_file_id: payload.audio_file_id ?? null,
    job_type: payload.job_type || "audio_pipeline",
    status,
    stage,
    progress: payload.progress ?? 0,
    error_code: payload.error_code ?? null,
    error_message: payload.error_message || "",
    result_refs: payload.result_refs || {},
    created_at: payload.created_at,
    updated_at: payload.updated_at || payload.created_at,
    started_at: payload.started_at ?? null,
    finished_at: payload.finished_at ?? null
  });
}

export function processingJobToSessionUpdates(job = {}) {
  return {
    processing_status: processingJobSessionStatus(job),
    processing_job_id: job.job_id || null,
    processing_stage: normalizeProcessingJobStage(job.stage, job.status),
    processing_progress: job.progress ?? 0,
    processing_error_code: job.error_code ?? null,
    processing_error_message: job.error_message || ""
  };
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

export function mapBackendLinesToTranscriptLines(payload = {}, { transcriptId = null, session = null, ownerUserId = null } = {}) {
  const transcriptPayload = payload.transcript || {};
  const rows =
    payload.transcript_lines ||
    payload.lines ||
    payload.utterances ||
    transcriptPayload.transcript_lines ||
    transcriptPayload.lines ||
    transcriptPayload.utterances ||
    parseChatTextToBackendRows(
      transcriptPayload.chat_text ||
      transcriptPayload.transcript_text ||
      payload.chat_text ||
      payload.transcript_text ||
      ""
    );
  return rows.map((item, index) => {
    const lineNumber = item.line_number || index + 1;
    return {
      line_id: item.line_id || (transcriptId ? `${transcriptId}_L${String(lineNumber).padStart(4, "0")}` : undefined),
      transcript_id: item.transcript_id || transcriptId,
      session_id: item.session_id || session?.session_id,
      case_id: item.case_id || session?.case_id,
      owner_user_id: item.owner_user_id || ownerUserId,
      line_number: lineNumber,
      speaker: toTranscriptSpeakerLabel(item),
      text: item.text || item.utterance_text || item.transcript || "",
      confidence: item.confidence ?? null,
      timing: item.start_time || item.end_time || item.start || item.end
        ? {
            start_time: item.start_time ?? item.start ?? null,
            end_time: item.end_time ?? item.end ?? null
          }
        : null,
      start_time: item.start_time ?? item.start ?? null,
      end_time: item.end_time ?? item.end ?? null,
      clinical_flags: item.clinical_flags || item.flags || [],
      review_status: item.review_status || "needs_review",
      reviewed: item.reviewed || false,
      interpretation_note: item.interpretation_note || "",
      version: item.version || 1,
      updated_at: item.updated_at || null,
      updated_by_user_id: item.updated_by_user_id || null
    };
  });
}

function parseChatTextToBackendRows(chatText = "") {
  const rows = [];
  let pendingTiming = null;
  for (const rawLine of String(chatText).split(/\r?\n/)) {
    const timingMatch = rawLine.match(/^%tim:\s*(.+)$/);
    if (timingMatch && rows.length) {
      pendingTiming = parseChatTiming(timingMatch[1]);
      if (pendingTiming) {
        rows[rows.length - 1] = {
          ...rows[rows.length - 1],
          start_time: pendingTiming.start_time,
          end_time: pendingTiming.end_time
        };
      }
      continue;
    }

    const mainLineMatch = rawLine.match(/^\*([A-Z]{3}):\s*(.+)$/);
    if (!mainLineMatch) continue;

    const lineNumber = rows.length + 1;
    rows.push({
      line_number: lineNumber,
      speaker_code: mainLineMatch[1],
      utterance_text: stripChatTiming(mainLineMatch[2]),
      confidence: 1,
      review_status: "needs_review",
      reviewed: false
    });
    pendingTiming = null;
  }
  return rows;
}

function stripChatTiming(text = "") {
  return String(text).replace(/\x15\d+_\d+\x15/g, "").trim();
}

function parseChatTiming(value = "") {
  const times = String(value).match(/(\d{2}:\d{2}:\d{2}\.\d{3})/g);
  if (!times?.length) return null;
  const start = chatTimeToSeconds(times[0]);
  const end = times[1] ? chatTimeToSeconds(times[1]) : null;
  return { start_time: start, end_time: end };
}

function chatTimeToSeconds(value) {
  const [hh = "0", mm = "0", ss = "0"] = String(value).split(":");
  return Number(hh) * 3600 + Number(mm) * 60 + Number(ss);
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
  const optionalRows = featuresPayload.optional_indicators || featuresPayload.indicators || featureRows;
  const coreFeatures = pickFeatureKeys(featureRows || {}, CORE_14_FEATURE_KEYS);
  const optionalIndicators = pickFeatureKeys(optionalRows || {}, OPTIONAL_INDICATOR_KEYS);
  const featuresSet = {
    feature_id: featuresPayload.feature_id || `FEATURE-${String(transcriptCount + 1).padStart(3, "0")}`,
    session_id: session.session_id,
    case_id: session.case_id,
    owner_user_id: ownerUserId,
    feature_schema_version: featuresPayload.feature_schema_version || "14-feature-schema",
    core_features: coreFeatures,
    optional_indicators: {
      ...optionalIndicators,
      ...(featuresPayload.interaction_indicators || {}),
      ...(featuresPayload.acoustic_indicators || {})
    },
    features: {
      ...coreFeatures,
      ...optionalIndicators,
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
        model_version: aiPayload.model_version || "screening-support-v0.2.0",
        confidence_interval: aiPayload.confidence_interval ?? null,
        evidence_items: aiPayload.evidence_items || [],
        top_contributing_features: aiPayload.top_contributing_features || [],
        plain_language_explanation:
          aiPayload.plain_language_explanation ||
          "This output highlights speech-language patterns that may warrant closer clinical review. It is not a diagnosis.",
        therapist_review_status: "requires_transcript_review",
        explanation:
          aiPayload.explanation ||
          "AI-assisted explanation requires transcript review before clinical interpretation. It is not a diagnosis.",
        created_at: aiPayload.created_at || now
      }
    : null;

  return {
    transcriptRecord,
    transcriptLines: mapBackendLinesToTranscriptLines(payload, { transcriptId, session, ownerUserId }),
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
