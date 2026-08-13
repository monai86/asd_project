import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

beforeEach(() => {
  vi.unstubAllGlobals();
});

test("shows unavailable state without sample cases when backend loading fails", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => {
    throw new Error("offline");
  }));

  render(<CasesWorkspaceClient />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Cases are unavailable");
  expect(screen.queryByText("Demo child")).not.toBeInTheDocument();
});

test("does not substitute the first sample case for an unknown case id", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("not found", { status: 404 })));

  render(<CasesWorkspaceClient caseId="missing-case" />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Case could not be loaded");
  expect(screen.queryByText("Demo child")).not.toBeInTheDocument();
});

test.each(["timeline", "goals"])(
  "fails closed when the case %s request fails",
  async (failedResource) => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases/case-001")) {
        return new Response(JSON.stringify({
          case_id: "case-001",
          child_code: "C-001",
          nickname: "Backend child",
          consent_status: "granted",
        }), { status: 200 });
      }
      if (url.endsWith(`/cases/case-001/${failedResource}`)) {
        return new Response("secondary read failed", { status: 503 });
      }
      if (url.endsWith("/cases/case-001/timeline") || url.endsWith("/cases/case-001/goals")) {
        return new Response("[]", { status: 200 });
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<CasesWorkspaceClient caseId="case-001" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Case could not be loaded");
    expect(screen.queryByText("No sessions recorded yet for this case.")).not.toBeInTheDocument();
    expect(screen.queryByText("No communication goals recorded yet.")).not.toBeInTheDocument();
    expect(screen.queryByText("Add communication goals when the care plan is ready.")).not.toBeInTheDocument();
  },
);
