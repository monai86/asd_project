"use client";

import { useState, ReactNode } from "react";
import Image from "next/image";
import { Menu, X } from "lucide-react";

import { Sidebar, type ShellActive } from "@/components/sidebar";
import { RightRail } from "@/components/right-rail";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseWorkspaceAccessGate } from "@/components/supabase-workspace-access-gate";
import { WorkspaceAccessGate } from "@/components/workspace-access-gate";
import { ConfirmedRuntimeSettingsProvider } from "@/lib/confirmed-runtime-settings";
import { loadMockAccessSession } from "@/lib/mock-access-session";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export type { ShellActive };

export function AppShell({
  children,
  active = "Today",
  activeSessionId,
  rightRail,
}: {
  children: ReactNode;
  active?: ShellActive;
  activeSessionId?: string;
  rightRail?: ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const runtimeSettings = useRuntimeSettings();
  const confirmedRuntimeSettings = runtimeSettings.status === "success" ? runtimeSettings.data : null;
  const session = typeof window !== "undefined" ? loadMockAccessSession() : null;
  const supabaseSession = useSupabaseAccessSession();

  const gateRequired = confirmedRuntimeSettings?.auth_mode === "mock" && session?.aal === "aal1";
  const supabaseGateRequired =
    confirmedRuntimeSettings?.auth_mode === "supabase" &&
    !(
      supabaseSession?.stage === "authenticated" &&
      supabaseSession.organizationId &&
      supabaseSession.aal === "aal2"
    );

  if (runtimeSettings.status !== "success") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-xl text-slate-900" role="alert">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Runtime verification required
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">Workspace access is blocked</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Authentication mode and access requirements must be confirmed before workspace content can load.
          </p>
        </section>
      </main>
    );
  }

  if (supabaseGateRequired) {
    return (
      <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
        <SupabaseAuthRuntimeBridge />
        <SupabaseWorkspaceAccessGate>{children}</SupabaseWorkspaceAccessGate>
      </ConfirmedRuntimeSettingsProvider>
    );
  }

  if (gateRequired) {
    return (
      <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
        <SupabaseAuthRuntimeBridge />
        <WorkspaceAccessGate>{children}</WorkspaceAccessGate>
      </ConfirmedRuntimeSettingsProvider>
    );
  }

  return (
    <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
      <SupabaseAuthRuntimeBridge />
      <div className="flex h-screen w-full bg-[#f9fafb] text-slate-900 font-sans overflow-hidden">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-slate-900 focus:shadow-md"
        >
          Skip to main content
        </a>

        {/* Mobile Backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <Sidebar
          active={active}
          activeSessionId={activeSessionId}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
          {/* Mobile Header Top Bar */}
          <header className="flex h-12 items-center justify-between border-b border-slate-200 bg-white px-4 lg:hidden">
            <button
              type="button"
              aria-label="Toggle navigation"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100 transition"
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <span className="text-sm font-bold text-slate-800 tracking-tight">LinguaLens</span>
            <div className="w-5" />
          </header>

          <main id="main-content" className="flex-1 overflow-y-auto p-4 md:p-6 min-w-0 bg-[#ffffff]">
            <div className="flex items-start gap-6">
              <div className="min-w-0 flex-1">{children}</div>
              {rightRail ? <RightRail>{rightRail}</RightRail> : null}
            </div>
          </main>
        </div>
      </div>
    </ConfirmedRuntimeSettingsProvider>
  );
}

export function WorkflowVisual() {
  return (
    <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm">
      <Image src="/clinical-workflow.svg" width={960} height={320} alt="Case to transcript review to signed report workflow" priority />
    </div>
  );
}
