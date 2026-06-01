import {
  AUTH_API_BASE_URL,
  DATA_MODE,
  PROCESSING_API_BASE_URL
} from "../constants.js";
import { checkTranscriptQuality } from "@shared/services/safety-service.js";

export const TRANSCRIPT_QA_ROUTE = "GET /api/sessions/:sessionId/qa";

export const TRANSCRIPT_QA_LOAD_STATUS = {
  LOADING: "loading",
  READY: "ready",
  UNAVAILABLE: "unavailable",
  ERROR: "error"
};

function resolveFetch(fetchImpl) {
  if (fetchImpl) return fetchImpl;
  if (typeof fetch !== "undefined") return fetch;
  throw new Error("Fetch is unavailable in this runtime.");
}

function endpoint(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

function defaultReadiness(quality) {
  const failed = quality === "fail";
  return {
    feature_extraction_ready: !failed,
    reference_comparison_ready: !failed,
    clan_metric_ready: quality === "pass",
    blockers: {
      feature_extraction: failed ? ["qa_failed"] : [],
      reference_comparison: failed ? ["qa_failed"] : []
    },
    warnings: {
      clan_metric: quality === "pass" ? [] : ["lightweight_local_qa"]
    }
  };
}

export function normalizeTranscriptQaPayload(payload = {}, source = "api") {
  const quality = payload.status || payload.qa_status || payload.quality || "needs_review";
  const score = payload.quality_score ?? payload.qa_score ?? payload.score ?? null;
  const issues = payload.issues || payload.qa_issues || payload.warnings || [];
  return {
    load_status: TRANSCRIPT_QA_LOAD_STATUS.READY,
    source,
    transcript_id: payload.transcript_id || null,
    session_id: payload.session_id || null,
    quality,
    score,
    summary: payload.summary || {},
    issues,
    readiness: payload.readiness || defaultReadiness(quality),
    generated_at: payload.generated_at || null
  };
}

export function buildLocalTranscriptQaResult(transcript, transcriptLines = []) {
  if (!transcript) {
    return {
      load_status: TRANSCRIPT_QA_LOAD_STATUS.UNAVAILABLE,
      source: "local_missing_transcript",
      quality: "fail",
      score: 0,
      issues: [],
      readiness: defaultReadiness("fail")
    };
  }
  const qa = checkTranscriptQuality(transcript.transcript_text, transcriptLines);
  const readiness = defaultReadiness(qa.quality);
  readiness.clan_metric_ready = false;
  readiness.warnings.clan_metric = Array.from(new Set([
    ...(readiness.warnings.clan_metric || []),
    "lightweight_local_qa"
  ]));
  return normalizeTranscriptQaPayload({
    transcript_id: transcript.transcript_id,
    session_id: transcript.session_id,
    quality: qa.quality,
    score: qa.score,
    issues: qa.warnings,
    readiness,
  }, "local_lightweight");
}

export function shouldLoadBackendTranscriptQa({
  transcript,
  currentUser,
  qaState,
  apiBaseUrl = AUTH_API_BASE_URL || PROCESSING_API_BASE_URL,
  dataMode = DATA_MODE
} = {}) {
  if (!transcript || !currentUser?.user_id || !apiBaseUrl) return false;
  if (dataMode === "mock") return false;
  return !qaState;
}

export async function loadTranscriptQaForSession({
  sessionId,
  currentUser,
  apiBaseUrl = AUTH_API_BASE_URL || PROCESSING_API_BASE_URL,
  fetchImpl = null
} = {}) {
  if (!sessionId || !currentUser?.user_id || !apiBaseUrl) {
    return {
      load_status: TRANSCRIPT_QA_LOAD_STATUS.UNAVAILABLE,
      source: "api_not_configured",
      quality: "needs_review",
      score: null,
      issues: [],
      readiness: defaultReadiness("needs_review")
    };
  }

  try {
    const response = await resolveFetch(fetchImpl)(
      endpoint(apiBaseUrl, `/api/sessions/${sessionId}/qa`),
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": currentUser.user_id
        }
      }
    );
    const text = await response.text();
    const payload = text ? JSON.parse(text) : {};
    if (!response.ok) {
      return {
        load_status: TRANSCRIPT_QA_LOAD_STATUS.ERROR,
        source: "api",
        quality: "needs_review",
        score: null,
        issues: [],
        readiness: defaultReadiness("needs_review"),
        error_status: response.status,
        error_detail: payload?.detail || "Transcript QA request failed."
      };
    }
    return normalizeTranscriptQaPayload(payload, "api");
  } catch (error) {
    return {
      load_status: TRANSCRIPT_QA_LOAD_STATUS.ERROR,
      source: "api",
      quality: "needs_review",
      score: null,
      issues: [],
      readiness: defaultReadiness("needs_review"),
      error_detail: error.message || "Transcript QA request failed."
    };
  }
}
