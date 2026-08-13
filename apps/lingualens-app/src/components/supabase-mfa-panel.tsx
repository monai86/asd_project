"use client";

import { useRouter } from "next/navigation";
import { KeyRound, QrCode, RefreshCw, ShieldCheck } from "lucide-react";
import { startTransition, useCallback, useEffect, useState } from "react";

import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { syncSupabaseAccessSessionFromSession } from "@/lib/supabase-browser-auth";

type TotpFactor = {
  id: string;
  factor_type: "totp";
  status: "verified" | "unverified";
  friendly_name?: string;
};

type EnrollmentState = {
  factorId: string;
  friendlyName?: string;
  qrCode: string;
  secret: string;
};

function toTotpFactors(value: unknown): TotpFactor[] {
  if (!Array.isArray(value)) return [];

  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const factor = item as Partial<TotpFactor>;

    if (
      typeof factor.id !== "string"
      || factor.factor_type !== "totp"
      || (factor.status !== "verified" && factor.status !== "unverified")
    ) {
      return [];
    }

    return [{
      id: factor.id,
      factor_type: "totp",
      status: factor.status,
      friendly_name: typeof factor.friendly_name === "string" ? factor.friendly_name : undefined,
    }];
  });
}

export function SupabaseMfaPanel({
  email,
}: {
  email?: string;
}) {
  const router = useRouter();
  const [factors, setFactors] = useState<TotpFactor[]>([]);
  const [isLoadingFactors, setIsLoadingFactors] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [enrollment, setEnrollment] = useState<EnrollmentState | null>(null);
  const [code, setCode] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const [browserClient] = useState(() => getSupabaseBrowserClient());
  const verifiedFactor = factors.find((factor) => factor.status === "verified");
  const pendingFactor = factors.find((factor) => factor.status === "unverified");

  const refreshFactors = useCallback(async () => {
    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      setIsLoadingFactors(false);
      return;
    }

    setIsLoadingFactors(true);
    setErrorMessage("");

    try {
      const { data, error } = await browserClient.auth.mfa.listFactors();
      if (error) {
        setErrorMessage(error.message);
        return;
      }

      setFactors(toTotpFactors(data?.all));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load MFA factors.");
    } finally {
      setIsLoadingFactors(false);
    }
  }, [browserClient]);

  useEffect(() => {
    void refreshFactors();
  }, [refreshFactors]);

  async function handleStartEnrollment() {
    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");
    setStatusMessage("");

    try {
      const { data, error } = await browserClient.auth.mfa.enroll({
        factorType: "totp",
        friendlyName: "LinguaLens Authenticator",
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      setEnrollment({
        factorId: data.id,
        friendlyName: data.friendly_name,
        qrCode: data.totp.qr_code,
        secret: data.totp.secret,
      });
      setStatusMessage("TOTP enrollment started. Scan the QR code or enter the secret, then verify with a current code.");
      await refreshFactors();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to start MFA enrollment.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleVerifyCode() {
    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    const factorId = verifiedFactor?.id ?? pendingFactor?.id ?? enrollment?.factorId;
    if (!factorId) {
      setErrorMessage("No TOTP factor is available for verification.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");
    setStatusMessage("");

    try {
      const { error } = await browserClient.auth.mfa.challengeAndVerify({
        factorId,
        code: code.trim(),
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      const { data } = await browserClient.auth.getSession();
      syncSupabaseAccessSessionFromSession((data.session ?? null) as Parameters<typeof syncSupabaseAccessSessionFromSession>[0]);
      setStatusMessage("MFA verified. Refreshing workspace access.");
      setCode("");
      await refreshFactors();
      startTransition(() => {
        router.refresh();
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to verify MFA code.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const qrImageSource = enrollment
    ? `data:image/svg+xml;utf8,${encodeURIComponent(enrollment.qrCode)}`
    : null;

  return (
    <div className="mt-5 grid gap-4">
      <div className="rounded-[var(--radius-panel)] border border-line bg-slate-50 p-4 text-sm text-slate-700">
        <div className="flex items-start gap-3">
          <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-clinical" />
          <div>
            <p className="font-semibold text-ink">Real TOTP MFA flow</p>
            <p className="mt-1">
              Continue with the browser-side Supabase MFA flow for
              {" "}
              <strong>{email ?? "this account"}</strong>
              . The workspace opens only after the session is elevated to <strong>aal2</strong>.
            </p>
          </div>
        </div>
      </div>

      {verifiedFactor ? (
        <div className="rounded-[var(--radius-panel)] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
          <div className="flex items-start gap-3">
            <KeyRound size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Verified authenticator ready</p>
              <p className="mt-1">
                Use the current code from
                {" "}
                <strong>{verifiedFactor.friendly_name ?? "your authenticator app"}</strong>
                {" "}
                to elevate this session.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {!verifiedFactor && qrImageSource ? (
        <div className="rounded-[var(--radius-panel)] border border-cyan-100 bg-cyan-50 p-4 text-sm text-cyan-950">
          <div className="flex items-start gap-3">
            <QrCode size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="font-semibold">Scan your authenticator app</p>
              <p className="mt-1">
                Add the new TOTP factor
                {" "}
                <strong>{enrollment?.friendlyName ?? "LinguaLens Authenticator"}</strong>
                {" "}
                and verify the first code.
              </p>
              {/* The enrollment QR is an in-memory data URI and must not be sent through an image optimizer. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={qrImageSource}
                alt="Supabase TOTP QR code"
                className="mt-4 h-40 w-40 rounded-xl border border-cyan-200 bg-white p-2"
              />
              <label className="mt-4 grid gap-1 text-xs font-medium text-cyan-950">
                Backup secret
                <input
                  type="text"
                  readOnly
                  value={enrollment?.secret ?? ""}
                  className="rounded-xl border border-cyan-200 bg-white px-3 py-2 font-mono text-xs text-cyan-950"
                />
              </label>
            </div>
          </div>
        </div>
      ) : null}

      {!verifiedFactor && !enrollment && pendingFactor ? (
        <div className="rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <div className="flex items-start gap-3">
            <RefreshCw size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Enrollment pending verification</p>
              <p className="mt-1">
                A TOTP factor already exists for this account but has not been verified yet. Enter the current code
                from the authenticator app to finish enrollment and elevate the session.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {!verifiedFactor && !pendingFactor && !enrollment ? (
        <button
          type="button"
          onClick={() => void handleStartEnrollment()}
          disabled={isSubmitting || isLoadingFactors}
          className="inline-flex min-h-11 items-center justify-center rounded-full bg-clinical px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {isSubmitting ? "Starting TOTP enrollment..." : "Start TOTP enrollment"}
        </button>
      ) : null}

      {(verifiedFactor || pendingFactor || enrollment) ? (
        <div className="grid gap-3 rounded-[var(--radius-panel)] border border-line bg-white p-4">
          <label className="grid gap-2 text-sm font-medium text-ink">
            Authenticator code
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="123456"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              className="min-h-11 rounded-[var(--radius-pill)] border border-line bg-white px-4 text-sm text-ink outline-none"
            />
          </label>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void handleVerifyCode()}
              disabled={isSubmitting || !code.trim()}
              className="inline-flex min-h-11 items-center justify-center rounded-full bg-clinical px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isSubmitting ? "Verifying code..." : verifiedFactor ? "Verify TOTP and continue" : "Complete TOTP enrollment"}
            </button>

            <button
              type="button"
              onClick={() => void refreshFactors()}
              disabled={isSubmitting || isLoadingFactors}
              className="inline-flex min-h-11 items-center justify-center rounded-full border border-line bg-white px-5 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:bg-slate-100"
            >
              Refresh factors
            </button>
          </div>
        </div>
      ) : null}

      {statusMessage ? (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900" aria-live="polite">
          {statusMessage}
        </p>
      ) : null}

      {errorMessage ? (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
