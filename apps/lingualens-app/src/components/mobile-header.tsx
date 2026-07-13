import Link from "next/link";
import { LogOut, Menu, SquareActivity } from "lucide-react";
import { ActiveOrganizationSummary } from "@/components/active-organization-summary";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";

export function MobileHeader({ title = "lingualens" }: { title?: string }) {
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const showLogout = (runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase")
    || Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out");

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  return (
    <header className="grid gap-3 pb-5 lg:hidden">
      <div className="flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-[1.1rem] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)] shadow-soft">
            <SquareActivity size={21} aria-hidden="true" />
          </span>
          <div>
            <p className="text-base font-semibold tracking-[-0.02em] text-[color:var(--color-text-strong)]">{title}</p>
            <p className="text-xs text-[color:var(--color-text-muted)]">Therapist Workspace</p>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          {showLogout ? (
            <button
              type="button"
              onClick={() => void handleLogout()}
              className="inline-flex min-h-11 items-center gap-2 rounded-full border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-3 text-sm font-semibold text-[color:var(--color-text-strong)] shadow-soft"
            >
              <LogOut size={16} aria-hidden="true" />
              Log out
            </button>
          ) : null}
          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-full border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)] shadow-soft"
            aria-label="Open navigation"
          >
            <Menu size={18} aria-hidden="true" />
          </button>
        </div>
      </div>
      <ActiveOrganizationSummary />
    </header>
  );
}
