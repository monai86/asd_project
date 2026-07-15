import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

vi.mock("@/features/sessions/components/session-workspace-model", () => ({
  SessionWorkflowWorkspace: (props: Record<string, string | undefined>) => (
    <section data-testid="workflow-view" data-view={props.view} />
  ),
  resolveWorkspaceFeature: (view?: string) => (
    view === "transcript" ? "transcript" : view === "findings" ? "findings" : "intake"
  ),
}));

vi.mock("@/features/sessions/report/session-report-view", () => ({
  SessionReportView: (props: Record<string, string | undefined>) => (
    <section
      data-testid="report-view"
      data-session-id={props.sessionId}
      data-report-id={props.reportId}
    />
  ),
}));

import {
  SessionWorkspace,
  resolveWorkspaceFeature,
} from "@/features/sessions/components/session-workspace";

afterEach(cleanup);

describe("SessionWorkspace dispatcher", () => {
  test.each([
    ["intake", "intake"],
    ["transcript", "transcript"],
    ["findings", "findings"],
  ] as const)("dispatches %s through the feature-owned workflow as %s", (view, implementation) => {
    render(<SessionWorkspace view={view} />);
    expect(screen.getByTestId("workflow-view")).toHaveAttribute("data-view", view);
    expect(resolveWorkspaceFeature(view)).toBe(implementation);
  });

  test("dispatches report identity to the sole feature-owned report editor", () => {
    render(
      <SessionWorkspace
        view="report"
        sessionId="session-1"
        reportId="signed-report-1"
      />,
    );
    expect(screen.getByTestId("report-view")).toHaveAttribute("data-session-id", "session-1");
    expect(screen.getByTestId("report-view")).toHaveAttribute("data-report-id", "signed-report-1");
    expect(screen.queryByTestId("workflow-view")).not.toBeInTheDocument();
  });
});
