import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  FileText,
  FolderOpen,
  Home,
  Mic,
  MoreHorizontal,
  ShieldCheck
} from "lucide-react";

type IconTone = "purple" | "teal" | "green" | "orange" | "pink" | "blue";

const toneClasses: Record<IconTone, string> = {
  purple: "bg-[#ede8ff] text-clinical",
  teal: "bg-[#e7fbf8] text-aqua",
  green: "bg-[#e7f8ef] text-moss",
  orange: "bg-[#fff0e6] text-orange-500",
  pink: "bg-[#ffebf8] text-blossom",
  blue: "bg-[#eaf4ff] text-river"
};

export function AppHeader() {
  return (
    <header className="flex items-center justify-between gap-4 pb-6">
      <Link href="/" className="flex items-center gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-[1.1rem] bg-[#efeaff] text-clinical shadow-soft">
          <BarChart3 size={23} aria-hidden="true" />
        </span>
        <span>
          <span className="block text-xl font-bold text-ink">LinguaCare</span>
          <span className="block text-sm text-slate-600">Speech Therapy Suite</span>
        </span>
      </Link>
      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-semibold text-ink">Dr. Sarah Miller</p>
          <p className="text-xs text-slate-600">Speech Therapist</p>
        </div>
        <div className="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-pink-100 to-purple-100 text-sm font-bold text-ink shadow-soft">
          SM
        </div>
      </div>
    </header>
  );
}

export function GlassCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`clinical-card rounded-[1.6rem] ${className}`}>{children}</section>;
}

export function GradientButton({
  children,
  href,
  icon: Icon,
  className = "",
  onClick,
  disabled = false,
  type = "button"
}: {
  children: React.ReactNode;
  href?: string;
  icon?: LucideIcon;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
}) {
  const content = (
    <>
      {Icon ? <Icon size={24} aria-hidden="true" /> : null}
      <span>{children}</span>
    </>
  );
  const classes = `inline-flex min-h-14 items-center justify-center gap-3 rounded-[1.35rem] bg-gradient-to-r from-[#7664ff] via-[#7a52ef] to-[#ef8ad7] px-5 py-4 text-center text-base font-bold text-white shadow-[0_18px_40px_rgba(111,84,246,0.32)] transition hover:-translate-y-0.5 hover:shadow-lift focus:outline-none focus:ring-2 focus:ring-clinical disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-65 ${className}`;
  return href ? (
    <Link href={href} className={classes}>
      {content}
    </Link>
  ) : (
    <button className={classes} onClick={onClick} disabled={disabled} type={type}>{content}</button>
  );
}

export function QuickActionCard({
  icon: Icon,
  title,
  subtitle,
  tone = "purple",
  href,
  onClick
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  tone?: IconTone;
  href?: string;
  onClick?: () => void;
}) {
  const content = (
    <>
      <span className={`mb-3 grid h-12 w-12 place-items-center rounded-2xl ${toneClasses[tone]}`}>
        <Icon size={25} aria-hidden="true" />
      </span>
      <span className="font-bold text-ink">{title}</span>
      <span className="mt-1 text-sm text-slate-600">{subtitle}</span>
    </>
  );
  const classes = "clinical-card flex min-h-32 flex-col items-center justify-center rounded-[1.35rem] p-4 text-center transition hover:-translate-y-0.5 hover:shadow-lift";
  return href ? (
    <Link href={href} className={classes}>
      {content}
    </Link>
  ) : (
    <button className={classes} onClick={onClick} type="button">
      {content}
    </button>
  );
}

export function SessionCard({
  initials,
  name,
  meta,
  time,
  status,
  expanded,
  children
}: {
  initials: string;
  name: string;
  meta: string;
  time: string;
  status: string;
  expanded?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <GlassCard className={`p-4 ${expanded ? "border-clinical/45 shadow-lift" : ""}`}>
      <div className="flex items-center gap-3">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#efe9ff] to-[#fff0fb] font-bold text-clinical">
          {initials}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-bold text-ink">{name}</h3>
          <p className="text-sm text-slate-600">{meta}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold text-ink">{time}</p>
          <span className="mt-1 inline-flex rounded-full bg-[#f0ebff] px-3 py-1 text-xs font-semibold text-clinical">{status}</span>
        </div>
      </div>
      {children ? <div className="mt-4">{children}</div> : null}
    </GlassCard>
  );
}

