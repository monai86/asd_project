import Link from "next/link";
import { CalendarDays, FileText, FolderOpen, LayoutGrid, Settings2 } from "lucide-react";

import type { ShellActive } from "@/components/sidebar";

const items = [
  { href: "/", label: "Home", active: "Home", icon: LayoutGrid },
  { href: "/today", label: "Today", active: "Sessions", icon: CalendarDays },
  { href: "/cases", label: "Cases", active: "Cases", icon: FolderOpen },
  { href: "/reports", label: "Reports", active: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", active: "More", icon: Settings2 }
] as const;

export function BottomNav({ active }: { active: ShellActive }) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Bottom navigation">
      <div className="grid grid-cols-5 rounded-[1.75rem] border border-[color:var(--color-border)] bg-[color:rgba(255,255,255,0.92)] p-2 shadow-lift backdrop-blur-xl">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.active === active;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-11 flex-col items-center justify-center gap-1 rounded-[1.15rem] px-2 py-1 text-[11px] font-medium transition duration-200 ease-out motion-reduce:transition-none ${
                isActive
                  ? "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
                  : "text-[color:var(--color-text-subtle)]"
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
