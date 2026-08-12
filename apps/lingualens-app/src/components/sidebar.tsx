"use client";

import Link from "next/link";
import { Plus, Sparkles, Home, Users, FileText, Settings, LogOut } from "lucide-react";

import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

export type ShellActive = "Today" | "Cases" | "Session" | "Reports" | "Settings";

export function Sidebar({
  active,
  activeSessionId,
  isOpen = false,
  onClose,
}: {
  active: ShellActive;
  activeSessionId?: string;
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

  const navItems = [
    {
      label: "Today Queue",
      href: "/today",
      icon: Home,
      active: active === "Today",
    },
    {
      label: "Child Cases",
      href: "/cases",
      icon: Users,
      active: active === "Cases",
    },
    {
      label: "Clinical Reports",
      href: "/reports",
      icon: FileText,
      active: active === "Reports",
    },
  ];

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-[#f8fafc] border-r border-slate-200 shadow-sm transition-transform duration-200 lg:static lg:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {/* New Session Action */}
      <div className="p-3">
        <Link
          href="/cases?intent=start-session"
          onClick={onClose}
          className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-slate-800 shadow-sm hover:border-[#10a37f] hover:bg-slate-50 transition"
        >
          <span className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-[#10a37f]" />
            New Session
          </span>
          <Sparkles className="h-3.5 w-3.5 text-[#10a37f]" />
        </Link>
      </div>

      {/* Navigation Sections */}
      <nav aria-label="Primary navigation" className="flex-1 space-y-1 px-3 py-2 overflow-y-auto text-sm">
        <div className="pb-2 px-2 text-[11px] font-bold tracking-wider text-slate-400 uppercase">
          LinguaLens Workspace
        </div>

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
                  ? "bg-slate-200/70 text-slate-900 font-bold shadow-xs"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon className={`h-4 w-4 ${item.active ? "text-[#10a37f]" : "text-slate-500"}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User / Settings / Logout Footer */}
      <div className="border-t border-slate-200 p-3 space-y-1 bg-[#f8fafc]">
        <Link
          href="/settings"
          onClick={onClose}
          aria-current={active === "Settings" ? "page" : undefined}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
            active === "Settings"
              ? "bg-slate-200/70 text-slate-900 font-bold"
              : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          }`}
        >
          <Settings className="h-4 w-4 text-slate-500" />
          <span>Settings</span>
        </Link>

        {showLogout ? (
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition"
          >
            <LogOut className="h-4 w-4 text-slate-500" />
            <span>Log out</span>
          </button>
        ) : null}
      </div>

      <div className="hidden p-3 lg:block">
        <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-600 shadow-xs">
          <p className="font-bold text-slate-800">Clinical Safety</p>
          <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
            Decision-support research prototype. Therapist review required.
          </p>
        </div>
      </div>
    </aside>
  );
}
