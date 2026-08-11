import { loadMockAccessSession } from "@/lib/mock-access-session";
import { loadPersistedSupabaseSessionFromStorage } from "@/lib/supabase-auth-runtime";
import { loadSupabaseBrowserAuthSnapshot } from "@/lib/supabase-browser-auth";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { getSupabaseBrowserClientConfigStatus } from "@/lib/supabase-browser-client-config";
import { loadSupabaseAccessSession } from "@/lib/supabase-access-session";
import { loadSupabaseSessionToken, saveSupabaseSessionToken } from "@/lib/supabase-session-token";
import {
  runtimeSettingsSchema,
  type RuntimeSettings,
} from "@/services/api/runtime-settings-schema";

export type { RuntimeSettings } from "@/services/api/runtime-settings-schema";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000/api/v1";
const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_DEMO_USER_ID ?? "therapist-demo";
let runtimeSettingsCache: RuntimeSettings | null = null;

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
  await applyRuntimeAuthHeaders(headers);
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

export async function apiGet<T>(path: string, init: RequestInit = {}): Promise<T> {
  return apiRequest<T>(path, init);
}

export async function getRuntimeSettings(): Promise<RuntimeSettings> {
  const settings = runtimeSettingsSchema.parse(await apiGet("/settings"));
  runtimeSettingsCache = settings;
  return settings;
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
  await applyRuntimeAuthHeaders(headers);
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

export async function apiBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  const headers = new Headers(init.headers);
  await applyRuntimeAuthHeaders(headers);
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
    headers,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response.blob();
}

export async function apiUploadBlob(
  pathOrUrl: string,
  blob: Blob,
  requiredHeaders: Record<string, string> = {},
): Promise<void> {
  const isAbsoluteUrl = /^https?:\/\//i.test(pathOrUrl);
  const isSupabaseSignedUpload = isAbsoluteUrl && /\/storage\/v1\/object\/upload\/sign\//.test(pathOrUrl);
  const headers = new Headers(requiredHeaders);
  let body: BodyInit = blob;

  if (isSupabaseSignedUpload) {
    const formData = new FormData();
    formData.append("file", blob, filenameFromUploadUrl(pathOrUrl));
    body = formData;
    headers.delete("content-type");
  } else {
    if (!headers.has("content-type")) headers.set("content-type", blob.type);
  }

  if (!isAbsoluteUrl) {
    await applyRuntimeAuthHeaders(headers);
  }

  const response = await fetch(isAbsoluteUrl ? pathOrUrl : `${API_BASE}${pathOrUrl}`, {
    method: "PUT",
    body,
    headers,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
}

function filenameFromUploadUrl(url: string): string {
  try {
    const pathname = new URL(url).pathname;
    const filename = pathname.split("/").filter(Boolean).at(-1);
    return filename || "upload";
  } catch {
    return "upload";
  }
}

export function getMockAccessHeaders(overrides: Record<string, string> = {}): Record<string, string> {
  if (isSupabaseRuntimeContext()) {
    return { ...overrides };
  }

  const session = loadMockAccessSession();
  return {
    "X-Mock-Role": session?.role ?? "org_admin",
    "X-Mock-Display-Name": "Pilot Org Admin",
    "X-Organization-Id": session?.organizationId ?? "pilot_org_001",
    ...overrides,
  };
}

async function applyRuntimeAuthHeaders(headers: Headers): Promise<void> {
  if (isSupabaseRuntimeContext()) {
    headers.delete("X-User-Id");
    headers.delete("X-Mock-Role");
    headers.delete("X-Mock-Display-Name");

    const browserClient = getSupabaseBrowserClient();
    const currentAccessSession = loadSupabaseAccessSession();
    const cachedAccessToken = loadSupabaseSessionToken();
    const { data } = browserClient
      ? await browserClient.auth.getSession()
      : { data: { session: null } };
    const persistedSession = !data.session?.access_token
      ? loadPersistedSupabaseSessionFromStorage()
      : null;
    const accessToken = data.session?.access_token?.trim()
      ?? persistedSession?.access_token?.trim()
      ?? cachedAccessToken;

    saveSupabaseSessionToken(accessToken ?? null);

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    } else {
      headers.delete("Authorization");
    }

    if (currentAccessSession?.organizationId) {
      headers.set("X-Organization-Id", currentAccessSession.organizationId);
    } else {
      headers.delete("X-Organization-Id");
    }

    return;
  }

  headers.delete("Authorization");
  headers.set("X-User-Id", DEFAULT_USER_ID);
}

function isSupabaseRuntimeContext(): boolean {
  if (runtimeSettingsCache?.auth_mode === "supabase") {
    return true;
  }

  if (runtimeSettingsCache?.auth_mode === "mock") {
    return false;
  }

  if (loadSupabaseBrowserAuthSnapshot() || loadSupabaseAccessSession()) {
    return true;
  }

  return getSupabaseBrowserClientConfigStatus().configured;
}

export function resetApiRuntimeSettingsCacheForTests(): void {
  runtimeSettingsCache = null;
}

export { API_BASE, DEFAULT_USER_ID };
