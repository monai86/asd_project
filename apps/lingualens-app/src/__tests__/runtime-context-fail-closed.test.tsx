import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { ActiveOrganizationSummary } from "@/components/active-organization-summary";
import { Topbar } from "@/components/topbar";

const { runtimeState } = vi.hoisted(() => ({
  runtimeState: {
    current: { status: "loading", mode: "backend" } as Record<string, unknown>,
  },
}));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => runtimeState.current,
}));

beforeEach(() => {
  window.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
});

test("does not expose mock organization or clinician context while runtime settings are loading", () => {
  runtimeState.current = { status: "loading", mode: "backend" };

  render(
    <>
      <ActiveOrganizationSummary />
      <Topbar />
    </>,
  );

  expect(screen.getAllByText("Verifying organization context").length).toBeGreaterThan(0);
  expect(screen.getByText("Verifying workspace user")).toBeInTheDocument();
  expect(screen.queryByText("Pilot Speech Clinic")).not.toBeInTheDocument();
  expect(screen.queryByText("Demo Therapist")).not.toBeInTheDocument();
  expect(screen.queryByText("Local clinician workspace")).not.toBeInTheDocument();
});

test("does not expose mock organization or clinician context when runtime settings are unavailable", () => {
  runtimeState.current = {
    status: "error",
    mode: "backend",
    message: "Runtime settings unavailable",
  };

  render(
    <>
      <ActiveOrganizationSummary />
      <Topbar />
    </>,
  );

  expect(screen.getAllByText("Organization context unavailable").length).toBeGreaterThan(0);
  expect(screen.getByText("Workspace user unavailable")).toBeInTheDocument();
  expect(screen.getAllByText("Runtime settings unavailable").length).toBeGreaterThan(0);
  expect(screen.queryByText("Pilot Speech Clinic")).not.toBeInTheDocument();
  expect(screen.queryByText("Demo Therapist")).not.toBeInTheDocument();
  expect(screen.queryByText("Local clinician workspace")).not.toBeInTheDocument();
});
