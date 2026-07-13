import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ReportSummaryClient } from "@/components/report-summary-client";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";
import {
  createInitialWorkflowState,
  loadWorkflowState,
  saveWorkflowState,
} from "@/lib/workflow";

const priorReportText = "Prior private report content.";
const priorTranscriptText = "@Begin\n*CHI:\tPrior private transcript.\n@End";

beforeEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("identity-scoped workflow loaders", () => {
  test("Session clears stored identity and findings while an explicit locator is still loading", async () => {
    seedPriorWorkflow();
    const sessionRequest = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/settings")) return jsonResponse({});
      if (url.endsWith("/sessions/REQUESTED-SESSION")) return sessionRequest.promise;
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<SessionWorkspaceClient sessionId="REQUESTED-SESSION" view="results" />);

    expect(screen.queryByText("PRIOR CHILD")).not.toBeInTheDocument();
    expect(screen.queryByText("Prior private feature")).not.toBeInTheDocument();
    expect(screen.queryByText(priorReportText)).not.toBeInTheDocument();
    await expectPersistedIdentityToBeEmpty();
  });

  test("Session ignores a late successful response after navigating to a different session", async () => {
    const sessionARequest = deferred<Response>();
    const sessionBRequest = deferred<Response>();
    const sessionAMlRequest = deferred<Response>();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/settings")) return jsonResponse({});
      if (url.endsWith("/sessions/SESSION-A")) return sessionARequest.promise;
      if (url.endsWith("/sessions/SESSION-B")) return sessionBRequest.promise;
      if (url.endsWith("/transcripts/TRANSCRIPT-A")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-A",
          session_id: "SESSION-A",
          case_id: "CASE-A",
          raw_text: "@Begin\n*CHI:\tSession A private transcript.\n@End",
          utterances: [{ utterance_id: "line-a", speaker: "CHI", text: "Session A private transcript." }],
          therapist_attested: true,
          qa_status: "pass",
          qa_issues: [],
        });
      }
      if (url.endsWith("/cases/CASE-A")) {
        return jsonResponse({ case_id: "CASE-A", nickname: "SESSION A CHILD", consent_status: "granted" });
      }
      if (url.endsWith("/sessions/SESSION-A/audio")) return jsonResponse([]);
      if (url.endsWith("/transcripts/TRANSCRIPT-A/ml-readiness")) {
        return jsonResponse({ ready: true, provider_id: "test", reason_codes: [], reasons: [] });
      }
      if (url.endsWith("/sessions/SESSION-A/ml-review")) return sessionAMlRequest.promise;
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(<SessionWorkspaceClient sessionId="SESSION-A" view="results" />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/sessions/SESSION-A"),
      expect.anything(),
    ));

    rerender(<SessionWorkspaceClient sessionId="SESSION-B" view="results" />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/sessions/SESSION-B"),
      expect.anything(),
    ));

    sessionARequest.resolve(jsonResponse({
      session_id: "SESSION-A",
      case_id: "CASE-A",
      transcript_id: "TRANSCRIPT-A",
    }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/sessions/SESSION-A/ml-review"),
      expect.anything(),
    ));
    await act(async () => {
      sessionAMlRequest.resolve(jsonResponse({
        result_id: "ML-A",
        status: "completed",
        provider_name: "test",
        provider_version: "1",
        input_feature_schema_version: "1",
        generated_at: "2026-07-14T00:00:00Z",
        cues: [{
          cue_code: "private-a",
          title: "Session A private finding",
          severity: "review",
          explanation: "Session A only.",
          supporting_features: {},
          limitations: [],
          recommended_next_review_step: "Review A.",
          review_state: { status: "unreviewed" },
        }],
        limitations: [],
        not_diagnostic: true,
        decision_support_only: true,
      }));
      await sessionAMlRequest.promise;
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(screen.queryByText("SESSION A CHILD")).not.toBeInTheDocument();
    expect(screen.queryByText("Session A private finding")).not.toBeInTheDocument();
    await expectPersistedIdentityToBeEmpty();
  });

  test("Report clears stored and demo identity while an explicit locator is still loading", async () => {
    seedPriorWorkflow();
    const sessionRequest = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/settings")) return jsonResponse({});
      if (url.endsWith("/sessions/REQUESTED-SESSION")) return sessionRequest.promise;
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<ReportSummaryClient sessionId="REQUESTED-SESSION" />);

    expect(screen.queryByText("PRIOR CHILD")).not.toBeInTheDocument();
    expect(screen.queryByText("Ethan L.")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(priorReportText)).not.toBeInTheDocument();
    expectReportExportsDisabled();
    await expectPersistedIdentityToBeEmpty();
  });

  test.each([
    ["authorization", 403, "Access denied.", "You are not authorized to access this persisted workflow.", false],
    ["not found", 404, "Workflow not found.", "The requested persisted workflow was not found.", false],
    ["network", undefined, "Backend unavailable.", "Could not load the persisted workflow. Check the backend and retry.", true],
  ] as const)(
    "Session classifies %s failure without restoring a prior identity",
    async (_scenario, status, statusMessage, errorMessage, unavailable) => {
      seedPriorWorkflow();
      stubSessionFailure(status);

      render(<SessionWorkspaceClient sessionId="REQUESTED-SESSION" view="transcript" />);

      expect(await screen.findByText(errorMessage)).toBeInTheDocument();
      expect(screen.getByText(statusMessage)).toBeInTheDocument();
      expect(screen.queryByDisplayValue("Prior private transcript.")).not.toBeInTheDocument();
      expect(screen.queryByText("Backend unavailable — local workspace mode")).toBe(
        unavailable ? screen.getByText("Backend unavailable — local workspace mode") : null,
      );
      await expectPersistedIdentityToBeEmpty();
    },
  );

  test.each([
    ["authorization", 403, "Access denied.", "You are not authorized to access this persisted report.", false],
    ["not found", 404, "Report not found.", "The requested persisted report was not found.", false],
    ["network", undefined, "Backend unavailable.", "Could not load the persisted report. Check the backend and retry.", true],
  ] as const)(
    "Report classifies %s failure and keeps prior export paths disabled",
    async (_scenario, status, statusMessage, errorMessage, unavailable) => {
      seedPriorWorkflow();
      stubSessionFailure(status);

      render(<ReportSummaryClient sessionId="REQUESTED-SESSION" />);

      expect(await screen.findByText(errorMessage)).toBeInTheDocument();
      expect(screen.getByText(statusMessage)).toBeInTheDocument();
      expect(screen.queryByText("PRIOR CHILD")).not.toBeInTheDocument();
      expect(screen.queryByDisplayValue(priorReportText)).not.toBeInTheDocument();
      expectReportExportsDisabled();
      expect(screen.queryByText("Backend unavailable — local workspace mode")).toBe(
        unavailable ? screen.getByText("Backend unavailable — local workspace mode") : null,
      );
      await expectPersistedIdentityToBeEmpty();
    },
  );
});

