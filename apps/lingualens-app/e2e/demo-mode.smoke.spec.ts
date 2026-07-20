import { expect, test } from "@playwright/test";
import path from "node:path";

const evidenceDirectory = path.resolve(process.cwd(), "../../docs/frontend/navigation-phase-screenshots");
const prohibitedNormativeCopy = /ต่ำกว่าเกณฑ์|สูงกว่าเกณฑ์|ผ่านเกณฑ์|เกณฑ์อายุ|เกณฑ์ปกติ|มาตรฐานปฏิสัมพันธ์/;

test("explicit demo mode keeps sample data isolated and visibly labeled", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/demo/dashboard", { waitUntil: "networkidle" });

  await expect(page.getByRole("status")).toContainText("Sample data demonstration");
  await expect(page.getByRole("heading", { name: /Dr\. Somchai/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Transcript บทสนทนา/ })).toHaveAttribute("href", "/demo/transcript");
  await expect(page.locator('a[href^="/sessions/"]')).toHaveCount(0);
  await expect(page.locator('a[href^="/cases/"]')).toHaveCount(0);
});

test("demo findings and report use descriptive non-normative sample copy", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });

  await page.goto("/demo/features", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /ผลวิเคราะห์ฟีเจอร์ทางภาษา/ })).toBeVisible();
  await expect(page.getByText("ข้อมูลเชิงพรรณนา").first()).toBeVisible();
  await expect(page.locator("body")).not.toContainText(prohibitedNormativeCopy);
  await page.screenshot({
    path: path.join(evidenceDirectory, "demo-features-descriptive-copy-1280x800.png"),
    fullPage: true,
  });

  await page.goto("/demo/report", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /รายงานผลการบำบัดภาษาและพูด/ })).toBeVisible();
  await expect(page.getByText(/ไม่ได้ใช้เปรียบเทียบตามช่วงวัยหรือเป็นข้อสรุปเชิงวินิจฉัย/)).toBeVisible();
  await expect(page.locator("body")).not.toContainText(prohibitedNormativeCopy);
  await page.screenshot({
    path: path.join(evidenceDirectory, "demo-report-descriptive-copy-1280x800.png"),
    fullPage: true,
  });
});
