"use client";

import { MockLoginFormClient } from "@/components/mock-login-form-client";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseLoginFormClient } from "@/components/supabase-login-form-client";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function RuntimeLoginPanelClient() {
  const runtimeSettings = useRuntimeSettings();

  if (runtimeSettings === undefined) {
    return (
      <section className="workspace-panel self-start p-5 sm:p-6" aria-live="polite">
        <h2 className="font-semibold text-[color:var(--color-text-strong)]">Loading runtime settings</h2>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">Confirming the authentication mode.</p>
      </section>
    );
  }

  if (runtimeSettings === null) {
    return (
      <section className="workspace-panel self-start p-5 sm:p-6" role="alert">
        <h2 className="font-semibold text-[color:var(--color-text-strong)]">Runtime settings unavailable</h2>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          Login is blocked until the application can confirm its authentication and access requirements.
        </p>
      </section>
    );
  }

  if (runtimeSettings.auth_mode === "supabase") {
    return (
      <>
        <SupabaseAuthRuntimeBridge />
        <SupabaseLoginFormClient runtimeSettings={runtimeSettings} />
      </>
    );
  }

  return (
    <>
      <SupabaseAuthRuntimeBridge />
      <MockLoginFormClient runtimeSettings={runtimeSettings} />
    </>
  );
}
