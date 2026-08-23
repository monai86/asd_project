import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { capturePairedEvidence } from "./evidence-screenshots";

const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const backendBaseUrl = `http://127.0.0.1:${backendPort}/api/v1`;
const authHeaders = {
  "X-Mock-Role": "therapist",
  "X-Mock-User-Id": "therapist-demo",
  "X-Organization-Id": "pilot_org_001",
};

async function setTherapistSession(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  });
}

async function createConsentedCase(request: APIRequestContext, childCode: string) {
  const response = await request.post(`${backendBaseUrl}/cases`, {
    headers: authHeaders,
    data: {
      child_code: childCode,
      age_months: 60,
      language: "English",
      consent_status: "granted",
    },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const caseId = (await response.json()).case_id as string;
  // Give the case a session so it never surfaces as a "Start session" queue row:
  // today-responsive and accessibility-acceptance expect the Today queue to
  // hold zero sessionless cases (the hero button is the only "Start session").
  const sessionResponse = await request.post(`${backendBaseUrl}/cases/${caseId}/sessions`, {
    headers: authHeaders,
    data: { session_date: "2026-07-21", session_type: "language_sample" },
  });
  expect(sessionResponse.ok(), await sessionResponse.text()).toBe(true);
  return caseId;
}

async function bottomNavBox(page: Page) {
  return page.evaluate(() => {
    const nav = document.querySelector<HTMLElement>("nav[aria-label='Bottom navigation']")!;
    const rect = nav.getBoundingClientRect();
    return {
      position: getComputedStyle(nav).position,
      display: getComputedStyle(nav).display,
      top: rect.top,
      bottom: rect.bottom,
      viewportHeight: window.innerHeight,
    };
  });
}

test.describe("mobile bottom navigation", () => {
  test("mounts a fixed canonical bottom nav on mobile with content clearance", async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await setTherapistSession(page);
    await createConsentedCase(request, "BOTNAV-001");
    await page.goto("/today", { waitUntil: "networkidle" });

    const bottomNav = page.getByRole("navigation", { name: "Bottom navigation" });
    await expect(bottomNav).toBeVisible();
    const navBox = await bottomNavBox(page);
    expect(navBox.position).toBe("fixed");
    expect(navBox.bottom).toBeLessThanOrEqual(navBox.viewportHeight + 1);
    expect(navBox.top).toBeGreaterThanOrEqual(navBox.viewportHeight - 120);

    const links = bottomNav.getByRole("link");
    await expect(links).toHaveCount(5);
    await expect(bottomNav.getByRole("link", { name: "Today" })).toHaveAttribute("href", "/today");
    await expect(bottomNav.getByRole("link", { name: "Cases" })).toHaveAttribute("href", "/cases");
    await expect(bottomNav.getByRole("link", { name: "Session" })).toHaveAttribute("href", "/cases?intent=start-session");
    await expect(bottomNav.getByRole("link", { name: "Reports" })).toHaveAttribute("href", "/reports");
    await expect(bottomNav.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
    await expect(bottomNav.getByRole("link", { name: "Today" })).toHaveAttribute("aria-current", "page");

    // main is the scroll container. Scrolled to its bottom, the deepest visible
    // content clears the fixed nav thanks to the mobile bottom padding.
    await page.evaluate(() => {
      const main = document.querySelector<HTMLElement>("main")!;
      main.scrollTo(0, main.scrollHeight);
    });
    await page.waitForTimeout(100);
    const clearance = await page.evaluate(() => {
      const main = document.querySelector<HTMLElement>("main")!;
      const nav = document.querySelector<HTMLElement>("nav[aria-label='Bottom navigation']")!;
      const navTop = nav.getBoundingClientRect().top;
      const visibleBottom = Math.max(0, ...[...main.querySelectorAll<HTMLElement>("*")]
        .filter((element) => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
        })
        .map((element) => element.getBoundingClientRect().bottom));
      return {
        visibleBottom,
        navTop,
        scrolled: main.scrollTop + main.clientHeight >= main.scrollHeight - 1,
      };
    });
    expect(clearance.scrolled).toBe(true);
    expect(clearance.visibleBottom).toBeLessThanOrEqual(clearance.navTop + 1);

    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
    await capturePairedEvidence(page, "bottom-nav", { width: 390, height: 844 });
  });

  test("carries a preselected case through the bottom nav Session link", async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await setTherapistSession(page);
    const caseId = await createConsentedCase(request, "BOTNAV-CASE-002");

    await page.goto(`/cases?intent=start-session&case_id=${caseId}`, { waitUntil: "networkidle" });

    const bottomNav = page.getByRole("navigation", { name: "Bottom navigation" });
    await expect(bottomNav).toBeVisible();
    await expect(bottomNav.getByRole("link", { name: "Session" })).toHaveAttribute(
      "href",
      `/cases?intent=start-session&case_id=${caseId}`,
    );
    await expect(page.getByText(/preselected from the previous screen/i)).toBeVisible();
  });
});

test.describe("bottom navigation breakpoints", () => {
  for (const viewport of [
    { name: "tablet-portrait", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ]) {
    test(`hides the bottom nav at ${viewport.name}`, async ({ page, request }) => {
      await page.setViewportSize(viewport);
      await setTherapistSession(page);
      await createConsentedCase(request, `BOTNAV-${viewport.name.toUpperCase()}`);
      await page.goto("/today", { waitUntil: "networkidle" });

      const bottomNav = page.getByRole("navigation", { name: "Bottom navigation" });
      await expect(bottomNav).toBeHidden();
      expect((await bottomNavBox(page)).display).toBe("none");
    });
  }
});
