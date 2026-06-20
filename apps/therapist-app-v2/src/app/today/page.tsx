import type { LucideIcon } from "lucide-react";
import { Building2, Mic, NotebookPen, Play, Target } from "lucide-react";
import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { GlassCard, GradientButton, SafetyNote, SessionCard } from "@/components/liquid-ui";

const dates = [
  ["Sun", "May 11"],
  ["Mon", "May 12"],
  ["Tue", "May 13"],
  ["Wed", "May 14"],
  ["Thu", "May 15"]
];

export default function TodayPage() {
  return (
    <AppShell active="Sessions">
      <div className="grid gap-6 lg:grid-cols-[430px_1fr]">
        <div className="space-y-5">
          <header>
            <h1 className="text-3xl font-bold text-ink">Today&apos;s Sessions</h1>
            <p className="mt-2 text-slate-600">Manage and view today&apos;s appointments.</p>
          </header>

          <GlassCard className="grid grid-cols-5 overflow-hidden p-2">
            {dates.map(([day, date], index) => (
              <div key={date} className={`rounded-[1.15rem] px-2 py-3 text-center text-sm ${index === 2 ? "bg-gradient-to-br from-[#7664ff] to-[#8c6df8] font-bold text-white shadow-soft" : "text-slate-600"}`}>
                <span className="block">{day}</span>
                <span className="mt-1 block">{date}</span>
              </div>
            ))}
          </GlassCard>

          <div className="space-y-4">
            <SessionCard initials="AM" name="Ava M." meta="4y 8m · Language" time="10:30 AM" status="Confirmed" />
            <SessionCard initials="EL" name="Ethan L." meta="5y 2m · Articulation" time="1:00 PM" status="In Progress" expanded>
              <GlassCard className="space-y-4 bg-white/50 p-4 shadow-none">
                <InfoLine icon={Building2} label="Room" value="Room 2" />
                <InfoLine icon={Target} label="Goal" value="Produce /s/ in all word positions" />
                <InfoLine icon={NotebookPen} label="Caregiver Note" value="Working on sounds at home daily. He has been more confident this week." />
                <div className="grid grid-cols-3 gap-3 border-t border-line/70 pt-4">
                  <GradientButton href="/record" icon={Play} className="min-h-20 rounded-[1.1rem] px-2 text-sm">
                    Start Session
                  </GradientButton>
                  <Link href="/record" className="clinical-card flex min-h-20 flex-col items-center justify-center gap-2 rounded-[1.1rem] text-sm font-bold text-clinical">
                    <Mic size={24} aria-hidden="true" />
                    Record
                  </Link>
                  <Link href="/record?mode=paste" className="clinical-card flex min-h-20 flex-col items-center justify-center gap-2 rounded-[1.1rem] text-sm font-bold text-clinical">
                    <NotebookPen size={24} aria-hidden="true" />
                    Add Note
                  </Link>
                </div>
              </GlassCard>
            </SessionCard>
            <SessionCard initials="JW" name="Jacob W." meta="7y 1m · Fluency" time="3:30 PM" status="Needs attention" />
          </div>
          <SafetyNote />
        </div>
        <GlassCard className="hidden p-6 lg:block">
          <h2 className="text-xl font-bold text-ink">Therapist flow</h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">
            Today stays intentionally small: pick a session, record, add a note, and move forward to review. Additional case details remain off the mobile home screen.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <SessionCard initials="AM" name="Ava M." meta="Language sample" time="10:30" status="Confirmed" />
            <SessionCard initials="EL" name="Ethan L." meta="Articulation therapy" time="1:00" status="In Progress" />
            <SessionCard initials="JW" name="Jacob W." meta="Fluency support" time="3:30" status="Needs attention" />
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
}

function InfoLine({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f1edff] text-clinical">
        <Icon size={18} aria-hidden="true" />
      </span>
      <div>
        <p className="text-sm text-slate-500">{label}</p>
        <p className="font-semibold leading-6 text-ink">{value}</p>
      </div>
    </div>
  );
}
