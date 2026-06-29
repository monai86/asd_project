"use client";

import type { SupabaseBrowserAuthSnapshot } from "@/lib/supabase-browser-auth";

export const SUPABASE_SESSION_SOURCE_EVENT = "lingualens:supabase-session-source";

type SupabaseSessionSourcePayload = {
  kind: "session";
  session: unknown;
} | {
  kind: "snapshot";
  snapshot: SupabaseBrowserAuthSnapshot | null;
};

export function publishSupabaseSessionPayload(session: unknown): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<SupabaseSessionSourcePayload>(SUPABASE_SESSION_SOURCE_EVENT, {
    detail: {
      kind: "session",
      session,
    },
  }));
}

export function publishSupabaseBrowserAuthSnapshot(snapshot: SupabaseBrowserAuthSnapshot | null): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<SupabaseSessionSourcePayload>(SUPABASE_SESSION_SOURCE_EVENT, {
    detail: {
      kind: "snapshot",
      snapshot,
    },
  }));
}
