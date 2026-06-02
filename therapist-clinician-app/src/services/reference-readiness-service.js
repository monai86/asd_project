import {
  AUTH_API_BASE_URL,
  DATA_MODE,
  PROCESSING_API_BASE_URL
} from "../constants.js";

export const REFERENCE_READINESS_ROUTE = "GET /api/reference/readiness";

export const REFERENCE_READINESS_STATUS = {
  READY: "ready",
  LOADING: "loading",
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

export async function loadReferenceReadiness({
  currentUser,
  apiBaseUrl = AUTH_API_BASE_URL || PROCESSING_API_BASE_URL,
  dataMode = DATA_MODE,
  fetchImpl = null
} = {}) {
  if (!currentUser?.user_id) {
    return {
      status: REFERENCE_READINESS_STATUS.UNAVAILABLE,
      summary: { ok: 0, low_n: 0, not_cohort_ready: 0 },
      cells: [],
      error_detail: "Sign in is required to load reference readiness."
    };
  }

  // Handle mock mode
  if (dataMode === "mock" || !apiBaseUrl) {
    return {
      status: REFERENCE_READINESS_STATUS.READY,
      summary: { ok: 28, low_n: 20, not_cohort_ready: 1 },
      cells: [
        {
          language: "eng",
          age_band_12mo: "36-47",
          task_type: "toyplay",
          group: "ASD",
          cohort_n: 33,
          coverage_status: "ok",
          confidence_flag: "ok",
          clan_metric_ready: true
        },
        {
          language: "eng",
          age_band_12mo: "24-35",
          task_type: "toyplay",
          group: "ASD",
          cohort_n: 10,
          coverage_status: "low_n",
          confidence_flag: "low_n",
          clan_metric_ready: true
        },
        {
          language: "eng",
          age_band_12mo: "UNASSIGNED",
          task_type: "narrative",
          group: "TD",
          cohort_n: 0,
          coverage_status: "not_cohort_ready",
          confidence_flag: "",
          clan_metric_ready: true
        }
      ],
      generated_at: new Date().toISOString(),
      source_files: [
        "data/reference/english_child_reference_coverage.csv",
        "data/reference/english_child_reference_cohorts.csv",
        "data/manifests/english_child_clan_qc_summary.csv"
      ]
    };
  }

  try {
    const response = await resolveFetch(fetchImpl)(
      endpoint(apiBaseUrl, "/api/reference/readiness"),
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
        status: REFERENCE_READINESS_STATUS.ERROR,
        summary: { ok: 0, low_n: 0, not_cohort_ready: 0 },
        cells: [],
        error_detail: payload?.detail || "Reference Readiness request failed.",
        loaded_at: new Date().toISOString()
      };
    }

    return {
      status: REFERENCE_READINESS_STATUS.READY,
      summary: payload.summary || { ok: 0, low_n: 0, not_cohort_ready: 0 },
      cells: payload.cells || [],
      generated_at: payload.generated_at,
      source_files: payload.source_files,
      loaded_at: new Date().toISOString()
    };
  } catch (error) {
    return {
      status: REFERENCE_READINESS_STATUS.ERROR,
      summary: { ok: 0, low_n: 0, not_cohort_ready: 0 },
      cells: [],
      error_detail: error.message || "Reference Readiness request failed.",
      loaded_at: new Date().toISOString()
    };
  }
}
