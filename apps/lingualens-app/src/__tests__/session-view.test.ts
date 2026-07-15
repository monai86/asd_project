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
  resolveSessionHref,
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

  test.each([
    "",
    "   ",
    ".",
    "..",
    "./session-1",
    "session/1",
    "session\\1",
    "session%2F1",
    ["session-1", "session-2"],
  ])(
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

  test("preserves a path-safe opaque session identifier", () => {
    expect(resolveLegacySessionHref("report", "session_ABC-123")).toBe(
      "/sessions/session_ABC-123?view=report",
    );
  });

  test("preserves selected report and transcript identity in canonical deep links", () => {
    expect(resolveSessionHref("report", "session-1", {
      caseId: "case-1",
      transcriptId: "transcript-2",
      reportId: "signed-report-1",
    })).toBe(
      "/sessions/session-1?view=report&case_id=case-1&transcript_id=transcript-2&report_id=signed-report-1",
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
      await expect((page as LegacyPage)({})).rejects.toThrow("NEXT_REDIRECT");

      expect(redirectMock).toHaveBeenCalledOnce();
      expect(redirectMock).toHaveBeenCalledWith("/cases?intent=start-session");
    },
  );

  test.each(legacyRoutes)(
    "/%s maps identified traffic to its canonical Session view",
    async (_route, page, view) => {
      await expect((page as LegacyPage)({
        searchParams: Promise.resolve({ session_id: "session_safe-1" }),
      })).rejects.toThrow("NEXT_REDIRECT");

      expect(redirectMock).toHaveBeenCalledOnce();
      expect(redirectMock).toHaveBeenCalledWith(
        `/sessions/session_safe-1?view=${view}`,
      );
    },
  );
});
