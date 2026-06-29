import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

export function EmptyState({
  title,
  description,
  action,
  icon: Icon = Inbox
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <section className="rounded-[var(--radius-panel)] border border-dashed border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-5 py-8 text-center shadow-soft">
      <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]">
        <Icon size={24} aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-xl font-semibold text-[color:var(--color-text-strong)]">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[color:var(--color-text-muted)]">{description}</p>
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </section>
  );
}
