import { expect, test, type Page } from "@playwright/test";
import { capturePairedEvidence } from "./evidence-screenshots";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "desktop-compact", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

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

async function expectCareTeamFormControlsDoNotOverlap(page: Page) {
  const boxes = await page.getByTestId("care-team-assignment-form").locator(":scope > *").evaluateAll((elements) =>
    elements.map((element) => {
      const rect = element.getBoundingClientRect();
      return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
    }),
  );
  for (let first = 0; first < boxes.length; first += 1) {
    for (let second = first + 1; second < boxes.length; second += 1) {
      const a = boxes[first];
      const b = boxes[second];
      const horizontal = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const vertical = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      expect(horizontal > 1 && vertical > 1, `care-team controls ${first} and ${second} overlap`).toBe(false);
    }
  }
}

for (const viewport of viewports) {
  test(`therapist and admin Settings remain role-safe at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await setMockRole(page, "therapist");
    await page.goto("/settings", { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
    const therapistNavigation = page.getByRole("navigation", { name: "Settings categories mobile" });
    await expect(therapistNavigation.locator('a[aria-current="page"]')).toHaveText("Account");
    if (viewport.width < 768) {
      await expect(therapistNavigation.getByRole("link", { name: "Account", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Account", exact: true })).toBeHidden();
      await expectNoHorizontalOverflow(page);
      await capturePairedEvidence(page, "settings", viewport);
      await therapistNavigation.getByRole("link", { name: "Account", exact: true }).click();
      await expect(page.getByRole("button", { name: "All settings categories" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Account", exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole("heading", { name: "Account", exact: true })).toBeVisible();
      await expectNoHorizontalOverflow(page);
      await capturePairedEvidence(page, "settings", viewport);
    }
    await expect(page.getByRole("link", { name: "Team", exact: true })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Team", exact: true })).toHaveCount(0);
    await expectNoHorizontalOverflow(page);

    const adminPage = await page.context().newPage();
    await adminPage.setViewportSize(viewport);
    await setMockRole(adminPage, "org_admin");
    await adminPage.goto("/settings?section=team", { waitUntil: "networkidle" });

    await expect(adminPage.getByRole("heading", { name: "Team", exact: true })).toBeVisible();
    await expect(adminPage.getByRole("heading", { name: "Care-team administration" })).toBeVisible();
    const adminNavigation = adminPage.getByRole("navigation", { name: "Settings categories mobile" });
    await expect(adminNavigation.locator('a[aria-current="page"]')).toHaveText("Team");
    if (viewport.width < 768) {
      await expect(adminPage.getByRole("button", { name: "All settings categories" })).toBeVisible();
    }
    await expectCareTeamFormControlsDoNotOverlap(adminPage);
    await expectNoHorizontalOverflow(adminPage);
    await capturePairedEvidence(adminPage, "settings-admin", viewport);
    await adminPage.close();
  });
}
