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
  Draft: "border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-muted)]",
  "Needs Review": "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  Attested: "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  Processing: "border-[color:var(--color-info-border)] bg-[color:var(--color-info-bg)] text-[color:var(--color-info-text)]",
  Failed: "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]",
  Ready: "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  "Signed Off": "border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-strong)] text-white",
  Withdrawn: "border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]"
};

export function StatusBadge({ status }: { status: string }) {
  const normalized = (Object.keys(styles) as WorkflowStatus[]).includes(status as WorkflowStatus)
    ? (status as WorkflowStatus)
    : "Draft";
  return (
    <span
      className={`inline-flex min-h-8 min-w-24 items-center justify-center rounded-full border px-3 py-1 text-xs font-semibold ${styles[normalized]}`}
    >
      {status}
    </span>
  );
}
