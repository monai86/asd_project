import fs from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { UI_AUDIT_HARD_GATES, uiDesignAuditBattery } from "./support/ui-audit-battery";

/**
 * Repeatable UI design audit across the five therapist surfaces (Today, Cases,
 * Session workspace, Reports, Settings) at mobile and desktop viewports.
 *
 * Hard gates (fail CI when violated):
 *   - headingSkips    (heading levels that jump, e.g. h1 -> h3)
 *   - smallText       (visible text below 12px)
 *   - iconOnlyButtons (buttons with no text and no accessible label)
 *   - overflow        (horizontal overflow of the viewport)
 *
 * All other battery categories (touch targets, contrast, tight line height,
 * empty links, alt text, multiple h1) are advisory and recorded as evidence.
 *
 * Data is self-bootstrapped against the API (seeded case -> session ->
 * manual transcript -> QA -> attestation -> features -> report draft) so the
 * audit is deterministic on a fresh backend (CI) or a running one (local).
 */
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const backendBaseUrl = `http://127.0.0.1:${backendPort}`;
const outputDir = process.env.UI_AUDIT_OUTPUT_DIR ?? path.resolve("test-results", "ui-design-audit");

const mockHeaders = {
  "X-Mock-Role": "therapist",
  "X-Mock-User-Id": "therapist-demo",
  "X-Organization-Id": "pilot_org_001",
  "content-type": "application/json",
};

const validTranscript = [
  "THER: what do you see",
  "CHI: I see a red car",
  "THER: tell me more",
  "CHI: the car goes fast",
  "CHI: I want car again",
].join("\n");

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "desktop", width: 1280, height: 800 },
];

type Surface = { name: string; url: string };
type RunResult = { surface: string; viewport: string; url: string; audit: Record<string, unknown> };

const allResults: RunResult[] = [];
const screenshotsDir = path.join(outputDir, "screenshots");

let sessionId = "";
let caseId = "case_demo_001";

async function bootstrapWorkflow(request: APIRequestContext): Promise<void> {
  // The seeded demo case has granted consent; create a fresh session under it.
  const sessionResponse = await request.post(`${backendBaseUrl}/api/v1/cases/${caseId}/sessions`, {
    headers: mockHeaders,
    data: { session_date: "2026-08-10", session_type: "therapy_session" },
  });
  expect(sessionResponse.ok(), `create session: ${sessionResponse.status()} ${await sessionResponse.text()}`).toBeTruthy();
  const session = await sessionResponse.json();
  sessionId = session.session_id;
  expect(sessionId).toMatch(/^session_/);

  const transcriptResponse = await request.post(`${backendBaseUrl}/api/v1/sessions/${sessionId}/transcripts/manual`, {
    headers: mockHeaders,
    data: { text: validTranscript, language: "English", replace_existing: true },
  });
  expect(transcriptResponse.ok(), `upload transcript: ${transcriptResponse.status()} ${await transcriptResponse.text()}`).toBeTruthy();
  const transcript = await transcriptResponse.json();

  const qaResponse = await request.post(`${backendBaseUrl}/api/v1/transcripts/${transcript.transcript_id}/qa`, { headers: mockHeaders });
  expect(qaResponse.ok(), `run QA: ${qaResponse.status()} ${await qaResponse.text()}`).toBeTruthy();

  const attestResponse = await request.post(`${backendBaseUrl}/api/v1/transcripts/${transcript.transcript_id}/attest`, {
    headers: mockHeaders,
    data: { attested_by: "", reason: "Audit bootstrap attestation." },
  });
  expect(attestResponse.ok(), `attest: ${attestResponse.status()} ${await attestResponse.text()}`).toBeTruthy();

  const featuresResponse = await request.post(`${backendBaseUrl}/api/v1/transcripts/${transcript.transcript_id}/extract-features`, {
    headers: mockHeaders,
    data: {},
  });
  expect(featuresResponse.ok(), `extract features: ${featuresResponse.status()} ${await featuresResponse.text()}`).toBeTruthy();

  const reportResponse = await request.post(`${backendBaseUrl}/api/v1/sessions/${sessionId}/reports/draft`, {
    headers: mockHeaders,
    data: {},
  });
  expect(reportResponse.ok(), `draft report: ${reportResponse.status()} ${await reportResponse.text()}`).toBeTruthy();
}

function buildSurfaces(): Surface[] {
  return [
    { name: "today", url: "/today" },
    { name: "cases", url: "/cases" },
    { name: "case-detail", url: `/cases/${caseId}` },
    { name: "session-intake", url: `/sessions/${sessionId}?view=intake` },
    { name: "session-transcript", url: `/sessions/${sessionId}?view=transcript` },
    { name: "session-findings", url: `/sessions/${sessionId}?view=findings` },
    { name: "session-report", url: `/sessions/${sessionId}?view=report` },
    { name: "reports", url: "/reports" },
    { name: "settings", url: "/settings?section=account" },
  ];
}

test.beforeAll(async ({ request }) => {
  fs.mkdirSync(screenshotsDir, { recursive: true });
  await bootstrapWorkflow(request);
});

function writeFindingsJson() {
  fs.writeFileSync(path.join(outputDir, "findings.json"), JSON.stringify(allResults, null, 2));
}

test.afterAll(() => {
  writeFindingsJson();
  console.log(`UI design audit evidence written to ${outputDir}`);
});

for (const viewport of viewports) {
  test(`UI design audit gates pass at ${viewport.name}`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.addInitScript(() => {
      window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
        role: "therapist",
        organizationId: "pilot_org_001",
        aal: "aal2",
      }));
    });

    for (const surface of buildSurfaces()) {
      await page.goto(surface.url, { waitUntil: "networkidle" });
      await page.waitForTimeout(400);
      const audit = (await page.evaluate(uiDesignAuditBattery)) as Record<string, unknown>;
      allResults.push({ surface: surface.name, viewport: viewport.name, url: surface.url, audit });

      await page.screenshot({
        path: path.join(screenshotsDir, `${surface.name}-${viewport.name}.png`),
        fullPage: true,
        animations: "disabled",
        caret: "hide",
      });

      const summary = Object.fromEntries(
        Object.entries(audit).map(([key, value]) => [key, Array.isArray(value) ? value.length : value]),
      );
      console.log(surface.name.padEnd(18), viewport.name.padEnd(8), JSON.stringify(summary));

      for (const gate of UI_AUDIT_HARD_GATES) {
        if (gate === "overflow") {
          expect(audit[gate], `${surface.name}@${viewport.name}: horizontal overflow detected`).toBe(false);
        } else {
          expect(
            audit[gate],
            `${surface.name}@${viewport.name}: ${gate} violations: ${JSON.stringify(audit[gate], null, 2)}`,
          ).toEqual([]);
        }
      }
    }      writeFindingsJson();
      await testInfo.attach("findings.json", {
        path: path.join(outputDir, "findings.json"),
        contentType: "application/json",
      });
  });
}