export function ResultMetricCard({ icon: Icon, value, label, helper, tone = "purple" }: { icon: LucideIcon; value: string; label: string; helper: string; tone?: IconTone }) {
  return (
    <GlassCard className="p-4 text-center">
      <span className={`mx-auto mb-3 grid h-16 w-16 place-items-center rounded-full border border-current/25 ${toneClasses[tone]}`}>
        <Icon size={28} aria-hidden="true" />
      </span>
      <p className="text-3xl font-bold text-ink">{value}</p>
      <h3 className="mt-2 font-bold text-ink">{label}</h3>
      <p className="mt-1 text-sm leading-5 text-slate-600">{helper}</p>
    </GlassCard>
  );
}

export function SafetyNote({ children = "For clinician use only. Not a diagnostic tool." }: { children?: React.ReactNode }) {
  return (
    <p className="flex items-center justify-center gap-2 px-2 py-4 text-center text-xs font-medium text-slate-600">
      <ShieldCheck size={16} aria-hidden="true" className="text-clinical" />
      {children}
    </p>
  );
}

export function BottomNav({ active = "Home" }: { active?: "Home" | "Sessions" | "Cases" | "Reports" | "More" }) {
  const items = [
    { href: "/", label: "Home", icon: Home },
    { href: "/today", label: "Sessions", icon: CalendarDays },
    { href: "/cases", label: "Cases", icon: FolderOpen },
    { href: "/reports", label: "Reports", icon: FileText },
    { href: "/settings", label: "More", icon: MoreHorizontal }
  ] as const;
  return (
    <nav className="mobile-bottom-nav" aria-label="Bottom navigation">
      <div className="clinical-card grid grid-cols-5 rounded-[1.7rem] bg-white/72 px-2 py-2 shadow-[0_18px_55px_rgba(83,65,158,0.22)]">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.label === active;
          return (
            <Link key={item.label} href={item.href} className={`flex flex-col items-center gap-1 rounded-[1.2rem] px-2 py-2 text-xs font-medium ${isActive ? "bg-[#f0ebff] text-clinical" : "text-slate-500"}`}>
              <Icon size={22} aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function ProgressSummaryCard() {
  const rows = [
    { label: "Language", value: 88, color: "bg-orange-500" },
    { label: "Fluency", value: 76, color: "bg-clinical" },
    { label: "Listening", value: 82, color: "bg-moss" },
    { label: "Pronunciation", value: 71, color: "bg-blossom" }
  ];
  return (
    <GlassCard className="p-5">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-ink">Overall Progress</h2>
          <p className="text-sm text-slate-600">Compared to previous 2 weeks</p>
        </div>
        <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-bold text-emerald-700">+18%</span>
      </div>
      <div className="space-y-4">
        {rows.map((row) => (
          <div key={row.label} className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-3">
            <span className="font-semibold text-ink">{row.label}</span>
            <span className="h-2.5 overflow-hidden rounded-full bg-[#ece9f8]">
              <span className={`block h-full rounded-full ${row.color}`} style={{ width: `${row.value}%` }} />
            </span>
            <span className="text-right font-bold text-ink">{row.value}%</span>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

export function SmallListRow({ icon: Icon, title, meta, href }: { icon: LucideIcon; title: string; meta: string; href?: string }) {
  const content = (
    <div className="flex items-center gap-3">
      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[#efeaff] text-clinical">
        <Icon size={21} aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-semibold text-ink">{title}</span>
        <span className="block text-sm text-slate-600">{meta}</span>
      </span>
      <ChevronRight size={20} aria-hidden="true" className="text-slate-400" />
    </div>
  );
  return href ? (
    <Link href={href} className="block rounded-2xl px-3 py-3 transition hover:bg-white/70">
      {content}
    </Link>
  ) : (
    <div className="rounded-2xl px-3 py-3">{content}</div>
  );
}

export function WorkflowStep({ icon: Icon, title, helper, tone = "purple" }: { icon: LucideIcon; title: string; helper: string; tone?: IconTone }) {
  return (
    <div className="flex flex-1 flex-col items-center text-center">
      <span className={`mb-2 grid h-14 w-14 place-items-center rounded-full ${toneClasses[tone]}`}>
        <Icon size={25} aria-hidden="true" />
      </span>
      <p className="text-sm font-bold text-ink">{title}</p>
      <p className="mt-1 text-xs text-slate-600">{helper}</p>
    </div>
  );
}

export function PrimaryActionRow() {
  return (
    <div className="grid grid-cols-3 gap-3">
      <GradientButton href="/record" icon={Mic} className="col-span-3 min-h-20 text-xl sm:col-span-2">
        Start Recording
      </GradientButton>
      <Link href="/today" className="clinical-card flex items-center justify-center rounded-[1.35rem] px-4 py-4 text-center font-bold text-clinical">
        Today
      </Link>
    </div>
  );
}
