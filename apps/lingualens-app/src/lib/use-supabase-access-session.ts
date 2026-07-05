"use client";

import { useEffect, useState } from "react";

import { loadPersistedSupabaseSessionFromStorage } from "@/lib/supabase-auth-runtime";
import {
  loadSupabaseAccessSession,
  SUPABASE_ACCESS_SESSION_EVENT,
  type SupabaseAccessSession,
} from "@/lib/supabase-access-session";
import {
  loadSupabaseBrowserAuthSnapshot,
  syncSupabaseAccessSessionFromBrowserAuth,
  syncSupabaseAccessSessionFromSession,
} from "@/lib/supabase-browser-auth";

export function loadOrRestoreSupabaseAccessSession(): SupabaseAccessSession | null {
  const existingSession = loadSupabaseAccessSession();
  if (existingSession?.stage && existingSession.stage !== "signed_out") return existingSession;
  if (loadSupabaseBrowserAuthSnapshot()) return syncSupabaseAccessSessionFromBrowserAuth();
  const persistedSession = loadPersistedSupabaseSessionFromStorage();
  if (persistedSession) return syncSupabaseAccessSessionFromSession(persistedSession);
  return existingSession;
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
