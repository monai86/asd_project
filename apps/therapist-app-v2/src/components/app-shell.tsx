import Image from "next/image";
import Link from "next/link";
import {
  BarChart3,
  Bell,
  CalendarDays,
  ChevronDown,
  FileText,
  FolderOpen,
  Home,
  MoreHorizontal,
  Search,
  Settings,
  Sparkles,
  SquareActivity
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { AppHeader, BottomNav } from "@/components/liquid-ui";

type AppShellActive = "Home" | "Sessions" | "Cases" | "Reports" | "More";

const desktopNav = [
  { href: "/", label: "Dashboard", active: "Home", icon: Home },
  { href: "/cases", label: "Cases", active: "Cases", icon: FolderOpen },
  { href: "/today", label: "Sessions", active: "Sessions", icon: CalendarDays },
  { href: "/review-transcript", label: "Transcript Review", active: "Sessions", icon: FileText },
  { href: "/results", label: "Session Results", active: "Sessions", icon: Sparkles },
  { href: "/report-summary", label: "Reports", active: "Reports", icon: BarChart3 },
  { href: "/settings", label: "Settings", active: "More", icon: Settings }
] satisfies Array<{ href: string; label: string; active: AppShellActive; icon: LucideIcon }>;

export function AppShell({ children, active = "Home" }: { children: React.ReactNode; active?: AppShellActive }) {
  return (
    <div className="min-h-screen px-4 pb-[calc(8.5rem+env(safe-area-inset-bottom))] pt-5 sm:px-6 lg:flex lg:px-0 lg:pb-0 lg:pt-0">
      <DesktopSidebar active={active} />
      <main className="mx-auto w-full max-w-[1180px] lg:ml-72 lg:max-w-none">
        <div className="lg:hidden">
          <AppHeader />
        </div>
        <DesktopTopbar />
        <div className="mx-auto max-w-[430px] lg:mx-0 lg:max-w-none lg:px-10 lg:py-7 xl:px-14">
          {children}
        </div>
      </main>
      <BottomNav active={active} />
    </div>
  );
}

function DesktopSidebar({ active }: { active: AppShellActive }) {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-white/70 bg-white/58 px-5 py-7 shadow-[18px_0_55px_rgba(96,93,150,0.08)] backdrop-blur-2xl lg:flex lg:flex-col">
      <Link href="/" className="mb-9 flex items-center gap-3">
        <span className="grid h-14 w-14 place-items-center rounded-[1.25rem] bg-[#efeaff] text-clinical shadow-soft">
          <SquareActivity size={27} aria-hidden="true" />
        </span>
        <span>
          <span className="block text-xl font-bold text-ink">LinguaCare</span>
          <span className="block text-sm text-slate-600">Speech Therapy Suite</span>
        </span>
      </Link>

      <nav className="space-y-2" aria-label="Desktop navigation">
        {desktopNav.map((item) => {
          const Icon = item.icon;
          const isActive = item.active === active;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={`flex min-h-12 items-center gap-3 rounded-2xl px-4 text-[15px] font-semibold transition ${
                isActive ? "bg-[#edeaff] text-clinical shadow-soft" : "text-ink/80 hover:bg-white/70 hover:text-clinical"
              }`}
            >
              <Icon size={20} aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-[1.45rem] border border-white/70 bg-gradient-to-br from-white/78 via-[#f4efff]/76 to-[#e9fbff]/76 p-5 shadow-soft">
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-[#efeaff] text-clinical">
          <Sparkles size={22} aria-hidden="true" />
        </div>
        <p className="font-bold text-ink">AI is here to help</p>
        <p className="mt-2 text-sm leading-5 text-slate-600">Decision-support only. You&apos;re always in control.</p>
        <Link href="/settings" className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-clinical">
          Learn more
          <MoreHorizontal size={18} aria-hidden="true" />
        </Link>
      </div>
    </aside>
  );
}

function DesktopTopbar() {
  return (
    <header className="sticky top-0 z-10 hidden h-[5.35rem] items-center justify-between border-b border-white/60 bg-white/42 px-10 backdrop-blur-2xl lg:flex xl:px-14">
      <label className="flex h-12 w-[36rem] max-w-[44vw] items-center gap-3 rounded-2xl border border-line/70 bg-white/72 px-4 text-sm text-slate-500 shadow-soft">
        <Search size={19} aria-hidden="true" />
        <span className="sr-only">Search</span>
        <input className="w-full bg-transparent text-ink outline-none placeholder:text-slate-500" placeholder="Search cases, sessions, transcripts..." />
        <span className="rounded-xl bg-[#f7f5ff] px-2 py-1 text-xs font-semibold text-slate-500">⌘ K</span>
      </label>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <CalendarDays size={18} aria-hidden="true" />
          Today, Jun 14, 2026
        </div>
        <div className="relative grid h-11 w-11 place-items-center rounded-full border border-line/70 bg-white/70 text-ink shadow-soft" aria-label="3 demo notifications">
          <Bell size={19} aria-hidden="true" />
          <span className="absolute right-1 top-1 grid h-5 min-w-5 place-items-center rounded-full bg-blossom px-1 text-[11px] font-bold text-white">3</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-pink-100 to-purple-100 text-sm font-bold text-ink shadow-soft">
            SM
          </div>
          <div>
            <p className="text-sm font-bold text-ink">Dr. Sarah Miller</p>
            <p className="text-xs text-slate-600">Speech Therapist</p>
          </div>
          <ChevronDown size={18} aria-hidden="true" className="text-slate-600" />
        </div>
      </div>
    </header>
  );
}

export function WorkflowVisual() {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-white shadow-soft">
      <Image src="/clinical-workflow.svg" width={960} height={320} alt="Case to transcript review to signed report workflow" priority />
    </div>
  );
}
