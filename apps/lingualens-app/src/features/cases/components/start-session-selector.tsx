"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ShieldCheck } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { PageHeader } from "@/components/page-header";
import { SafetyNotice } from "@/components/safety-notice";
import { createBackendSessionForCase, type BackendCase } from "@/lib/workflow";

function caseLabel(caseItem: BackendCase) {
  return caseItem.nickname ?? caseItem.child_code ?? caseItem.display_label ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function codeLabel(caseItem: BackendCase) {
  return caseItem.child_code ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function canStartSession(caseItem: BackendCase) {
  return caseItem.consent_status?.toLowerCase() === "granted";
}

export function StartSessionSelector({ cases }: { cases: BackendCase[] }) {
  const router = useRouter();
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selectedCase = cases.find((caseItem) => caseItem.case_id === selectedCaseId && canStartSession(caseItem));
  const hasConsentedCase = cases.some(canStartSession);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCase || busy) return;

    setBusy(true);
    setMessage("Creating the session…");
    try {
      const session = await createBackendSessionForCase(selectedCase.case_id);
      router.push(`/sessions/${encodeURIComponent(session.session_id)}?view=intake`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The session could not be created. Please retry.");
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Choose a case to start a session"
        description="Select one consented case. LinguaLens creates the session on the backend before opening Intake."
        meta={["No session is created until you confirm"]}
        actions={<ActionButton href="/cases" tone="ghost"><ArrowLeft size={16} aria-hidden="true" />Back to Cases</ActionButton>}
      />

      <form className="workspace-panel p-4 sm:p-5" onSubmit={handleSubmit}>
        <fieldset disabled={busy}>
          <legend className="text-lg font-semibold text-[color:var(--color-text-strong)]">Available cases</legend>
          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
            Cases without active consent remain visible for context but cannot be selected.
          </p>
          {!hasConsentedCase ? (
            <div className="mt-4 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-4 text-amber-950">
              <h2 className="font-semibold">No consented cases available</h2>
              <p className="mt-1 text-sm leading-6">
                Confirm consent from the case record before starting a session.
              </p>
            </div>
          ) : null}
          <ul className="mt-4 grid gap-3" aria-label="Cases available for a new session">
            {cases.map((caseItem) => {
              const allowed = canStartSession(caseItem);
              const selected = selectedCaseId === caseItem.case_id;
              return (
                <li key={caseItem.case_id}>
                  <label className={`flex min-h-16 cursor-pointer items-start gap-3 rounded-[var(--radius-card)] border p-4 transition focus-within:ring-4 focus-within:ring-[color:var(--color-focus-ring)] ${
                    selected
                      ? "border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-soft)]"
                      : "border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)]"
                  } ${allowed ? "" : "cursor-not-allowed opacity-65"}`}>
                    <input
                      type="radio"
                      name="case-id"
                      value={caseItem.case_id}
                      checked={selected}
                      onChange={() => setSelectedCaseId(caseItem.case_id)}
                      disabled={!allowed}
                      className="mt-1 h-5 w-5 shrink-0 accent-[color:var(--color-accent-strong)]"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold text-[color:var(--color-text-strong)]">{caseLabel(caseItem)}</span>
                      <span className="mt-1 block text-sm text-[color:var(--color-text-muted)]">
                        {codeLabel(caseItem)} · {caseItem.language ?? "Language not recorded"}
                      </span>
                    </span>
                    <span className="inline-flex min-h-8 shrink-0 items-center gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border)] px-3 text-xs font-semibold text-[color:var(--color-text-muted)]">
                      <ShieldCheck size={14} aria-hidden="true" />
                      {allowed ? "Consent active" : "Consent required"}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <ActionButton type="submit" disabled={!selectedCase || busy}>
            {busy ? "Creating session…" : selectedCase ? `Start session for ${codeLabel(selectedCase)}` : "Start session"}
          </ActionButton>
          <p className="text-sm text-[color:var(--color-text-muted)]" role="status" aria-live="polite">
            {message}
          </p>
        </div>
      </form>

      <SafetyNotice>
        Starting a session does not generate findings or a report. Therapist review and consent gates remain required.
      </SafetyNotice>
    </div>
  );
}
