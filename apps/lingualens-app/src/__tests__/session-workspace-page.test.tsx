import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";

vi.mock("@/components/app-shell", () => ({
  AppShell: ({ active, children }: { active: string; children: ReactNode }) => (
    <main data-active={active}>{children}</main>
  ),
}));

vi.mock("@/components/session-workspace-client", () => ({
  SessionWorkspaceClient: (props: Record<string, string | undefined>) => (
    <section
      data-testid="session-workspace"
      data-view={props.view}
      data-session-id={props.sessionId}
      data-case-id={props.caseId}
      data-transcript-id={props.transcriptId}
      data-report-id={props.reportId}
      data-mode={props.mode}
    />
  ),
}));

vi.mock("@/components/report-summary-client", () => ({
  ReportSummaryClient: (props: Record<string, string | undefined>) => (
    <section
      data-testid="report-summary"
      data-session-id={props.sessionId}
      data-case-id={props.caseId}
      data-transcript-id={props.transcriptId}
      data-report-id={props.reportId}
    />
  ),
}));

import SessionWorkspacePage from "@/app/sessions/[sessionId]/page";

afterEach(cleanup);

describe("canonical Session workspace page", () => {
  test.each([
    ["intake", "session-workspace", "record"],
    ["transcript", "session-workspace", "transcript"],
    ["findings", "session-workspace", "results"],
    ["report", "report-summary", undefined],
  ] as const)(
    "renders the current %s implementation inside the Session shell",
    async (view, testId, currentView) => {
      render(await SessionWorkspacePage({
        params: Promise.resolve({ sessionId: "SESSION-1" }),
        searchParams: Promise.resolve({
          view,
          case_id: "CASE-1",
          transcript_id: "TRANSCRIPT-1",
          report_id: "REPORT-1",
          mode: "paste",
        }),
      }));

      const implementation = screen.getByTestId(testId);
      expect(implementation.closest("main")).toHaveAttribute("data-active", "Sessions");
      expect(implementation).toHaveAttribute("data-session-id", "SESSION-1");
      expect(implementation).toHaveAttribute("data-case-id", "CASE-1");
      expect(implementation).toHaveAttribute("data-transcript-id", "TRANSCRIPT-1");
      expect(implementation).toHaveAttribute("data-report-id", "REPORT-1");
      if (currentView) {
        expect(implementation).toHaveAttribute("data-view", currentView);
        expect(implementation).toHaveAttribute("data-mode", "paste");
      }
    },
  );
});
