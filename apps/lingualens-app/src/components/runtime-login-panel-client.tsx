"use client";

import { MockLoginFormClient } from "@/components/mock-login-form-client";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseLoginFormClient } from "@/components/supabase-login-form-client";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function RuntimeLoginPanelClient() {
  const runtimeSettings = useRuntimeSettings();

  if (runtimeSettings?.auth_mode === "supabase") {
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
