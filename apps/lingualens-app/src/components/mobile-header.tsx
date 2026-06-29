import Link from "next/link";
import { Menu, SquareActivity } from "lucide-react";
import { ActiveOrganizationSummary } from "@/components/active-organization-summary";

export function MobileHeader({ title = "lingualens" }: { title?: string }) {
  return (
    <header className="grid gap-3 pb-5 lg:hidden">
      <div className="flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-[1.1rem] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)] shadow-soft">
            <SquareActivity size={21} aria-hidden="true" />
          </span>
          <div>
            <p className="text-base font-semibold tracking-[-0.02em] text-[color:var(--color-text-strong)]">{title}</p>
            <p className="text-xs text-[color:var(--color-text-muted)]">Therapist Workspace</p>
          </div>
        </Link>

        <button
          type="button"
          className="grid h-11 w-11 place-items-center rounded-full border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)] shadow-soft"
          aria-label="Open navigation"
        >
          <Menu size={18} aria-hidden="true" />
        </button>
      </div>
      <ActiveOrganizationSummary />
    </header>
  );
}
