export type WorkflowStatus =
  | "Draft"
  | "Needs Review"
  | "Attested"
  | "Processing"
  | "Failed"
  | "Ready"
  | "Signed Off"
  | "Withdrawn"
  | "Awaiting Consent"
  | "Ready for Audio"
  | "Recording"
  | "Uploading"
  | "Transcribing"
  | "CHA Generating"
  | "ML Pending"
  | "Review Required"
  | "Report Ready";

const styles: Record<WorkflowStatus, string> = {
  Draft: "border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-muted)]",
  "Needs Review": "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  Attested: "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  Processing: "border-[color:var(--color-info-border)] bg-[color:var(--color-info-bg)] text-[color:var(--color-info-text)]",
  Failed: "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]",
  Ready: "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  "Signed Off": "border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-strong)] text-white",
  Withdrawn: "border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]",
  "Awaiting Consent": "border-orange-200 bg-orange-50 text-orange-800",
  "Ready for Audio": "border-blue-200 bg-blue-50 text-blue-800",
  "Recording": "border-red-200 bg-red-50 text-red-800 animate-pulse",
  "Uploading": "border-blue-200 bg-blue-50 text-blue-800 animate-pulse",
  "Transcribing": "border-indigo-200 bg-indigo-50 text-indigo-800",
  "CHA Generating": "border-purple-200 bg-purple-50 text-purple-800",
  "ML Pending": "border-amber-200 bg-amber-50 text-amber-800",
  "Review Required": "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  "Report Ready": "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
};

export function StatusBadge({ status }: { status: string }) {
  const isDirectMatch = (Object.keys(styles) as WorkflowStatus[]).includes(status as WorkflowStatus);

  const getNormalizedStatus = (s: string): WorkflowStatus => {
    if (isDirectMatch) return s as WorkflowStatus;

    const canonicalize = (val: string) =>
      val.toLowerCase().replace(/[_-]/g, " ").replace(/\s+/g, " ").trim();

    const canonicalInput = canonicalize(s);
    const matched = (Object.keys(styles) as WorkflowStatus[]).find(
      (key) => canonicalize(key) === canonicalInput
    );
    return matched || "Draft";
  };

  const matchedStatus = getNormalizedStatus(status);
  const displayText =
    matchedStatus === "Draft" && !isDirectMatch && status !== "Draft"
      ? status
      : matchedStatus;

  return (
    <span
      className={`inline-flex min-h-8 min-w-24 items-center justify-center rounded-full border px-3 py-1 text-xs font-semibold ${styles[matchedStatus]}`}
    >
      {displayText}
    </span>
  );
}

