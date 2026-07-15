export const sessionViews = ["intake", "transcript", "findings", "report"] as const;

export type SessionView = (typeof sessionViews)[number];

export type SessionViewIdentity = {
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
};

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
  return resolveSessionHref(view, sessionId);
}

export function resolveSessionHref(
  view: SessionView,
  sessionId?: unknown,
  identity: SessionViewIdentity = {},
): string {
  if (
    typeof sessionId !== "string"
    || !sessionIdPattern.test(sessionId)
  ) {
    return "/cases?intent=start-session";
  }

  const params = new URLSearchParams({ view });
  if (identity.caseId) params.set("case_id", identity.caseId);
  if (identity.transcriptId) params.set("transcript_id", identity.transcriptId);
  if (identity.reportId) params.set("report_id", identity.reportId);
  return `/sessions/${encodeURIComponent(sessionId)}?${params.toString()}`;
}
