import { expect, test, type Page } from "@playwright/test";

const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const backendBaseUrl = `http://127.0.0.1:${backendPort}`;

const validTranscript = [
  "THER: what do you see",
  "CHI: I see a red car",
  "THER: tell me more",
  "CHI: the car goes fast",
  "CHI: I want car again",
].join("\n");

const invalidTranscript = [
  "THER: hello there",
  "THER: tell me more",
].join("\n");

function recordRequests(page: Page) {
  const urls: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/")) {
      urls.push(url);
    }
  });
  return urls;
}

function expectNoDuplicatedApiPrefix(urls: string[]) {
  expect(urls.some((url) => url.includes("/api/v1/v1"))).toBe(false);
}

function currentWorkflowQuery(page: Page) {
  return new URL(page.url()).searchParams;
}

async function pasteTranscript(page: Page, transcript: string) {
  await page.goto("/record?mode=paste");
  await page.getByTestId("transcript-input").fill(transcript);
  await page.getByTestId("save-transcript-button").click();
  await expect(page).toHaveURL(/\/review-transcript\?/);
}

async function attestTranscript(page: Page) {
  await expect(page.getByTestId("run-transcript-qa-button")).toBeEnabled();
  await page.getByTestId("run-transcript-qa-button").click();
  await expect(page.getByTestId("transcript-qa-panel")).toBeVisible();
  await page.getByTestId("attest-transcript-button").click();
  await expect(page.getByTestId("transcript-attestation-badge")).toHaveText("Attested");
}

async function openRecordStep(page: Page) {
  const params = currentWorkflowQuery(page);
  params.set("mode", "paste");
  await page.goto(`/record?${params.toString()}`);
}

async function openReportSummary(page: Page) {
  await expect(page.getByTestId("generate-report-button")).toBeEnabled();
  await page.getByTestId("generate-report-button").click();
  await expect(page).toHaveURL(/\/report-summary\?/);
}

test("happy path smoke flow covers transcript QA, ML readiness, evidence review, and safe report output", async ({ page }) => {
  const requestUrls = recordRequests(page);

  await pasteTranscript(page, validTranscript);
  await attestTranscript(page);

  await openRecordStep(page);
  await expect(page.getByTestId("extract-features-button")).toBeEnabled({ timeout: 20_000 });
  await page.getByTestId("extract-features-button").click();
  await expect(page).toHaveURL(/\/results\?/);

  await expect(page.getByRole("heading", { name: "Session Results", level: 1 })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Report readiness")).toBeVisible();
  await expect(page.getByText(/Ready|Blocked/).first()).toBeVisible();
  const evidenceButton = page.getByTestId("generate-evidence-review-button");
  if (await evidenceButton.count() && await evidenceButton.isEnabled()) {
    await evidenceButton.click();
    await expect(page.getByTestId("evidence-review-panel")).toContainText("Not diagnostic");
  }

  await openReportSummary(page);
  await page.getByTestId("generate-report-draft-button").click();
  await expect(page.getByTestId("report-preview")).toHaveValue(/decision-support only/i);
  await expect(page.getByTestId("report-preview")).toHaveValue(/not diagnostic/i);

  expectNoDuplicatedApiPrefix(requestUrls);
});

test("negative path smoke flow blocks attestation when transcript QA has a critical error", async ({ page }) => {
  const requestUrls = recordRequests(page);

  await pasteTranscript(page, invalidTranscript);
  await expect(page.getByTestId("run-transcript-qa-button")).toBeEnabled();
  await page.getByTestId("run-transcript-qa-button").click();

  await expect(page.getByTestId("transcript-qa-panel")).toContainText("No child speaker lines were detected.");
  await expect(page.getByTestId("attest-transcript-button")).toBeDisabled();

  expectNoDuplicatedApiPrefix(requestUrls);
});

test("safety path smoke flow blocks diagnostic claims in edited report text", async ({ page }) => {
  const requestUrls = recordRequests(page);

  await pasteTranscript(page, validTranscript);
  await attestTranscript(page);

  await openRecordStep(page);
  await expect(page.getByTestId("extract-features-button")).toBeEnabled({ timeout: 20_000 });
  await page.getByTestId("extract-features-button").click();
  await expect(page).toHaveURL(/\/results\?/);
  await openReportSummary(page);

  await page.getByTestId("generate-report-draft-button").click();
  await expect(page.getByTestId("report-preview")).toHaveValue(/decision-support only/i);
  const reportId = new URL(page.url()).searchParams.get("report_id");
  expect(reportId).toBeTruthy();
  const patchResponse = await page.request.patch(`${backendBaseUrl}/api/v1/reports/${reportId}`, {
    headers: {
      "X-User-Id": "user_therapist_001",
      "content-type": "application/json",
    },
    data: {
      markdown: "Child is ASD positive and diagnosed with autism.",
      therapist_notes: "",
    },
  });
  expect(patchResponse.ok()).toBe(true);
  await page.reload();
  const failedBanner = page.getByTestId("report-safety-failed");
  const warningBanner = page.getByTestId("report-safety-warning");
  if (await failedBanner.count()) {
    await expect(failedBanner).toContainText(/Safety Validation Failed|ASD positive|diagnosed with autism/i);
  } else {
    await expect(warningBanner).toContainText(/Clinical Safety Warnings|ASD positive|diagnosed with autism/i);
  }
  await expect(page.getByTestId("finalize-report-button")).toBeDisabled();

  expectNoDuplicatedApiPrefix(requestUrls);
});
