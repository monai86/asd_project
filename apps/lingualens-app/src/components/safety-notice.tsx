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
        <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]">
          <ShieldCheck size={18} aria-hidden="true" />
        </span>
        <p className="leading-6">{children}</p>
      </div>
    </aside>
  );
}
