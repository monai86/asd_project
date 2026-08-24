import { expect, test, type Page } from "@playwright/test";

import {
  safeMutationResponseBreadcrumb,
  type MutationResponseBreadcrumb,
} from "./support/mutation-response-breadcrumb";

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

function recordApiPrefixState(page: Page) {
  const state = { hasDuplicatedApiPrefix: false };
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/v1")) state.hasDuplicatedApiPrefix = true;
  });
  return state;
}

function recordMutationResponses(page: Page) {
  const responses: MutationResponseBreadcrumb[] = [];
  page.on("response", (response) => {
    const breadcrumb = safeMutationResponseBreadcrumb(
      response.request().method(),
      response.url(),
      response.status(),
    );
    if (breadcrumb) responses.push(breadcrumb);
  });
  return responses;
}

function expectNoDuplicatedApiPrefix(state: { hasDuplicatedApiPrefix: boolean }) {
  expect(state.hasDuplicatedApiPrefix).toBe(false);
}

function currentWorkflowQuery(page: Page) {
  return new URL(page.url()).searchParams;
}

async function pasteTranscript(page: Page, transcript: string, mutationResponses: MutationResponseBreadcrumb[]) {
  await page.goto("/cases?intent=start-session");
  await expect(page.getByRole("heading", { name: "Choose a case to start a session" })).toBeVisible();
  await page.getByRole("radio").first().check();
  await page.getByRole("button", { name: "Start session" }).click();
  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=intake/);
  await expect(page.getByRole("heading", { name: "Session Intake", exact: true })).toBeVisible();
  const childInput = page.getByLabel("Child or client");
  if (!(await childInput.inputValue()).trim()) await childInput.fill("Demo child");
  const clinicianInput = page.getByLabel("Clinician");
  if (!(await clinicianInput.inputValue()).trim()) await clinicianInput.fill("Demo Therapist");
  const dateInput = page.getByLabel("Session date");
  if (!(await dateInput.inputValue()).trim()) await dateInput.fill("2026-07-17");
  await page.getByRole("button", { name: "Continue to Source Material" }).click();
  await page.getByRole("button", { name: "Paste transcript" }).click();
  await page.getByTestId("transcript-input").fill(transcript);
  await page.getByTestId("save-transcript-button").click();
  try {
    await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=transcript/);
  } catch (error) {
    await test.info().attach("transcript-mutation-responses", {
      body: JSON.stringify(mutationResponses, null, 2),
      contentType: "application/json",
    });
    throw error;
  }
}

async function attestTranscript(page: Page) {
  await expect(page.getByTestId("run-transcript-qa-button")).toBeEnabled();
  await page.getByTestId("run-transcript-qa-button").click();
  await page.getByRole("button", { name: "QA", exact: true }).click();
  await expect(page.getByTestId("transcript-qa-panel")).toBeVisible();
  await page.getByTestId("attest-transcript-button").click();
  await expect(page.getByTestId("transcript-attestation-badge")).toHaveText("Attested");
}

async function openRecordStep(page: Page) {
  const params = currentWorkflowQuery(page);
  params.set("view", "intake");
  await page.goto(`${new URL(page.url()).pathname}?${params.toString()}`);
}

async function openReportSummary(page: Page) {
  await expect(page.getByTestId("generate-report-button")).toBeEnabled();
  await page.getByTestId("generate-report-button").click();
  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=report/);
}

