import Link from "next/link";
import { ChevronRight } from "lucide-react";

export type BreadcrumbItem = { label: string; href?: string };

/**
 * Quiet, tokenized breadcrumb trail for deep flows (e.g. Cases → case →
 * session step). The current step is plain text; ancestors link back.
 */
export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="-mt-1 mb-4 flex items-center gap-1.5 overflow-x-auto text-sm"
    >
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`} className="flex min-w-0 items-center gap-1.5">
            {index > 0 ? (
              <ChevronRight
                aria-hidden="true"
                className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-subtle)]"
              />
            ) : null}
            {item.href && !isLast ? (
              <Link
                href={item.href}
                className="shrink-0 font-medium text-[color:var(--color-text-muted)] transition hover:text-[color:var(--color-accent-strong)]"
              >
                {item.label}
              </Link>
            ) : (
              <span
                className={
                  isLast
                    ? "shrink-0 font-semibold text-[color:var(--color-text-strong)]"
                    : "shrink-0 text-[color:var(--color-text-muted)]"
                }
                aria-current={isLast ? "page" : undefined}
              >
                {item.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
