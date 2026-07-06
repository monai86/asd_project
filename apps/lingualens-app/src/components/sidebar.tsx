"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { CalendarDays, FileText, FolderOpen, LayoutGrid, LogOut, Settings2, SquareActivity } from "lucide-react";

import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export type ShellActive = "Home" | "Sessions" | "Cases" | "Reports" | "More";

type NavItem = {
  href: string;
  label: string;
  active: ShellActive;
  icon: LucideIcon;
};

const items: NavItem[] = [
  { href: "/", label: "Home", active: "Home", icon: LayoutGrid },
  { href: "/today", label: "Today", active: "Sessions", icon: CalendarDays },
  { href: "/cases", label: "Cases", active: "Cases", icon: FolderOpen },
  { href: "/reports", label: "Reports", active: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", active: "More", icon: Settings2 }
];

export function Sidebar({ active }: { active: ShellActive }) {
  const runtimeSettings = useRuntimeSettings();
  const showLogout = runtimeSettings?.auth_mode === "supabase";

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  return (
    <aside className="sticky top-0 hidden h-dvh w-[17.5rem] shrink-0 border-r border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-5 py-6 lg:flex lg:flex-col">
      <Link href="/" className="flex items-center gap-3 rounded-[var(--radius-panel)] px-2 py-2">
        <span className="grid h-12 w-12 place-items-center rounded-[1rem] bg-[color:var(--color-accent)] text-white shadow-soft">
          <SquareActivity size={24} aria-hidden="true" />
        </span>
        <span>
          <span className="block text-lg font-normal tracking-[-0.03em] text-[color:var(--color-text-strong)]">lingualens</span>
          <span className="block text-sm text-[color:var(--color-text-muted)]">Therapist Workspace</span>
        </span>
      </Link>

      <nav className="mt-8 space-y-2" aria-label="Primary navigation">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.active === active;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-11 items-center gap-3 rounded-[var(--radius-pill)] px-4 text-sm font-medium transition duration-200 ease-out motion-reduce:transition-none ${
                isActive
                  ? "bg-[color:var(--color-accent)] text-white shadow-soft"
                  : "text-[color:var(--color-text-muted)] hover:bg-white hover:text-[color:var(--color-text-strong)]"
              }`}
            >
              <Icon size={18} aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {showLogout ? (
        <button
          type="button"
          onClick={() => void handleLogout()}
          className="mt-6 flex min-h-11 items-center gap-3 rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 text-sm font-semibold text-[color:var(--color-text-strong)] shadow-soft transition duration-200 ease-out hover:border-[color:var(--color-text-strong)] motion-reduce:transition-none"
        >
          <LogOut size={18} aria-hidden="true" />
          Log out
        </button>
      ) : null}

      <div className="mt-auto rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
        <p className="text-sm font-medium text-[color:var(--color-text-strong)]">Clinical safety boundary</p>
        <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
          Decision-support only. Therapist review and sign-off remain required.
        </p>
      </div>
    </aside>
  );
}
