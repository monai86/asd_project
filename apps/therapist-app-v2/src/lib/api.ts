const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_DEMO_USER_ID ?? "user_therapist_001";

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(body || `API request failed: ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-User-Id", DEFAULT_USER_ID);
  if (init.body && !(init.body instanceof FormData) && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
    headers
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export async function checkBackendAvailability(): Promise<boolean> {
  try {
    await apiGet("/settings");
    return true;
  } catch {
    return false;
  }
}

export async function apiText(path: string, init: RequestInit = {}): Promise<string> {
  const headers = new Headers(init.headers);
  headers.set("X-User-Id", DEFAULT_USER_ID);
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
    headers
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response.text();
}

export { API_BASE, DEFAULT_USER_ID };
