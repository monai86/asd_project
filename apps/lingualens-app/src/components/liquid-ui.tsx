import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Mic,
  ShieldCheck
} from "lucide-react";

type IconTone = "purple" | "teal" | "green" | "orange" | "pink" | "blue";

const toneClasses: Record<IconTone, string> = {
  purple: "text-[color:var(--color-accent)]",
  teal: "text-[color:var(--color-accent)]",
  green: "text-[color:var(--color-success-text)]",
  orange: "text-[color:var(--color-warning-text)]",
  pink: "text-[color:var(--color-danger-text)]",
  blue: "text-[color:var(--color-info-text)]"
};

export function AppHeader() {
  return (
    <header className="flex items-center justify-between gap-4 pb-6">
      <Link href="/today" className="flex items-center gap-3">
        <span className="text-[color:var(--color-accent)]">
          <BarChart3 size={24} aria-hidden="true" />
        </span>
        <span>
          <span className="block text-xl font-bold text-ink">lingualens</span>
          <span className="block text-sm text-slate-600">Speech Therapy Suite</span>
        </span>
      </Link>
      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-semibold text-ink">Dr. Sarah Miller</p>
          <p className="text-xs text-slate-600">Speech Therapist</p>
        </div>
        <div className="grid h-10 w-10 place-items-center rounded-full bg-slate-100 text-sm font-bold text-ink border border-slate-200">
          SM
        </div>
      </div>
    </header>
  );
}

export function GlassCard({
  children,
  className = "",
  ...props
}: {
  children: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLElement>) {
  return <section className={`workspace-panel ${className}`} {...props}>{children}</section>;
}

export function GradientButton({
  children,
  href,
  icon: Icon,
  className = "",
  onClick,
  disabled = false,
  type = "button",
  ...props
}: {
  children: React.ReactNode;
  href?: string;
  icon?: LucideIcon;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
} & React.ButtonHTMLAttributes<HTMLButtonElement> & React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const content = (
    <>
      {Icon ? <Icon size={20} aria-hidden="true" /> : null}
      <span>{children}</span>
    </>
  );
  const classes = `inline-flex min-h-11 items-center justify-center gap-2.5 rounded-[var(--radius-card)] bg-[color:var(--color-accent)] hover:bg-[color:var(--color-accent-strong)] px-5 py-3.5 text-center text-sm font-semibold text-white transition-all duration-200 ease-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-clinical disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 ${className}`;
  return href ? (
    <Link href={href} className={classes} {...props}>
      {content}
    </Link>
  ) : (
    <button className={classes} onClick={onClick} disabled={disabled} type={type} {...props}>{content}</button>
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
      <span className={`mb-2 flex h-10 w-10 items-center justify-center ${toneClasses[tone]}`}>
        <Icon size={24} aria-hidden="true" />
      </span>
      <span className="font-semibold text-ink text-sm">{title}</span>
      <span className="mt-1 text-xs text-slate-500">{subtitle}</span>
    </>
  );
  const classes = "workspace-panel flex min-h-28 flex-col items-center justify-center p-4 text-center transition duration-200 hover:border-[color:var(--color-accent)]";
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
    <GlassCard className={`p-4 ${expanded ? "border-clinical" : ""}`}>
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[var(--radius-card)] bg-[color:var(--color-accent-soft)] border border-[color:var(--color-border)] font-semibold text-clinical text-sm">
          {initials}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-ink text-sm">{name}</h3>
          <p className="text-xs text-slate-500">{meta}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold text-ink text-sm">{time}</p>
          <span className="mt-1 inline-flex rounded-[var(--radius-card)] bg-[color:var(--color-accent-soft)] px-2.5 py-0.5 text-xs font-medium text-clinical">{status}</span>
        </div>
      </div>
      {children ? <div className="mt-4">{children}</div> : null}
    </GlassCard>
  );
}

export function ResultMetricCard({ icon: Icon, value, label, helper, tone = "purple" }: { icon: LucideIcon; value: string; label: string; helper: string; tone?: IconTone }) {
  return (
    <GlassCard className="p-4 text-center">
      <Icon size={24} aria-hidden="true" className={`mx-auto mb-2 ${toneClasses[tone]}`} />
      <p className="text-2xl font-bold text-ink">{value}</p>
      <h3 className="mt-1 font-semibold text-ink text-sm">{label}</h3>
      <p className="mt-0.5 text-xs leading-5 text-slate-500">{helper}</p>
    </GlassCard>
  );
}

export function SafetyNote({ children = "For clinician use only. Not a diagnostic tool." }: { children?: React.ReactNode }) {
  return (
    <p className="flex items-center justify-center gap-2 px-2 py-3 text-center text-xs font-medium text-slate-500">
      <ShieldCheck size={16} aria-hidden="true" className="text-clinical" />
      {children}
    </p>
  );
}

export function ProgressSummaryCard() {
  const rows = [
    { label: "Language", value: 88, color: "bg-[color:var(--color-accent-subtle)]" },
    { label: "Fluency", value: 76, color: "bg-clinical" },
    { label: "Listening", value: 82, color: "bg-moss" },
    { label: "Pronunciation", value: 71, color: "bg-[color:var(--color-danger-text)]" }
  ];
  return (
    <GlassCard className="p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">Overall Progress</h2>
          <p className="text-xs text-slate-500">Compared to previous 2 weeks</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">+18%</span>
      </div>
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.label} className="grid grid-cols-[6rem_1fr_2.5rem] items-center gap-3 text-sm">
            <span className="font-medium text-ink">{row.label}</span>
            <span className="h-2 overflow-hidden rounded-full bg-slate-100">
              <span className={`block h-full rounded-full ${row.color}`} style={{ width: `${row.value}%` }} />
            </span>
            <span className="text-right font-semibold text-ink">{row.value}%</span>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

export function SmallListRow({ icon: Icon, title, meta, href }: { icon: LucideIcon; title: string; meta: string; href?: string }) {
  const content = (
    <div className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center text-clinical">
        <Icon size={20} aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-semibold text-ink text-sm">{title}</span>
        <span className="block text-xs text-slate-500">{meta}</span>
      </span>
      <ChevronRight size={18} aria-hidden="true" className="text-slate-400" />
    </div>
  );
  return href ? (
    <Link href={href} className="block rounded-[var(--radius-card)] px-3 py-2.5 transition hover:bg-slate-50">
      {content}
    </Link>
  ) : (
    <div className="rounded-[var(--radius-card)] px-3 py-2.5">{content}</div>
  );
}

export function WorkflowStep({ icon: Icon, title, helper, tone = "purple" }: { icon: LucideIcon; title: string; helper: string; tone?: IconTone }) {
  return (
    <div className="flex flex-1 flex-col items-center text-center">
      <span className={`mb-2 flex h-10 w-10 items-center justify-center ${toneClasses[tone]}`}>
        <Icon size={22} aria-hidden="true" />
      </span>
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="mt-0.5 text-xs text-slate-500">{helper}</p>
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
