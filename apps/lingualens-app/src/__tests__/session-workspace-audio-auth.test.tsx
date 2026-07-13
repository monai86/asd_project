import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionWorkspaceClient } from "@/components/session-workspace-client";
import {
  createInitialWorkflowState,
  loadWorkflowState,
  saveWorkflowState,
} from "@/lib/workflow";

describe("SessionWorkspaceClient audio auth path", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.restoreAllMocks();
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
