import Link from "next/link";
import { isValidElement } from "react";
import type { LucideIcon } from "lucide-react";

type ActionButtonTone = "primary" | "secondary" | "ghost" | "destructive";
type ActionButtonSize = "md" | "lg";

const toneClasses: Record<ActionButtonTone, string> = {
  primary:
    "border border-transparent bg-[linear-gradient(135deg,var(--color-accent),var(--color-accent-strong))] text-white shadow-soft hover:shadow-lift",
  secondary:
    "border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)] shadow-soft hover:border-[color:var(--color-accent-subtle)] hover:bg-white",
  ghost:
    "border border-transparent bg-transparent text-[color:var(--color-text-strong)] hover:bg-[color:var(--color-surface-muted)]",
  destructive:
    "border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)] hover:border-[color:var(--color-danger-text)]"
};

const sizeClasses: Record<ActionButtonSize, string> = {
  md: "min-h-11 px-4 py-2.5 text-sm",
  lg: "min-h-14 px-5 py-3.5 text-base"
};

type BaseProps = {
  children: React.ReactNode;
  icon?: LucideIcon | React.ReactNode;
  tone?: ActionButtonTone;
  size?: ActionButtonSize;
  className?: string;
};

type ButtonProps = BaseProps & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  href?: undefined;
};

type LinkProps = BaseProps & Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "children"> & {
  href: string;
  disabled?: boolean;
};

export function ActionButton(props: ButtonProps): JSX.Element;
export function ActionButton(props: LinkProps): JSX.Element;
export function ActionButton(props: ButtonProps | LinkProps) {
  const {
    children,
    icon,
    tone = "primary",
    size = "md",
    className = ""
  } = props;
  const classes = [
    "inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius-pill)] font-semibold transition duration-200 ease-out focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none sm:w-auto",
    "active:scale-[0.99] motion-reduce:active:scale-100",
    toneClasses[tone],
    sizeClasses[size],
    props.disabled ? "cursor-not-allowed opacity-60 shadow-none" : "",
    className
  ].filter(Boolean).join(" ");

  const renderedIcon = renderIcon(icon);
  const content = (
    <>
      {renderedIcon}
      <span>{children}</span>
    </>
  );

  if ("href" in props && props.href) {
    const { children: _children, className: _className, disabled, href, icon: _icon, size: _size, tone: _tone, ...linkProps } = props;
    return (
      <Link
        href={href}
        className={classes}
        aria-disabled={disabled ? "true" : undefined}
        tabIndex={disabled ? -1 : undefined}
        {...linkProps}
      >
        {content}
      </Link>
    );
  }

  const { children: _children, className: _className, disabled, icon: _icon, size: _size, tone: _tone, ...buttonProps } = props as ButtonProps;
  return (
    <button className={classes} disabled={disabled} {...buttonProps}>
      {content}
    </button>
  );
}

function renderIcon(icon: LucideIcon | React.ReactNode | undefined) {
  if (!icon) return null;
  if (isValidElement(icon)) return icon;
  if (typeof icon === "function") {
    const Icon = icon as LucideIcon;
    return <Icon size={18} aria-hidden="true" />;
  }
  return icon;
}
