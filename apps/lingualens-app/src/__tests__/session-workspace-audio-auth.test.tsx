import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionWorkspaceClient } from "@/components/session-workspace-client";
import {
  createInitialWorkflowState,
  loadWorkflowState,
  saveWorkflowState,
} from "@/lib/workflow";
import { routerPush } from "./setup";

describe("SessionWorkspaceClient audio auth path", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.restoreAllMocks();
    routerPush.mockReset();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:protected-audio"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("runs the verified upload-normalize-ASR lifecycle with the strict real-provider contract", async () => {
    const requests: Array<{ url: string; method: string; body?: string; headers: Headers }> = [];
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      requests.push({
        url,
        method,
        body: typeof init?.body === "string" ? init.body : undefined,
        headers: new Headers(init?.headers),
      });
      if (url.endsWith("/settings")) return jsonResponse({ mock_mode: true, auth_mode: "mock" });
      if (url.endsWith("/audio/capabilities")) return jsonResponse(audioCapabilities());
      if (url.endsWith("/sessions/SESSION-UPLOAD") && method === "GET") {
        return jsonResponse({ session_id: "SESSION-UPLOAD", case_id: "CASE-UPLOAD" });
      }
      if (url.endsWith("/cases/CASE-UPLOAD")) {
        return jsonResponse({ case_id: "CASE-UPLOAD", child_code: "SYNTH-001", nickname: "Synthetic sample", consent_status: "granted" });
      }
      if (url.endsWith("/sessions/SESSION-UPLOAD/audio") && method === "GET") return jsonResponse([]);
      if (url.endsWith("/transcripts/TRANSCRIPT-UPLOAD/ml-readiness")) return jsonResponse({ ready: false, provider_id: "none", reason_codes: [], reasons: [] });
      if (url.endsWith("/sessions/SESSION-UPLOAD/ml-decision-support")) return new Response("not found", { status: 404 });
      if (url.endsWith("/sessions/SESSION-UPLOAD/audio/upload") && method === "POST") {
        return jsonResponse({
          job_id: "UPLOAD-JOB",
          status: "queued",
          message: "Private upload intent issued.",
          details: {
            audio_file: { audio_file_id: "AUDIO-UPLOAD", source_asset_version: 3 },
            upload_intent: {
              upload_url: "/audio/AUDIO-UPLOAD/upload-file",
              required_headers: { "content-type": "audio/wav" },
            },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-UPLOAD/upload-file") && method === "PUT") return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-UPLOAD/complete-upload") && method === "POST") return jsonResponse({ upload_status: "uploaded" });
      if (url.endsWith("/audio/AUDIO-UPLOAD/verify-and-normalize") && method === "POST") {
        return jsonResponse({
          source_audio_file_id: "AUDIO-UPLOAD",
          source_asset_version: 3,
          normalized_asset_version: 4,
          source_checksum_sha256: "a".repeat(64),
          normalized_checksum_sha256: "b".repeat(64),
          duration_ms: 60_000,
          verification_status: "verified",
        });
      }
      if (url.endsWith("/sessions/SESSION-UPLOAD/audio/process") && method === "POST") {
        return jsonResponse({ job_id: "ASR-JOB", status: "queued", message: "Real ASR queued." });
      }
      if (url.endsWith("/jobs/ASR-JOB")) {
        return jsonResponse({
          job_id: "ASR-JOB",
          status: "needs_review",
          message: "Draft ready.",
          details: { asr_draft: { transcript_id: "TRANSCRIPT-UPLOAD" } },
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-UPLOAD")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-UPLOAD",
          session_id: "SESSION-UPLOAD",
          case_id: "CASE-UPLOAD",
          version: 1,
          source: "local_faster_whisper_asr_draft",
          raw_text: "@Begin\n*SPK_01:\tsynthetic words .\n@End",
          utterances: [{ utterance_id: "utt-synthetic-1", speaker: "SPK_01", text: "synthetic words" }],
        });
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SessionWorkspaceClient sessionId="SESSION-UPLOAD" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    const file = new File(["versioned-synthetic-wav"], "fixture.wav", { type: "audio/wav" });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("transcript_id=TRANSCRIPT-UPLOAD")));
    const processRequest = requests.find((request) => request.url.endsWith("/audio/process") && request.method === "POST");
    expect(JSON.parse(processRequest?.body ?? "{}")).toEqual({
      audio_file_id: "AUDIO-UPLOAD",
      provider_id: "local_faster_whisper",
      expected_source_asset_version: 3,
      expected_normalized_asset_version: 4,
    });
    expect(requests.map((request) => request.url)).toEqual(expect.arrayContaining([
      expect.stringContaining("/audio/capabilities"),
      expect.stringContaining("/audio/upload"),
      expect.stringContaining("/upload-file"),
      expect.stringContaining("/complete-upload"),
      expect.stringContaining("/verify-and-normalize"),
      expect.stringContaining("/audio/process"),
      expect.stringContaining("/jobs/ASR-JOB"),
      expect.stringContaining("/transcripts/TRANSCRIPT-UPLOAD"),
    ]));
    const uploadRequest = requests.find((request) => request.url.endsWith("/upload-file"));
    expect(uploadRequest?.headers.get("content-type")).toBe("audio/wav");
    expect(uploadRequest?.headers.get("x-user-id")).toBeTruthy();
    expect(JSON.stringify(requests)).not.toContain('"provider_id":"mock"');
    expect(JSON.stringify(requests)).not.toContain('"provider":"manual"');
    expect(JSON.stringify(requests)).not.toContain("draft_text");
    expect(consoleError).not.toHaveBeenCalled();
  });

  it("surfaces decoded-duration rejection from the server without starting ASR", async () => {
    let processCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/settings")) return jsonResponse({ mock_mode: true, auth_mode: "mock" });
      if (url.endsWith("/audio/capabilities")) return jsonResponse(audioCapabilities());
      if (url.endsWith("/sessions/SESSION-LIMIT")) return jsonResponse({ session_id: "SESSION-LIMIT", case_id: "CASE-LIMIT" });
      if (url.endsWith("/cases/CASE-LIMIT")) return jsonResponse({ case_id: "CASE-LIMIT", child_code: "SYNTH-LIMIT", consent_status: "granted" });
      if (url.endsWith("/sessions/SESSION-LIMIT/audio") && method === "GET") return jsonResponse([]);
      if (url.endsWith("/sessions/SESSION-LIMIT/ml-decision-support")) return new Response("not found", { status: 404 });
      if (url.endsWith("/sessions/SESSION-LIMIT/audio/upload")) {
        return jsonResponse({
          details: {
            audio_file: { audio_file_id: "AUDIO-LIMIT", source_asset_version: 1 },
            upload_intent: { upload_url: "/audio/AUDIO-LIMIT/upload-file", required_headers: {} },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-LIMIT/upload-file")) return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-LIMIT/complete-upload")) return jsonResponse({ upload_status: "uploaded" });
      if (url.endsWith("/audio/AUDIO-LIMIT/verify-and-normalize")) {
        return errorResponse(400, {
          detail: {
            error_code: "audio_duration_limit_exceeded",
            configured_limit: 900,
            unit: "seconds",
            remediation: "Upload a file no longer than 15 minutes.",
          },
        });
      }
      if (url.endsWith("/sessions/SESSION-LIMIT/audio/process")) processCalls += 1;
      throw new Error(`Unexpected request: ${method} ${url}`);
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-LIMIT" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["small-client-file"], "plausible.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect((await screen.findAllByText("Upload a file no longer than 15 minutes."))[0]).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry transcription" })).not.toBeInTheDocument();
    expect(processCalls).toBe(0);
  });

  it("offers retry only for a retryable provider failure and polls the backend retry job", async () => {
    let oldJobPolls = 0;
    let retryCalls = 0;
    let uploadIntentCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/settings")) return jsonResponse({ mock_mode: true, auth_mode: "mock" });
      if (url.endsWith("/audio/capabilities")) return jsonResponse(audioCapabilities());
      if (url.endsWith("/sessions/SESSION-RETRY") && method === "GET") return jsonResponse({ session_id: "SESSION-RETRY", case_id: "CASE-RETRY" });
      if (url.endsWith("/cases/CASE-RETRY")) return jsonResponse({ case_id: "CASE-RETRY", child_code: "SYNTH-RETRY", consent_status: "granted" });
      if (url.endsWith("/sessions/SESSION-RETRY/audio") && method === "GET") return jsonResponse([]);
      if (url.endsWith("/sessions/SESSION-RETRY/ml-decision-support")) return new Response("not found", { status: 404 });
      if (url.endsWith("/sessions/SESSION-RETRY/audio/upload")) {
        uploadIntentCalls += 1;
        return jsonResponse({
          details: {
            audio_file: { audio_file_id: "AUDIO-RETRY", source_asset_version: 1 },
            upload_intent: { upload_url: "/audio/AUDIO-RETRY/upload-file", required_headers: {} },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-RETRY/upload-file")) return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-RETRY/complete-upload")) return jsonResponse({ upload_status: "uploaded" });
      if (url.endsWith("/audio/AUDIO-RETRY/verify-and-normalize")) {
        return jsonResponse({
          source_audio_file_id: "AUDIO-RETRY",
          source_asset_version: 1,
          normalized_asset_version: 1,
          source_checksum_sha256: "a".repeat(64),
          normalized_checksum_sha256: "b".repeat(64),
          duration_ms: 60_000,
          verification_status: "verified",
        });
      }
      if (url.endsWith("/sessions/SESSION-RETRY/audio/process")) return jsonResponse({ job_id: "JOB-FAILED", status: "queued", message: "queued" });
      if (url.endsWith("/jobs/JOB-FAILED") && method === "GET") {
        oldJobPolls += 1;
        return jsonResponse({
          job_id: "JOB-FAILED",
          status: "failed",
          message: "Provider unavailable.",
          error_code: "provider_unavailable",
          details: {
            retry_allowed: true,
            provider_reason_code: "model_artifact_missing",
            provider_remediation: "Install the pinned faster-whisper model artifact and retry.",
          },
        });
      }
      if (url.endsWith("/jobs/JOB-FAILED/retry") && method === "POST") {
        retryCalls += 1;
        return jsonResponse({ job_id: "JOB-RETRY", status: "queued", message: "Retry queued." });
      }
      if (url.endsWith("/jobs/JOB-RETRY") && method === "GET") {
        return jsonResponse({
          job_id: "JOB-RETRY",
          status: "needs_review",
          message: "Draft ready.",
          details: { asr_draft: { transcript_id: "TRANSCRIPT-RETRY" } },
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-RETRY")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-RETRY",
          session_id: "SESSION-RETRY",
          case_id: "CASE-RETRY",
          version: 1,
          source: "local_faster_whisper_asr_draft",
          raw_text: "@Begin\n*SPK_01:\tretried synthetic words .\n@End",
          utterances: [{ utterance_id: "utt-retry-1", speaker: "SPK_01", text: "retried synthetic words" }],
        });
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-RETRY" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["retry-audio"], "retry.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(
      await screen.findAllByText("Install the pinned faster-whisper model artifact and retry."),
    ).not.toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Retry transcription" }));

    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("transcript_id=TRANSCRIPT-RETRY")));
    expect(retryCalls).toBe(1);
    expect(oldJobPolls).toBe(1);
    expect(uploadIntentCalls).toBe(1);
  });

  it("stops polling after repeated network failures without inventing a successful draft", async () => {
    let jobPolls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/settings")) return jsonResponse({ mock_mode: true, auth_mode: "mock" });
      if (url.endsWith("/audio/capabilities")) return jsonResponse(audioCapabilities());
      if (url.endsWith("/sessions/SESSION-NETWORK") && method === "GET") {
        return jsonResponse({ session_id: "SESSION-NETWORK", case_id: "CASE-NETWORK" });
      }
      if (url.endsWith("/cases/CASE-NETWORK")) {
        return jsonResponse({ case_id: "CASE-NETWORK", child_code: "SYNTH-NETWORK", consent_status: "granted" });
      }
      if (url.endsWith("/sessions/SESSION-NETWORK/audio") && method === "GET") return jsonResponse([]);
      if (url.endsWith("/sessions/SESSION-NETWORK/ml-decision-support")) return new Response("not found", { status: 404 });
      if (url.endsWith("/sessions/SESSION-NETWORK/audio/upload")) {
        return jsonResponse({
          details: {
            audio_file: { audio_file_id: "AUDIO-NETWORK", source_asset_version: 1 },
            upload_intent: { upload_url: "/audio/AUDIO-NETWORK/upload-file", required_headers: {} },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-NETWORK/upload-file")) return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-NETWORK/complete-upload")) return jsonResponse({ upload_status: "uploaded" });
      if (url.endsWith("/audio/AUDIO-NETWORK/verify-and-normalize")) {
        return jsonResponse({
          source_audio_file_id: "AUDIO-NETWORK",
          source_asset_version: 1,
          normalized_asset_version: 1,
          source_checksum_sha256: "a".repeat(64),
          normalized_checksum_sha256: "b".repeat(64),
          duration_ms: 60_000,
          verification_status: "verified",
        });
      }
      if (url.endsWith("/sessions/SESSION-NETWORK/audio/process")) {
        return jsonResponse({ job_id: "JOB-NETWORK", status: "queued", message: "queued" });
      }
      if (url.endsWith("/jobs/JOB-NETWORK")) {
        jobPolls += 1;
        throw new TypeError("synthetic network failure");
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-NETWORK" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["network-audio"], "network.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(await screen.findByText(/could not be verified after repeated network failures/i)).toBeInTheDocument();
    expect(jobPolls).toBe(3);
    expect(routerPush).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Review transcript" })).not.toBeInTheDocument();
  });

  it("hydrates protected backend audio into a blob URL for transcript playback", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      if (url.endsWith("/sessions/SESSION-123")) {
        return jsonResponse({
          session_id: "SESSION-123",
          case_id: "CASE-123",
          transcript_id: "TRANSCRIPT-123",
        });
      }

      if (url.endsWith("/transcripts/TRANSCRIPT-123")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-123",
          session_id: "SESSION-123",
          case_id: "CASE-123",
          raw_text: "@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child\n*CHI:\tBlue car.\n@End",
          therapist_attested: true,
          qa_status: "pass",
          qa_issues: [],
          utterances: [
            { utterance_id: "utt-1", speaker: "CHI", text: "Blue car." },
          ],
        });
      }

      if (url.endsWith("/cases/CASE-123")) {
        return jsonResponse({
          case_id: "CASE-123",
          child_code: "CASE-123",
          nickname: "Ava M.",
        });
      }

      if (url.endsWith("/sessions/SESSION-123/audio")) {
        return jsonResponse([
          {
            audio_file_id: "AUDIO-123",
            session_id: "SESSION-123",
            case_id: "CASE-123",
            original_filename: "session.webm",
            content_type: "audio/webm",
            size_bytes: 128,
            upload_status: "uploaded",
          },
        ]);
      }

      if (url.endsWith("/audio/AUDIO-123/file")) {
        return new Response(new Blob(["audio-bytes"], { type: "audio/webm" }), {
          status: 200,
          headers: { "Content-Type": "audio/webm" },
        });
      }

      if (url.endsWith("/transcripts/TRANSCRIPT-123/ml-readiness")) {
        return jsonResponse({
          ready: false,
          provider_id: "mock",
          reason_codes: [],
          reasons: [],
        });
      }

      if (url.endsWith("/sessions/SESSION-123/ml-decision-support")) {
        return new Response("not found", { status: 404 });
      }

      return jsonResponse({});
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<SessionWorkspaceClient sessionId="SESSION-123" view="transcript" />);

    const audio = await screen.findByLabelText("Workspace audio playback") as HTMLAudioElement;

    await waitFor(() => {
      expect(audio).toHaveAttribute("src", "blob:protected-audio");
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/audio/AUDIO-123/file"),
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("deduplicates transcript saves and ignores a late settlement after navigation", async () => {
    let resolveSave!: (response: Response) => void;
    const deferredSave = new Promise<Response>((resolve) => { resolveSave = resolve; });
    let saveRequests = 0;

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/settings")) return jsonResponse({});
      if (url.endsWith("/sessions/SESSION-SAVE")) {
        return jsonResponse({ session_id: "SESSION-SAVE", case_id: "CASE-SAVE", transcript_id: "TRANSCRIPT-SAVE" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-SAVE") && init?.method === "PATCH") {
        saveRequests += 1;
        return deferredSave;
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-SAVE")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-SAVE",
          session_id: "SESSION-SAVE",
          case_id: "CASE-SAVE",
          version: 1,
          raw_text: "@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child\n*CHI:\tBlue car.\n@End",
          therapist_attested: true,
          qa_status: "pass",
          qa_issues: [],
          utterances: [{ utterance_id: "utt-save", speaker: "CHI", text: "Blue car." }],
        });
      }
      if (url.endsWith("/cases/CASE-SAVE")) return jsonResponse({ case_id: "CASE-SAVE", nickname: "Ava M.", consent_status: "granted" });
      if (url.endsWith("/sessions/SESSION-SAVE/audio")) return jsonResponse([]);
      if (url.endsWith("/transcripts/TRANSCRIPT-SAVE/ml-readiness")) {
        return jsonResponse({ ready: false, provider_id: "mock", reason_codes: [], reasons: [] });
      }
      if (url.endsWith("/sessions/SESSION-SAVE/ml-decision-support")) return new Response("not found", { status: 404 });
      throw new Error(`Unexpected request: ${url}`);
    }));

    const workspace = render(<SessionWorkspaceClient sessionId="SESSION-SAVE" view="transcript" />);
    const editor = await screen.findByLabelText("Utterance text 1");
    fireEvent.change(editor, { target: { value: "Blue car changed." } });

    const saveButton = screen.getByRole("button", { name: "Save draft" });
    fireEvent.click(saveButton);
    fireEvent.click(saveButton);
    await waitFor(() => expect(saveRequests).toBe(1));

    workspace.unmount();
    await act(async () => {
      resolveSave(jsonResponse({
        transcript_id: "TRANSCRIPT-SAVE",
        session_id: "SESSION-SAVE",
        case_id: "CASE-SAVE",
        version: 2,
        raw_text: "@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child\n*CHI:\tBlue car changed.\n@End",
        utterances: [{ utterance_id: "utt-save", speaker: "CHI", text: "Blue car changed." }],
      }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(saveRequests).toBe(1);
    expect(loadWorkflowState().backendTranscriptVersion).toBe(1);
  });

  it.each([
    [
      "forbidden",
      403,
      "You are not authorized to access this persisted workflow.",
      false,
    ],
    [
      "not found",
      404,
      "The requested persisted workflow was not found.",
      false,
    ],
    [
      "network failure",
      undefined,
      "Could not load the persisted workflow. Check the backend and retry.",
      true,
    ],
  ] as const)(
    "fails closed on an explicit session locator %s without restoring stored clinical state",
    async (_scenario, status, expectedError, backendUnavailable) => {
      saveWorkflowState({
        ...createInitialWorkflowState(),
        sessionId: "PRIOR-SESSION",
        backendSessionId: "PRIOR-SESSION",
        backendTranscriptId: "PRIOR-TRANSCRIPT",
        transcriptText: "@Begin\n*CHI:\tPrior private transcript.\n@End",
        transcriptLines: [{
          lineId: "prior-line",
          speaker: "CHI",
          text: "Prior private transcript.",
        }],
        transcriptReady: true,
        transcriptReviewStatus: "in_review",
      });

      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/settings")) return jsonResponse({});
        if (url.endsWith("/sessions/REQUESTED-SESSION")) {
          if (status === undefined) throw new TypeError("Failed to fetch");
          return new Response(JSON.stringify({ detail: _scenario }), { status });
        }
        throw new Error(`Unexpected request: ${url}`);
      }));

      render(
        <SessionWorkspaceClient
          sessionId="REQUESTED-SESSION"
          view="transcript"
        />,
      );

      expect(await screen.findByText(expectedError)).toBeInTheDocument();

      if (backendUnavailable) {
        expect(screen.getByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
      } else {
        expect(screen.queryByText("Backend unavailable — local workspace mode")).not.toBeInTheDocument();
      }

      expect(screen.queryByDisplayValue("Prior private transcript.")).not.toBeInTheDocument();
      const persisted = loadWorkflowState();
      expect(persisted.sessionId).toBeUndefined();
      expect(persisted.backendSessionId).toBeUndefined();
      expect(persisted.backendTranscriptId).toBeUndefined();
      expect(persisted).toMatchObject({
        transcriptText: "",
        transcriptLines: [],
        transcriptReady: false,
        transcriptReviewStatus: "not_started",
      });
    },
  );
});

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function errorResponse(status: number, data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function audioCapabilities() {
  return {
    milestone: "v1.7.0-testbed",
    max_size_bytes: 100 * 1024 * 1024,
    max_duration_seconds: 15 * 60,
    supported_formats: ["wav", "mp3"],
    processing_state: "available",
    unavailable_reason: null,
    normalization: { channels: 1, sample_rate_hz: 16_000, format: "wav_pcm_s16le" },
    browser_recording: { state: "experimental_unavailable", blocks_milestone: false },
  };
}
