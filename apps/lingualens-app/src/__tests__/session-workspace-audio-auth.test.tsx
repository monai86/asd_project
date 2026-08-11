import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionWorkspaceClient } from "@/components/session-workspace-client";
import {
  describeAudioWorkflowFailure,
  sessionWorkflowService,
  type AudioUploadIntent,
} from "@/features/sessions/services/session-workflow-service";
import { ApiError } from "@/lib/api";
import {
  WORKFLOW_STORAGE_KEY,
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
    const consoleLog = vi.spyOn(console, "log").mockImplementation(() => undefined);
    const consoleWarn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const consoleDebug = vi.spyOn(console, "debug").mockImplementation(() => undefined);
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
          session_id: "SESSION-UPLOAD",
          status: "queued",
          message: "Private upload intent issued.",
          details: {
            audio_file: { audio_file_id: "AUDIO-UPLOAD", session_id: "SESSION-UPLOAD", source_asset_version: 3 },
            upload_intent: {
              audio_file_id: "AUDIO-UPLOAD",
              upload_url: "/audio/AUDIO-UPLOAD/upload-file",
              required_headers: { "content-type": "audio/wav" },
            },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-UPLOAD/upload-file") && method === "PUT") return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-UPLOAD/complete-upload") && method === "POST") return jsonResponse({ audio_file_id: "AUDIO-UPLOAD", source_asset_version: 3, upload_status: "uploaded" });
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
        return jsonResponse({
          job_id: "ASR-JOB",
          session_id: "SESSION-UPLOAD",
          status: "queued",
          message: "Real ASR queued.",
          details: audioJobDetails("AUDIO-UPLOAD", {
            source_asset_version: 3,
            normalized_asset_version: 4,
          }),
        });
      }
      if (url.endsWith("/jobs/ASR-JOB")) {
        return jsonResponse({
          job_id: "ASR-JOB",
          session_id: "SESSION-UPLOAD",
          status: "needs_review",
          message: "Draft ready.",
          details: audioJobDetails("AUDIO-UPLOAD", {
            source_asset_version: 3,
            normalized_asset_version: 4,
            asr_draft: { transcript_id: "TRANSCRIPT-UPLOAD" },
          }),
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-UPLOAD")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-UPLOAD",
          session_id: "SESSION-UPLOAD",
          case_id: "CASE-UPLOAD",
          version: 1,
          source: "asr_draft:local_faster_whisper",
          asr_provenance: asrProvenance("AUDIO-UPLOAD", "ASR-JOB", 3, 4),
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
    const lifecycleStages = requests.flatMap((request) => {
      if (request.url.endsWith("/audio/upload") && request.method === "POST") return ["intent"];
      if (request.url.endsWith("/upload-file") && request.method === "PUT") return ["bytes"];
      if (request.url.endsWith("/complete-upload") && request.method === "POST") return ["complete"];
      if (request.url.endsWith("/verify-and-normalize") && request.method === "POST") return ["normalize"];
      if (request.url.endsWith("/audio/process") && request.method === "POST") return ["process"];
      if (request.url.endsWith("/jobs/ASR-JOB") && request.method === "GET") return ["poll"];
      if (request.url.endsWith("/transcripts/TRANSCRIPT-UPLOAD") && request.method === "GET") return ["transcript"];
      return [];
    });
    expect(lifecycleStages).toEqual([
      "intent",
      "bytes",
      "complete",
      "normalize",
      "process",
      "poll",
      "transcript",
    ]);
    const uploadRequest = requests.find((request) => request.url.endsWith("/upload-file"));
    expect(uploadRequest?.headers.get("content-type")).toBe("audio/wav");
    expect(uploadRequest?.headers.get("x-user-id")).toBeTruthy();
    expect(JSON.stringify(requests)).not.toContain('"provider_id":"mock"');
    expect(JSON.stringify(requests)).not.toContain('"provider":"manual"');
    expect(JSON.stringify(requests)).not.toContain("draft_text");
    expect(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "").not.toContain("fixture.wav");
    expect(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "").not.toContain("/upload-file");
    expect(consoleError).not.toHaveBeenCalled();
    expect(consoleLog).not.toHaveBeenCalled();
    expect(consoleWarn).not.toHaveBeenCalled();
    expect(consoleDebug).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Paste transcript" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Pasted transcript text" })).toBeInTheDocument());
    expect(loadWorkflowState()).toMatchObject({
      source: "paste-transcript",
      transcriptReplacementRequired: true,
      replacementTranscriptId: "TRANSCRIPT-UPLOAD",
      replacementTranscriptVersion: 1,
      transcriptText: "",
      transcriptLines: [],
      transcriptReady: false,
      transcriptAttested: false,
      qaStatus: "not_run",
      analysisStatus: "not_started",
      featuresExtracted: false,
      reportStatus: "not_started",
    });
    expect(loadWorkflowState().backendTranscriptId).toBeUndefined();
    expect(loadWorkflowState().backendTranscriptVersion).toBeUndefined();
    expect(loadWorkflowState().backendReportId).toBeUndefined();
    expect(loadWorkflowState().featureSetId).toBeUndefined();
  });

  it("preserves an actionable string-detail remediation from an upload failure", () => {
    expect(describeAudioWorkflowFailure(new ApiError(
      503,
      JSON.stringify({
        detail: "Upload state could not be returned safely. Retry the upload status request.",
      }),
    ))).toEqual({
      code: "http_503",
      message: "Upload state could not be returned safely. Retry the upload status request.",
      retryable: false,
    });
  });

  it("fails closed when the capability response omits normalization provenance", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/settings")) return jsonResponse({ mock_mode: true, auth_mode: "mock" });
      if (url.endsWith("/audio/capabilities")) {
        const { normalization: _normalization, ...incomplete } = audioCapabilities();
        return jsonResponse(incomplete);
      }
      if (url.endsWith("/sessions/SESSION-CAPABILITY") && method === "GET") {
        return jsonResponse({ session_id: "SESSION-CAPABILITY", case_id: "CASE-CAPABILITY" });
      }
      if (url.endsWith("/cases/CASE-CAPABILITY")) {
        return jsonResponse({ case_id: "CASE-CAPABILITY", child_code: "SYNTH-CAPABILITY", consent_status: "granted" });
      }
      if (url.endsWith("/sessions/SESSION-CAPABILITY/audio")) return jsonResponse([]);
      if (url.endsWith("/sessions/SESSION-CAPABILITY/ml-decision-support")) return new Response("not found", { status: 404 });
      throw new Error(`Unexpected request: ${method} ${url}`);
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-CAPABILITY" view="intake" mode="audio" />);

    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeDisabled());
    expect(screen.getByText(/audio processing unavailable/i)).toBeInTheDocument();
  });

  it("rejects a present malformed required-headers contract before uploading bytes", async () => {
    let byteUploads = 0;
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-HEADERS",
      caseId: "CASE-HEADERS",
      audioFileId: "AUDIO-HEADERS",
      jobId: "JOB-HEADERS",
      onIntent: async () => jsonResponse({
        session_id: "SESSION-HEADERS",
        details: {
          audio_file: { audio_file_id: "AUDIO-HEADERS", session_id: "SESSION-HEADERS", source_asset_version: 1 },
          upload_intent: {
            audio_file_id: "AUDIO-HEADERS",
            upload_url: "/audio/AUDIO-HEADERS/upload-file",
            required_headers: ["content-type", "audio/wav"],
          },
        },
      }),
      onUpload: async () => {
        byteUploads += 1;
        return jsonResponse({ status: "success" });
      },
      onJob: async () => jsonResponse({}),
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-HEADERS" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["headers-audio"], "headers.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(await screen.findByText("Error code: audio_upload_intent_incomplete")).toBeInTheDocument();
    expect(byteUploads).toBe(0);
  });

  it("rejects upload and normalization responses from a different source lineage", async () => {
    const file = new File(["lineage-contract"], "contract.wav", { type: "audio/wav" });
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      session_id: "SESSION-CONTRACT",
      details: {
        audio_file: {
          audio_file_id: "AUDIO-CONTRACT",
          session_id: "OTHER-SESSION",
          source_asset_version: 2,
        },
        upload_intent: {
          audio_file_id: "OTHER-AUDIO",
          upload_url: "/audio/OTHER-AUDIO/upload-file",
          required_headers: {},
        },
      },
    })));

    await expect(
      sessionWorkflowService.createAudioUploadIntent("SESSION-CONTRACT", file),
    ).rejects.toThrow("audio_upload_intent_incomplete");

    const intent: AudioUploadIntent = {
      sessionId: "SESSION-CONTRACT",
      audioFileId: "AUDIO-CONTRACT",
      sourceAssetVersion: 2,
      uploadUrl: "/audio/AUDIO-CONTRACT/upload-file",
      requiredHeaders: {},
    };
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      source_audio_file_id: "AUDIO-CONTRACT",
      source_asset_version: 3,
      normalized_asset_version: 1,
      source_checksum_sha256: "a".repeat(64),
      normalized_checksum_sha256: "b".repeat(64),
      duration_ms: 60_000,
      verification_status: "verified",
    })));

    await expect(sessionWorkflowService.verifyAndNormalizeAudio(intent)).rejects.toThrow(
      "audio_normalization_response_invalid",
    );
  });

  it("uses an exact replacement CAS instead of patching an ASR transcript as manual text", async () => {
    let requestUrl = "";
    let requestBody: Record<string, unknown> = {};
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      requestUrl = String(input);
      requestBody = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
      return jsonResponse({
        transcript_id: "TRANSCRIPT-MANUAL-REPLACEMENT",
        session_id: "SESSION-REPLACEMENT",
        case_id: "CASE-REPLACEMENT",
        source: "manual_entry",
        version: 1,
        raw_text: "@Begin\n*UNK:\treplacement words .\n@End",
        utterances: [{ utterance_id: "replacement-1", speaker: "UNK", text: "replacement words" }],
      });
    }));

    const saved = await sessionWorkflowService.saveTranscript({
      sessionId: "SESSION-REPLACEMENT",
      transcriptId: undefined,
      source: "paste-transcript",
      originalText: "replacement words",
      normalizedText: "replacement words",
      replaceExisting: true,
      expectedExistingTranscriptId: "TRANSCRIPT-ASR-OLD",
      expectedExistingTranscriptVersion: 4,
    });

    expect(requestUrl).toContain("/sessions/SESSION-REPLACEMENT/transcripts/manual");
    expect(requestUrl).not.toContain("/transcripts/TRANSCRIPT-ASR-OLD");
    expect(requestBody).toMatchObject({
      text: "replacement words",
      replace_existing: true,
      expected_existing_transcript_id: "TRANSCRIPT-ASR-OLD",
      expected_existing_transcript_version: 4,
    });
    expect(saved).toMatchObject({
      transcript_id: "TRANSCRIPT-MANUAL-REPLACEMENT",
      session_id: "SESSION-REPLACEMENT",
      source: "manual_entry",
      version: 1,
    });
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
          session_id: "SESSION-LIMIT",
          details: {
            audio_file: { audio_file_id: "AUDIO-LIMIT", session_id: "SESSION-LIMIT", source_asset_version: 1 },
            upload_intent: { audio_file_id: "AUDIO-LIMIT", upload_url: "/audio/AUDIO-LIMIT/upload-file", required_headers: {} },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-LIMIT/upload-file")) return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-LIMIT/complete-upload")) return jsonResponse({ audio_file_id: "AUDIO-LIMIT", source_asset_version: 1, upload_status: "uploaded" });
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
    let resolveRetryJob: ((response: Response) => void) | undefined;
    const retryJobResponse = new Promise<Response>((resolve) => {
      resolveRetryJob = resolve;
    });
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
          session_id: "SESSION-RETRY",
          details: {
            audio_file: { audio_file_id: "AUDIO-RETRY", session_id: "SESSION-RETRY", source_asset_version: 1 },
            upload_intent: { audio_file_id: "AUDIO-RETRY", upload_url: "/audio/AUDIO-RETRY/upload-file", required_headers: {} },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-RETRY/upload-file")) return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-RETRY/complete-upload")) return jsonResponse({ audio_file_id: "AUDIO-RETRY", source_asset_version: 1, upload_status: "uploaded" });
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
      if (url.endsWith("/sessions/SESSION-RETRY/audio/process")) {
        return jsonResponse({
          job_id: "JOB-FAILED",
          session_id: "SESSION-RETRY",
          status: "queued",
          message: "queued",
          details: audioJobDetails("AUDIO-RETRY"),
        });
      }
      if (url.endsWith("/jobs/JOB-FAILED") && method === "GET") {
        oldJobPolls += 1;
        return jsonResponse({
          job_id: "JOB-FAILED",
          session_id: "SESSION-RETRY",
          status: "failed",
          message: "Provider unavailable.",
          error_code: "provider_unavailable",
          details: audioJobDetails("AUDIO-RETRY", {
            retry_allowed: true,
            provider_reason_code: "model_artifact_missing",
            provider_remediation: "Install the pinned faster-whisper model artifact and retry.",
          }),
        });
      }
      if (url.endsWith("/jobs/JOB-FAILED/retry") && method === "POST") {
        retryCalls += 1;
        return jsonResponse({
          job_id: "JOB-RETRY",
          session_id: "SESSION-RETRY",
          status: "queued",
          message: "Retry queued.",
          details: audioJobDetails("AUDIO-RETRY"),
        });
      }
      if (url.endsWith("/jobs/JOB-RETRY") && method === "GET") {
        return retryJobResponse;
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-RETRY")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-RETRY",
          session_id: "SESSION-RETRY",
          case_id: "CASE-RETRY",
          version: 1,
          source: "asr_draft:local_faster_whisper",
          asr_provenance: asrProvenance("AUDIO-RETRY", "JOB-RETRY"),
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

    await waitFor(() => expect(retryCalls).toBe(1));
    expect(loadWorkflowState()).toMatchObject({
      transcriptionJobId: "JOB-RETRY",
      transcriptionJobStatus: "queued",
    });
    resolveRetryJob?.(jsonResponse({
      job_id: "JOB-RETRY",
      session_id: "SESSION-RETRY",
      status: "needs_review",
      message: "Draft ready.",
      details: audioJobDetails("AUDIO-RETRY", {
        asr_draft: { transcript_id: "TRANSCRIPT-RETRY" },
      }),
    }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("transcript_id=TRANSCRIPT-RETRY")));
    expect(oldJobPolls).toBe(1);
    expect(uploadIntentCalls).toBe(1);
  });

  it("persists an immediate failed process response without waiting for a poll", async () => {
    let jobPolls = 0;
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-IMMEDIATE",
      caseId: "CASE-IMMEDIATE",
      audioFileId: "AUDIO-IMMEDIATE",
      jobId: "JOB-IMMEDIATE",
      onProcess: async () => jsonResponse({
        job_id: "JOB-IMMEDIATE",
        session_id: "SESSION-IMMEDIATE",
        status: "failed",
        message: "Provider unavailable.",
        error_code: "provider_unavailable",
        details: audioJobDetails("AUDIO-IMMEDIATE", {
          retry_allowed: true,
          provider_remediation: "Restore the pinned model artifact and retry.",
        }),
      }),
      onJob: async () => {
        jobPolls += 1;
        return jsonResponse({});
      },
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-IMMEDIATE" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["immediate-audio"], "immediate.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(await screen.findAllByText("Restore the pinned model artifact and retry.")).not.toHaveLength(0);
    expect(loadWorkflowState()).toMatchObject({
      transcriptionJobId: "JOB-IMMEDIATE",
      transcriptionJobStatus: "failed",
      transcriptionJobMessage: "Restore the pinned model artifact and retry.",
    });
    expect(jobPolls).toBe(0);
  });

  it("persists the new retry identity when retry fails immediately", async () => {
    let jobPolls = 0;
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-RETRY-IMMEDIATE",
      caseId: "CASE-RETRY-IMMEDIATE",
      audioFileId: "AUDIO-RETRY-IMMEDIATE",
      jobId: "JOB-INITIAL-FAILED",
      onProcess: async () => jsonResponse({
        job_id: "JOB-INITIAL-FAILED",
        session_id: "SESSION-RETRY-IMMEDIATE",
        status: "failed",
        message: "Provider unavailable.",
        error_code: "provider_unavailable",
        details: audioJobDetails("AUDIO-RETRY-IMMEDIATE", {
          retry_allowed: true,
          provider_remediation: "Restore the provider and retry.",
        }),
      }),
      onRetry: async () => jsonResponse({
        job_id: "JOB-RETRY-FAILED",
        session_id: "SESSION-RETRY-IMMEDIATE",
        status: "failed",
        message: "Provider still unavailable.",
        error_code: "provider_unavailable",
        details: audioJobDetails("AUDIO-RETRY-IMMEDIATE", {
          retry_allowed: true,
          provider_remediation: "Provider remains unavailable after retry.",
        }),
      }),
      onJob: async () => {
        jobPolls += 1;
        return jsonResponse({});
      },
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-RETRY-IMMEDIATE" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["retry-immediate"], "retry.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));
    await screen.findAllByText("Restore the provider and retry.");

    fireEvent.click(screen.getByRole("button", { name: "Retry transcription" }));

    expect(await screen.findAllByText("Provider remains unavailable after retry.")).not.toHaveLength(0);
    expect(loadWorkflowState()).toMatchObject({
      transcriptionJobId: "JOB-RETRY-FAILED",
      transcriptionJobStatus: "failed",
      transcriptionJobMessage: "Provider remains unavailable after retry.",
    });
    expect(jobPolls).toBe(0);
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
          session_id: "SESSION-NETWORK",
          details: {
            audio_file: { audio_file_id: "AUDIO-NETWORK", session_id: "SESSION-NETWORK", source_asset_version: 1 },
            upload_intent: { audio_file_id: "AUDIO-NETWORK", upload_url: "/audio/AUDIO-NETWORK/upload-file", required_headers: {} },
          },
        });
      }
      if (url.endsWith("/audio/AUDIO-NETWORK/upload-file")) return jsonResponse({ status: "success" });
      if (url.endsWith("/audio/AUDIO-NETWORK/complete-upload")) return jsonResponse({ audio_file_id: "AUDIO-NETWORK", source_asset_version: 1, upload_status: "uploaded" });
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
        return jsonResponse({
          job_id: "JOB-NETWORK",
          session_id: "SESSION-NETWORK",
          status: "queued",
          message: "queued",
          details: audioJobDetails("AUDIO-NETWORK"),
        });
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

    expect(await screen.findAllByText(/could not be verified after repeated network failures/i)).not.toHaveLength(0);
    expect(jobPolls).toBe(3);
    expect(routerPush).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Review transcript" })).not.toBeInTheDocument();
  });

  it("aborts and isolates the active monitor when the therapist changes source", async () => {
    let pollSignal: AbortSignal | undefined;
    let cancelCalls = 0;
    const pendingJobHooks: { attachAbort?: (signal?: AbortSignal) => void } = {};
    const pendingJob = new Promise<Response>((_resolve, reject) => {
      const attachAbort = (signal?: AbortSignal) => {
        pollSignal = signal;
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      };
      Object.assign(pendingJobHooks, { attachAbort });
    });
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-SWITCH",
      caseId: "CASE-SWITCH",
      audioFileId: "AUDIO-SWITCH",
      jobId: "JOB-SWITCH",
      onJob: (_url, init) => {
        pendingJobHooks.attachAbort?.(init?.signal ?? undefined);
        return pendingJob;
      },
      onCancel: async () => {
        cancelCalls += 1;
        return jsonResponse({
          job_id: "JOB-SWITCH",
          session_id: "SESSION-SWITCH",
          status: "cancelled",
          message: "Job cancelled by therapist.",
          details: audioJobDetails("AUDIO-SWITCH"),
        });
      },
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-SWITCH" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["switch-audio"], "switch.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));
    await waitFor(() => expect(pollSignal).toBeDefined());

    fireEvent.click(screen.getByRole("button", { name: "Paste transcript" }));

    await waitFor(() => expect(pollSignal?.aborted).toBe(true));
    expect(screen.getByRole("textbox", { name: "Pasted transcript text" })).toBeInTheDocument();
    expect(loadWorkflowState().transcriptionJobId).toBeUndefined();
    expect(loadWorkflowState().transcriptionJobStatus).toBeUndefined();
    expect(loadWorkflowState().transcriptionJobMessage).toBeUndefined();
    await waitFor(() => expect(cancelCalls).toBe(1));
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("aborts the raw audio upload when the therapist changes source", async () => {
    let uploadSignal: AbortSignal | undefined;
    let uploadRequestSeen = false;
    const uploadHooks: { attach?: (signal?: AbortSignal | null) => void } = {};
    const pendingUpload = new Promise<Response>((_resolve, reject) => {
      uploadHooks.attach = (signal?: AbortSignal | null) => {
        uploadSignal = signal ?? undefined;
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      };
    });
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-UPLOAD-ABORT",
      caseId: "CASE-UPLOAD-ABORT",
      audioFileId: "AUDIO-UPLOAD-ABORT",
      jobId: "JOB-UPLOAD-ABORT",
      onUpload: async (_url, init) => {
        uploadRequestSeen = true;
        uploadHooks.attach?.(init?.signal);
        return pendingUpload;
      },
      onJob: async () => jsonResponse({}),
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-UPLOAD-ABORT" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["abort-audio"], "abort.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));
    await waitFor(() => expect(uploadRequestSeen).toBe(true));

    fireEvent.click(screen.getByRole("button", { name: "Paste transcript" }));

    await waitFor(() => expect(uploadSignal?.aborted).toBe(true));
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("detaches a prior transcript before a replacement audio upload intent settles", async () => {
    let intentSeen = false;
    const pendingIntent = new Promise<Response>(() => undefined);
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-UPLOAD-START",
      caseId: "CASE-UPLOAD-START",
      audioFileId: "AUDIO-UPLOAD-START",
      jobId: "JOB-UPLOAD-START",
      initialTranscript: {
        transcript_id: "TRANSCRIPT-PRIOR-START",
        session_id: "SESSION-UPLOAD-START",
        case_id: "CASE-UPLOAD-START",
        source: "asr_draft:local_faster_whisper",
        version: 5,
        raw_text: "@Begin\n*SPK_01:\tprior start words .\n@End",
        utterances: [{ utterance_id: "prior-start-1", speaker: "SPK_01", text: "prior start words" }],
      },
      onIntent: async () => {
        intentSeen = true;
        return pendingIntent;
      },
      onJob: async () => jsonResponse({}),
    }));

    const workspace = render(<SessionWorkspaceClient sessionId="SESSION-UPLOAD-START" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(loadWorkflowState().backendTranscriptId).toBe("TRANSCRIPT-PRIOR-START"));
    fireEvent.change(input, { target: { files: [new File(["start-audio"], "start.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    await waitFor(() => expect(intentSeen).toBe(true));
    expect(loadWorkflowState()).toMatchObject({
      source: "audio-upload",
      transcriptReplacementRequired: true,
      replacementTranscriptId: "TRANSCRIPT-PRIOR-START",
      replacementTranscriptVersion: 5,
      transcriptText: "",
      transcriptLines: [],
      transcriptReady: false,
      qaStatus: "not_run",
      analysisStatus: "not_started",
      reportStatus: "not_started",
    });
    expect(loadWorkflowState().backendTranscriptId).toBeUndefined();
    expect(loadWorkflowState().backendTranscriptVersion).toBeUndefined();
    workspace.unmount();
  });

  it("detaches a prior transcript when a replacement audio job is accepted", async () => {
    let pollSignal: AbortSignal | undefined;
    const replacementAudioHooks: { attach?: (signal?: AbortSignal) => void } = {};
    const pendingJob = new Promise<Response>((_resolve, reject) => {
      const attach = (signal?: AbortSignal) => {
        pollSignal = signal;
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      };
      Object.assign(replacementAudioHooks, { attach });
    });
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-SECOND-AUDIO",
      caseId: "CASE-SECOND-AUDIO",
      audioFileId: "AUDIO-SECOND",
      jobId: "JOB-SECOND",
      initialTranscript: {
        transcript_id: "TRANSCRIPT-FIRST-AUDIO",
        session_id: "SESSION-SECOND-AUDIO",
        case_id: "CASE-SECOND-AUDIO",
        source: "asr_draft:local_faster_whisper",
        version: 3,
        raw_text: "@Begin\n*SPK_01:\tprior words .\n@End",
        utterances: [{ utterance_id: "prior-1", speaker: "SPK_01", text: "prior words" }],
      },
      onJob: (_url, init) => {
        replacementAudioHooks.attach?.(init?.signal ?? undefined);
        return pendingJob;
      },
    }));

    const workspace = render(<SessionWorkspaceClient sessionId="SESSION-SECOND-AUDIO" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["second-audio"], "second.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));
    await waitFor(() => expect(pollSignal).toBeDefined());

    expect(loadWorkflowState()).toMatchObject({
      source: "audio-upload",
      transcriptionJobId: "JOB-SECOND",
      transcriptReplacementRequired: true,
      replacementTranscriptId: "TRANSCRIPT-FIRST-AUDIO",
      replacementTranscriptVersion: 3,
      transcriptText: "",
      transcriptLines: [],
      transcriptReady: false,
      qaStatus: "not_run",
      featuresExtracted: false,
      reportStatus: "not_started",
    });
    expect(loadWorkflowState().backendTranscriptId).toBeUndefined();
    expect(loadWorkflowState().featureSetId).toBeUndefined();
    expect(loadWorkflowState().backendReportId).toBeUndefined();
    workspace.unmount();
  });

  it("aborts an in-flight job request when the workspace unmounts", async () => {
    let pollSignal: AbortSignal | undefined;
    const abortHooks: { attach?: (signal?: AbortSignal) => void } = {};
    const pendingJob = new Promise<Response>((_resolve, reject) => {
      abortHooks.attach = (signal?: AbortSignal) => {
        pollSignal = signal;
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      };
    });
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-UNMOUNT",
      caseId: "CASE-UNMOUNT",
      audioFileId: "AUDIO-UNMOUNT",
      jobId: "JOB-UNMOUNT",
      onJob: (_url, init) => {
        abortHooks.attach?.(init?.signal ?? undefined);
        return pendingJob;
      },
    }));

    const workspace = render(<SessionWorkspaceClient sessionId="SESSION-UNMOUNT" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["unmount-audio"], "unmount.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));
    await waitFor(() => expect(pollSignal).toBeDefined());

    workspace.unmount();

    expect(pollSignal?.aborted).toBe(true);
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("fails closed immediately for an unknown job status", async () => {
    let jobPolls = 0;
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-UNKNOWN",
      caseId: "CASE-UNKNOWN",
      audioFileId: "AUDIO-UNKNOWN",
      jobId: "JOB-UNKNOWN",
      onJob: async () => {
        jobPolls += 1;
        return jsonResponse({
          job_id: "JOB-UNKNOWN",
          session_id: "SESSION-UNKNOWN",
          status: "mystery_status",
          message: "Malformed fixture response.",
          details: {},
        });
      },
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-UNKNOWN" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["unknown-audio"], "unknown.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(await screen.findByText("Error code: audio_job_response_invalid")).toBeInTheDocument();
    expect(jobPolls).toBe(1);
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("rejects a completed draft whose transcript lineage does not match the active session", async () => {
    let transcriptReads = 0;
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-LINEAGE",
      caseId: "CASE-LINEAGE",
      audioFileId: "AUDIO-LINEAGE",
      jobId: "JOB-LINEAGE",
      onJob: async () => jsonResponse({
        job_id: "JOB-LINEAGE",
        session_id: "SESSION-LINEAGE",
        status: "needs_review",
        message: "Draft ready.",
        details: audioJobDetails("AUDIO-LINEAGE", {
          asr_draft: { transcript_id: "TRANSCRIPT-LINEAGE" },
        }),
      }),
      onTranscript: async () => {
        transcriptReads += 1;
        return jsonResponse({
          transcript_id: "TRANSCRIPT-LINEAGE",
          session_id: "OTHER-SESSION",
          case_id: "OTHER-CASE",
          version: 1,
          raw_text: "@Begin\n*UNK:\twrong session .\n@End",
          utterances: [{ utterance_id: "wrong-1", speaker: "UNK", text: "wrong session" }],
        });
      },
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-LINEAGE" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["lineage-audio"], "lineage.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(await screen.findByText("Error code: transcript_lineage_mismatch")).toBeInTheDocument();
    expect(transcriptReads).toBe(1);
    expect(routerPush).not.toHaveBeenCalled();
    expect(loadWorkflowState().backendTranscriptId).toBeUndefined();
  });

  it("rejects a same-session job whose exact audio lineage does not match", async () => {
    let jobPolls = 0;
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-JOB-LINEAGE",
      caseId: "CASE-JOB-LINEAGE",
      audioFileId: "AUDIO-JOB-LINEAGE",
      jobId: "JOB-JOB-LINEAGE",
      onProcess: async () => jsonResponse({
        job_id: "JOB-JOB-LINEAGE",
        session_id: "SESSION-JOB-LINEAGE",
        status: "queued",
        message: "queued",
        details: audioJobDetails("OTHER-AUDIO"),
      }),
      onJob: async () => {
        jobPolls += 1;
        return jsonResponse({});
      },
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-JOB-LINEAGE" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["lineage-audio"], "lineage.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(await screen.findByText("Error code: audio_job_response_invalid")).toBeInTheDocument();
    expect(jobPolls).toBe(0);
    expect(loadWorkflowState().transcriptionJobStatus).toBe("failed");
  });

  it("rejects a same-session transcript without the exact ASR provenance", async () => {
    vi.stubGlobal("fetch", createLifecycleFetch({
      sessionId: "SESSION-TRANSCRIPT-LINEAGE",
      caseId: "CASE-TRANSCRIPT-LINEAGE",
      audioFileId: "AUDIO-TRANSCRIPT-LINEAGE",
      jobId: "JOB-TRANSCRIPT-LINEAGE",
      onJob: async () => jsonResponse({
        job_id: "JOB-TRANSCRIPT-LINEAGE",
        session_id: "SESSION-TRANSCRIPT-LINEAGE",
        status: "needs_review",
        message: "Draft ready.",
        details: audioJobDetails("AUDIO-TRANSCRIPT-LINEAGE", {
          asr_draft: { transcript_id: "TRANSCRIPT-SAME-SESSION" },
        }),
      }),
      onTranscript: async () => jsonResponse({
        transcript_id: "TRANSCRIPT-SAME-SESSION",
        session_id: "SESSION-TRANSCRIPT-LINEAGE",
        case_id: "CASE-TRANSCRIPT-LINEAGE",
        version: 1,
        source: "paste-transcript",
        raw_text: "@Begin\n*UNK:\tmanual words .\n@End",
        utterances: [{ utterance_id: "manual-1", speaker: "UNK", text: "manual words" }],
      }),
    }));

    render(<SessionWorkspaceClient sessionId="SESSION-TRANSCRIPT-LINEAGE" view="intake" mode="audio" />);
    const input = await screen.findByLabelText("Synthetic audio file");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { files: [new File(["lineage-audio"], "lineage.wav", { type: "audio/wav" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and upload" }));

    expect(await screen.findByText("Error code: transcript_lineage_mismatch")).toBeInTheDocument();
    expect(loadWorkflowState()).toMatchObject({
      transcriptionJobId: "JOB-TRANSCRIPT-LINEAGE",
      transcriptionJobStatus: "failed",
    });
    expect(loadWorkflowState().backendTranscriptId).toBeUndefined();
    expect(routerPush).not.toHaveBeenCalled();
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

function createLifecycleFetch({
  sessionId,
  caseId,
  audioFileId,
  jobId,
  onJob,
  onCancel,
  onIntent,
  onProcess,
  onRetry,
  onUpload,
  initialTranscript,
  onTranscript,
}: {
  sessionId: string;
  caseId: string;
  audioFileId: string;
  jobId: string;
  onJob: (url: string, init?: RequestInit) => Promise<Response>;
  onCancel?: (url: string, init?: RequestInit) => Promise<Response>;
  onIntent?: (url: string, init?: RequestInit) => Promise<Response>;
  onProcess?: (url: string, init?: RequestInit) => Promise<Response>;
  onRetry?: (url: string, init?: RequestInit) => Promise<Response>;
  onUpload?: (url: string, init?: RequestInit) => Promise<Response>;
  initialTranscript?: Record<string, unknown>;
  onTranscript?: (url: string, init?: RequestInit) => Promise<Response>;
}) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/settings")) return jsonResponse({ mock_mode: true, auth_mode: "mock" });
    if (url.endsWith("/audio/capabilities")) return jsonResponse(audioCapabilities());
    if (url.endsWith(`/sessions/${sessionId}`) && method === "GET") {
      return jsonResponse({
        session_id: sessionId,
        case_id: caseId,
        transcript_id: initialTranscript?.transcript_id,
      });
    }
    if (url.endsWith(`/cases/${caseId}`)) {
      return jsonResponse({ case_id: caseId, child_code: "SYNTH-TEST", consent_status: "granted" });
    }
    if (url.endsWith(`/sessions/${sessionId}/audio`) && method === "GET") return jsonResponse([]);
    if (url.endsWith(`/sessions/${sessionId}/ml-decision-support`)) return new Response("not found", { status: 404 });
    if (url.endsWith(`/sessions/${sessionId}/audio/upload`)) {
      if (onIntent) return onIntent(url, init);
      return jsonResponse({
        session_id: sessionId,
        details: {
          audio_file: { audio_file_id: audioFileId, session_id: sessionId, source_asset_version: 1 },
          upload_intent: { audio_file_id: audioFileId, upload_url: `/audio/${audioFileId}/upload-file`, required_headers: {} },
        },
      });
    }
    if (url.endsWith(`/audio/${audioFileId}/upload-file`)) {
      return onUpload ? onUpload(url, init) : jsonResponse({ status: "success" });
    }
    if (url.endsWith(`/audio/${audioFileId}/complete-upload`)) {
      return jsonResponse({ audio_file_id: audioFileId, source_asset_version: 1, upload_status: "uploaded" });
    }
    if (url.endsWith(`/audio/${audioFileId}/verify-and-normalize`)) {
      return jsonResponse({
        source_audio_file_id: audioFileId,
        source_asset_version: 1,
        normalized_asset_version: 1,
        source_checksum_sha256: "a".repeat(64),
        normalized_checksum_sha256: "b".repeat(64),
        duration_ms: 60_000,
        verification_status: "verified",
      });
    }
    if (url.endsWith(`/sessions/${sessionId}/audio/process`)) {
      return onProcess
        ? onProcess(url, init)
        : jsonResponse({
            job_id: jobId,
            session_id: sessionId,
            status: "queued",
            message: "queued",
            details: audioJobDetails(audioFileId),
          });
    }
    if (url.endsWith(`/jobs/${jobId}/retry`) && onRetry) return onRetry(url, init);
    if (url.endsWith(`/jobs/${jobId}/cancel`) && onCancel) return onCancel(url, init);
    if (url.endsWith(`/jobs/${jobId}`)) return onJob(url, init);
    if (initialTranscript && url.endsWith(`/transcripts/${String(initialTranscript.transcript_id)}`)) {
      return jsonResponse(initialTranscript);
    }
    if (url.includes("/transcripts/") && onTranscript) return onTranscript(url, init);
    throw new Error(`Unexpected request: ${method} ${url}`);
  });
}

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
    normalization: {
      channels: 1,
      sample_rate_hz: 16_000,
      format: "wav_pcm_s16le",
      source_min_sample_rate_hz: 8_000,
      source_max_sample_rate_hz: 192_000,
      source_max_channels: 8,
      max_rational_factor: 512,
      max_filter_taps: 262_144,
      max_working_bytes: 512 * 1024 * 1024,
    },
    browser_recording: { state: "experimental_unavailable", blocks_milestone: false },
  };
}

function audioJobDetails(audioFileId: string, extra: Record<string, unknown> = {}) {
  return {
    audio_file_id: audioFileId,
    source_asset_version: 1,
    source_checksum_sha256: "a".repeat(64),
    normalized_asset_version: 1,
    normalized_checksum_sha256: "b".repeat(64),
    provider_id: "local_faster_whisper",
    ...extra,
  };
}

function asrProvenance(
  audioFileId: string,
  jobId: string,
  sourceAssetVersion = 1,
  normalizedAssetVersion = 1,
) {
  return {
    job_id: jobId,
    source_audio_file_id: audioFileId,
    source_asset_version: sourceAssetVersion,
    source_checksum_sha256: "a".repeat(64),
    normalized_asset_version: normalizedAssetVersion,
    normalized_checksum_sha256: "b".repeat(64),
    provider_id: "local_faster_whisper",
  };
}
