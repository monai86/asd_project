import { render, screen, within } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AppShell } from "@/components/app-shell";

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock" },
  }),
}));

describe("AppShell", () => {
  it("renders ChatGPT style sidebar with + New Session button and navigation links", () => {
    render(<AppShell active="Today"><div>Content</div></AppShell>);
    expect(screen.getByText(/New Session/i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /primary navigation/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Today/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Cases/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Reports/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Settings/i }).length).toBeGreaterThan(0);
  });

  it("mounts the mobile bottom navigation with the canonical route set", () => {
    render(<AppShell active="Cases"><div>Content</div></AppShell>);

    const bottomNav = screen.getByRole("navigation", { name: "Bottom navigation" });
    const links = within(bottomNav).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/today",
      "/cases",
      "/cases?intent=start-session",
      "/reports",
      "/settings",
    ]);
    expect(within(bottomNav).getByRole("link", { name: "Cases" })).toHaveAttribute("aria-current", "page");
  });

  it("threads the active session and case into the bottom navigation", () => {
    render(<AppShell active="Cases" activeSessionId="session_approved_001" activeCaseId="case_approved_001"><div>Content</div></AppShell>);

    const bottomNav = screen.getByRole("navigation", { name: "Bottom navigation" });
    expect(within(bottomNav).getByRole("link", { name: "Session" })).toHaveAttribute(
      "href",
      "/sessions/session_approved_001",
    );
  });
});
