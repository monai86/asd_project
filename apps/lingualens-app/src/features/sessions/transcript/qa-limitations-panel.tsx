"use client";

import { useState } from "react";

export type QaOutcome = {
  code: string;
  disposition: "integrity_blocker" | "acknowledgeable_limitation";
  severity: string;
  rule_version: string;
  affected_resources: string[];
  remediation: string;
  message: string;
};

type AcknowledgmentReason =
  | "reviewed_and_accepted"
  | "context_documented"
  | "metric_will_remain_unavailable"
  | "manual_review_completed";

export function QaLimitationsPanel({
  blockers,
  limitations,
  acknowledgedCodes,
  busy,
  onAcknowledge,
}: {
  blockers: QaOutcome[];
  limitations: QaOutcome[];
  acknowledgedCodes: string[];
  busy: boolean;
  onAcknowledge: (code: string, reason: AcknowledgmentReason, note: string) => void;
}) {
  const [reasons, setReasons] = useState<Record<string, AcknowledgmentReason>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  if (!blockers.length && !limitations.length) return null;

  return (
    <section className="space-y-4 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4" aria-labelledby="qa-policy-title">
      <div>
        <h2 id="qa-policy-title" className="font-semibold text-ink">QA blockers and limitations</h2>
        <p className="mt-1 text-sm text-muted">Integrity blockers must be resolved. Reviewable limitations stay version-bound and visible downstream.</p>
      </div>
      {blockers.length ? (
        <div className="space-y-2" role="alert">
          <h3 className="font-semibold text-red-900">Integrity blockers</h3>
          {blockers.map((item) => (
            <article key={item.code} data-testid={`qa-blocker-${item.code}`} className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-950">
              <div className="flex flex-wrap items-center justify-between gap-2"><strong>{item.code}</strong><span className="font-semibold">Cannot be overridden</span></div>
              <p className="mt-1">{item.message}</p><p className="mt-1">{item.remediation}</p>
              <p className="mt-1 text-xs">{item.rule_version}</p>
            </article>
          ))}
        </div>
      ) : null}
      {limitations.length ? (
        <div className="space-y-2">
          <h3 className="font-semibold text-amber-900">Acknowledgeable limitations</h3>
          {limitations.map((item) => {
            const acknowledged = acknowledgedCodes.includes(item.code);
            const reason = reasons[item.code] ?? "reviewed_and_accepted";
            return (
              <article key={item.code} data-testid={`qa-limitation-${item.code}`} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
                <div className="flex flex-wrap items-center justify-between gap-2"><strong>{item.code}</strong><span>{item.rule_version}</span></div>
                <p className="mt-1">{item.message}</p><p className="mt-1">{item.remediation}</p>
                {acknowledged ? <p className="mt-2 font-semibold text-emerald-800">Acknowledged for this transcript version</p> : (
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <label className="grid gap-1">Reason for {item.code}
                      <select aria-label={`Reason for ${item.code}`} value={reason} onChange={(event) => setReasons((current) => ({ ...current, [item.code]: event.target.value as AcknowledgmentReason }))} className="min-h-11 rounded-md border bg-white px-2">
                        <option value="reviewed_and_accepted">Reviewed and accepted</option>
                        <option value="context_documented">Context documented</option>
                        <option value="metric_will_remain_unavailable">Metric remains unavailable</option>
                        <option value="manual_review_completed">Manual review completed</option>
                      </select>
                    </label>
                    <label className="grid gap-1">Optional note
                      <input aria-label={`Note for ${item.code}`} value={notes[item.code] ?? ""} onChange={(event) => setNotes((current) => ({ ...current, [item.code]: event.target.value }))} className="min-h-11 rounded-md border bg-white px-2" />
                    </label>
                    <button type="button" disabled={busy} onClick={() => onAcknowledge(item.code, reason, notes[item.code] ?? "")} className="min-h-11 rounded-md bg-amber-900 px-3 font-semibold text-white disabled:opacity-50">Acknowledge {item.code}</button>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
