import {
  AUTH_API_BASE_URL,
  DATA_MODE,
  PROCESSING_API_BASE_URL
} from "../constants.js";

export const REFERENCE_COMPARISON_ROUTE = "GET /api/sessions/:sessionId/reference-comparison";

export const REFERENCE_COMPARISON_STATUS = {
  BLOCKED: "blocked",
  LOADING: "loading",
  READY: "ready",
  UNAVAILABLE: "unavailable",
  ERROR: "error"
};

export const REFERENCE_REASON_LABELS = {
  no_transcript: "Upload or generate a CHAT transcript before comparison.",
  transcript_review_required: "Transcript review sign-off is required first.",
  features_missing: "Run feature extraction before comparison.",
  features_preliminary: "Feature extraction is still preliminary until transcript review is complete.",
  features_stale: "Re-run feature extraction after transcript edits.",
  features_not_completed: "Feature extraction must be completed before comparison.",
  qa_unavailable: "Backend Transcript QA must be available before comparison in API runtime.",
  qa_failed: "Transcript QA failed; correct blocking issues before comparison.",
  qa_needs_review: "Transcript QA still has warnings; interpret the comparison cautiously.",
  qa_reference_not_ready: "Transcript QA found metadata that must be corrected before reference comparison.",
  clan_metric_not_ready: "CLAN-derived metric readiness is limited for this transcript; interpret CLAN metrics cautiously.",
  backend_reference_unavailable_in_mock_mode: "Backend Reference Comparison is not configured in this mock runtime.",
  missing_user: "Sign in before loading a backend Reference Comparison."
};

export function referenceReasonLabel(reason) {
  return REFERENCE_REASON_LABELS[reason] || String(reason || "Reference Comparison is not ready.");
}

export function evaluateReferenceComparisonReadiness({ transcript, features, qaResult } = {}) {
  const reasons = [];
  const warnings = [];

  if (!transcript) {
    reasons.push("no_transcript");
  } else {
    if (transcript.review_status !== "reviewed") {
      reasons.push("transcript_review_required");
    }
    if (qaResult?.load_status === "error") {
      reasons.push("qa_unavailable");
    }
    const qaQuality = qaResult?.quality || transcript.qa_status;
    if (qaQuality === "fail") {
      reasons.push("qa_failed");
    } else if (qaQuality === "needs_review") {
      warnings.push("qa_needs_review");
    }
    if (qaResult?.readiness?.reference_comparison_ready === false && !reasons.includes("qa_failed")) {
      reasons.push("qa_reference_not_ready");
    }
    if (qaResult?.readiness?.clan_metric_ready === false) {
      warnings.push("clan_metric_not_ready");
    }
  }

  if (!features) {
    reasons.push("features_missing");
  } else {
    if (features.extraction_status === "stale") {
      reasons.push("features_stale");
    } else if (features.extraction_status === "preliminary") {
      reasons.push("features_preliminary");
    } else if (features.extraction_status !== "completed") {
      reasons.push("features_not_completed");
    }
    
    if ((features.features?.clan_metric_not_ready || (features.warnings && features.warnings.some(w => w.code === "CLAN_METRIC_NOT_READY"))) && !warnings.includes("clan_metric_not_ready")) {
      warnings.push("clan_metric_not_ready");
    }
  }

  return {
    ready: reasons.length === 0,
    status: reasons.length ? REFERENCE_COMPARISON_STATUS.BLOCKED : REFERENCE_COMPARISON_STATUS.READY,
    reasons,
    warnings
  };
}

function resolveFetch(fetchImpl) {
  if (fetchImpl) return fetchImpl;
  if (typeof fetch !== "undefined") return fetch;
  throw new Error("Fetch is unavailable in this runtime.");
}

function endpoint(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

export async function loadReferenceComparisonForSession({
  sessionId,
  transcript,
  features,
  qaResult,
  currentUser,
  apiBaseUrl = AUTH_API_BASE_URL || PROCESSING_API_BASE_URL,
  dataMode = DATA_MODE,
  fetchImpl = null
} = {}) {
  const readiness = evaluateReferenceComparisonReadiness({ transcript, features, qaResult });
  if (!readiness.ready) {
    return {
      ...readiness,
      payload: null,
      source: "readiness_gate",
      loaded_at: new Date().toISOString()
    };
  }

  if (!currentUser?.user_id) {
    return {
      status: REFERENCE_COMPARISON_STATUS.UNAVAILABLE,
      ready: false,
      reasons: ["missing_user"],
      warnings: readiness.warnings,
      payload: null,
      source: "auth",
      loaded_at: new Date().toISOString()
    };
  }

  if (!apiBaseUrl) {
    return {
      status: REFERENCE_COMPARISON_STATUS.UNAVAILABLE,
      ready: false,
      reasons: ["backend_reference_unavailable_in_mock_mode"],
      warnings: readiness.warnings,
      payload: null,
      source: dataMode === "mock" ? "mock_status_only" : "api_not_configured",
      loaded_at: new Date().toISOString()
    };
  }

  try {
    const response = await resolveFetch(fetchImpl)(
      endpoint(apiBaseUrl, `/api/sessions/${sessionId}/reference-comparison`),
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": currentUser.user_id
        }
      }
    );
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;
    if (!response.ok) {
      return {
        status: REFERENCE_COMPARISON_STATUS.ERROR,
        ready: false,
        reasons: [],
        warnings: readiness.warnings,
        payload: null,
        error_status: response.status,
        error_detail: payload?.detail || "Reference Comparison request failed.",
        source: "api",
        loaded_at: new Date().toISOString()
      };
    }

    return {
      status: REFERENCE_COMPARISON_STATUS.READY,
      ready: true,
      reasons: [],
      warnings: readiness.warnings,
      payload,
      source: "api",
      loaded_at: new Date().toISOString()
    };
  } catch (error) {
    return {
      status: REFERENCE_COMPARISON_STATUS.ERROR,
      ready: false,
      reasons: [],
      warnings: readiness.warnings,
      payload: null,
      error_detail: error.message || "Reference Comparison request failed.",
      source: "api",
      loaded_at: new Date().toISOString()
    };
  }
}

export function topReferenceFeatures(comparisonPayload = {}, aiOutput = {}, fallbackLimit = 5) {
  const preferred = new Set(aiOutput?.top_contributing_features || []);
  const cohorts = comparisonPayload?.cohorts || [];
  const firstCohort = cohorts[0] || {};
  const rows = firstCohort.feature_comparisons || [];
  const preferredRows = rows.filter(row => preferred.has(row.feature));
  if (preferredRows.length) return preferredRows;
  return rows.slice(0, fallbackLimit);
}
