import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import HomePage from "@/app/page";
import { BottomNav } from "@/components/bottom-nav";
import { Sidebar } from "@/components/sidebar";

const redirectMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

vi.mock("@/components/work-queue-dashboard", () => ({
  WorkQueueDashboard: () => <div>Legacy home dashboard</div>,
}));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock" },
  }),
}));

vi.mock("@/lib/use-supabase-access-session", () => ({
  useSupabaseAccessSession: () => null,
}));

describe("canonical workbench navigation", () => {
  beforeEach(() => {
    redirectMock.mockReset();
  });

  test.each([
    ["desktop", (activeSessionId?: string) => <Sidebar active="Today" activeSessionId={activeSessionId} />],
    ["mobile", (activeSessionId?: string) => <BottomNav active="Today" activeSessionId={activeSessionId} />],
  ])("%s navigation exposes one canonical route set", (_surface, renderNavigation) => {
    render(renderNavigation());

    expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Today" })).toHaveAttribute("href", "/today");
    expect(screen.getByRole("link", { name: "Cases" })).toHaveAttribute("href", "/cases");
    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute("href", "/cases?intent=start-session");
    expect(screen.getByRole("link", { name: "Reports" })).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
  });

  test.each([
    ["desktop", (activeSessionId: string) => <Sidebar active="Session" activeSessionId={activeSessionId} />],
    ["mobile", (activeSessionId: string) => <BottomNav active="Session" activeSessionId={activeSessionId} />],
  ])("%s navigation deep-links only to the explicitly active session", (_surface, renderNavigation) => {
    render(renderNavigation("session_approved_001"));

    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute(
      "href",
      "/sessions/session_approved_001",
    );
    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute("aria-current", "page");
  });

  test.each(["", "   ", "../audit", "session/other", "session?view=report"])(
    "does not construct a Session deep link from unsafe identifier %j",
    (activeSessionId) => {
      render(<Sidebar active="Session" activeSessionId={activeSessionId} />);

      expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute(
        "href",
        "/cases?intent=start-session",
      );
    },
  );

  test("the identifier-less root route redirects to Today", () => {
    HomePage();

    expect(redirectMock).toHaveBeenCalledOnce();
    expect(redirectMock).toHaveBeenCalledWith("/today");
  });
});
