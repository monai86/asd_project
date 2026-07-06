"use client";

import { saveSupabaseAccessSession } from "@/lib/supabase-access-session";
import { saveSupabaseBrowserAuthSnapshot } from "@/lib/supabase-browser-auth";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { saveSupabaseSessionToken } from "@/lib/supabase-session-token";

export async function signOutSupabaseWorkspace(): Promise<void> {
  saveSupabaseSessionToken(null);
  saveSupabaseBrowserAuthSnapshot(null);
  saveSupabaseAccessSession({ stage: "signed_out" });
  await getSupabaseBrowserClient()?.auth.signOut?.().catch(() => undefined);
}
