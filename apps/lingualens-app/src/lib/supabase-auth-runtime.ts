"use client";

import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";

let runtimeSyncStarted = false;

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
    publishSupabaseSessionPayload(data.session ?? null);
  });

  client.auth.onAuthStateChange((_event, session) => {
    publishSupabaseSessionPayload(session ?? null);
  });
}

export function resetSupabaseAuthRuntimeSyncForTests(): void {
  runtimeSyncStarted = false;
}
