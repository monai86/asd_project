/** Shared loading-skeleton primitives. Use these instead of spinner-only or
 *  bare-text loading states so the page reads as stable while content loads.
 *  All blocks pulse with reduced-motion disabled. */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)] motion-reduce:animate-none ${className}`}
    />
  );
}

/** A single text-line-shaped skeleton of the given width. */
export function SkeletonLine({ className = "" }: { className?: string }) {
  return <Skeleton className={`h-4 ${className}`} />;
}

/** A labeled loading panel: one title line plus several body lines. */
export function SkeletonPanel({
  lines = 3,
  className = "",
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-4 ${className}`} role="status" aria-live="polite">
      <span className="sr-only">Loading…</span>
      <Skeleton className="h-6 w-2/5" />
      {Array.from({ length: lines }, (_, index) => (
        <SkeletonLine
          key={index}
          className={index === lines - 1 ? "w-3/5" : "w-full"}
        />
      ))}
    </div>
  );
}
