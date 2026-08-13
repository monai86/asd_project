import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "small-desktop", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

const evidenceDirectory = path.resolve(process.cwd(), "../../docs/frontend/session-intake-phase-screenshots");

async function setTherapistSession(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
    offenders: Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          className: element.className,
          text: element.textContent?.trim().replace(/\s+/g, " ").slice(0, 80) ?? "",
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
        };
      })
      .filter(({ left, right }) => left < 0 || right > window.innerWidth)
      .slice(0, 20),
  }));
  expect(
    dimensions.document,
    `Horizontal overflow offenders: ${JSON.stringify(dimensions.offenders, null, 2)}`,
  ).toBeLessThanOrEqual(dimensions.viewport);
}

for (const viewport of viewports) {
  test(`Session Intake preserves context and actions at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await setTherapistSession(page);
    let sessionReads = 0;
    page.on("request", (request) => {
      if (
        request.method() === "GET"
        && new URL(request.url()).pathname === "/api/v1/sessions/session_demo_001"
      ) {
        sessionReads += 1;
      }
    });
    await page.goto("/sessions/session_demo_001?view=intake", { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "Session Intake", exact: true })).toHaveCount(1);
    await expect(page.getByRole("region", { name: "Session context" })).toBeVisible();
    await expect(page.getByText("Backend mode", { exact: true })).toBeVisible();
    await expect(page.getByText("Consent granted", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Intake", exact: true })).toHaveAttribute("aria-current", "page");
    await expect(page.getByRole("link", { name: "Transcript", exact: true })).toHaveAttribute(
      "href",
      "/sessions/session_demo_001?view=transcript",
    );

    const viewTargets = await page.getByRole("navigation", { name: "Session views" }).evaluate((navigation) => {
      const navRect = navigation.getBoundingClientRect();
      return Array.from(navigation.querySelectorAll("a")).map((link) => {
        const rect = link.getBoundingClientRect();
        return {
          height: Math.round(rect.height),
          fullyVisible: rect.left >= navRect.left && rect.right <= navRect.right,
        };
      });
    });
    expect(viewTargets.every(({ height }) => height >= 44)).toBe(true);
    expect(viewTargets.every(({ fullyVisible }) => fullyVisible)).toBe(true);
    expect(sessionReads).toBe(1);
    await expectNoHorizontalOverflow(page);

    if (process.env.UPDATE_SESSION_INTAKE_SCREENSHOTS === "1") {
      await page.screenshot({
        path: path.join(evidenceDirectory, `session-intake-${viewport.width}x${viewport.height}.png`),
        fullPage: true,
      });
    }
  });
}
