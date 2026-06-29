"use client";

import { useEffect, useState } from "react";

import {
  loadSupabaseAccessSession,
  SUPABASE_ACCESS_SESSION_EVENT,
  type SupabaseAccessSession,
} from "@/lib/supabase-access-session";
import {
  loadSupabaseBrowserAuthSnapshot,
  syncSupabaseAccessSessionFromBrowserAuth,
} from "@/lib/supabase-browser-auth";

function loadOrRestoreSupabaseAccessSession(): SupabaseAccessSession | null {
  const existingSession = loadSupabaseAccessSession();
  if (existingSession) return existingSession;
  if (!loadSupabaseBrowserAuthSnapshot()) return null;
  return syncSupabaseAccessSessionFromBrowserAuth();
}

export function useSupabaseAccessSession() {
  const [session, setSession] = useState<SupabaseAccessSession | null>(() => {
    if (typeof window === "undefined") return null;
    return loadOrRestoreSupabaseAccessSession();
  });

  useEffect(() => {
    const syncSession = () => setSession(loadOrRestoreSupabaseAccessSession());
    syncSession();
    window.addEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
    return () => window.removeEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
  }, []);

  return session;
}
