import fs from "node:fs";
import path from "node:path";

import type { Page } from "@playwright/test";

export const finalEvidenceDirectory = path.resolve(
  process.cwd(),
  "../../docs/frontend/final-remediation-screenshots",
);

export async function capturePairedEvidence(
  page: Page,
  screen: string,
  viewport: { width: number; height: number },
) {
  fs.mkdirSync(finalEvidenceDirectory, { recursive: true });
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    const previousScrollBehavior = document.documentElement.style.scrollBehavior;
    document.documentElement.style.scrollBehavior = "auto";
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    window.scrollTo(0, 0);
    document.documentElement.style.scrollBehavior = previousScrollBehavior;
  });
  await page.waitForFunction(() => window.scrollY === 0);
  await page.waitForTimeout(50);

  await page.screenshot({
    path: path.join(finalEvidenceDirectory, `${screen}-viewport-${viewport.width}x${viewport.height}.png`),
    fullPage: false,
    animations: "disabled",
    caret: "hide",
  });
  await page.screenshot({
    path: path.join(finalEvidenceDirectory, `${screen}-fullpage-${viewport.width}x${viewport.height}.png`),
    fullPage: true,
    animations: "disabled",
    caret: "hide",
  });

}