function seedPriorWorkflow() {
  saveWorkflowState({
    ...createInitialWorkflowState(),
    sessionId: "PRIOR-SESSION",
    backendSessionId: "PRIOR-SESSION",
    backendTranscriptSessionId: "PRIOR-SESSION",
    backendTranscriptId: "PRIOR-TRANSCRIPT",
    backendReportId: "PRIOR-REPORT",
    reportId: "PRIOR-REPORT",
    caseId: "PRIOR-CASE",
    caseInfo: { caseId: "PRIOR-CASE", clientLabel: "PRIOR CHILD" },
    childName: "PRIOR CHILD",
    transcriptText: priorTranscriptText,
    transcriptLines: [{ lineId: "prior-line", speaker: "CHI", text: "Prior private transcript." }],
    transcriptReady: true,
    transcriptAttested: true,
    transcriptReviewStatus: "reviewed",
    featureSummary: [{ label: "Prior private feature", value: "secret" }],
    featuresExtracted: true,
    reportMarkdown: priorReportText,
    reportStatus: "Finalized",
    reportSaveStatus: "saved",
    finalizeStatus: "Report finalized.",
  });
}

function stubSessionFailure(status: 403 | 404 | undefined) {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/settings")) return jsonResponse({});
    if (url.endsWith("/sessions/REQUESTED-SESSION")) {
      if (status === undefined) throw new TypeError("Failed to fetch");
      return new Response(JSON.stringify({ detail: "loader failure" }), { status });
    }
    throw new Error(`Unexpected request: ${url}`);
  }));
}

function expectReportExportsDisabled() {
  expect(screen.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Export HTML" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Export reviewed .cha" })).toBeDisabled();
}

async function expectPersistedIdentityToBeEmpty() {
  await waitFor(() => {
    const persisted = loadWorkflowState();
    expect(persisted.sessionId).toBeUndefined();
    expect(persisted.backendSessionId).toBeUndefined();
    expect(persisted.backendTranscriptId).toBeUndefined();
    expect(persisted.backendReportId).toBeUndefined();
    expect(persisted.reportId).toBeUndefined();
    expect(persisted.caseId).toBeUndefined();
    expect(persisted.childName).toBe("");
    expect(persisted.caseInfo.clientLabel).toBe("");
    expect(persisted.transcriptText).toBe("");
    expect(persisted.featureSummary).toEqual([]);
    expect(persisted.mlDecisionSupport).toBeUndefined();
    expect(persisted.reportMarkdown).toBeUndefined();
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
