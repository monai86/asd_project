import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
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

export function WorkspacePanel({
  children,
  className = "",
  ...props
}: {
  children: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLElement>) {
  return <section className={`workspace-panel ${className}`} {...props}>{children}</section>;
}

export function PrimaryActionButton({
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
  const classes = `inline-flex min-h-11 items-center justify-center gap-2.5 rounded-[var(--radius-card)] bg-[color:var(--color-accent)] hover:bg-[color:var(--color-accent-strong)] px-5 py-3.5 text-center text-sm font-semibold text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-clinical disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 ${className}`;
  return href ? (
    <Link href={href} className={classes} {...props}>
      {content}
    </Link>
  ) : (
    <button className={classes} onClick={onClick} disabled={disabled} type={type} {...props}>{content}</button>
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
