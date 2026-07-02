"use client";

import Image from "next/image";

import { BottomNav } from "@/components/bottom-nav";
import { MobileHeader } from "@/components/mobile-header";
import { RightRail } from "@/components/right-rail";
import { Sidebar, type ShellActive } from "@/components/sidebar";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseWorkspaceAccessGate } from "@/components/supabase-workspace-access-gate";
import { Topbar } from "@/components/topbar";
import { WorkspaceAccessGate } from "@/components/workspace-access-gate";
import { loadMockAccessSession } from "@/lib/mock-access-session";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function AppShell({
  children,
  active = "Home",
  rightRail
}: {
  children: React.ReactNode;
  active?: ShellActive;
  rightRail?: React.ReactNode;
}) {
  const runtimeSettings = useRuntimeSettings();
  const session = typeof window !== "undefined" ? loadMockAccessSession() : null;
  const supabaseSession = useSupabaseAccessSession();
  const gateRequired = session?.aal === "aal1";
  const supabaseGateRequired = runtimeSettings?.auth_mode === "supabase"
    && !(supabaseSession?.stage === "authenticated" && supabaseSession.organizationId && supabaseSession.aal === "aal2");

  if (supabaseGateRequired) {
    return (
      <>
        <SupabaseAuthRuntimeBridge />
        <SupabaseWorkspaceAccessGate>{children}</SupabaseWorkspaceAccessGate>
      </>
    );
  }

  if (gateRequired) {
    return (
      <>
        <SupabaseAuthRuntimeBridge />
        <WorkspaceAccessGate>{children}</WorkspaceAccessGate>
      </>
    );
  }

  return (
    <>
      <SupabaseAuthRuntimeBridge />
      <div className="min-h-dvh bg-[color:var(--color-page-bg)] text-[color:var(--color-text-strong)]">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[color:var(--color-surface-strong)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold"
        >
          Skip to main content
        </a>

        <div className="mx-auto flex max-w-[1600px]">
          <Sidebar active={active} />

          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar />
            <main
              id="main-content"
              className="mx-auto w-full max-w-[1280px] flex-1 px-4 pb-[calc(7rem+env(safe-area-inset-bottom))] pt-6 sm:px-6 lg:px-10 lg:pb-12 lg:pt-10"
            >
              <MobileHeader />
              <div className="flex items-start gap-6">
                <div className="min-w-0 flex-1">{children}</div>
                {rightRail ? (
                  <RightRail>
                    {rightRail}
                  </RightRail>
                ) : null}
              </div>
            </main>
          </div>
        </div>

        <BottomNav active={active} />
      </div>
    </>
  );
}

export function WorkflowVisual() {
  return (
    <div className="signature-band overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] shadow-soft">
      <Image src="/clinical-workflow.svg" width={960} height={320} alt="Case to transcript review to signed report workflow" priority />
    </div>
  );
}
