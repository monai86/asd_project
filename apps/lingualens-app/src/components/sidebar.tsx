"use client";

import Link from "next/link";
import { Plus, LogOut } from "lucide-react";

import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { getWorkbenchNavigation } from "@/services/navigation/workbench-navigation";

export type ShellActive = "Today" | "Cases" | "Session" | "Reports" | "Settings";

export function Sidebar({
  active,
  activeSessionId,
  activeCaseId,
  isOpen = false,
  onClose,
}: {
  active: ShellActive;
  activeSessionId?: string;
  activeCaseId?: string;
  isOpen?: boolean;
  onClose?: () => void;
}) {
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const showLogout =
    (runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase") ||
    Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out");

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  const navItems = getWorkbenchNavigation(activeSessionId, activeCaseId).map((item) => ({
    ...item,
    active: item.active === active,
  }));

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 flex w-[264px] flex-col border-r border-[color:var(--color-border)] bg-[color:var(--color-page-bg)] transition-transform duration-200 lg:static lg:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {/* Brand */}
      <div className="px-5 pb-2 pt-5">
        <p className="text-[15px] font-semibold tracking-tight text-[color:var(--color-text-strong)]">LinguaLens</p>
      </div>

      {/* New Session Action */}
      <div className="p-3">
        <Link
          href="/cases?intent=start-session"
          onClick={onClose}
          className="flex w-full items-center gap-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-3.5 py-2.5 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-accent-subtle)] hover:bg-[color:var(--color-accent-soft)]"
        >
          <Plus className="h-4 w-4 text-[color:var(--color-accent-strong)]" />
          New Session
        </Link>
      </div>

      {/* Navigation Sections */}
      <nav aria-label="Primary navigation" className="flex-1 space-y-1 overflow-y-auto px-3 py-2 text-sm">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              aria-current={item.active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 transition ${
                item.active
                  ? "bg-[color:var(--color-accent-soft)] font-semibold text-[color:var(--color-accent-strong)]"
                  : "text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface)] hover:text-[color:var(--color-text-strong)]"
              }`}
            >
              <Icon
                className={`h-4 w-4 ${
                  item.active ? "text-[color:var(--color-accent-strong)]" : "text-[color:var(--color-text-subtle)]"
                }`}
              />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User / Settings / Logout Footer */}
      <div className="space-y-1 border-t border-[color:var(--color-border)] p-3">
        {showLogout ? (
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-[color:var(--color-text-muted)] transition hover:bg-[color:var(--color-surface)] hover:text-[color:var(--color-text-strong)]"
          >
            <LogOut className="h-4 w-4 text-[color:var(--color-text-subtle)]" />
            <span>Log out</span>
          </button>
        ) : null}
      </div>

      <div className="hidden p-3 lg:block">
        <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-3 text-xs text-[color:var(--color-text-muted)]">
          <p className="font-semibold text-[color:var(--color-text-strong)]">Clinical Safety</p>
          <p className="mt-1 text-[11px] leading-relaxed text-[color:var(--color-text-subtle)]">
            Decision-support research prototype. Therapist review required.
          </p>
        </div>
      </div>
    </aside>
  );
}