async function installSpeakerMappingWorkflowRoutes(page: Page) {
  const unexpectedApiRequests: string[] = [];
  let mappingPersisted = false;
  let mappingConfirmed = false;
  let entries = [
    { temporary_speaker_id: "speaker-0", source_speaker_label: "speaker-0", provider_metadata: { provider_id: "synthetic" }, affected_utterance_ids: ["utt-0"], reviewed_utterance_ids: [] as string[], confirmed_chat_code: null as "CHI" | "THER" | null, participant_role: null as "target_child" | "therapist" | null },
    { temporary_speaker_id: "speaker-1", source_speaker_label: "speaker-1", provider_metadata: { provider_id: "synthetic" }, affected_utterance_ids: ["utt-1"], reviewed_utterance_ids: [] as string[], confirmed_chat_code: null as "CHI" | "THER" | null, participant_role: null as "target_child" | "therapist" | null },
  ];
  const mapping = () => ({
    mapping_id: "spmap-synthetic",
    organization_id: "pilot_org_001",
    transcript_id: "tr-mapping",
    source_transcript_version: 1,
    applied_transcript_version: mappingConfirmed ? 2 : null,
    mapping_version: mappingPersisted || mappingConfirmed ? 2 : 1,
    status: mappingConfirmed ? "confirmed" : "draft",
    required: true,
    persisted: mappingPersisted || mappingConfirmed,
    effective_status: mappingConfirmed ? "confirmed" : "draft",
    issue_code: null,
    issue_message: null,
    confirmed_by_user_id: mappingConfirmed ? "therapist-demo" : null,
    confirmed_by_role: mappingConfirmed ? "therapist" : null,
    confirmed_at: mappingConfirmed ? "2026-08-24T00:00:00Z" : null,
    created_at: "2026-08-24T00:00:00Z",
    updated_at: "2026-08-24T00:00:00Z",
    entries,
  });
  const transcript = () => ({
    transcript_id: "tr-mapping",
    session_id: "session-mapping",
    case_id: "case-mapping",
    source: "asr_draft:synthetic",
    version: mappingConfirmed ? 2 : 1,
    raw_text: mappingConfirmed ? "@Begin\n*CHI:\tSynthetic zero.\n*THER:\tSynthetic one.\n@End" : "",
    qa_status: "NOT_RUN",
    therapist_attested: false,
    utterances: entries.map((entry, index) => ({
      utterance_id: `utt-${index}`,
      speaker: mappingConfirmed ? (index === 0 ? "CHI" : "THER") : "UNK",
      text: `Synthetic ${index}.`,
      temporary_speaker_id: entry.temporary_speaker_id,
      source_speaker_label: entry.source_speaker_label,
    })),
  });

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    const fulfill = (body: unknown, status = 200) => route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });

    if (path.endsWith("/settings")) return fulfill({
      mock_mode: true,
      auth_mode: "mock",
      model_version: "synthetic",
      feature_schema: "synthetic",
      guideline_mapping: "synthetic",
      user_roles: ["therapist"],
      data_retention: "synthetic test fixture",
      consent_policy: "required",
      capabilities: {
        cases: "available",
        audio_upload: "experimental",
        transcription: "experimental",
        transcript_qa: "available",
        feature_extraction: "available",
        ai_review: "disabled",
        report_drafting: "disabled",
        pdf_export: "available",
      },
      pipeline_settings: {
        audio_processing: "synthetic",
        job_queue_mode: "synthetic",
        repository_mode: "synthetic",
        storage_mode: "synthetic",
      },
    });
    if (path.endsWith("/sessions/session-mapping")) return fulfill({ session_id: "session-mapping", case_id: "case-mapping", transcript_id: "tr-mapping" });
    if (path.endsWith("/cases/case-mapping")) return fulfill({ case_id: "case-mapping", child_code: "C-SYNTHETIC", consent_status: "granted" });
    if (path.endsWith("/sessions/session-mapping/audio")) return fulfill([]);
    if (path.endsWith("/sessions/session-mapping/ml-review") || path.endsWith("/sessions/session-mapping/ai-review")) return fulfill({ detail: "Not found" }, 404);
    if (path.endsWith("/transcripts/tr-mapping/ml-readiness")) return fulfill({ ready: false, provider_id: "reference", reason_codes: [], reasons: [] });
    if (path.endsWith("/transcripts/tr-mapping/speaker-mapping/confirm") && method === "POST") {
      mappingConfirmed = true;
      return fulfill(mapping());
    }
    if (path.endsWith("/transcripts/tr-mapping/speaker-mapping") && method === "PUT") {
      const payload = request.postDataJSON() as { entries: typeof entries };
      entries = entries.map((entry, index) => ({ ...entry, ...payload.entries[index] }));
      mappingPersisted = true;
      return fulfill(mapping());
    }
    if (path.endsWith("/transcripts/tr-mapping/speaker-mapping")) return fulfill(mapping());
    if (path.endsWith("/transcripts/tr-mapping/qa") && method === "POST") return fulfill({ transcript_id: "tr-mapping", overall_status: "PASS", issues: [] });
    if (path.endsWith("/transcripts/tr-mapping/attest") && method === "POST") return route.fulfill({ status: 200, body: "" });
    if (path.endsWith("/transcripts/tr-mapping")) return fulfill(transcript());
    unexpectedApiRequests.push(`${method} ${path}`);
    return fulfill({ detail: "Unexpected synthetic mapping fixture request" }, 599);
  });
  return unexpectedApiRequests;
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
    window.sessionStorage.removeItem("lingualens.therapist.workflow.v1");
  });
});

