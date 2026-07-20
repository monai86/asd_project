import type { LucideIcon } from "lucide-react";
import { Activity } from "lucide-react";

type StatTone = "neutral" | "accent" | "success" | "warning";

const toneClasses: Record<StatTone, string> = {
  neutral: "bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-strong)]",
  accent: "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]",
  success: "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  warning: "bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]"
};

export function StatCard({
  label,
  value,
  helper,
  icon: Icon = Activity,
  tone = "neutral"
}: {
  label: string;
  value: string;
  helper?: string;
  icon?: LucideIcon;
  tone?: StatTone;
}) {
  return (
    <section className="workspace-panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[color:var(--color-text-muted)]">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-[color:var(--color-text-strong)]">{value}</p>
        </div>
        <span className={`inline-flex min-h-8 items-center rounded-[var(--radius-card)] px-2 ${toneClasses[tone]}`}>
          <Icon size={20} aria-hidden="true" />
        </span>
      </div>
      {helper ? <p className="mt-3 text-sm leading-6 text-[color:var(--color-text-muted)]">{helper}</p> : null}
    </section>
  );
}
