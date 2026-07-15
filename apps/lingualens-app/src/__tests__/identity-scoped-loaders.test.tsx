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

  test("Report renders stale provenance as read-only with a canonical regeneration action", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/settings")) return jsonResponse({});
      if (url.endsWith("/sessions/SESSION-STALE")) return jsonResponse({
        session_id: "SESSION-STALE",
        case_id: "CASE-STALE",
        transcript_id: "TRANSCRIPT-STALE",
        feature_set_id: "FEATURE-STALE",
        report_id: "REPORT-STALE",
      });
      if (url.endsWith("/reports/REPORT-STALE")) return jsonResponse({
        report_id: "REPORT-STALE",
        session_id: "SESSION-STALE",
        case_id: "CASE-STALE",
        transcript_id: "TRANSCRIPT-STALE",
        feature_result_id: "FEATURE-STALE",
        status: "stale",
        version: 4,
        markdown: "# Prior stale draft",
        generated_from_versions: { transcript_version: "2" },
      });
      if (url.endsWith("/transcripts/TRANSCRIPT-STALE")) return jsonResponse({
        transcript_id: "TRANSCRIPT-STALE",
        session_id: "SESSION-STALE",
        case_id: "CASE-STALE",
        version: 3,
        therapist_attested: false,
      });
      if (url.endsWith("/cases/CASE-STALE")) return jsonResponse({
        case_id: "CASE-STALE",
        nickname: "STALE CHILD",
        consent_status: "granted",
      });
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<ReportSummaryClient sessionId="SESSION-STALE" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/transcript changed.*regenerate/i);
    expect(screen.getByRole("link", { name: /regenerate findings/i })).toHaveAttribute(
      "href",
      "/sessions/SESSION-STALE?view=findings",
    );
    const staleReport = screen.getByRole("textbox", { name: /stale read-only report/i });
    expect(staleReport).toHaveValue("# Prior stale draft");
    expect(staleReport).toHaveAttribute("readonly");
    expect(staleReport).not.toBeDisabled();
    expect(staleReport).toHaveAccessibleDescription(/prior draft is read-only/i);
    expect(screen.getByRole("button", { name: /save draft/i })).toBeDisabled();
    expectReportExportsDisabled();
  });

  test("Findings hides stale values and offers explicit regeneration", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "SESSION-STALE",
      backendTranscriptId: "TRANSCRIPT-STALE",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      transcriptSaveStatus: "saved",
      qaStatus: "pass",
      analysisStatus: "stale",
      featureSetId: "FEATURE-STALE",
      featuresExtracted: false,
      featureSummary: [{ label: "Prior stale metric", value: "secret" }],
      reportStatus: "stale",
    });

    render(<SessionWorkspaceClient view="results" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/findings are stale.*transcript changed/i);
    expect(screen.getByRole("button", { name: /regenerate findings/i })).toBeEnabled();
    expect(screen.queryByText("Prior stale metric")).not.toBeInTheDocument();
  });

  test.each([
    ["Signed Off", "finalized"],
    ["stale", "stale"],
  ] as const)(
    "Session hydration uses backend report status %s even when findings are stale",
    async (backendReportStatus, expectedStatus) => {
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/settings")) return jsonResponse({});
        if (url.endsWith("/sessions/SESSION-REPORT-STATUS")) return jsonResponse({
          session_id: "SESSION-REPORT-STATUS",
          case_id: "CASE-REPORT-STATUS",
          transcript_id: "TRANSCRIPT-REPORT-STATUS",
          feature_set_id: "FEATURE-REPORT-STATUS",
          report_id: "REPORT-STATUS",
        });
        if (url.endsWith("/transcripts/TRANSCRIPT-REPORT-STATUS")) return jsonResponse({
          transcript_id: "TRANSCRIPT-REPORT-STATUS",
          session_id: "SESSION-REPORT-STATUS",
          case_id: "CASE-REPORT-STATUS",
          version: 3,
          raw_text: "@Begin\n*CHI:\tcurrent transcript .\n@End",
          utterances: [{ utterance_id: "line-current", speaker: "CHI", text: "current transcript" }],
          therapist_attested: true,
          qa_status: "PASS",
          qa_issues: [],
        });
        if (url.endsWith("/reports/REPORT-STATUS")) return jsonResponse({
          report_id: "REPORT-STATUS",
          status: backendReportStatus,
          version: 7,
          generated_from_versions: { transcript_version: "2" },
          markdown: "# Persisted report",
        });
        if (url.endsWith("/cases/CASE-REPORT-STATUS")) return jsonResponse({
          case_id: "CASE-REPORT-STATUS",
          nickname: "STATUS CHILD",
          consent_status: "granted",
        });
        if (url.endsWith("/sessions/SESSION-REPORT-STATUS/audio")) return jsonResponse([]);
        if (url.endsWith("/transcripts/TRANSCRIPT-REPORT-STATUS/ml-readiness")) {
          return jsonResponse({ ready: false, provider_id: "test", reason_codes: [], reasons: [] });
        }
        if (url.endsWith("/sessions/SESSION-REPORT-STATUS/ml-review")) {
          return new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
        }
        if (url.endsWith("/sessions/SESSION-REPORT-STATUS/features")) return jsonResponse({
          feature_set_id: "FEATURE-REPORT-STATUS",
          transcript_id: "TRANSCRIPT-REPORT-STATUS",
          transcript_version: 2,
          review_status: "stale",
          features: [],
        });
        if (url.endsWith("/features/definitions")) return jsonResponse([]);
        throw new Error(`Unexpected request: ${url}`);
      }));

      render(<SessionWorkspaceClient sessionId="SESSION-REPORT-STATUS" view="results" />);

      await waitFor(() => expect(loadWorkflowState()).toMatchObject({
        backendReportId: "REPORT-STATUS",
        backendReportVersion: 7,
        reportStatus: expectedStatus,
        reportGeneratedFromVersions: { transcript_version: "2" },
      }));
    },
  );

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
    reportStatus: "finalized",
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
