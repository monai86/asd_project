import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ReportsWorkspaceClient } from "@/components/reports-workspace-client";

vi.mock("@/components/backend-availability-banner", () => ({
  BackendAvailabilityBanner: () => null,
  useBackendAvailability: () => ({
    backendUnavailable: false,
    setBackendUnavailable: vi.fn(),
  }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubReports(reports: Array<Record<string, string>>) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(reports), {
    status: 200,
    headers: { "content-type": "application/json" },
  })));
}

test("opens report editing in canonical Session view with selected report identity", async () => {
  stubReports([
    {
      report_id: "report-1",
      session_id: "session-1",
      case_id: "case-1",
      title: "Session report",
      status: "Draft",
    },
  ]);

  render(<ReportsWorkspaceClient />);

  expect(await screen.findByRole("link", { name: "Review draft" })).toHaveAttribute(
    "href",
    "/sessions/session-1?view=report&case_id=case-1&report_id=report-1",
  );
});

test("keeps a historical signed report available beside a newer draft", async () => {
  stubReports([
    {
      report_id: "signed-report-1",
      session_id: "session-1",
      case_id: "case-1",
      title: "Signed report",
      status: "Signed Off",
    },
    {
      report_id: "draft-report-2",
      session_id: "session-1",
      case_id: "case-1",
      title: "Current draft",
      status: "Draft",
    },
  ]);

  render(<ReportsWorkspaceClient />);

  expect(await screen.findByRole("link", { name: "Review draft" })).toHaveAttribute(
    "href",
    "/sessions/session-1?view=report&case_id=case-1&report_id=draft-report-2",
  );
  expect(await screen.findByRole("link", { name: "View signed report" })).toHaveAttribute(
    "href",
    "/sessions/session-1?view=report&case_id=case-1&report_id=signed-report-1",
  );
});

test("routes reports without a session through start-session, carrying the known case", async () => {
  stubReports([
    {
      report_id: "report-without-session",
      case_id: "case-1",
      title: "Unlinked report",
      status: "Draft",
    },
  ]);

  render(<ReportsWorkspaceClient />);

  const links = await screen.findAllByRole("link", { name: "Find session" });
  expect(links.length).toBeGreaterThan(0);
  links.forEach((link) => expect(link).toHaveAttribute("href", "/cases?intent=start-session&case_id=case-1"));
  expect(screen.queryByRole("link", { name: /export|sign-off/i })).not.toBeInTheDocument();
});

test("keeps the plain start-session fallback when a session-less report has no case", async () => {
  stubReports([
    {
      report_id: "orphan-report",
      title: "Orphan report",
      status: "Draft",
    },
  ]);

  render(<ReportsWorkspaceClient />);

  const links = await screen.findAllByRole("link", { name: "Find session" });
  links.forEach((link) => expect(link).toHaveAttribute("href", "/cases?intent=start-session"));
});
