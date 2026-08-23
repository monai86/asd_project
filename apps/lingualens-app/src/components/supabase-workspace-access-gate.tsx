"use client";

import Link from "next/link";
import { Building2, LockKeyhole, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { SupabaseMfaPanel } from "@/components/supabase-mfa-panel";
import {
  SUPABASE_ACCESS_SESSION_EVENT,
  type SupabaseAccessSession,
} from "@/lib/supabase-access-session";
import { selectSupabaseBrowserOrganization } from "@/lib/supabase-browser-auth";
import { loadOrRestoreSupabaseAccessSession } from "@/lib/use-supabase-access-session";

export function SupabaseWorkspaceAccessGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const [session, setSession] = useState<SupabaseAccessSession | null>(null);
  const [pendingOrganizationId, setPendingOrganizationId] = useState("");
  const availableOrganizationIds = session?.availableOrganizations
    ?.map((option) => option.organizationId)
    .join("|");

  useEffect(() => {
    const syncSession = () => setSession(loadOrRestoreSupabaseAccessSession());
    syncSession();
    window.addEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
    return () => window.removeEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
  }, []);

  useEffect(() => {
    if (session?.stage !== "org_selection_required") {
      setPendingOrganizationId("");
      return;
    }

    const nextSelection = session.suggestedOrganizationId
      ?? session.organizationId
      ?? "";
    setPendingOrganizationId(nextSelection);
  }, [
    session?.stage,
    session?.suggestedOrganizationId,
    session?.organizationId,
    availableOrganizationIds,
  ]);

  if (session?.stage === "authenticated" && session.organizationId && session.aal === "aal2") {
    return <>{children}</>;
  }

  if (session?.stage === "org_selection_required" && session.availableOrganizations?.length) {
    const suggestedOrganization = session.availableOrganizations.find(
      (option) => option.organizationId === session.suggestedOrganizationId,
    );

    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-[1.75rem] border border-cyan-100 bg-white p-6">
          <p className="inline-flex min-h-8 items-center rounded-full border border-cyan-100 bg-cyan-50 px-3 text-xs font-semibold text-cyan-950">
            Organization selection required
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-ink">Choose an active organization</h1>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            This account has multiple active memberships. Exactly one organization must be selected before clinical or
            admin workflows can continue.
          </p>

          {suggestedOrganization ? (
            <div className="mt-5 rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-semibold">Last active organization hint</p>
              <p className="mt-1">
                The previous session used <strong>{suggestedOrganization.label}</strong>. This is a hint only. Review
                the selection and confirm before the workspace opens.
              </p>
            </div>
          ) : null}

          <label className="mt-6 grid gap-2 text-sm font-medium text-ink">
            Active organization
            <select
              aria-label="Select active organization"
              className="min-h-11 rounded-[var(--radius-pill)] border border-line bg-white px-4 text-sm text-ink outline-none focus:ring-2 focus:ring-[color:var(--color-focus-ring)]"
              value={pendingOrganizationId}
              onChange={(event) => setPendingOrganizationId(event.target.value)}
            >
              <option value="" disabled>Select one organization</option>
              {session.availableOrganizations.map((option) => (
                <option key={option.organizationId} value={option.organizationId}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              className="inline-flex min-h-11 items-center justify-center rounded-full bg-clinical px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!pendingOrganizationId}
              onClick={() => {
                if (!pendingOrganizationId) return;
                selectSupabaseBrowserOrganization(pendingOrganizationId);
              }}
            >
              Continue with selected organization
            </button>
          </div>

          <div className="mt-5 rounded-[var(--radius-panel)] border border-line bg-slate-50 p-4 text-sm text-slate-700">
            <div className="flex items-start gap-3">
              <Building2 size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-clinical" />
              <div>
                <p className="font-semibold text-ink">Launch rule</p>
                <p className="mt-1">
                  Organization memory is a hint only. When membership context is ambiguous, selection must be explicit.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (session?.stage === "mfa_required" || session?.aal === "aal1") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-[1.75rem] border border-amber-200 bg-white p-6">
          <p className="inline-flex min-h-8 items-center rounded-full border border-amber-200 bg-amber-50 px-3 text-xs font-semibold text-amber-900">
            AAL1 session detected
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-ink">Additional verification required</h1>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            Authentication has not yet reached <strong>aal2</strong>. The workspace remains blocked until TOTP MFA is
            completed and the app receives an elevated session.
          </p>

          <div className="mt-5 rounded-[var(--radius-panel)] border border-cyan-100 bg-cyan-50 p-4 text-sm text-cyan-950">
            <div className="flex items-start gap-3">
              <LockKeyhole size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold">MFA requirement</p>
                <p className="mt-1">
                  `aal1` may reach MFA screens only. `aal2` is required before case, report, or admin access.
                </p>
              </div>
            </div>
          </div>

          <p className="mt-5 text-sm leading-6 text-slate-600">
            Invitation-only onboarding still fails closed. Complete the Supabase TOTP step below to elevate this
            session to <strong>aal2</strong>.
          </p>

          <SupabaseMfaPanel email={session?.email} />
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
      <section className="w-full rounded-[1.75rem] border border-line bg-white p-6">
        <p className="inline-flex min-h-8 items-center rounded-full border border-line bg-slate-50 px-3 text-xs font-semibold text-slate-700">
          Sign-in required
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-ink">Workspace access is blocked</h1>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          This runtime expects Supabase authentication. Public signup is off, invitation acceptance is required, and no
          workspace route should open before a valid `aal2` session is established.
        </p>

        <div className="mt-5 rounded-[var(--radius-panel)] border border-cyan-100 bg-cyan-50 p-4 text-sm text-cyan-950">
          <div className="flex items-start gap-3">
            <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Production boundary</p>
              <p className="mt-1">
                Invitation-only onboarding, MFA, and explicit organization context are enforced before app access.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center justify-center rounded-full bg-clinical px-5 text-sm font-semibold text-white"
          >
            Go to login
          </Link>
        </div>
      </section>
    </main>
  );
}
