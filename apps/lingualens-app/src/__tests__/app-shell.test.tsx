import { render, screen } from "@testing-library/react";
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
});
