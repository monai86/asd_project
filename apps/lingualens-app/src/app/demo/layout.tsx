import { notFound } from "next/navigation";

import { DemoShell } from "@/components/demo-shell";
import { isDemoEnabled } from "@/services/adapters/demo-mode";

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  if (!isDemoEnabled()) {
    notFound();
  }

  return (
    <div className="min-h-dvh bg-[color:var(--color-page-bg)]">
      <div
        role="status"
        className="sticky top-0 z-50 border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-sm font-semibold text-amber-950"
      >
        Sample data demonstration — no clinical record or workflow action is real.
      </div>
      <DemoShell>{children}</DemoShell>
    </div>
  );
}
