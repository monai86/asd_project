import { store } from "../store/state.js";
import { PROCESSING_API_BASE_URL } from "../constants.js";

export class ApiClientConfigurationError extends Error {
  constructor(message) {
    super(message);
    this.name = "ApiClientConfigurationError";
  }
}

export class ApiClientRequestError extends Error {
  constructor(message, { status, payload } = {}) {
    super(message);
    this.name = "ApiClientRequestError";
    this.status = status;
    this.payload = payload;
  }
}

function joinUrl(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}/${String(path).replace(/^\//, "")}`;
}

function resolveFetch(fetchImpl) {
  if (fetchImpl) return fetchImpl;
  if (typeof fetch !== "undefined") return fetch;
  throw new ApiClientConfigurationError("Fetch is unavailable in this runtime.");
}

export function createApiClient({
  baseUrl = "",
  getToken = null,
  fetchImpl = null,
  defaultHeaders = {}
} = {}) {
  async function request(path, { method = "GET", body, headers = {} } = {}) {
    if (!baseUrl) {
      throw new ApiClientConfigurationError("Backend API base URL is not configured.");
    }

    const resolvedFetch = resolveFetch(fetchImpl);
    const token = typeof getToken === "function" ? await getToken() : null;
    const state = store ? store.getState() : null;
    const userId = state?.currentUser?.user_id;

    const response = await resolvedFetch(joinUrl(baseUrl, path), {
      method,
      headers: {
        "Content-Type": "application/json",
        ...defaultHeaders,
        ...(userId ? { "X-User-Id": userId } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers
      },
      body: body === undefined ? undefined : JSON.stringify(body)
    });

    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw new ApiClientRequestError(`API request failed with status ${response.status}.`, {
        status: response.status,
        payload
      });
    }

    return payload;
  }

  return {
    request,
    async text(path, options = {}) {
      if (!baseUrl) {
        throw new ApiClientConfigurationError("Backend API base URL is not configured.");
      }

      const resolvedFetch = resolveFetch(fetchImpl);
      const token = typeof getToken === "function" ? await getToken() : null;
      const state = store ? store.getState() : null;
      const userId = state?.currentUser?.user_id;

      const response = await resolvedFetch(joinUrl(baseUrl, path), {
        method: options.method || "GET",
        headers: {
          ...defaultHeaders,
          ...(userId ? { "X-User-Id": userId } : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(options.headers || {})
        }
      });
      const body = await response.text();
      if (!response.ok) {
        let payload = null;
        try {
          payload = body ? JSON.parse(body) : null;
        } catch {
          payload = body ? { detail: body } : null;
        }
        throw new ApiClientRequestError(`API request failed with status ${response.status}.`, {
          status: response.status,
          payload
        });
      }
      return { body, headers: response.headers, status: response.status };
    },
    get(path, options = {}) {
      return request(path, { ...options, method: "GET" });
    },
    post(path, body, options = {}) {
      return request(path, { ...options, method: "POST", body });
    },
    patch(path, body, options = {}) {
      return request(path, { ...options, method: "PATCH", body });
    },
    put(path, body, options = {}) {
      return request(path, { ...options, method: "PUT", body });
    }
  };
}

export const api = createApiClient({
  baseUrl: PROCESSING_API_BASE_URL || "http://localhost:8000"
});
