import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { capturePairedEvidence } from "./evidence-screenshots";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "desktop-compact", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

const apiBase = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const apiHeaders = {
  "X-User-Id": "therapist-demo",
  "X-Mock-Role": "therapist",
  "X-Mock-Display-Name": "Demo Therapist",
  "X-Organization-Id": "pilot_org_001",
};
let sessionId = "";
let caseId = "";
let transcriptId = "";
let reportId = "";

async function postJson<T extends Record<string, unknown>>(
  request: APIRequestContext,
  pathName: string,
  data?: Record<string, unknown>,
): Promise<T> {
  const response = await request.post(`${apiBase}${pathName}`, { headers: apiHeaders, data });
  const body = await response.text();
  expect(response.ok(), `${pathName}: ${response.status()} ${body}`).toBeTruthy();
  return JSON.parse(body) as T;
}

test.beforeAll(async ({ request }) => {
  const runId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const caseRecord = await postJson<{ case_id: string }>(request, "/cases", {
    child_code: `E2E-DOWNSTREAM-${runId}`,
    age_months: 54,
    language: "English",
  });
  caseId = caseRecord.case_id;

  const session = await postJson<{ session_id: string }>(request, `/cases/${caseId}/sessions`, {
    session_date: "2026-07-17",
    session_type: "therapy_session",
  });
  sessionId = session.session_id;

  const transcript = await postJson<{ transcript_id: string }>(request, `/sessions/${sessionId}/transcripts/manual`, {
    text: "THER: Tell me about the picture.\nCHI: I see a blue car.\nCHI: The car goes fast.\nTHER: What happens next?\nCHI: It stops by the house.",
    language: "English",
  });
  transcriptId = transcript.transcript_id;

  await postJson(request, `/transcripts/${transcriptId}/qa`);
  await postJson(request, `/transcripts/${transcriptId}/attest`, { reason: "Reviewed for responsive contract verification." });
  await postJson(request, `/transcripts/${transcriptId}/extract-features`, {});
  await postJson(request, `/transcripts/${transcriptId}/ml-review`, {});

  const report = await postJson<{ report_id: string }>(request, `/sessions/${sessionId}/reports/draft`, {});
  reportId = report.report_id;
  await postJson(request, `/reports/${reportId}/sign-off`, {
    therapist_name: "Demo Therapist",
    confirmation_checked: true,
  });
});

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
  const dimensions = await page.evaluate(() => {
    const offenders = Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ rect }) => rect.right > window.innerWidth + 1 || rect.width > window.innerWidth + 1)
      .slice(0, 8)
      .map(({ element, rect }) => ({
        tag: element.tagName,
        className: element.className,
        testId: element.dataset.testid,
        width: Math.round(rect.width),
        right: Math.round(rect.right),
      }));
    return {
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
      offenders,
    };
  });
  expect(dimensions.document, JSON.stringify(dimensions.offenders)).toBeLessThanOrEqual(dimensions.viewport);
}

for (const viewport of viewports) {
  test(`downstream workspaces preserve hierarchy and gates at ${viewport.name}`, async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    await page.setViewportSize(viewport);
    await setTherapistSession(page);

    await page.goto(
      `/sessions/${sessionId}?view=findings&case_id=${caseId}&transcript_id=${transcriptId}`,
      { waitUntil: "networkidle" },
    );
    await expect(page.getByRole("region", { name: "Session context" }).getByRole("heading", { name: "Session Results", exact: true })).toBeVisible();
    for (const group of ["Language sample", "Lexical use", "Interaction", "Speech / intelligibility", "Data quality"]) {
      await expect(page.getByText(group, { exact: true })).toBeVisible();
    }
    const provenanceToggle = page.getByText("Technical provenance", { exact: true });
    await expect(page.getByRole("region", { name: "Findings provenance" })).not.toBeVisible();
    await provenanceToggle.click();
    await expect(page.getByRole("region", { name: "Findings provenance" })).toBeVisible();
    await provenanceToggle.click();
    await expect(page.getByText("Interpret descriptive cues in context; limitations remain attached to each feature.", { exact: true })).toHaveCount(1);
    await expectNoHorizontalOverflow(page);
    await capturePairedEvidence(page, "findings", viewport);

    await page.goto(
      `/sessions/${sessionId}?view=report&case_id=${caseId}&transcript_id=${transcriptId}&report_id=${reportId}`,
      { waitUntil: "networkidle" },
    );
    await expect(page.getByRole("heading", { name: "Report Summary", exact: true })).toBeVisible();
    await expect(page.getByText("Signed snapshot · immutable")).toBeVisible();
    await expect(page.getByRole("region", { name: "Report provenance" })).toBeVisible();
    await expect(page.getByTestId("report-preview")).toHaveAttribute("readonly", "");
    await expect(page.getByRole("button", { name: "Export Markdown" })).toBeEnabled();
    await expectNoHorizontalOverflow(page);
    await capturePairedEvidence(page, "report", viewport);

    await page.goto("/reports", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: "Reports", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Needs review" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Needs regeneration" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Signed reports" })).toBeVisible();
    // The desktop table and the compact mobile list are the same reports at
    // different breakpoints; only the visible variant is rendered on screen.
    for (const row of await page.getByTestId("report-library-row").all()) {
      if (await row.isVisible()) {
        await expect(row.getByRole("link")).toHaveCount(1);
      }
    }
    await expectNoHorizontalOverflow(page);
    await capturePairedEvidence(page, "reports", viewport);

    expect(pageErrors).toEqual([]);
  });
}
