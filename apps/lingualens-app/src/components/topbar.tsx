import { ActiveOrganizationSummary } from "@/components/active-organization-summary";
import { Bell, Search } from "lucide-react";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function Topbar() {
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const clinicianLabel = runtimeSettings?.auth_mode === "supabase"
    ? supabaseSession?.displayName ?? supabaseSession?.email ?? "Workspace user"
    : "Demo Therapist";
  const workspaceLabel = runtimeSettings?.auth_mode === "supabase"
    ? "Supabase-authenticated workspace"
    : "Local clinician workspace";

  return (
    <header className="sticky top-0 z-20 hidden border-b border-[color:var(--color-border)] bg-[color:rgba(255,255,255,0.92)] px-8 py-4 backdrop-blur-xl lg:flex lg:items-center lg:justify-between">
      <label className="flex min-h-11 w-full max-w-[32rem] items-center gap-3 rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 shadow-soft">
        <Search size={18} aria-hidden="true" className="text-[color:var(--color-text-subtle)]" />
        <span className="sr-only">Search workspace</span>
        <input
          className="w-full bg-transparent text-sm text-[color:var(--color-text-strong)] outline-none placeholder:text-[color:var(--color-text-subtle)]"
          placeholder="Search cases, sessions, transcripts, or reports"
        />
      </label>

      <div className="ml-6 flex items-center gap-3">
        <ActiveOrganizationSummary />
        <button
          type="button"
          className="grid h-11 w-11 place-items-center rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)] shadow-soft transition hover:border-[color:var(--color-text-strong)] motion-reduce:transition-none"
          aria-label="3 demo notifications"
        >
          <Bell size={18} aria-hidden="true" />
        </button>
        <div className="rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-2 text-sm shadow-soft">
          <p className="font-medium text-[color:var(--color-text-strong)]">{clinicianLabel}</p>
          <p className="text-xs text-[color:var(--color-text-muted)]">{workspaceLabel}</p>
        </div>
      </div>
    </header>
  );
}
