"use client";

export const SUPABASE_SESSION_TOKEN_KEY = "lingualens.supabase-session-token.v1";

export function loadSupabaseSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  const value = window.sessionStorage.getItem(SUPABASE_SESSION_TOKEN_KEY)?.trim();
  return value ? value : null;
}

export function saveSupabaseSessionToken(token: string | null | undefined): void {
  if (typeof window === "undefined") return;
  const normalized = typeof token === "string" ? token.trim() : "";
  if (normalized) {
    window.sessionStorage.setItem(SUPABASE_SESSION_TOKEN_KEY, normalized);
    return;
  }
  window.sessionStorage.removeItem(SUPABASE_SESSION_TOKEN_KEY);
}
