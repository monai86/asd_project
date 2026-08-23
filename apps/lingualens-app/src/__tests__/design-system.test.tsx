import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";
import { ActionButton } from "@/components/action-button";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { SafetyNotice } from "@/components/safety-notice";
import { SkeletonPanel } from "@/components/skeleton";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock" },
  }),
}));

describe("design system primitives", () => {
  it("renders the shell with accessible navigation, a skip link, and an optional right rail", () => {
    render(
      <AppShell
        active="Cases"
        rightRail={
          <div>
            <h2>Right rail</h2>
            <p>Clinical safety guidance</p>
          </div>
        }
      >
        <div>Page content</div>
      </AppShell>
    );

    expect(screen.getByRole("link", { name: /skip to main content/i })).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("navigation", { name: /primary navigation/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Cases" })[0]).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("heading", { name: "Right rail" })).toBeInTheDocument();
    expect(screen.getByText("Page content")).toBeInTheDocument();
  });

  it("renders a richer page header with eyebrow, metadata, and actions", () => {
    render(
      <PageHeader
        eyebrow="Clinical decision-support prototype"
        title="Reports"
        description="Therapist review and sign-off remain required."
        meta={["Local demo mode", "Backend-backed records"]}
        actions={<ActionButton>Primary action</ActionButton>}
      />
    );

    expect(screen.getByText("Clinical decision-support prototype")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Reports" })).toBeInTheDocument();
    expect(screen.getByText("Local demo mode")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Primary action" })).toBeInTheDocument();
  });

  it("does not forward ActionButton design props to links", () => {
    render(
      <ActionButton
        href="/record"
        icon={<span data-testid="button-icon" aria-hidden="true" />}
        tone="secondary"
        size="lg"
      >
        Open Session Workspace
      </ActionButton>
    );

    const link = screen.getByRole("link", { name: "Open Session Workspace" });
    expect(link).toHaveAttribute("href", "/record");
    expect(link).not.toHaveAttribute("icon");
    expect(link).not.toHaveAttribute("tone");
    expect(link).not.toHaveAttribute("size");
    expect(screen.getByTestId("button-icon")).toBeInTheDocument();
  });

  it("renders stat cards, status badges, and safety notices with safe language", () => {
    render(
      <>
        <StatCard label="Transcript review" value="Required" helper="Therapist attestation remains required." />
        <StatusBadge status="Signed Off" />
        <SafetyNotice>
          Decision-support only. Not diagnostic. Therapist review required before report use.
        </SafetyNotice>
      </>
    );

    expect(screen.getByText("Transcript review")).toBeInTheDocument();
    expect(screen.getByText("Therapist attestation remains required.")).toBeInTheDocument();
    expect(screen.getByText("Signed Off")).toBeInTheDocument();
    expect(screen.getByText(/decision-support only/i)).toBeInTheDocument();
  });

  it("renders skeleton loading primitives with a polite announcement", () => {
    const { container } = render(<SkeletonPanel lines={2} />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(container.querySelectorAll("[aria-hidden='true']").length).toBeGreaterThan(0);
  });

  it("renders a reusable data table and a reusable empty state", () => {
    const { rerender } = render(
      <DataTable
        caption="Case list"
        columns={[
          { key: "case", header: "Case" },
          { key: "status", header: "Status" }
        ]}
        rows={[
          { id: "case-1", case: "C-1024", status: "Needs Review" }
        ]}
      />
    );

    expect(screen.getByRole("table", { name: "Case list" })).toBeInTheDocument();
    expect(screen.getByText("C-1024")).toBeInTheDocument();

    rerender(
      <EmptyState
        title="No reports yet"
        description="Create or open a session to generate a therapist-editable draft."
        action={<ActionButton href="/record">Open Session Workspace</ActionButton>}
      />
    );

    expect(screen.getByRole("heading", { name: "No reports yet" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Session Workspace" })).toHaveAttribute("href", "/record");
  });
});
