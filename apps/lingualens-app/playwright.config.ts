import { defineConfig, devices } from "@playwright/test";

function resolvePort(envValue: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(envValue ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const frontendPort = resolvePort(process.env.PLAYWRIGHT_FRONTEND_PORT, 3100);
const backendPort = resolvePort(process.env.PLAYWRIGHT_BACKEND_PORT, 8000);
// Benchmarks need a production build (see webServer below), so they only run
// when explicitly requested: `npx playwright test benchmarks/...`.
const benchmarkRun = process.argv.some((argument) => argument.includes("benchmarks/"));
// Demo-mode specs need a server started with NEXT_PUBLIC_DEMO_MODE=true, which
// cannot coexist with the main dev server under Next's single-dev-server lock.
// Run them with the dedicated demo config:
//   npx playwright test -c playwright.demo.config.ts
const allowedOrigins = [
  `http://127.0.0.1:${frontendPort}`,
  `http://localhost:${frontendPort}`,
].join(",");

export default defineConfig({
  testDir: ".",
  testMatch: [
    "e2e/**/*.spec.ts",
    ...(benchmarkRun ? ["benchmarks/**/*.spec.ts"] : []),
  ],
  testIgnore: ["e2e/demo-mode.smoke.spec.ts"],
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
      command: benchmarkRun
        ? `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run build && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run start -- --hostname 127.0.0.1 --port ${frontendPort}`
        : `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run dev -- --hostname 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
