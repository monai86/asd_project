import { loadMockAccessSession } from "@/lib/mock-access-session";
import { loadPersistedSupabaseSessionFromStorage } from "@/lib/supabase-auth-runtime";
import { loadSupabaseBrowserAuthSnapshot } from "@/lib/supabase-browser-auth";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { getSupabaseBrowserClientConfigStatus } from "@/lib/supabase-browser-client-config";
import { loadSupabaseAccessSession } from "@/lib/supabase-access-session";
import { loadSupabaseSessionToken, saveSupabaseSessionToken } from "@/lib/supabase-session-token";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000/api/v1";
const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_DEMO_USER_ID ?? "user_therapist_001";
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

export type RuntimeSettings = {
  mock_mode: boolean;
  auth_mode: string;
  model_version: string;
  feature_schema: string;
  guideline_mapping: string;
  user_roles: string[];
  access_model?: {
    invitation_only: boolean;
    required_app_aal: "aal1" | "aal2";
    active_organization_session: string;
    production_mock_mode: string;
  };
  data_retention: string;
  consent_policy: string;
  pipeline_settings: {
    audio_processing: string;
    job_queue_mode: string;
    repository_mode: string;
    storage_mode: string;
    ai_review_policy?: string;
    ai_report_drafting_enabled?: boolean;
  };
};

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

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export async function getRuntimeSettings(): Promise<RuntimeSettings> {
  const settings = await apiGet<RuntimeSettings>("/settings");
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

export async function apiUploadBlob(pathOrUrl: string, blob: Blob): Promise<void> {
  const isAbsoluteUrl = /^https?:\/\//i.test(pathOrUrl);
  const headers = new Headers({
    "content-type": blob.type,
  });

  if (!isAbsoluteUrl) {
    await applyRuntimeAuthHeaders(headers);
  }

  const response = await fetch(isAbsoluteUrl ? pathOrUrl : `${API_BASE}${pathOrUrl}`, {
    method: "PUT",
    body: blob,
    headers,
  });
  if (!response.ok) {
    throw new Error(`Failed to upload audio file: ${response.statusText}`);
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
