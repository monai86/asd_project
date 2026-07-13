import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";

test("does not expose mock login when runtime settings are malformed", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    mock_mode: true,
    auth_mode: "mock",
    capabilities: { cases: "maybe" },
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  })));

  render(<RuntimeLoginPanelClient />);

  expect(await screen.findByRole("heading", { name: "Runtime settings unavailable" })).toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Mock login form" })).not.toBeInTheDocument();
});
