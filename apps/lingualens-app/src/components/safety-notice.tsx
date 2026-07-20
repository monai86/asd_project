import { ShieldCheck } from "lucide-react";

export function SafetyNotice({
  children = "Decision-support only. Not diagnostic. Therapist review required before clinical use.",
  className = ""
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <aside
      className={`rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-sm text-[color:var(--color-text-muted)] ${className}`}
    >
      <div className="flex items-start gap-3">
        <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-[color:var(--color-accent)]" />
        <p className="leading-6">{children}</p>
      </div>
    </aside>
  );
}
