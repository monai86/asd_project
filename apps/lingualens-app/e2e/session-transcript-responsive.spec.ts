import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "small-desktop", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

const evidenceDirectory = path.resolve(process.cwd(), "../../docs/frontend/session-transcript-phase-screenshots");

async function setTherapistSession(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  });
}

for (const viewport of viewports) {
  test(`Transcript workbench preserves editing and inspector behavior at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await setTherapistSession(page);
    await page.goto("/sessions/session_demo_001?view=transcript", { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "Review Transcript", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Session context" })).toBeVisible();

    if (await page.getByRole("option", { name: "Transcript line 1" }).count() === 0) {
      await page.getByRole("button", { name: "Add line" }).click();
    }
    const line = page.getByRole("option", { name: "Transcript line 1" });
    await line.getByLabel("Utterance text 1").fill("The child points to the blue car.");
    await expect(line).toHaveAttribute("aria-selected", "true");
    await expect(line.getByRole("button", { name: "More actions for line 1" })).toBeVisible();

    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);

    if (viewport.width >= 1280) {
      const widths = await page.evaluate(() => {
        const workspace = document.querySelector<HTMLElement>("[data-testid='transcript-workbench']")!;
        const editor = document.querySelector<HTMLElement>("[role='listbox'][aria-label='Transcript lines']")!;
        const inspector = document.querySelector<HTMLElement>("[data-testid='transcript-audio-inspector']")!;
        return {
          workspace: workspace.getBoundingClientRect().width,
          editor: editor.getBoundingClientRect().width,
          inspectorRight: inspector.getBoundingClientRect().right,
          workspaceRight: workspace.getBoundingClientRect().right,
        };
      });
      expect(widths.editor / widths.workspace).toBeGreaterThanOrEqual(0.6);
      expect(widths.inspectorRight).toBeLessThanOrEqual(widths.workspaceRight + 1);
    }

    if (viewport.width >= 768 && viewport.width < 1280) {
      await page.getByRole("button", { name: "QA", exact: true }).click();
      await expect(page.getByTestId("transcript-qa-panel")).toBeVisible();
      await page.getByRole("button", { name: "Hide inspector" }).click();
      await expect(page.getByTestId("transcript-audio-inspector")).toBeHidden();
      await expect(line.getByLabel("Utterance text 1")).toBeVisible();
      await page.getByRole("button", { name: "Show Audio and QA" }).click();
    }

    if (viewport.width < 768) {
      const mobileContract = await page.evaluate(() => {
        const workspace = document.querySelector<HTMLElement>("[data-testid='transcript-workbench']")!;
        const audio = document.querySelector<HTMLElement>("[data-testid='transcript-audio-inspector']")!;
        const save = document.querySelector<HTMLElement>("[data-testid='save-transcript-draft-button']")!;
        const bar = save.closest<HTMLElement>(".max-md\\:sticky")!;
        return {
          workspacePaddingBottom: Number.parseFloat(getComputedStyle(workspace).paddingBottom),
          audioPosition: getComputedStyle(audio).position,
          actionPosition: getComputedStyle(bar).position,
        };
      });
      expect(mobileContract.workspacePaddingBottom).toBeGreaterThanOrEqual(176);
      expect(mobileContract.audioPosition).toBe("sticky");
      expect(mobileContract.actionPosition).toBe("sticky");
    }

    if (process.env.UPDATE_SESSION_TRANSCRIPT_SCREENSHOTS === "1") {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: path.join(evidenceDirectory, `session-transcript-${viewport.width}x${viewport.height}.png`),
        fullPage: true,
      });
    }
  });
}
