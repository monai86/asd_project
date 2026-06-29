import { defineConfig, devices } from "@playwright/test";

function resolvePort(envValue: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(envValue ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const frontendPort = resolvePort(process.env.PLAYWRIGHT_FRONTEND_PORT, 3100);
const backendPort = resolvePort(process.env.PLAYWRIGHT_BACKEND_PORT, 8000);
const allowedOrigins = [
  `http://127.0.0.1:${frontendPort}`,
  `http://localhost:${frontendPort}`,
].join(",");

export default defineConfig({
  testDir: "./e2e",
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
      command: `PYTHONPATH=. THERAPIST_APP_V2_REPOSITORY_MODE=memory THERAPIST_APP_V2_CORS_ALLOWED_ORIGINS=${allowedOrigins} python3 -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "../api",
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run dev -- --hostname 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
