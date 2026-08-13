import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TodayWorkbenchView } from "@/features/work-queue/components/today-workbench-view";
import { buildTodayWorkbench } from "@/features/work-queue/today-workbench-model";

const cases = [
  {
    case_id: "case-review",
    child_code: "C-1001",
    consent_status: "granted",
    language: "Thai / English",
    review_priority: "high",
    latest_session_date: "2026-07-18",
    latest_session_status: "Needs Review",
    latest_report_status: "Draft",
    updated_at: "2026-07-18T08:00:00Z",
  },
  {
    case_id: "case-processing",
    child_code: "C-1002",
    consent_status: "granted",
    language: "Thai",
    review_priority: "moderate",
    latest_session_date: "2026-07-19",
    latest_session_status: "Processing",
    latest_report_status: "Draft",
    updated_at: "2026-07-19T08:00:00Z",
  },
  {
    case_id: "case-stale",
    child_code: "C-1003",
    consent_status: "granted",
    language: "English",
    review_priority: "high",
    latest_session_date: "2026-07-17",
    latest_session_status: "Attested",
    latest_report_status: "stale",
    updated_at: "2026-07-17T08:00:00Z",
  },
];

const reports = [
  {
    report_id: "report-stale",
    case_id: "case-stale",
    session_id: "session-stale",
    status: "stale",
    updated_at: "2026-07-19T09:00:00Z",
  },
];

describe("Today focused workbench", () => {
  it("derives one backend-confirmed next action per case and groups status inside the queue", () => {
    const model = buildTodayWorkbench(cases, reports);

    expect(model.items).toHaveLength(3);
    expect(model.items.map((item) => item.group)).toEqual([
      "needs_action",
      "processing",
      "ready_for_review",
    ]);
    expect(model.items.find((item) => item.caseId === "case-stale")).toMatchObject({
      actionLabel: "Regenerate report",
      href: "/sessions/session-stale?view=report&case_id=case-stale&report_id=report-stale",
      reason: expect.stringMatching(/newer transcript/i),
    });
    expect(model.items.every((item) => item.caseLabel.startsWith("C-"))).toBe(true);
  });

  it("renders a single action in each queue row without sample or legacy workflow links", () => {
    const model = buildTodayWorkbench(cases, reports);
    render(<TodayWorkbenchView state={{ status: "ready", model }} />);

    expect(screen.getByRole("heading", { name: "Needs action" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Processing" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ready for review" })).toBeInTheDocument();
    expect(screen.getByText("Backend confirmed")).toBeInTheDocument();

    for (const row of screen.getAllByTestId("today-queue-row")) {
      expect(within(row).getAllByRole("link")).toHaveLength(1);
    }
    for (const link of screen.getAllByRole("link")) {
      expect(link.getAttribute("href")).not.toMatch(/^\/(record|review-transcript|transcript|results|report-summary)/);
    }
    expect(screen.queryByText(/Ava M\.|Ethan L\.|Jacob W\./)).not.toBeInTheDocument();
    expect(screen.queryByText(/demo fallback/i)).not.toBeInTheDocument();
  });

  it("shows honest loading, empty, and unavailable states with retry", () => {
    const retry = vi.fn();
    const { rerender } = render(<TodayWorkbenchView state={{ status: "loading" }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading today’s work queue");
    expect(screen.getByText("Backend verification pending")).toBeInTheDocument();
    expect(screen.queryByText("Backend confirmed")).not.toBeInTheDocument();

    rerender(<TodayWorkbenchView state={{ status: "ready", model: buildTodayWorkbench([], []) }} />);
    expect(screen.getByText("No work requires attention right now.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start session" })).toHaveAttribute("href", "/cases?intent=start-session");

    rerender(<TodayWorkbenchView state={{ status: "error", retry }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Today’s queue is unavailable");
    expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Backend confirmed")).not.toBeInTheDocument();
    expect(screen.queryByTestId("today-queue-row")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry work queue" }));
    expect(retry).toHaveBeenCalledTimes(1);
  });
});
