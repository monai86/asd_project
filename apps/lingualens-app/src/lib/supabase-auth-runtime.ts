"use client";

import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";

let runtimeSyncStarted = false;

type PersistedSupabaseSession = {
  access_token?: string | null;
  refresh_token?: string | null;
  aal?: string | null;
  user?: {
    id?: string | null;
    email?: string | null;
    app_metadata?: Record<string, unknown> | null;
    user_metadata?: Record<string, unknown> | null;
  } | null;
} | null;

export function ensureSupabaseAuthRuntimeSync(): void {
  if (runtimeSyncStarted || typeof window === "undefined") {
    return;
  }

  const client = getSupabaseBrowserClient();
  if (!client) {
    return;
  }

  runtimeSyncStarted = true;

  void client.auth.getSession().then(({ data }) => {
    publishSupabaseSessionPayload(data.session ?? loadPersistedSupabaseSessionFromStorage());
  });

  client.auth.onAuthStateChange((_event, session) => {
    publishSupabaseSessionPayload(session ?? null);
  });
}

export function resetSupabaseAuthRuntimeSyncForTests(): void {
  runtimeSyncStarted = false;
}

export function loadPersistedSupabaseSessionFromStorage(): PersistedSupabaseSession {
  if (typeof window === "undefined") {
    return null;
  }

  const storageKey = Object.keys(window.localStorage).find(
    (key) => key.startsWith("sb-") && key.includes("auth-token"),
  );
  if (!storageKey) {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as PersistedSupabaseSession;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    if (!parsed.access_token || !parsed.user?.id || !parsed.user?.email) {
      return null;
    }
    if (parsed.aal !== "aal1" && parsed.aal !== "aal2") {
      parsed.aal = decodeAalFromJwt(parsed.access_token);
    }
    return parsed;
  } catch {
    return null;
  }
}

function decodeAalFromJwt(token: string): "aal1" | "aal2" | null {
  try {
    const [, payloadSegment] = token.split(".");
    if (!payloadSegment) {
      return null;
    }
    const normalized = payloadSegment
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(payloadSegment.length / 4) * 4, "=");
    const payload = JSON.parse(window.atob(normalized)) as { aal?: unknown };
    return payload.aal === "aal1" || payload.aal === "aal2" ? payload.aal : null;
  } catch {
    return null;
  }
}
