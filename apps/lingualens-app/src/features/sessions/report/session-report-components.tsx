import { ArrowRight, Heart, Star } from "lucide-react";

import type { WorkflowState } from "@/lib/workflow";

export const reportSectionDefinitions = [
  {
    icon: Star,
    title: "Strengths",
    tone: "bg-emerald-100 text-emerald-700",
    items: ["Reviewed transcript available", "Feature summary prepared for therapist interpretation"],
  },
  {
    icon: Heart,
    title: "Needs Support",
    tone: "bg-orange-100 text-orange-600",
    items: ["Confirm transcript wording", "Review suggested next steps before sharing"],
  },
  {
    icon: ArrowRight,
    title: "Next Steps",
    tone: "bg-[#efeaff] text-clinical",
    items: ["Edit draft report language", "Finalize only after therapist review"],
  },
];

export function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  if (!state.statusMessage && !state.error) return null;
  const isError = Boolean(state.error);
  const isSuccess = Boolean(state.statusMessage && !isError);
  if (isSuccess && backendUnavailable) return null;
  const className = isError
    ? "rounded-[var(--radius-panel)] border border-red-200 bg-red-50 p-4 text-sm text-red-950 animate-fade-in"
    : isSuccess
      ? "rounded-[var(--radius-panel)] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 animate-fade-in"
      : "demo-note rounded-[var(--radius-panel)] p-4 text-sm";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}

export function ReportProvenanceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-muted)] p-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">{label}</dt>
      <dd className="mt-1 [overflow-wrap:anywhere] text-sm font-bold text-ink">{value}</dd>
    </div>
  );
}
