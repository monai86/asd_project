export type WorkflowStatus =
  | "Draft"
  | "Needs Review"
  | "Attested"
  | "Processing"
  | "Failed"
  | "Ready"
  | "Signed Off"
  | "Withdrawn";

const styles: Record<WorkflowStatus, string> = {
  Draft: "border-slate-300 bg-white text-slate-700",
  "Needs Review": "border-amber-300 bg-amber-50 text-amber-900",
  Attested: "border-teal-300 bg-teal-50 text-teal-900",
  Processing: "border-sky-300 bg-sky-50 text-sky-900",
  Failed: "border-red-300 bg-red-50 text-red-900",
  Ready: "border-emerald-300 bg-emerald-50 text-emerald-900",
  "Signed Off": "border-moss bg-moss text-white",
  Withdrawn: "border-slate-400 bg-slate-100 text-slate-700"
};

export function StatusBadge({ status }: { status: string }) {
  const normalized = (Object.keys(styles) as WorkflowStatus[]).includes(status as WorkflowStatus)
    ? (status as WorkflowStatus)
    : "Draft";
  return (
    <span className={`inline-flex min-h-7 min-w-24 items-center justify-center rounded-md border px-2.5 py-1 text-xs font-semibold ${styles[normalized]}`}>
      {status}
    </span>
  );
}
