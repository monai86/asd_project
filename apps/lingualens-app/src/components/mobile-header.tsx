import Image from "next/image";
import Link from "next/link";
import { LogOut, Menu } from "lucide-react";
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
    <header className="grid gap-2 pb-3 md:hidden">
      <div className="flex items-center justify-between gap-3">
        <Link href="/today" aria-label="LinguaLens home" className="flex items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-white">
            <Image src="/logo-mark.png" alt="" width={40} height={40} className="h-10 w-10 object-cover" />
          </span>
          <div>
            <p className="text-base font-semibold text-[color:var(--color-text-strong)]">{title === "lingualens" ? "LinguaLens" : title}</p>
            <p className="text-xs text-[color:var(--color-text-muted)]">Transcript workbench</p>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          {showLogout ? (
            <button
              type="button"
              onClick={() => void handleLogout()}
              className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-3 text-sm font-semibold text-[color:var(--color-text-strong)]"
            >
              <LogOut size={16} aria-hidden="true" />
              Log out
            </button>
          ) : null}
          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-[var(--radius-card)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)]"
            aria-label="Open navigation"
          >
            <Menu size={18} aria-hidden="true" />
          </button>
        </div>
      </div>
      <ActiveOrganizationSummary compact />
    </header>
  );
}
