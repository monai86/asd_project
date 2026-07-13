import { beforeEach, describe, expect, test } from "vitest";

import RecordPage from "@/app/record/page";
import ReportSummaryPage from "@/app/report-summary/page";
import ResultsPage from "@/app/results/page";
import ReviewTranscriptPage from "@/app/review-transcript/page";
import SessionWorkspacePage from "@/app/sessions/[sessionId]/page";
import TranscriptPage from "@/app/transcript/page";
import { redirectMock } from "@/__tests__/setup";
import {
  resolveLegacySessionHref,
  resolveSessionView,
} from "@/features/sessions/state/session-view";

type LegacyPage = (props: {
  searchParams?: Record<string, string> | Promise<Record<string, string>>;
}) => unknown;

const legacyRoutes = [
  ["record", RecordPage, "intake"],
  ["review-transcript", ReviewTranscriptPage, "transcript"],
  ["transcript", TranscriptPage, "transcript"],
  ["results", ResultsPage, "findings"],
  ["report-summary", ReportSummaryPage, "report"],
] as const;

describe("session view routing", () => {
  beforeEach(() => {
    redirectMock.mockClear();
  });

  test.each(["intake", "transcript", "findings", "report"] as const)(
    "accepts %s",
    (view) => {
      expect(resolveSessionView(view)).toBe(view);
    },
  );

  test.each([undefined, "", "results", "unknown"])(
    "defaults %s to intake",
    (view) => {
      expect(resolveSessionView(view)).toBe("intake");
    },
  );

  test("sends identifier-less legacy traffic to deliberate session selection", () => {
    expect(resolveLegacySessionHref("transcript", undefined)).toBe(
      "/cases?intent=start-session",
    );
  });

  test.each(["", "   ", ["session-1", "session-2"]])(
    "sends malformed legacy identifier %j to deliberate session selection",
    (sessionId) => {
      expect(resolveLegacySessionHref("transcript", sessionId)).toBe(
        "/cases?intent=start-session",
      );
    },
  );

  test("maps an identified legacy route to the canonical Session view", () => {
    expect(resolveLegacySessionHref("findings", "session-1")).toBe(
      "/sessions/session-1?view=findings",
    );
  });

  test("encodes legacy session identifiers before building the canonical href", () => {
    expect(resolveLegacySessionHref("report", "session/1 ?")).toBe(
      "/sessions/session%2F1%20%3F?view=report",
    );
  });

  test.each([undefined, "results", "unknown"])(
    "the canonical page passes intake for an invalid view value of %s",
    async (view) => {
      const page = await SessionWorkspacePage({
        params: Promise.resolve({ sessionId: "session-1" }),
        searchParams: Promise.resolve({ view }),
      }) as React.ReactElement<{
        children: React.ReactElement<{ view: string }>;
      }>;

      expect(page.props.children.props.view).toBe("intake");
    },
  );

  test.each(legacyRoutes)(
    "/%s sends identifier-less traffic to deliberate session selection",
    async (_route, page) => {
      await (page as LegacyPage)({});

      expect(redirectMock).toHaveBeenCalledOnce();
      expect(redirectMock).toHaveBeenCalledWith("/cases?intent=start-session");
    },
  );

  test.each(legacyRoutes)(
    "/%s maps identified traffic to its canonical Session view",
    async (_route, page, view) => {
      await (page as LegacyPage)({
        searchParams: Promise.resolve({ session_id: "session/1" }),
      });

      expect(redirectMock).toHaveBeenCalledOnce();
      expect(redirectMock).toHaveBeenCalledWith(
        `/sessions/session%2F1?view=${view}`,
      );
    },
  );
});
