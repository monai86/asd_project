import {
  AUTH_API_BASE_URL,
  DATA_MODE,
  PROCESSING_API_BASE_URL
} from "../constants.js";

function resolveFetch(fetchImpl) {
  if (fetchImpl) return fetchImpl;
  if (typeof fetch !== "undefined") return fetch;
  throw new Error("Fetch is unavailable in this runtime.");
}

function endpoint(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

export async function loadReferenceSimilarity({
  sessionId,
  currentUser,
  apiBaseUrl = AUTH_API_BASE_URL || PROCESSING_API_BASE_URL,
  dataMode = DATA_MODE,
  fetchImpl = null
} = {}) {
  if (!currentUser?.user_id) {
    return {
      status: "error",
      results: [],
      error_detail: "Sign in is required to load reference similarity."
    };
  }

  // Handle mock mode
  if (dataMode === "mock" || !apiBaseUrl) {
    return {
      status: "ok",
      results: [
        {
          transcript_uid: "Eigsti:1017",
          corpus: "Eigsti",
          group: "ASD",
          distance: 0.08,
          features: { mlu: 2.28, ttr: 0.58, total_words: 483 }
        },
        {
          transcript_uid: "Nadig:104",
          corpus: "Nadig",
          group: "ASD",
          distance: 0.14,
          features: { mlu: 2.12, ttr: 0.52, total_words: 395 }
        }
      ]
    };
  }

  try {
    const response = await resolveFetch(fetchImpl)(
      endpoint(apiBaseUrl, `/api/sessions/${sessionId}/reference-similarity`),
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
        status: "error",
        results: [],
        error_detail: payload?.detail || `API request failed with status: ${response.status}`
      };
    }
    return payload;
  } catch (error) {
    return {
      status: "error",
      results: [],
      error_detail: error.message || "Failed to load reference similarity."
    };
  }
}
