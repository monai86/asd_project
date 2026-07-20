import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "desktop-compact", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

const evidenceDirectory = path.resolve(process.cwd(), "../../docs/frontend/settings-phase-screenshots");

async function setMockRole(page: Page, role: "therapist" | "org_admin") {
  await page.addInitScript((requestedRole) => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: requestedRole,
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  }, role);
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
    offenders: Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ rect }) => rect.left < -1 || rect.right > window.innerWidth + 1)
      .slice(0, 10)
      .map(({ element, rect }) => ({
        tag: element.tagName.toLowerCase(),
        text: element.textContent?.trim().replace(/\s+/g, " ").slice(0, 60) ?? "",
        left: Math.round(rect.left),
        right: Math.round(rect.right),
      })),
  }));
  expect(dimensions.document, JSON.stringify(dimensions.offenders)).toBeLessThanOrEqual(dimensions.viewport);
}

for (const viewport of viewports) {
  test(`therapist and admin Settings remain role-safe at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await setMockRole(page, "therapist");
    await page.goto("/settings?section=profile", { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Profile", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Admin", exact: true })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Pilot admin controls" })).toHaveCount(0);
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      path: path.join(evidenceDirectory, `settings-therapist-${viewport.width}x${viewport.height}.png`),
      fullPage: true,
    });

    const adminPage = await page.context().newPage();
    await adminPage.setViewportSize(viewport);
    await setMockRole(adminPage, "org_admin");
    await adminPage.goto("/settings?section=team", { waitUntil: "networkidle" });

    await expect(adminPage.getByRole("heading", { name: "Pilot admin controls" })).toBeVisible();
    await expect(adminPage.getByRole("heading", { name: "Organization readiness cockpit" })).toBeVisible();
    await expect(adminPage.getByRole("button", { name: "Admin", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expectNoHorizontalOverflow(adminPage);
    await adminPage.screenshot({
      path: path.join(evidenceDirectory, `settings-admin-${viewport.width}x${viewport.height}.png`),
      fullPage: true,
    });
    await adminPage.close();
  });
}
