import { CheckCircle2, ClipboardPaste, FileText, Mic, ShieldCheck, Sparkles, UploadCloud } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { GlassCard, GradientButton, QuickActionCard, SafetyNote, SmallListRow } from "@/components/liquid-ui";

export default function Home() {
  return <QuickStartHome />;
}

function QuickStartHome() {
  return (
    <AppShell active="Home">
      <div className="grid gap-5 lg:grid-cols-[minmax(360px,0.9fr)_minmax(420px,1.45fr)_320px] lg:items-start 2xl:grid-cols-[430px_minmax(520px,1fr)_360px]">
        <div className="space-y-5">
          <GlassCard className="overflow-hidden p-5 lg:p-7">
            <div className="mb-5">
              <div className="mb-3 flex items-center gap-2 text-clinical">
                <Sparkles size={27} aria-hidden="true" />
                <h1 className="text-2xl font-bold text-ink lg:text-3xl">Quick Start</h1>
              </div>
              <p className="text-sm text-slate-600 lg:text-base">Start a new session in one tap.</p>
            </div>
            <GradientButton href="/record" icon={Mic} className="min-h-24 w-full text-2xl lg:min-h-28">
              Start Recording
            </GradientButton>
            <p className="mt-5 text-center text-sm text-slate-600 lg:text-base">Tap to record and prepare this session for review.</p>
          </GlassCard>

          <div className="grid grid-cols-3 gap-3 lg:gap-4">
            <QuickActionCard icon={UploadCloud} title="Upload audio" subtitle="Experimental" tone="purple" href="/record?mode=audio" />
            <QuickActionCard icon={FileText} title="Upload .cha" subtitle="Transcript file" tone="pink" href="/record?mode=cha" />
            <QuickActionCard icon={ClipboardPaste} title="Paste transcript" subtitle="From clipboard" tone="teal" href="/record?mode=paste" />
          </div>
        </div>

        <div className="space-y-5 lg:pt-1">
          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-ink lg:text-xl">Today</h2>
              <a href="/today" className="text-sm font-semibold text-clinical">View all</a>
            </div>
            <GlassCard className="divide-y divide-line/70 p-2 lg:p-3">
              <SmallListRow icon={Mic} title="Ava M." meta="10:30 AM · Language · Session today" href="/today" />
              <SmallListRow icon={Mic} title="Jacob W." meta="1:00 PM · Fluency · Needs attention" href="/today" />
              <div className="hidden lg:block">
                <SmallListRow icon={Mic} title="Sophia L." meta="3:30 PM · Social communication · Confirmed" href="/today" />
              </div>
            </GlassCard>
          </section>

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-ink lg:text-xl">Recent results</h2>
              <a href="/report-summary" className="text-sm font-semibold text-clinical">View all</a>
            </div>
            <GlassCard className="divide-y divide-line/70 p-2 lg:p-3">
              <SmallListRow icon={FileText} title="Ethan L." meta="Transcript review · 92% complete · 2:28" href="/review-transcript" />
              <SmallListRow icon={FileText} title="Ava M." meta="Feature summary ready · therapist review needed" href="/results" />
              <div className="hidden lg:block">
                <SmallListRow icon={FileText} title="Jacob W." meta="Report draft ready · therapist review required" href="/report-summary" />
              </div>
            </GlassCard>
          </section>
        </div>

        <aside className="hidden space-y-5 lg:block">
          <GlassCard className="p-5">
            <h2 className="font-bold text-ink">Session readiness</h2>
            <div className="mt-4 grid gap-3">
              <ReadinessRow icon={CheckCircle2} label="Consent checked" value="Ready" />
              <ReadinessRow icon={FileText} label="Transcript review" value="Required" />
              <ReadinessRow icon={ShieldCheck} label="Report finalization" value="Therapist only" />
            </div>
          </GlassCard>
          <GlassCard className="bg-gradient-to-br from-[#7b61ff] to-[#d474d1] p-5 text-white">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-white/20">
              <Sparkles size={22} aria-hidden="true" />
            </div>
            <h2 className="mt-4 font-bold">Decision-support only</h2>
            <p className="mt-2 text-sm leading-6 text-white/82">Use generated summaries as review aids. Therapist judgment and final edits remain required.</p>
          </GlassCard>
        </aside>
      </div>
      <SafetyNote />
    </AppShell>
  );
}

function ReadinessRow({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line/70 bg-white/58 p-3">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#efeaff] text-clinical">
        <Icon size={19} aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-ink">{label}</span>
        <span className="block text-xs text-slate-600">{value}</span>
      </span>
    </div>
  );
}
