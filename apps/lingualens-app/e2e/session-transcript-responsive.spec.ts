import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { capturePairedEvidence } from "./evidence-screenshots";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "small-desktop", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

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

async function createResponsiveTranscript(request: APIRequestContext, viewportName: string) {
  const caseResponse = await request.post(`${backendBaseUrl}/cases`, {
    headers: authHeaders,
    data: {
      child_code: `RESP-${viewportName}`,
      age_months: 60,
      language: "English",
      consent_status: "granted",
    },
  });
  expect(caseResponse.ok(), await caseResponse.text()).toBe(true);
  const caseId = (await caseResponse.json()).case_id as string;
  const sessionResponse = await request.post(`${backendBaseUrl}/cases/${caseId}/sessions`, {
    headers: authHeaders,
    data: { session_date: "2026-07-21", session_type: "language_sample" },
  });
  expect(sessionResponse.ok(), await sessionResponse.text()).toBe(true);
  const sessionId = (await sessionResponse.json()).session_id as string;
  const transcriptResponse = await request.post(`${backendBaseUrl}/sessions/${sessionId}/transcripts/manual`, {
    headers: authHeaders,
    data: {
      text: [
        "THER: What do you see in the picture?",
        "CHI: I see the blue car.",
        "THER: Tell me more about the car.",
        "CHI: The car goes to the house.",
      ].join("\n"),
      language: "English",
    },
  });
  expect(transcriptResponse.ok(), await transcriptResponse.text()).toBe(true);
  return sessionId;
}

for (const viewport of viewports) {
  test(`Transcript workbench preserves editing and inspector behavior at ${viewport.name}`, async ({ page, request }) => {
    let evidenceCaptured = false;
    await page.setViewportSize(viewport);
    await setTherapistSession(page);
    const sessionId = await createResponsiveTranscript(request, viewport.name);
    await page.goto(`/sessions/${sessionId}?view=transcript`, { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "Review Transcript", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Session context" })).toBeVisible();

    if (await page.getByRole("option", { name: "Transcript line 1", exact: true }).count() === 0) {
      await page.getByRole("button", { name: "Add line" }).click();
    }
    const line = page.getByRole("option", { name: "Transcript line 1", exact: true });
    await line.getByLabel("Utterance text 1", { exact: true }).fill("The child points to the blue car.");
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
      await page.evaluate(() => window.scrollTo(0, 0));
      const mobileContract = await page.evaluate(() => {
        const workspace = document.querySelector<HTMLElement>("[data-testid='transcript-workbench']")!;
        const mobileHeader = document.querySelector<HTMLElement>("main header")!;
        const audio = document.querySelector<HTMLElement>("[data-testid='transcript-audio-inspector']")!;
        const bar = document.querySelector<HTMLElement>("[data-testid='mobile-transcript-primary-actions']")!;
        const navigation = document.querySelector<HTMLElement>("nav[aria-label='Bottom navigation']")!;
        const firstUtterance = document.querySelector<HTMLElement>("textarea[aria-label='Utterance text 1']")!;
        const mobileBrand = mobileHeader.querySelector<HTMLElement>("a[href='/today']")!;
        const actionRect = bar.getBoundingClientRect();
        const navigationRect = navigation.getBoundingClientRect();
        const utteranceRect = firstUtterance.getBoundingClientRect();
        return {
          workspacePaddingBottom: Number.parseFloat(getComputedStyle(workspace).paddingBottom),
          scrollY: window.scrollY,
          mobileHeaderTop: mobileHeader.getBoundingClientRect().top,
          mobileBrandTop: mobileBrand.getBoundingClientRect().top,
          audioPosition: getComputedStyle(audio).position,
          actionPosition: getComputedStyle(bar).position,
          navigationPosition: getComputedStyle(navigation).position,
          actionTop: actionRect.top,
          actionBottom: actionRect.bottom,
          navigationTop: navigationRect.top,
          navigationBottom: navigationRect.bottom,
          firstUtteranceTop: utteranceRect.top,
          firstUtteranceBottom: utteranceRect.bottom,
          viewportHeight: window.innerHeight,
        };
      });
      expect(mobileContract.workspacePaddingBottom).toBeGreaterThanOrEqual(176);
      expect(mobileContract.scrollY).toBe(0);
      expect(mobileContract.mobileHeaderTop).toBeGreaterThanOrEqual(0);
      expect(mobileContract.mobileBrandTop).toBeGreaterThanOrEqual(0);
      expect(mobileContract.audioPosition).toBe("sticky");
      expect(mobileContract.actionPosition).toBe("fixed");
      expect(mobileContract.navigationPosition).toBe("fixed");
      expect(mobileContract.actionTop).toBeGreaterThanOrEqual(0);
      expect(mobileContract.actionBottom).toBeLessThanOrEqual(mobileContract.navigationTop + 1);
      expect(mobileContract.navigationBottom).toBeLessThanOrEqual(mobileContract.viewportHeight + 1);
      expect(mobileContract.firstUtteranceTop).toBeGreaterThanOrEqual(0);
      expect(mobileContract.firstUtteranceBottom).toBeLessThanOrEqual(mobileContract.actionTop);

      await capturePairedEvidence(page, "transcript", viewport);
      evidenceCaptured = true;

      const lastLine = page.locator("[role='option'][aria-label^='Transcript line']").last();
      await lastLine.evaluate((node) => node.scrollIntoView({ block: "center" }));
      const overlap = await page.evaluate(() => {
        const rows = [...document.querySelectorAll<HTMLElement>("[role='option'][aria-label^='Transcript line']")];
        const lastRow = rows.at(-1)!;
        const bar = document.querySelector<HTMLElement>("[data-testid='mobile-transcript-primary-actions']")!;
        return lastRow.getBoundingClientRect().bottom - bar.getBoundingClientRect().top;
      });
      expect(overlap).toBeLessThanOrEqual(0);
    }

    if (!evidenceCaptured) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await capturePairedEvidence(page, "transcript", viewport);
    }
  });
}
