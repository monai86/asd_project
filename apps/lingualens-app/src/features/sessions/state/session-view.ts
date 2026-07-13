export const sessionViews = ["intake", "transcript", "findings", "report"] as const;

export type SessionView = (typeof sessionViews)[number];

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
    || sessionId.length === 0
    || sessionId.trim() !== sessionId
  ) {
    return "/cases?intent=start-session";
  }

  return `/sessions/${encodeURIComponent(sessionId)}?view=${view}`;
}
