import Link from "next/link";

import type { ShellActive } from "@/components/sidebar";
import { getWorkbenchNavigation } from "@/services/navigation/workbench-navigation";

export function BottomNav({
  active,
  activeSessionId,
  activeCaseId,
}: {
  active: ShellActive;
  activeSessionId?: string;
  activeCaseId?: string;
}) {
  const items = getWorkbenchNavigation(activeSessionId, activeCaseId, { forBottomNav: true });
  return (
    <nav className="mobile-bottom-nav" aria-label="Bottom navigation">
      <div className="grid grid-cols-5 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-1.5">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.active === active;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-11 flex-col items-center justify-center gap-1 rounded-[var(--radius-card)] px-2 py-1 text-xs font-medium transition duration-200 ease-out motion-reduce:transition-none ${
                isActive
                  ? "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
                  : "text-[color:var(--color-text-subtle)] hover:text-[color:var(--color-text-strong)]"
              }`}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