test("happy path smoke flow covers transcript QA, ML readiness, evidence review, and safe report output", async ({ page }) => {
  const apiPrefixState = recordApiPrefixState(page);
  const mutationResponses = recordMutationResponses(page);

  await pasteTranscript(page, validTranscript, mutationResponses);
  await attestTranscript(page);

  await openRecordStep(page);
  await expect(page.getByTestId("extract-features-button")).toBeEnabled({ timeout: 20_000 });
  await page.getByTestId("extract-features-button").click();
  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=findings/);

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

  expectNoDuplicatedApiPrefix(apiPrefixState);
});

test("temporary ASR speaker mapping refreshes the transcript before QA and attestation", async ({ page }) => {
  const unexpectedApiRequests = await installSpeakerMappingWorkflowRoutes(page);
  await page.goto("/sessions/session-mapping?view=transcript&transcript_id=tr-mapping");

  await expect(page.getByRole("region", { name: "Speaker mapping review" })).toBeVisible();
  await expect(page.getByTestId("run-transcript-qa-button")).toBeDisabled();
  await page.getByLabel("CHAT code for speaker-0").selectOption("CHI");
  await page.getByLabel("Participant role for speaker-0").selectOption("target_child");
  await page.getByLabel("Reviewed utterance utt-0 for speaker-0").check();
  await page.getByLabel("CHAT code for speaker-1").selectOption("THER");
  await page.getByLabel("Participant role for speaker-1").selectOption("therapist");
  await page.getByLabel("Reviewed utterance utt-1 for speaker-1").check();
  await page.getByRole("button", { name: "Save speaker mapping draft" }).click();
  await page.getByRole("button", { name: "Confirm speaker mapping" }).click();

  await expect(page.getByText("Speaker mapping confirmed. Run transcript QA next.")).toBeVisible();
  await expect(page.getByLabel("Speaker for line 1")).toHaveValue("CHI");
  await expect(page.getByLabel("Speaker for line 2")).toHaveValue("THER");
  await expect(page.getByTestId("run-transcript-qa-button")).toBeEnabled();
  await page.getByTestId("run-transcript-qa-button").click();
  await expect(page.getByTestId("attest-transcript-button")).toBeEnabled();
  await page.getByTestId("attest-transcript-button").click();
  await expect(page.getByTestId("transcript-attestation-badge")).toHaveText("Attested");
  expect(unexpectedApiRequests).toEqual([]);
});

test("negative path smoke flow blocks attestation when transcript QA has a critical error", async ({ page }) => {
  const apiPrefixState = recordApiPrefixState(page);
  const mutationResponses = recordMutationResponses(page);

  await pasteTranscript(page, invalidTranscript, mutationResponses);
  await expect(page.getByTestId("run-transcript-qa-button")).toBeEnabled();
  await page.getByTestId("run-transcript-qa-button").click();
  await page.getByRole("button", { name: "QA", exact: true }).click();

  await expect(page.getByTestId("transcript-qa-panel")).toContainText("No child speaker lines were detected.");
  await expect(page.getByTestId("attest-transcript-button")).toBeDisabled();

  expectNoDuplicatedApiPrefix(apiPrefixState);
});

test("safety path smoke flow blocks diagnostic claims in edited report text", async ({ page }) => {
  const apiPrefixState = recordApiPrefixState(page);
  const mutationResponses = recordMutationResponses(page);

  await pasteTranscript(page, validTranscript, mutationResponses);
  await attestTranscript(page);

  await openRecordStep(page);
  await expect(page.getByTestId("extract-features-button")).toBeEnabled({ timeout: 20_000 });
  await page.getByTestId("extract-features-button").click();
  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=findings/);
  await openReportSummary(page);

  await page.getByTestId("generate-report-draft-button").click();
  await expect(page.getByTestId("report-preview")).toHaveValue(/decision-support only/i);
  const reportId = new URL(page.url()).searchParams.get("report_id");
  expect(reportId).toBeTruthy();
  const patchResponse = await page.request.patch(`${backendBaseUrl}/api/v1/reports/${reportId}`, {
    headers: {
      "X-Mock-Role": "therapist",
      "X-Mock-User-Id": "therapist-demo",
      "X-Organization-Id": "pilot_org_001",
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

  expectNoDuplicatedApiPrefix(apiPrefixState);
});
