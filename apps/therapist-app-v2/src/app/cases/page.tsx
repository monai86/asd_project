import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowRight, CalendarDays, FolderOpen, ShieldCheck } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { GlassCard, SafetyNote } from "@/components/liquid-ui";
import { cases } from "@/lib/mock-data";

export default function CasesPage() {
  return (
    <AppShell active="Cases">
      <div className="mx-auto max-w-3xl space-y-5">
        <header>
          <h1 className="text-3xl font-bold text-ink">Cases</h1>
          <p className="mt-2 text-slate-600">Open a child record only when you need session context or consent status.</p>
        </header>
        <div className="space-y-4">
          {cases.map((row) => (
            <Link key={row.id} href={`/cases/${row.id}`}>
              <GlassCard className="p-4 transition hover:-translate-y-0.5 hover:shadow-lift">
                <div className="flex items-center gap-3">
                  <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-[#efeaff] font-bold text-clinical">
                    {row.childCode.slice(-2)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h2 className="font-bold text-ink">{row.nickname}</h2>
                    <p className="text-sm text-slate-600">{row.childCode} · {row.age} · {row.language}</p>
                  </div>
                  <ArrowRight size={20} aria-hidden="true" className="text-slate-400" />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                  <MiniStatus icon={ShieldCheck} label="Consent" value={row.consentStatus} />
                  <MiniStatus icon={CalendarDays} label="Latest" value={row.latestSessionDate} />
                  <MiniStatus icon={FolderOpen} label="Next" value={row.latestSessionStatus} />
                </div>
              </GlassCard>
            </Link>
          ))}
        </div>
        <SafetyNote>Use case details for context. Session support still requires therapist review.</SafetyNote>
      </div>
    </AppShell>
  );
}

function MiniStatus({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white/55 p-3">
      <Icon className="mx-auto mb-1 text-clinical" size={18} aria-hidden="true" />
      <p className="text-slate-500">{label}</p>
      <p className="mt-1 truncate font-semibold text-ink">{value}</p>
    </div>
  );
}
