"use client";

export type SupabaseBrowserClientConfig = {
  url: string;
  anonKey: string;
};

export function getSupabaseBrowserClientConfig(): SupabaseBrowserClientConfig | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();

  if (!isValidSupabaseProjectUrl(url) || !isValidSupabaseAnonKey(anonKey)) {
    return null;
  }

  return { url, anonKey };
}

export function getSupabaseBrowserClientConfigStatus() {
  const config = getSupabaseBrowserClientConfig();

  return {
    configured: Boolean(config),
    missingUrl: !process.env.NEXT_PUBLIC_SUPABASE_URL?.trim(),
    missingAnonKey: !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim(),
    invalidUrl: Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL?.trim())
      && !isValidSupabaseProjectUrl(process.env.NEXT_PUBLIC_SUPABASE_URL?.trim()),
    invalidAnonKey: Boolean(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim())
      && !isValidSupabaseAnonKey(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim()),
    config,
  };
}

function isValidSupabaseProjectUrl(value: string | undefined): value is string {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && /\.supabase\.co$/i.test(url.hostname);
  } catch {
    return false;
  }
}

function isValidSupabaseAnonKey(value: string | undefined): value is string {
  if (!value) return false;
  return value.startsWith("sb_publishable_") || value.startsWith("eyJ");
}
