export function RightRail({
  title,
  description,
  children
}: {
  title?: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <aside className="hidden w-full max-w-[22rem] space-y-4 xl:block">
      <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
        {title ? <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">{title}</h2> : null}
        {description ? <p className={`${title ? "mt-2" : ""} text-sm leading-6 text-[color:var(--color-text-muted)]`}>{description}</p> : null}
        <div className={`${title || description ? "mt-4" : ""} space-y-4`}>{children}</div>
      </section>
    </aside>
  );
}
