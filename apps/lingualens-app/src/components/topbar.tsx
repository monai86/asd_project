import { ActiveOrganizationSummary } from "@/components/active-organization-summary";
import { Bell, LogOut, Search } from "lucide-react";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";

export function Topbar() {
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const isSupabaseRuntime = runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase";
  const clinicianLabel = isSupabaseRuntime
    ? supabaseSession?.displayName ?? supabaseSession?.email ?? "Workspace user"
    : "Demo Therapist";
  const workspaceLabel = isSupabaseRuntime
    ? `Supabase-authenticated workspace${supabaseSession?.role ? ` · ${supabaseSession.role}` : ""}`
    : "Local clinician workspace";
  const showLogout = isSupabaseRuntime || Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out");

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  return (
    <header className="sticky top-0 z-20 hidden min-w-0 border-b border-[color:var(--color-border)] bg-[color:rgba(255,255,255,0.92)] px-6 py-4 backdrop-blur-xl lg:flex lg:items-center lg:justify-between lg:gap-4">
      <label className="hidden min-h-11 min-w-0 flex-1 items-center gap-3 rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 shadow-soft xl:flex">
        <Search size={18} aria-hidden="true" className="text-[color:var(--color-text-subtle)]" />
        <span className="sr-only">Search workspace</span>
        <input
          className="w-full bg-transparent text-sm text-[color:var(--color-text-strong)] outline-none placeholder:text-[color:var(--color-text-subtle)]"
          placeholder="Search cases, sessions, transcripts, or reports"
        />
      </label>

      <div className="ml-auto flex min-w-0 items-center justify-end gap-3">
        <div className="hidden min-w-0 shrink overflow-hidden xl:block xl:max-w-[15rem] 2xl:max-w-[18rem]">
          <ActiveOrganizationSummary />
        </div>
        <button
          type="button"
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)] shadow-soft transition hover:border-[color:var(--color-text-strong)] motion-reduce:transition-none"
          aria-label="3 demo notifications"
        >
          <Bell size={18} aria-hidden="true" />
        </button>
        <div className="min-w-0 max-w-[18rem] rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-2 text-sm shadow-soft">
          <p className="truncate font-medium text-[color:var(--color-text-strong)]">{clinicianLabel}</p>
          <p className="truncate text-xs text-[color:var(--color-text-muted)]">{workspaceLabel}</p>
        </div>
        {showLogout ? (
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="hidden min-h-11 shrink-0 items-center gap-2 rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-2 text-sm font-semibold text-[color:var(--color-text-strong)] shadow-soft transition hover:border-[color:var(--color-text-strong)] motion-reduce:transition-none 2xl:inline-flex"
          >
            <LogOut size={16} aria-hidden="true" />
            Log out
          </button>
        ) : null}
      </div>
    </header>
  );
}
