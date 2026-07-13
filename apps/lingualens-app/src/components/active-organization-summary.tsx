"use client";

import { useRouter } from "next/navigation";
import { Building2 } from "lucide-react";
import { startTransition, useEffect, useState } from "react";

import {
  getMockOrganizationOptions,
  loadMockAccessSession,
  MOCK_ACCESS_SESSION_EVENT,
  resolveOrganizationLabel,
  updateMockAccessSessionOrganizationId,
  type MockAccessSession,
} from "@/lib/mock-access-session";
import {
  loadSupabaseAccessSession,
  SUPABASE_ACCESS_SESSION_EVENT,
  type SupabaseAccessSession,
} from "@/lib/supabase-access-session";
import { beginSupabaseBrowserOrganizationSwitch } from "@/lib/supabase-browser-auth";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function ActiveOrganizationSummary() {
  const router = useRouter();
  const runtimeSettings = useRuntimeSettings();
  const [session, setSession] = useState<MockAccessSession | null>(null);
  const [supabaseSession, setSupabaseSession] = useState<SupabaseAccessSession | null>(null);
  const [switchMessage, setSwitchMessage] = useState("");

  useEffect(() => {
    const syncSession = () => setSession(loadMockAccessSession());
    syncSession();
    window.addEventListener(MOCK_ACCESS_SESSION_EVENT, syncSession);
    return () => window.removeEventListener(MOCK_ACCESS_SESSION_EVENT, syncSession);
  }, []);

  useEffect(() => {
    const syncSession = () => setSupabaseSession(loadSupabaseAccessSession());
    syncSession();
    window.addEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
    return () => window.removeEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
  }, []);

  if (runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase") {
    const organizationLabel = supabaseSession?.availableOrganizations?.find(
      (option) => option.organizationId === supabaseSession.organizationId,
    )?.label ?? supabaseSession?.organizationId ?? "Organization not selected";
    const canSwitch = (supabaseSession?.availableOrganizations?.length ?? 0) > 1;

    return (
      <div className="min-w-0 rounded-[1.25rem] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm shadow-soft">
        <div className="flex items-center gap-2">
          <Building2 size={15} aria-hidden="true" className="text-[color:var(--color-accent-strong)]" />
          <div className="min-w-0">
            <p className="truncate font-semibold text-[color:var(--color-text-strong)]">{organizationLabel}</p>
            <p className="truncate text-xs text-[color:var(--color-text-muted)]">Active organization session</p>
          </div>
        </div>
        {canSwitch ? (
          <div className="mt-3 grid gap-2 text-xs text-[color:var(--color-text-muted)]">
            <span className="font-semibold uppercase tracking-[0.08em]">Switch active org</span>
            <button
              type="button"
              className="min-h-10 rounded-[var(--radius-pill)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-muted)] px-3 text-sm text-[color:var(--color-text-strong)]"
              onClick={() => {
                beginSupabaseBrowserOrganizationSwitch();
                setSwitchMessage("Choose the next active organization before workspace access resumes.");
                startTransition(() => {
                  router.refresh();
                });
              }}
            >
              Choose another organization
            </button>
            <span>Only one organization is active per session. Switching reopens explicit selection.</span>
            {switchMessage ? <span aria-live="polite">{switchMessage}</span> : null}
          </div>
        ) : null}
      </div>
    );
  }

  const organizationId = session?.organizationId ?? "pilot_org_001";
  const options = session ? getMockOrganizationOptions(session.role) : [];
  const requiresExplicitSelection = options.length > 1;

  return (
    <div className="min-w-0 rounded-[1.25rem] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm shadow-soft">
      <div className="flex items-center gap-2">
        <Building2 size={15} aria-hidden="true" className="text-[color:var(--color-accent-strong)]" />
        <div className="min-w-0">
          <p className="truncate font-semibold text-[color:var(--color-text-strong)]">{resolveOrganizationLabel(organizationId)}</p>
          <p className="truncate text-xs text-[color:var(--color-text-muted)]">Active organization session</p>
        </div>
      </div>
      {requiresExplicitSelection ? (
        <label className="mt-3 grid gap-1 text-xs text-[color:var(--color-text-muted)]">
          <span className="font-semibold uppercase tracking-[0.08em]">Switch active org</span>
          <select
            aria-label="Switch active organization"
            className="min-h-10 rounded-[var(--radius-pill)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-muted)] px-3 text-sm text-[color:var(--color-text-strong)] outline-none"
            value={organizationId}
            onChange={(event) => {
              updateMockAccessSessionOrganizationId(event.target.value);
              setSwitchMessage("Active organization switched. Refreshing scoped workspace data.");
              startTransition(() => {
                router.refresh();
              });
            }}
          >
            {options.map((option) => (
              <option key={option.organizationId} value={option.organizationId}>
                {option.label}
              </option>
            ))}
          </select>
          <span>Only one organization is active per session. Switching changes the next scoped request.</span>
          {switchMessage ? <span aria-live="polite">{switchMessage}</span> : null}
        </label>
      ) : null}
    </div>
  );
}
