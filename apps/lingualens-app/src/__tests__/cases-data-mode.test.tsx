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
