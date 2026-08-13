import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const evidenceDirectory = path.resolve(process.cwd(), "../../docs/frontend/accessibility-phase-screenshots");

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
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);
}

test("the canonical workbench reflows at the 200 percent zoom equivalent", async ({ page }) => {
  await page.setViewportSize({ width: 640, height: 800 });
  await setTherapistSession(page);
  await page.goto("/today", { waitUntil: "networkidle" });

  await expect(page.getByRole("heading", { name: "Work Queue" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Start session", exact: true })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: path.join(evidenceDirectory, "today-200-percent-zoom-equivalent-640x800.png"),
    fullPage: true,
  });
});

test("forced colors preserve selected transcript state and keyboard focus", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.emulateMedia({ forcedColors: "active" });
  await setTherapistSession(page);
  await page.goto("/sessions/session_demo_001?view=transcript", { waitUntil: "networkidle" });

  if (await page.getByRole("option", { name: "Transcript line 1", exact: true }).count() === 0) {
    await page.getByRole("button", { name: "Add line" }).click();
  }
  const line = page.getByRole("option", { name: "Transcript line 1", exact: true });
  const editor = line.getByLabel("Utterance text 1", { exact: true });
  await editor.focus();

  await expect(line).toHaveAttribute("aria-selected", "true");
  await expect(editor).toBeFocused();
  expect(await line.evaluate((element) => getComputedStyle(element).forcedColorAdjust)).toBe("none");
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: path.join(evidenceDirectory, "transcript-forced-colors-1280x800.png"),
    fullPage: true,
  });
});
