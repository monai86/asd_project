"use client";

import { useRouter } from "next/navigation";
import { Building2, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { type FormEvent, useState } from "react";

import { type RuntimeSettings } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { getSupabaseBrowserClientConfigStatus } from "@/lib/supabase-browser-client-config";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";

function resolvePostLoginRoute(role: unknown): string {
  if (role === "org_admin" || role === "platform_operator") {
    return "/settings?scope=admin";
  }

  return "/today";
}

export function SupabaseLoginFormClient({
  runtimeSettings,
}: {
  runtimeSettings: RuntimeSettings;
}) {
  const router = useRouter();
  const invitationOnly = runtimeSettings.access_model?.invitation_only !== false;
  const browserClientStatus = getSupabaseBrowserClientConfigStatus();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSendingRecovery, setIsSendingRecovery] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const browserClient = browserClientStatus.configured ? getSupabaseBrowserClient() : null;
  const configStatusLabel = browserClientStatus.configured
    ? "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY detected."
    : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
      ? "waiting for NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
      : "NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is malformed for the launch contract.";

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    setIsSubmitting(true);

    try {
      const { data, error } = await browserClient.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      publishSupabaseSessionPayload(data.session ?? null);
      setStatusMessage("Sign-in accepted. Routing through organization and MFA access gates.");
      router.push(resolvePostLoginRoute(data.session?.user?.app_metadata?.role));
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Sign-in failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePasswordRecovery() {
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    if (!email.trim()) {
      setErrorMessage("Enter the invitation email address first.");
      return;
    }

    setIsSendingRecovery(true);

    try {
      const { error } = await browserClient.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}/login`,
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      setStatusMessage("Recovery email sent. App access still requires accepted membership and AAL2 after reset.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Recovery request failed.");
    } finally {
      setIsSendingRecovery(false);
    }
  }

  return (
    <form className="clinical-card self-start rounded-md p-5" aria-label="Supabase login form" onSubmit={handleSignIn}>
      <div className="mb-5 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-md bg-clinical text-white">
          <ShieldCheck size={20} aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-semibold">Secure sign in</h2>
          <p className="text-xs text-slate-600">
            Production-capable access uses invitation-only email/password sign-in plus required TOTP MFA.
          </p>
        </div>
      </div>

      <label className="mb-4 block text-sm font-medium">
        Email
        <input
          className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2"
          type="email"
          inputMode="email"
          autoComplete="username"
          placeholder="clinician@clinic.example"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </label>

      <label className="mb-4 block text-sm font-medium">
        Password
        <input
          className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2"
          type="password"
          autoComplete="current-password"
          placeholder="Enter password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>

      <button
        type="submit"
        disabled={!browserClient || isSubmitting || !email.trim() || !password}
        aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
        className="inline-flex w-full justify-center rounded-md bg-clinical px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-700"
      >
        {isSubmitting
          ? "Signing in..."
          : browserClientStatus.configured
            ? "Sign in with Supabase"
            : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
              ? "Supabase browser config missing"
              : "Supabase browser config invalid"}
      </button>

      <button
        type="button"
        onClick={handlePasswordRecovery}
        disabled={!browserClient || isSendingRecovery}
        className="mt-3 inline-flex w-full justify-center rounded-md border border-line bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
      >
        {isSendingRecovery ? "Sending recovery email..." : "Send recovery email"}
      </button>

      {errorMessage ? (
        <p className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900" role="alert">
          {errorMessage}
        </p>
      ) : null}

      {statusMessage ? (
        <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900" aria-live="polite">
          {statusMessage}
        </p>
      ) : null}

      <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
        <div className="flex items-start gap-2">
          <Mail size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Invitation-only access</p>
            <p className="mt-1">
              {invitationOnly
                ? "Public signup is off. Only users with an accepted invitation can continue to account access."
                : "Runtime settings are not currently enforcing invitation-only onboarding."}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-cyan-100 bg-cyan-50 p-3 text-xs text-cyan-950">
        <div className="flex items-start gap-2">
          <LockKeyhole size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">MFA and app access</p>
            <p className="mt-1">
              After invitation acceptance, TOTP MFA enrollment is mandatory. <strong>aal1</strong> can reach MFA screens
              only, and <strong>aal2</strong> is required before any clinical or admin workflow access.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
        <div className="flex items-start gap-2">
          <Building2 size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Organization session selection</p>
            <p className="mt-1">
              If multiple memberships are active, the user must explicitly choose one organization before workspace
              access. The last active organization is a hint only when the choice is ambiguous.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-line bg-white p-3 text-xs text-slate-700">
        <p className="font-semibold text-ink">Recovery and current runtime status</p>
        <p className="mt-1">
          Password recovery uses the Supabase-managed reset path and still returns through membership and MFA gates
          before app access.
        </p>
        <p className="mt-2 text-slate-600">
          Browser sign-in now depends on the configured Supabase project and claim contract. Workspace access still
          fails closed until invitation, membership, MFA, and active organization requirements are satisfied.
        </p>
        <p className="mt-2 text-slate-600">
          Browser config:
          {" "}
          {configStatusLabel}
        </p>
      </div>
    </form>
  );
}
