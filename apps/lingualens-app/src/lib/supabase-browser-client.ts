"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { getSupabaseBrowserClientConfig } from "@/lib/supabase-browser-client-config";

let browserClient: SupabaseClient | null | undefined;

export function getSupabaseBrowserClient(): SupabaseClient | null {
  if (browserClient !== undefined) {
    return browserClient;
  }

  const config = getSupabaseBrowserClientConfig();
  browserClient = config
    ? createClient(config.url, config.anonKey, {
        auth: {
          autoRefreshToken: true,
          detectSessionInUrl: true,
          persistSession: true,
        },
      })
    : null;

  return browserClient;
}

export function resetSupabaseBrowserClientForTests(): void {
  browserClient = undefined;
}
