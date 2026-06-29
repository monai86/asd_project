"use client";

import { useEffect } from "react";

import { ensureSupabaseAuthRuntimeSync } from "@/lib/supabase-auth-runtime";
import {
  saveSupabaseBrowserAuthSnapshot,
  SUPABASE_BROWSER_AUTH_EVENT,
  syncSupabaseAccessSessionFromBrowserAuth,
  syncSupabaseAccessSessionFromSession,
} from "@/lib/supabase-browser-auth";
import { SUPABASE_SESSION_SOURCE_EVENT } from "@/lib/supabase-session-source";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function SupabaseAuthRuntimeBridge() {
  const runtimeSettings = useRuntimeSettings();

  useEffect(() => {
    if (runtimeSettings?.auth_mode !== "supabase") return;

    ensureSupabaseAuthRuntimeSync();

    const sync = () => {
      syncSupabaseAccessSessionFromBrowserAuth();
    };
    const syncFromSource = (event: Event) => {
      const customEvent = event as CustomEvent<{
        kind: "session" | "snapshot";
        session?: unknown;
        snapshot?: Parameters<typeof saveSupabaseBrowserAuthSnapshot>[0];
      }>;

      if (customEvent.detail?.kind === "snapshot") {
        saveSupabaseBrowserAuthSnapshot(customEvent.detail.snapshot ?? null);
        syncSupabaseAccessSessionFromBrowserAuth();
        return;
      }

      syncSupabaseAccessSessionFromSession(customEvent.detail?.session ?? null);
    };

    sync();
    window.addEventListener(SUPABASE_BROWSER_AUTH_EVENT, sync);
    window.addEventListener(SUPABASE_SESSION_SOURCE_EVENT, syncFromSource as EventListener);
    window.addEventListener("storage", sync);

    return () => {
      window.removeEventListener(SUPABASE_BROWSER_AUTH_EVENT, sync);
      window.removeEventListener(SUPABASE_SESSION_SOURCE_EVENT, syncFromSource as EventListener);
      window.removeEventListener("storage", sync);
    };
  }, [runtimeSettings?.auth_mode]);

  return null;
}
