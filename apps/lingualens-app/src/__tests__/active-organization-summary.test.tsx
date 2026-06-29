import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { routerRefresh } from "@/__tests__/setup";
import { ActiveOrganizationSummary } from "@/components/active-organization-summary";
import { saveMockAccessSession } from "@/lib/mock-access-session";

describe("ActiveOrganizationSummary", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    routerRefresh.mockClear();
  });

  it("shows a read-only active organization label for single-org sessions", async () => {
    saveMockAccessSession({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    });

    render(<ActiveOrganizationSummary />);

    expect(await screen.findByText("Pilot Speech Clinic")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Switch active organization" })).not.toBeInTheDocument();
  });

  it("allows explicit active-organization switching for multi-org sessions", async () => {
    saveMockAccessSession({
      role: "clinical_supervisor",
      organizationId: "pilot_org_001",
      aal: "aal2",
    });

    render(<ActiveOrganizationSummary />);

    const switcher = await screen.findByRole("combobox", { name: "Switch active organization" });
    fireEvent.change(switcher, { target: { value: "pilot_org_002" } });

    expect((await screen.findAllByText("North Review Clinic")).length).toBeGreaterThan(0);
    expect(window.sessionStorage.getItem("lingualens.mock-access-session.v1")).toContain("pilot_org_002");
    expect(screen.getByText("Only one organization is active per session. Switching changes the next scoped request.")).toBeInTheDocument();
    expect(screen.getByText("Active organization switched. Refreshing scoped workspace data.")).toBeInTheDocument();
    expect(routerRefresh).toHaveBeenCalled();
  });
});
