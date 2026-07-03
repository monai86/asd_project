import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import { renderAsyncPage } from "@/__tests__/setup";
import RecordPage from "@/app/record/page";
import ResultsPage from "@/app/results/page";

beforeEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("session intake flow", () => {
  it("renders the four-step session intake flow and supports step navigation", async () => {
    await renderAsyncPage(RecordPage);

    expect(screen.getByRole("heading", { name: "Session Intake" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Session Details" })).toBeInTheDocument();
    expect(screen.getAllByText("Source Material").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Transcript Setup").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Review & Start").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.change(screen.getByLabelText("Session goals"), { target: { value: "Support joint attention" } });

    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    expect(await screen.findByRole("heading", { name: "Source Material" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Continue to Transcript Setup" }));

    expect(await screen.findByRole("heading", { name: "Transcript Setup" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Back to Source Material" }));
    expect(await screen.findByRole("heading", { name: "Source Material" })).toBeInTheDocument();
  });

  it("switches between source material types without breaking the existing workflows", async () => {
    await renderAsyncPage(RecordPage);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    await screen.findByRole("heading", { name: "Source Material" });

    fireEvent.click(screen.getByRole("button", { name: "Paste transcript" }));
    expect(screen.getByRole("textbox", { name: "Pasted transcript text" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Upload .cha" }));
    expect(screen.getByLabelText("CHA transcript file")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Upload audio" }));
    expect(screen.getByRole("button", { name: "Mark audio upload as experimental" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Record in browser" }));
    expect(screen.getByRole("button", { name: "Start recording" })).toBeInTheDocument();
  });

  it("keeps Start Transcript Review disabled until required intake fields are valid", async () => {
    await renderAsyncPage(RecordPage);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.change(screen.getByLabelText("Session goals"), { target: { value: "Support turn-taking" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    await screen.findByRole("heading", { name: "Source Material" });
    fireEvent.click(screen.getByRole("button", { name: "Paste transcript" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Pasted transcript text" }), {
      target: { value: "THER: hello\nCHI: hi" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Transcript Setup" }));

    await screen.findByRole("heading", { name: "Transcript Setup" });
    fireEvent.change(screen.getByLabelText("Speaker labels"), { target: { value: "THER = Therapist\nCHI = Child" } });
    fireEvent.change(screen.getByLabelText("Session metadata"), { target: { value: "Collected in clinic with caregiver present." } });
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "eng" } });
    fireEvent.change(screen.getByLabelText("Sample type"), { target: { value: "conversation" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Review & Start" }));

    expect(await screen.findByRole("button", { name: "Start Transcript Review" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Back to Transcript Setup" }));
    fireEvent.click(await screen.findByLabelText("I will review speaker labels and transcript wording before attestation."));
    fireEvent.click(screen.getByLabelText("I understand feature extraction stays locked until transcript review, QA, and attestation are complete."));
    fireEvent.click(screen.getByRole("button", { name: "Continue to Review & Start" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Start Transcript Review" })).toBeEnabled();
    });
  });

  it("requires explicit confirmation before audio upload transcription begins", async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
      getAudioTracks: () => [{ addEventListener: vi.fn(), removeEventListener: vi.fn() }]
    } as unknown as MediaStream;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => stream) }
    });

    class TestMediaRecorder {
      static isTypeSupported() { return true; }
      state: RecordingState = "inactive";
      mimeType = "audio/webm";
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onstop: (() => void) | null = null;
      constructor(public mediaStream: MediaStream) {}
      start() { this.state = "recording"; }
      pause() { this.state = "paused"; }
      resume() { this.state = "recording"; }
      stop() {
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["audio"], { type: this.mimeType }) } as BlobEvent);
        this.onstop?.();
      }
    }

    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: TestMediaRecorder });
    Object.defineProperty(globalThis, "MediaRecorder", { configurable: true, value: TestMediaRecorder });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:session-intake") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });

    await renderAsyncPage(RecordPage);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    await screen.findByRole("heading", { name: "Source Material" });
    fireEvent.click(screen.getByRole("button", { name: "Record in browser" }));
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));

    await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));

    expect(await screen.findByRole("region", { name: "Audio upload confirmation" })).toBeInTheDocument();
  });

  it("blocks intake details step when caregiver consent is pending, and unlocks on verification form submission", async () => {
    let updateCaseCalled = false;
    let updateCasePayload: any = null;

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases/case_test_pending") && init?.method === "PATCH") {
        updateCaseCalled = true;
        updateCasePayload = JSON.parse(init.body as string);
        return jsonResponse({
          case_id: "case_test_pending",
          child_code: "C-test-pending",
          nickname: "Ava M.",
          consent_status: "granted",
        });
      }
      if (url.endsWith("/cases/case_test_pending")) {
        return jsonResponse({
          case_id: "case_test_pending",
          child_code: "C-test-pending",
          nickname: "Ava M.",
          consent_status: "pending",
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    await renderAsyncPage(RecordPage, { searchParams: { case_id: "case_test_pending" } });

    // Expect Consent Verification Required card to be visible
    expect(await screen.findByRole("heading", { name: "Consent Verification Required" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Child or client")).not.toBeInTheDocument();

    // Check the box
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);

    // Submit
    const submitButton = screen.getByRole("button", { name: "Verify & Grant Consent" });
    fireEvent.click(submitButton);

    // Wait for form to unlock and regular details step to show
    expect(await screen.findByLabelText("Child or client")).toBeInTheDocument();
    expect(updateCaseCalled).toBe(true);
    expect(updateCasePayload.consent_status).toBe("granted");
  });

  it("renders the ML-pending loading screen when features are extracted but ML decision support is missing, and supports skipping to draft report", async () => {
    let generateReportCalled = false;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/sessions/session-test")) {
        return jsonResponse({
          session_id: "session-test",
          case_id: "case-test",
          feature_set_id: "feat-test",
          transcript_id: "transcript-test",
          report_id: null,
        });
      }
      if (url.endsWith("/transcripts/transcript-test")) {
        return jsonResponse({
          transcript_id: "transcript-test",
          session_id: "session-test",
          case_id: "case-test",
          therapist_attested: true,
          qa_status: "pass",
          raw_text: "@UTF8\n@Begin\n@Participants:\tCHI Child, THER Therapist\n*THER:\thello .\n*CHI:\thi .\n@End",
        });
      }
      if (url.endsWith("/cases/case-test")) {
        return jsonResponse({
          case_id: "case-test",
          nickname: "Ava M.",
          consent_status: "granted",
        });
      }
      if (url.endsWith("/sessions/session-test/audio-files")) {
        return jsonResponse([]);
      }
      if (url.includes("/ml-readiness")) {
        return jsonResponse({ ready: true, providerId: "mock", reasonCodes: [], reasons: [] });
      }
      if (url.includes("/ml-review")) {
        return errorResponse(404, { detail: "Not found" });
      }
      if (url.endsWith("/sessions/session-test/features")) {
        return jsonResponse({
          session_id: "session-test",
          totalUtterances: 10,
          childUtterances: 5,
          adultUtterances: 5,
        });
      }
      if (url.endsWith("/features/definitions")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/sessions/session-test/reports/draft") && init?.method === "POST") {
        generateReportCalled = true;
        return jsonResponse({
          report_id: "report-test",
          content_markdown: "# Therapist Progress Report",
        });
      }
      if (url.endsWith("/settings")) {
        return jsonResponse({
          mock_mode: true,
          auth_mode: "mock",
          model_version: "reference",
          feature_schema: "v1",
          guideline_mapping: "v1",
          user_roles: ["therapist"],
          data_retention: "standard",
          consent_policy: "standard",
          pipeline_settings: {
            audio_processing: "local",
            job_queue_mode: "sync",
            repository_mode: "in_memory",
            storage_mode: "local",
          }
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    await renderAsyncPage(ResultsPage, { searchParams: { session_id: "session-test" } });

    // Expect the ML-pending Observer review card with safety notice
    expect(await screen.findByRole("heading", { name: "Analyzing linguistic observations..." })).toBeInTheDocument();
    expect(screen.getByText(/ระบบสนับสนุนการตัดสินใจทางคลินิก/)).toBeInTheDocument();

    const skipButton = screen.getByRole("button", { name: "Skip to Draft Report" });
    fireEvent.click(skipButton);

    await waitFor(() => {
      expect(generateReportCalled).toBe(true);
    });
  });
});

function jsonResponse(body: unknown) {
  return {
    ok: true,
    json: async () => body,
    text: async () => JSON.stringify(body)
  } as Response;
}

function errorResponse(status: number, body: unknown) {
  return {
    ok: false,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body)
  } as Response;
}
