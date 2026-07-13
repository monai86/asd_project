export const sessionViews = ["intake", "transcript", "findings", "report"] as const;

export type SessionView = (typeof sessionViews)[number];

const sessionIdPattern = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;

export function resolveSessionView(value?: unknown): SessionView {
  return typeof value === "string" && sessionViews.includes(value as SessionView)
    ? (value as SessionView)
    : "intake";
}

export function resolveLegacySessionHref(
  view: SessionView,
  sessionId?: unknown,
): string {
  if (
    typeof sessionId !== "string"
    || !sessionIdPattern.test(sessionId)
  ) {
    return "/cases?intent=start-session";
  }

  return `/sessions/${encodeURIComponent(sessionId)}?view=${view}`;
}
