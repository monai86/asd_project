import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import DemoLayout from "@/app/demo/layout";
import { isDemoEnabled } from "@/services/adapters/demo-mode";

const notFoundMock = vi.hoisted(() => vi.fn((): never => {
  throw new Error("NEXT_NOT_FOUND");
}));

vi.mock("next/navigation", () => ({
  notFound: notFoundMock,
  usePathname: () => "/demo/dashboard",
}));

vi.mock("@/components/demo-shell", () => ({
  DemoShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("explicit demo mode boundary", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    notFoundMock.mockClear();
  });

  test.each([
    ["true", true],
    ["false", false],
    ["1", false],
    ["TRUE", false],
    [undefined, false],
  ])("treats NEXT_PUBLIC_DEMO_MODE=%s as enabled=%s", (value, expected) => {
    expect(isDemoEnabled({ NEXT_PUBLIC_DEMO_MODE: value })).toBe(expected);
  });

  test("disabled demo routes resolve through the framework not-found boundary", () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "false");

    expect(() => DemoLayout({ children: <div>Demo payload</div> })).toThrow("NEXT_NOT_FOUND");
    expect(notFoundMock).toHaveBeenCalledOnce();
  });

  test("enabled demo routes retain a persistent and explicit sample-data notice", () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true");

    render(DemoLayout({ children: <div>Demo payload</div> }));

    expect(screen.getByRole("status")).toHaveTextContent(/sample data demonstration/i);
    expect(screen.getByText("Demo payload")).toBeInTheDocument();
    expect(notFoundMock).not.toHaveBeenCalled();
  });
});
