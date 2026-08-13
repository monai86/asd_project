"use client";

import { LockKeyhole, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import {
  loadMockAccessSession,
  resolveOrganizationLabel,
  updateMockAccessSessionAal,
  type MockAccessSession,
} from "@/lib/mock-access-session";

export function WorkspaceAccessGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const [session, setSession] = useState<MockAccessSession | null>(null);

  useEffect(() => {
    setSession(loadMockAccessSession());
  }, []);

  if (!session || session.aal === "aal2") {
    return <>{children}</>;
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
      <section className="w-full rounded-[1.75rem] border border-amber-200 bg-white p-6">
        <p className="inline-flex min-h-8 items-center rounded-full border border-amber-200 bg-amber-50 px-3 text-xs font-semibold text-amber-900">
          AAL1 session detected
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-ink">Additional verification required</h1>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          This mock session is signed in for <strong>{resolveOrganizationLabel(session.organizationId)}</strong>, but the
          workspace remains blocked until the session reaches <strong>aal2</strong>.
        </p>

        <div className="mt-5 rounded-[var(--radius-panel)] border border-cyan-100 bg-cyan-50 p-4 text-sm text-cyan-950">
          <div className="flex items-start gap-3">
            <LockKeyhole size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Production rule</p>
              <p className="mt-1">
                Invitation-only onboarding and AAL2 are required before clinical or admin workflow access.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-5 rounded-[var(--radius-panel)] border border-line bg-slate-50 p-4 text-sm text-slate-700">
          <div className="flex items-start gap-3">
            <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-clinical" />
            <div>
              <p className="font-semibold text-ink">Mock MFA step</p>
              <p className="mt-1">
                Use this control to simulate completing the second factor and promote the session to <strong>aal2</strong>.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => {
              updateMockAccessSessionAal("aal2");
              setSession(loadMockAccessSession());
            }}
            className="inline-flex min-h-11 items-center justify-center rounded-full bg-clinical px-5 text-sm font-semibold text-white"
          >
            Complete mock MFA
          </button>
        </div>
      </section>
    </main>
  );
}
