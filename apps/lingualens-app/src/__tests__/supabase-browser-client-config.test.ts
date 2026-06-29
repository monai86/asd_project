import { describe, expect, it, vi } from "vitest";

describe("supabase browser client config", () => {
  it("reports missing env when browser client config is not provided", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    const { getSupabaseBrowserClientConfigStatus } = await import("@/lib/supabase-browser-client-config");
    expect(getSupabaseBrowserClientConfigStatus()).toEqual({
      configured: false,
      missingUrl: true,
      missingAnonKey: true,
      invalidUrl: false,
      invalidAnonKey: false,
      config: null,
    });
  });

  it("returns config when NEXT_PUBLIC Supabase env vars are present", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project-ref.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "sb_publishable_test-key");

    const { getSupabaseBrowserClientConfigStatus } = await import("@/lib/supabase-browser-client-config");
    expect(getSupabaseBrowserClientConfigStatus()).toEqual({
      configured: true,
      missingUrl: false,
      missingAnonKey: false,
      invalidUrl: false,
      invalidAnonKey: false,
      config: {
        url: "https://project-ref.supabase.co",
        anonKey: "sb_publishable_test-key",
      },
    });
  });

  it("fails closed when the browser Supabase env is malformed", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://project-ref.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "not-a-real-key");

    const { getSupabaseBrowserClientConfigStatus } = await import("@/lib/supabase-browser-client-config");
    expect(getSupabaseBrowserClientConfigStatus()).toEqual({
      configured: false,
      missingUrl: false,
      missingAnonKey: false,
      invalidUrl: true,
      invalidAnonKey: true,
      config: null,
    });
  });
});
