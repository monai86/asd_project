"use client";

import Link from "next/link";
import { LogOut, SquareActivity } from "lucide-react";

import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import {
  getWorkbenchNavigation,
  type ShellActive,
} from "@/services/navigation/workbench-navigation";

export type { ShellActive } from "@/services/navigation/workbench-navigation";

export function Sidebar({
  active,
  activeSessionId,
}: {
  active: ShellActive;
  activeSessionId?: string;
}) {
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const items = getWorkbenchNavigation(activeSessionId);
  const showLogout = (runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase")
    || Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out");

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  return (
    <aside className="sticky top-0 hidden h-dvh w-[5.5rem] shrink-0 border-r border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-5 md:flex md:flex-col md:items-center lg:w-[17rem] lg:px-5 lg:items-stretch">
      <Link href="/today" className="flex min-h-12 items-center gap-3 rounded-[var(--radius-panel)] px-2 py-1">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[var(--radius-card)] bg-[color:var(--color-accent)] text-white">
          <SquareActivity size={24} aria-hidden="true" />
        </span>
        <span className="hidden lg:block">
          <span className="block text-lg font-semibold text-[color:var(--color-text-strong)]">LinguaLens</span>
          <span className="block text-sm text-[color:var(--color-text-muted)]">Transcript workbench</span>
        </span>
      </Link>

      <nav className="mt-8 w-full space-y-1.5" aria-label="Primary navigation">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.active === active;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              title={item.label}
              className={`transcript-wave-ruler flex min-h-11 items-center gap-3 rounded-[var(--radius-card)] px-3 pl-4 lg:px-4 lg:pl-5 text-sm font-medium justify-center lg:justify-start transition duration-200 ease-out motion-reduce:transition-none ${
                isActive
                  ? "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
                  : "text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-strong)] hover:text-[color:var(--color-text-strong)]"
              }`}
            >
              <Icon size={18} aria-hidden="true" className="shrink-0" />
              <span className="hidden lg:inline">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {showLogout ? (
        <button
          type="button"
          onClick={() => void handleLogout()}
          title="Log out"
          className="mt-6 flex min-h-11 w-full items-center gap-3 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-3 lg:px-4 text-sm font-semibold text-[color:var(--color-text-strong)] justify-center lg:justify-start transition duration-200 ease-out hover:border-[color:var(--color-text-strong)] motion-reduce:transition-none"
        >
          <LogOut size={18} aria-hidden="true" className="shrink-0" />
          <span className="hidden lg:inline">Log out</span>
        </button>
      ) : null}

      <div className="mt-auto hidden w-full rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 lg:block">
        <p className="text-sm font-medium text-[color:var(--color-text-strong)]">Clinical safety boundary</p>
        <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
          Decision-support only. Therapist review and sign-off remain required.
        </p>
      </div>
    </aside>
  );
}
