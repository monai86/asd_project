import Link from "next/link";
import { ArrowRight, MessageCircle } from "lucide-react";

/**
 * Conversational "what's next" prompt for the session workspace.
 *
 * Renders like the app speaking to the therapist: a short human prompt in a
 * message bubble, one primary reply-style action, and optional quick-reply
 * chips for alternate paths. Answers the two questions every therapist asks on
 * a session page: "what do I do here?" and "where can I go next?" without
 * adding technical language.
 */
export type SessionGuideAction = {
  label: string;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  reason?: string;
};

export type SessionGuideQuickReply = {
  label: string;
  href?: string;
  onClick?: () => void;
};

export function SessionGuide({
  prompt,
  primaryAction,
  quickReplies = [],
  testId,
  reasonId: explicitReasonId,
}: {
  prompt: string;
  primaryAction?: SessionGuideAction;
  quickReplies?: SessionGuideQuickReply[];
  testId?: string;
  reasonId?: string;
}) {
  const primaryId = testId ? `${testId}-primary` : undefined;
  const reasonId = explicitReasonId ?? (testId ? `${testId}-reason` : undefined);

  return (
    <section
      aria-label="What to do next"
      data-testid={testId}
      className="overflow-hidden rounded-[var(--radius-shell)] border border-[color:var(--color-accent-strong)]/30 bg-[color:var(--color-surface-reading)]"
    >
      <div className="flex gap-3 p-4 sm:p-5">
        <span
          aria-hidden="true"
          className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
        >
          <MessageCircle size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[color:var(--color-accent-strong)]">
            Next step
          </p>
          <p className="mt-1.5 text-base font-medium leading-6 text-[color:var(--color-text-strong)]">{prompt}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {primaryAction && primaryAction.href ? (
              <Link
                href={primaryAction.href}
                id={primaryId}
                aria-describedby={primaryAction.disabled ? undefined : reasonId}
                aria-disabled={primaryAction.disabled}
                data-testid={`${testId}-primary`}
                className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-[color:var(--color-accent-strong)] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-clinical ${
                  primaryAction.disabled ? "pointer-events-none opacity-50" : ""
                }`}
              >
                {primaryAction.label}
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            ) : primaryAction ? (
              <button
                type="button"
                id={primaryId}
                onClick={primaryAction.onClick}
                disabled={primaryAction.disabled}
                aria-describedby={primaryAction.disabled && primaryAction.reason ? reasonId : undefined}
                data-testid={`${testId}-primary`}
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-[color:var(--color-accent-strong)] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-clinical disabled:cursor-not-allowed disabled:opacity-50"
              >
                {primaryAction.label}
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            ) : null}
            {quickReplies.map((reply) =>
              reply.href ? (
                <Link
                  key={reply.label}
                  href={reply.href}
                  data-testid={`${testId}-reply-${reply.label}`}
                  className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-card)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-4 py-2.5 text-sm font-semibold text-[color:var(--color-text-strong)] transition-colors hover:border-[color:var(--color-accent-strong)] hover:text-[color:var(--color-accent-strong)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-clinical"
                >
                  {reply.label}
                </Link>
              ) : (
                <button
                  key={reply.label}
                  type="button"
                  onClick={reply.onClick}
                  data-testid={`${testId}-reply-${reply.label}`}
                  className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-card)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-4 py-2.5 text-sm font-semibold text-[color:var(--color-text-strong)] transition-colors hover:border-[color:var(--color-accent-strong)] hover:text-[color:var(--color-accent-strong)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-clinical"
                >
                  {reply.label}
                </button>
              ),
            )}
          </div>
          {primaryAction && primaryAction.disabled && primaryAction.reason ? (
            <p
              id={reasonId}
              role="status"
              data-testid={`${testId}-reason`}
              className="mt-3 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900"
            >
              {primaryAction.reason}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
