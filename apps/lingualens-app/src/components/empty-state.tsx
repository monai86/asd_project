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
    <section className="reading-surface px-5 py-8 text-center">
      <Icon size={28} aria-hidden="true" className="mx-auto text-[color:var(--color-accent)]" />
      <h2 className="mt-4 text-xl font-semibold text-[color:var(--color-text-strong)]">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[color:var(--color-text-muted)]">{description}</p>
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </section>
  );
}
