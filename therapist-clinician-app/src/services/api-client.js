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
  const resolvedFetch = resolveFetch(fetchImpl);

  async function request(path, { method = "GET", body, headers = {} } = {}) {
    if (!baseUrl) {
      throw new ApiClientConfigurationError("Backend API base URL is not configured.");
    }

    const token = typeof getToken === "function" ? await getToken() : null;
    const response = await resolvedFetch(joinUrl(baseUrl, path), {
      method,
      headers: {
        "Content-Type": "application/json",
        ...defaultHeaders,
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
