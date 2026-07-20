import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "desktop-compact", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];
const evidenceDirectory = path.resolve(process.cwd(), "../../docs/frontend/cases-phase-screenshots");

async function captureEvidence(page: Page, filename: string) {
  await page.screenshot({ path: path.join(evidenceDirectory, filename), fullPage: true });
}

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
  test(`Cases list remains readable at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await setMockRole(page, "therapist");
    await page.goto("/cases");

    await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Consent filter" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Sort cases" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Clinician filter" })).toHaveCount(0);

    if (viewport.width >= 1024) {
      await expect(page.getByRole("table", { name: "Cases workspace" })).toBeVisible();
      if (viewport.width >= 1280) {
        await expect(page.getByRole("complementary", { name: "Selected case context" })).toBeVisible();
      }
    } else {
      await expect(page.getByRole("list", { name: "Cases" })).toBeVisible();
      await expect(page.getByRole("table", { name: "Cases workspace" })).toBeHidden();
    }

    await expectNoHorizontalOverflow(page);
    await captureEvidence(page, `cases-list-${viewport.width}x${viewport.height}.png`);
  });
}

test("authorized organization admins receive the clinician filter", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setMockRole(page, "org_admin");
  await page.goto("/cases");

  await expect(page.getByRole("combobox", { name: "Clinician filter" })).toBeVisible();
});

test("the shared shell loads runtime settings once", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setMockRole(page, "therapist");
  let settingsRequestCount = 0;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() === "GET" && url.pathname === "/api/v1/settings") {
      settingsRequestCount += 1;
    }
  });

  await page.goto("/cases", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();

  expect(settingsRequestCount).toBe(1);
});

test("start-session intent creates only after selection and opens canonical Intake", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await setMockRole(page, "therapist");
  await page.goto("/cases?intent=start-session");

  await expect(page.getByRole("heading", { name: "Choose a case to start a session" })).toBeVisible();
  const startButton = page.getByRole("button", { name: "Start session", exact: true });
  await expect(startButton).toBeDisabled();

  const selectableCase = page.locator('input[type="radio"]:not(:disabled)').first();
  await selectableCase.check();
  await expect(page.getByRole("button", { name: /Start session for/ })).toBeEnabled();
  await page.getByRole("button", { name: /Start session for/ }).click();

  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=intake$/);
  await expect(page.getByRole("heading", { name: /Session intake/i })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("Case Detail exposes the approved sections and canonical session link", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setMockRole(page, "therapist");
  await page.goto("/cases/case_demo_001");

  for (const section of ["Overview", "Sessions", "Goals", "Progress", "Reports"]) {
    await expect(page.getByRole("heading", { name: section, exact: true })).toBeVisible();
  }
  await expect(page.locator('a[href="/sessions/session_demo_001?view=intake"]')).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

for (const viewport of viewports) {
  test(`records selector and detail evidence at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await setMockRole(page, "therapist");

    await page.goto("/cases?intent=start-session");
    await expect(page.getByRole("heading", { name: "Choose a case to start a session" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureEvidence(page, `cases-selector-${viewport.width}x${viewport.height}.png`);

    await page.goto("/cases/case_demo_001");
    await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureEvidence(page, `case-detail-${viewport.width}x${viewport.height}.png`);
  });
}
