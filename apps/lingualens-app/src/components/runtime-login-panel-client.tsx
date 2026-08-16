"use client";

import { MockLoginFormClient } from "@/components/mock-login-form-client";
import { SkeletonLine } from "@/components/skeleton";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseLoginFormClient } from "@/components/supabase-login-form-client";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function RuntimeLoginPanelClient() {
  const runtimeSettings = useRuntimeSettings();

  if (runtimeSettings.status === "loading") {
    return (
      <section className="workspace-panel self-start p-5 sm:p-6" aria-live="polite">
        <span className="sr-only">Loading runtime settings…</span>
        <SkeletonLine className="w-2/5" />
        <div className="mt-3 space-y-2" aria-hidden="true">
          <SkeletonLine className="w-3/5" />
          <SkeletonLine className="w-2/5" />
        </div>
      </section>
    );
  }

  if (runtimeSettings.status !== "success") {
    return (
      <section className="workspace-panel self-start p-5 sm:p-6" role="alert">
        <h2 className="font-semibold text-[color:var(--color-text-strong)]">Runtime settings unavailable</h2>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          Login is blocked until the application can confirm its authentication and access requirements.
        </p>
      </section>
    );
  }

  if (runtimeSettings.data.auth_mode === "supabase") {
    return (
      <>
        <SupabaseAuthRuntimeBridge />
        <SupabaseLoginFormClient runtimeSettings={runtimeSettings.data} />
      </>
    );
  }

  return (
    <>
      <SupabaseAuthRuntimeBridge />
      <MockLoginFormClient runtimeSettings={runtimeSettings.data} />
    </>
  );
}
