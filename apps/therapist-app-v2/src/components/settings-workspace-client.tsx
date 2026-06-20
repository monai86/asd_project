"use client";

import { useState } from "react";
import { ShieldCheck, UserRound } from "lucide-react";

import { privacyOperations, type PrivacyOperation } from "@/lib/mock-data";

type Scope = "therapist" | "admin";

const therapistSettings = [
  ["Profile", "Demo Therapist"],
  ["Credentials", "Speech therapist / clinician"],
  ["Organization", "Mock clinic workspace"],
  ["Sample data mode", "Visible local demo data only"],
  ["Owned privacy requests", "Case export and consent withdrawal requests for owned cases"],
  ["Consent policy", "Visible per case with withdrawal workflow"]
];

const adminSettings = [
  ["Model version", "v2-mock, review-support-only"],
  ["Feature schema", "therapist-app-v2.1"],
  ["Guideline mapping", "Shown as limitations and review prompts"],
  ["Audit logs", "Admin role required"],
  ["Runtime diagnostics", "Repository, job queue, and storage mode"],
  ["Pipeline settings", "Audio automation is experimental and asynchronous"]
];

function SettingRows({ rows }: { rows: string[][] }) {
  return (
    <div className="clinical-card rounded-md">
      {rows.map(([label, value]) => (
        <div key={label} className="grid gap-1 border-b border-line px-4 py-3 text-sm last:border-b-0 md:grid-cols-[240px_1fr]">
          <div className="font-medium">{label}</div>
          <div className="text-slate-700">{value}</div>
        </div>
      ))}
    </div>
  );
}

function PrivacyOperationList({ operations, scope }: { operations: PrivacyOperation[]; scope: Scope }) {
  return (
    <section className="clinical-card rounded-md p-4" aria-label={scope === "admin" ? "Admin privacy operation queue" : "Owned privacy requests"}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">{scope === "admin" ? "Privacy operation queue" : "Owned privacy requests"}</h2>
          <p className="mt-1 text-xs text-slate-600">
            {scope === "admin" ? "Admin review of export, consent, and deletion-review requests." : "Requests tied to cases owned by the current therapist."}
          </p>
        </div>
        <span className="rounded-md border border-line bg-field px-2 py-1 text-xs font-medium text-slate-700">{operations.length} open</span>
      </div>
      <div className="grid gap-2">
        {operations.map((operation) => (
          <article key={operation.id} className="rounded-md border border-line bg-field p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-medium">{operation.operationType}</h3>
                <p className="mt-1 text-xs text-slate-600">{operation.caseCode} - Requested by {operation.requestedBy} - {operation.age}</p>
              </div>
              <span className="rounded-md border border-clinical bg-white px-2 py-1 text-xs font-medium text-clinical">{operation.status}</span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{operation.note}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function SettingsWorkspaceClient({ initialScope = "therapist" }: { initialScope?: Scope }) {
  const [scope, setScope] = useState<Scope>(initialScope);
  const rows = scope === "therapist" ? therapistSettings : adminSettings;
  const visiblePrivacyOperations = scope === "therapist" ? privacyOperations.filter((operation) => operation.requestedBy === "Demo Therapist") : privacyOperations;

  return (
    <section className="grid gap-4">
      <div className="inline-flex w-fit rounded-md border border-line bg-white p-1 shadow-soft" aria-label="Settings scope">
        <button
          type="button"
          className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${scope === "therapist" ? "bg-clinical text-white" : "text-slate-600"}`}
          onClick={() => setScope("therapist")}
        >
          <UserRound size={16} aria-hidden="true" />
          Therapist
        </button>
        <button
          type="button"
          className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${scope === "admin" ? "bg-clinical text-white" : "text-slate-600"}`}
          onClick={() => setScope("admin")}
        >
          <ShieldCheck size={16} aria-hidden="true" />
          Admin
        </button>
      </div>
      <SettingRows rows={rows} />
      <PrivacyOperationList operations={visiblePrivacyOperations} scope={scope} />
    </section>
  );
}
