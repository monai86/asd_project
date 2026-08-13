import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";

vi.mock("@/components/app-shell", () => ({
  AppShell: ({ active, children }: { active: string; children: ReactNode }) => (
    <main data-active={active}>{children}</main>
  ),
}));

vi.mock("@/features/sessions/components/session-workspace", () => ({
  SessionWorkspace: (props: Record<string, string | undefined>) => (
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

import SessionWorkspacePage from "@/app/sessions/[sessionId]/page";

afterEach(cleanup);

describe("canonical Session workspace page", () => {
  test.each([
    ["intake"],
    ["transcript"],
    ["findings"],
    ["report"],
  ] as const)(
    "dispatches the validated %s view inside the Session shell",
    async (view) => {
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

      const implementation = screen.getByTestId("session-workspace");
      expect(implementation.closest("main")).toHaveAttribute("data-active", "Session");
      expect(implementation).toHaveAttribute("data-session-id", "SESSION-1");
      expect(implementation).toHaveAttribute("data-case-id", "CASE-1");
      expect(implementation).toHaveAttribute("data-transcript-id", "TRANSCRIPT-1");
      expect(implementation).toHaveAttribute("data-report-id", "REPORT-1");
      expect(implementation).toHaveAttribute("data-view", view);
      expect(implementation).toHaveAttribute("data-mode", "paste");
    },
  );
});
