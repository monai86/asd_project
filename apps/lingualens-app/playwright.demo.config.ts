import { defineConfig, devices } from "@playwright/test";

function resolvePort(envValue: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(envValue ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const frontendPort = resolvePort(process.env.PLAYWRIGHT_DEMO_PORT, 3101);
const backendPort = resolvePort(process.env.PLAYWRIGHT_DEMO_BACKEND_PORT, 8001);
const allowedOrigins = [
  `http://127.0.0.1:${frontendPort}`,
  `http://localhost:${frontendPort}`,
].join(",");

/**
 * Dedicated config for the explicit demo-mode smoke specs. The demo routes
 * (`/demo/*`) render only when the server is started with
 * NEXT_PUBLIC_DEMO_MODE=true, which cannot coexist with the main dev server
 * under Next 16's single-dev-server lock, so the demo specs run here against
 * their own server instead of being part of the default `npx playwright test`.
 *
 * Run with:
 *   npx playwright test -c playwright.demo.config.ts
 */
export default defineConfig({
  testDir: ".",
  testMatch: ["e2e/demo-mode.smoke.spec.ts"],
  timeout: 120_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "on-first-retry",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command: `PYTHONPATH=. LINGUALENS_REPOSITORY_MODE=memory LINGUALENS_CORS_ALLOWED_ORIGINS=${allowedOrigins} python3 -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "../api",
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: `NEXT_PUBLIC_DEMO_MODE=true NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run dev -- --hostname 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
