import { createHash } from "node:crypto";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ReportsWorkspaceClient } from "@/components/reports-workspace-client";
import { SessionFindingsView } from "@/features/sessions/findings/session-findings-view";
import { SessionReportView } from "@/features/sessions/report/session-report-view";
import { createInitialWorkflowState, saveWorkflowState, type WorkflowState } from "@/lib/workflow";

const setBackendUnavailable = vi.fn();

vi.mock("@/components/backend-availability-banner", () => ({
  BackendAvailabilityBanner: () => null,
  useBackendAvailability: () => ({
    backendUnavailable: false,
    setBackendUnavailable,
  }),
}));

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function signedSnapshotFixture(payload: Record<string, unknown>) {
  const canonical = JSON.stringify(sortJsonValue(payload));
  const reportHash = createHash("sha256").update(canonical, "utf8").digest("hex");
  return { snapshot: { ...payload, report_hash: reportHash }, reportHash };
}

function sortJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJsonValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, sortJsonValue(item)]));
  }
  return value;
}

function findingsState(overrides: Partial<WorkflowState> = {}): WorkflowState {
  return {
    ...createInitialWorkflowState(),
    backendSessionId: "session-findings",
    backendTranscriptId: "transcript-findings",
    backendTranscriptVersion: 4,
    transcriptReady: true,
    transcriptAttested: true,
    transcriptReviewStatus: "reviewed",
    analysisStatus: "completed",
    featuresExtracted: true,
    featureSetId: "features-findings",
    featureTranscriptVersion: 4,
    featureSchemaVersion: "features-basic-v1",
    featurePercent: 100,
    featureSummary: [{ label: "MLU words", value: "3.4" }],
    mlDecisionSupport: {
      resultId: "review-findings",
      status: "completed",
      providerName: "Reference evidence review",
      providerVersion: "1.0.0",
      featureSchemaVersion: "features-basic-v1",
      generatedAt: "2026-07-16T00:00:00Z",
      cues: [],
      profileEvidence: [],
      artifactProvenance: {},
      limitations: ["Reference coverage is limited to the configured research corpus."],
      notDiagnostic: true,
      decisionSupportOnly: true,
    },
    ...overrides,
  };
}

function renderFindings(state: WorkflowState) {
  const onGenerateReport = vi.fn();
  render(
    <SessionFindingsView
      sessionContext={{
        sessionId: state.backendSessionId,
        caseLabel: "Case F-01",
        workflowStatus: state.analysisStatus,
        dataMode: "backend",
        activeView: "findings",
      }}
      state={state}
      busy={false}
      backendUnavailable={false}
      onRegenerateFindings={vi.fn()}
      onGenerateReport={onGenerateReport}
      onGenerateMlDecisionSupport={vi.fn()}
      onProfileEvidenceReview={vi.fn()}
    />,
  );
  return { onGenerateReport };
}

beforeEach(() => {
  window.sessionStorage.clear();
  window.history.replaceState({}, "", "/");
  setBackendUnavailable.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Findings Session workspace", () => {
  test("uses three levels of disclosure for descriptive feature review", () => {
    renderFindings(findingsState({
      featureSummary: [],
      featureSignals: [
        {
          featureName: "mean_length_of_utterance_words",
          displayName: "MLU (Words)",
          description: "Mean word tokens per child utterance.",
          valueType: "float",
          unit: "words per utterance",
          value: "3.4",
          rawValue: 3.4,
          calculationMethod: "total words divided by child utterances",
          requiredInputs: ["reviewed transcript"],
          limitations: ["Word-based language sample only."],
          clinicalInterpretationCaution: "Interpret with transcript context.",
          interpretationHint: "Descriptive cue only.",
          referenceText: "Reference comparison unavailable",
        },
      ],
    }));

    for (const group of ["Language sample", "Lexical use", "Interaction", "Speech / intelligibility", "Data quality"]) {
      expect(screen.getByText(group)).toBeVisible();
    }

    const languageSample = screen.getByText("Language sample").closest("details");
    expect(languageSample).not.toBeNull();
    const languageSampleView = within(languageSample as HTMLElement);
    expect(languageSampleView.getByText("MLU (Words)")).not.toBeVisible();
    fireEvent.click(languageSampleView.getByText("Language sample"));
    expect(languageSampleView.getByText("MLU (Words)")).toBeVisible();
    expect(languageSampleView.getByText("total words divided by child utterances")).not.toBeVisible();

    fireEvent.click(languageSampleView.getByText("Evidence and limitations"));
    expect(languageSampleView.getByText("total words divided by child utterances")).toBeVisible();
    expect(languageSampleView.getByText("Reference comparison unavailable")).toBeVisible();
    expect(languageSampleView.getByText("Interpret with transcript context.")).toBeVisible();
  });

  test.each([
    ["not_started", "Not generated"],
    ["processing", "Processing"],
    ["failed", "Failed"],
  ] as const)("shows an explicit %s disposition and never labels it current", (analysisStatus, disposition) => {
    const { onGenerateReport } = renderFindings(findingsState({ analysisStatus }));

    const provenance = screen.getByRole("region", { name: "Findings provenance" });
    expect(within(provenance).getAllByText(disposition).length).toBeGreaterThan(0);
    expect(within(provenance).queryByText("Current findings")).not.toBeInTheDocument();
    expect(screen.queryByText("Backend feature values are available for review.")).not.toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
    for (const button of screen.getAllByRole("button", { name: /Generate report/i })) {
      expect(button).toBeDisabled();
      fireEvent.click(button);
    }
    expect(onGenerateReport).not.toHaveBeenCalled();
  });

  test("shows reviewed transcript and feature-set provenance with AI disposition", () => {
    renderFindings(findingsState());

    expect(screen.getAllByRole("heading", { name: "Session Results" })).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: "Overall Progress" })).not.toBeInTheDocument();
    const provenance = screen.getByRole("region", { name: "Findings provenance" });
    expect(within(provenance).getAllByText("Version 4", { selector: "dd" })).toHaveLength(2);
    expect(within(provenance).getByText("features-findings", { selector: "dd" })).toBeInTheDocument();
    expect(within(provenance).getByText("features-basic-v1", { selector: "dd" })).toBeInTheDocument();
    expect(within(provenance).getByText("Completed", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByText("Reference coverage is limited to the configured research corpus.")).toBeInTheDocument();
    expect(screen.queryByText(/diagnos(?:e|is|tic) probability/i)).not.toBeInTheDocument();
  });

  test("never treats stale findings as current report input", () => {
    const { onGenerateReport } = renderFindings(findingsState({ analysisStatus: "stale" }));

    expect(screen.getByRole("alert")).toHaveTextContent("findings are stale");
    for (const button of screen.getAllByRole("button", { name: /Generate report/i })) {
      expect(button).toBeDisabled();
      fireEvent.click(button);
    }
    expect(onGenerateReport).not.toHaveBeenCalled();
    expect(screen.queryByText("Reference evidence review v1.0.0")).not.toBeInTheDocument();
    expect(screen.queryByText("Backend feature values are available for review.")).not.toBeInTheDocument();
    expect(screen.queryByText("Feature extraction complete")).not.toBeInTheDocument();
  });
});

describe("Report Session workspace", () => {
  test("keeps a never-generated report distinct from an editable draft", () => {
    render(<SessionReportView />);

    expect(screen.getAllByText("Never generated").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Report not generated" })).toBeInTheDocument();
    expect(screen.queryByText("Editable draft")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Draft report preview" })).not.toBeInTheDocument();
  });

  test("shows persisted report provider and safety metadata without inference", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/session-source")) return jsonResponse({ session_id: "session-source", case_id: "case-source", transcript_id: "transcript-source", report_id: "report-source" });
      if (url.endsWith("/reports/report-source")) return jsonResponse({
        report_id: "report-source",
        session_id: "session-source",
        case_id: "case-source",
        markdown: "# Persisted draft",
        status: "Draft",
        requested_provider: "local_llm",
        actual_provider: "template",
        provider_version: "template-2.4",
        fallback_reason: "Requested provider unavailable",
        validator_version: "validator-3",
        rule_set_version: "rules-8",
        input_hash: "input-abc",
        finalized_safety_result: { status: "passed" },
      });
      if (url.endsWith("/transcripts/transcript-source")) return jsonResponse({ transcript_id: "transcript-source", session_id: "session-source", therapist_attested: true, version: 2 });
      if (url.endsWith("/cases/case-source")) return jsonResponse({ case_id: "case-source", child_code: "Case Source", primary_therapist_user_id: "therapist-demo" });
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<SessionReportView sessionId="session-source" reportId="report-source" />);

    const inspector = await screen.findByRole("region", { name: "Report source and safety" });
    expect(screen.queryByRole("heading", { name: "Overall Progress" })).not.toBeInTheDocument();
    expect(screen.queryByText("+18%")).not.toBeInTheDocument();
    expect(within(inspector).getByText("local_llm", { selector: "dd" })).toBeInTheDocument();
    expect(within(inspector).getByText("template", { selector: "dd" })).toBeInTheDocument();
    expect(within(inspector).getByText("template-2.4", { selector: "dd" })).toBeInTheDocument();
    expect(within(inspector).getByText("Requested provider unavailable", { selector: "dd" })).toBeInTheDocument();
    expect(within(inspector).getByText("validator-3", { selector: "dd" })).toBeInTheDocument();
    expect(within(inspector).getByText("rules-8", { selector: "dd" })).toBeInTheDocument();
    expect(within(inspector).getByText("Passed", { selector: "dd" })).toBeInTheDocument();
    expect(within(inspector).getByText("input-abc", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByText("template (requested local_llm)")).toBeInTheDocument();
  });

  test("locks every report drafting control when the persisted draft is stale", () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "session-stale",
      backendTranscriptSessionId: "session-stale",
      backendTranscriptId: "transcript-stale",
      backendTranscriptVersion: 8,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      reportId: "report-stale",
      backendReportId: "report-stale",
      reportMarkdown: "# Prior stale draft",
      reportStatus: "stale",
      reportSaveStatus: "saved",
    });

    render(<SessionReportView />);

    expect(screen.getByRole("heading", { name: "Stale report draft" })).toBeInTheDocument();
    expect(screen.getByLabelText("Drafting Provider")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Generate draft" })).toBeDisabled();
    expect(screen.getByTestId("report-preview")).toHaveAttribute("readonly");
    expect(screen.getByText("This prior draft is read-only and cannot be used as current report content.")).toBeInTheDocument();
  });

  test("shows persisted provenance and keeps a signed snapshot read-only with a revision path", async () => {
    const signedFixture = signedSnapshotFixture({
      markdown: "# Immutable signed snapshot\n\nDecision-support only. Not diagnostic.\n\n## Therapist Sign-off\n- Signed by: Therapist Snapshot\n- Sign-off status: Signed Off\n- Export timestamp: 2026-07-16T10:30:00Z\n\n## Export Timestamp\n- 2026-07-16T10:30:00Z",
      report_version: 5,
      signed_by: "Therapist Snapshot",
      signed_at: "2026-07-16T10:30:00Z",
      generated_from_versions: { transcript_version: "4", schema_version: "signed-schema-v1" },
      provider: {
        requested_provider: "signed-requested",
        actual_provider: "signed-actual",
        provider_version: "signed-provider-version",
      },
      finalized_safety_result: {
        status: "passed",
        validator_version: "signed-validator",
        rule_set_version: "signed-rules",
      },
    });
    let resolvePatch!: (response: Response) => void;
    const patchResponse = new Promise<Response>((resolve) => { resolvePatch = resolve; });
    let releaseDigest!: () => void;
    const digestGate = new Promise<void>((resolve) => { releaseDigest = resolve; });
    const nativeDigest = globalThis.crypto.subtle.digest.bind(globalThis.crypto.subtle);
    const digestSpy = vi.spyOn(globalThis.crypto.subtle, "digest").mockImplementation(async (algorithm, data) => {
      await digestGate;
      return nativeDigest(algorithm, data);
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/sessions/session-signed")) {
        return jsonResponse({
          session_id: "session-signed",
          case_id: "case-signed",
          transcript_id: "transcript-signed",
          report_id: "report-signed",
        });
      }
      if (url.endsWith("/reports/report-signed") && init?.method === "PATCH") {
        return patchResponse;
      }
      if (url.endsWith("/reports/report-signed")) {
        return jsonResponse({
          report_id: "report-signed",
          session_id: "session-signed",
          case_id: "case-signed",
          transcript_id: "transcript-signed",
          feature_result_id: "features-signed",
          feature_schema_version: "mutable-schema-v99",
          generated_from_versions: { transcript_version: "99", schema_version: "mutable-schema-v99" },
          markdown: "# Mutable row content that must not render",
          status: "Signed Off",
          version: 5,
          requested_provider: "mutable-requested",
          actual_provider: "mutable-actual",
          provider_version: "mutable-provider-version",
          validator_version: "mutable-validator",
          rule_set_version: "mutable-rules",
          input_hash: "mutable-input-hash",
          finalized_safety_result: { status: "failed", validator_version: "mutable-validator", rule_set_version: "mutable-rules" },
          signed_snapshot_version: 5,
          signed_snapshot_hash: signedFixture.reportHash,
          signed_by: "Therapist Snapshot",
          signed_at: "2026-07-16T10:30:00Z",
          signed_snapshot: signedFixture.snapshot,
          revision_number: 2,
        });
      }
      if (url.endsWith("/reports/report-revision")) {
        return jsonResponse({
          report_id: "report-revision",
          session_id: "session-signed",
          case_id: "case-signed",
          transcript_id: "transcript-signed",
          feature_result_id: "features-signed",
          feature_schema_version: "features-basic-v1",
          generated_from_versions: { transcript_version: "7", schema_version: "features-basic-v1" },
          markdown: "# Revision draft\n\nDecision-support only. Not diagnostic.\n\n## Therapist Sign-off\nPending therapist edit and sign-off.\n\n## Export Timestamp\n- Pending until therapist sign-off.",
          status: "Draft",
          version: 1,
          revision_number: 3,
          supersedes_report_id: "report-signed",
        });
      }
      if (url.endsWith("/transcripts/transcript-signed")) {
        return jsonResponse({
          transcript_id: "transcript-signed",
          session_id: "session-signed",
          therapist_attested: true,
          version: 12,
        });
      }
      if (url.endsWith("/cases/case-signed")) {
        return jsonResponse({
          case_id: "case-signed",
          child_code: "Case S-01",
          primary_therapist_user_id: "therapist-demo",
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/sessions/session-signed?view=report&case_id=case-signed&transcript_id=transcript-signed&report_id=report-signed");

    render(<SessionReportView sessionId="session-signed" reportId="report-signed" />);

    expect(await screen.findByText("Verifying signed snapshot integrity…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create report revision" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Copy local demo share link" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Mark caregiver share recorded" })).toBeDisabled();
    expect(screen.queryByRole("region", { name: "Report provenance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Report source and safety" })).not.toBeInTheDocument();
    expect(screen.queryByText(/signed-actual \(requested signed-requested\)/)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Therapist notes" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Therapy goals" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Drafting Provider")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Overall Progress" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Strengths" })).not.toBeInTheDocument();
    releaseDigest();
    const editor = await screen.findByTestId("report-preview");
    await waitFor(() => expect((editor as HTMLTextAreaElement).value).toContain("Immutable signed snapshot"));
    expect(editor).toHaveAttribute("readonly");
    expect((editor as HTMLTextAreaElement).value).not.toContain("Mutable row content");
    const provenance = screen.getByRole("region", { name: "Report provenance" });
    expect(within(provenance).getByText("Version 4", { selector: "dd" })).toBeInTheDocument();
    expect(within(provenance).getAllByText("Version 5", { selector: "dd" })).toHaveLength(2);
    expect(within(provenance).getByText("signed-schema-v1", { selector: "dd" })).toBeInTheDocument();
    expect(within(provenance).getAllByText("Unavailable", { selector: "dd" }).length).toBeGreaterThan(0);
    expect(within(provenance).queryByText("Version 12", { selector: "dd" })).not.toBeInTheDocument();
    expect(within(provenance).queryByText("mutable-schema-v99", { selector: "dd" })).not.toBeInTheDocument();
    expect(screen.getByText("Signed snapshot · immutable")).toBeInTheDocument();
    expect(within(provenance).getByText("Therapist Snapshot", { selector: "dd" })).toBeInTheDocument();
    expect(within(provenance).getByText("2026-07-16T10:30:00Z", { selector: "dd" })).toBeInTheDocument();
    expect(within(provenance).getByText(signedFixture.reportHash, { selector: "dd" })).toBeInTheDocument();
    const sourceSafety = screen.getByRole("region", { name: "Report source and safety" });
    expect(within(sourceSafety).getByText("signed-requested", { selector: "dd" })).toBeInTheDocument();
    expect(within(sourceSafety).getByText("signed-actual", { selector: "dd" })).toBeInTheDocument();
    expect(within(sourceSafety).getByText("signed-provider-version", { selector: "dd" })).toBeInTheDocument();
    expect(within(sourceSafety).getByText("signed-validator", { selector: "dd" })).toBeInTheDocument();
    expect(within(sourceSafety).getByText("signed-rules", { selector: "dd" })).toBeInTheDocument();
    expect(within(sourceSafety).getByText("Passed", { selector: "dd" })).toBeInTheDocument();
    expect(within(sourceSafety).queryByText(/mutable-(?:actual|requested|provider-version|validator|rules)/)).not.toBeInTheDocument();

    const createRevision = screen.getByRole("button", { name: "Create report revision" });
    act(() => {
      createRevision.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      createRevision.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/reports/report-signed"),
      expect.objectContaining({ method: "PATCH" }),
    ));
    const patchCalls = fetchMock.mock.calls.filter(([input, init]) => String(input).endsWith("/reports/report-signed") && init?.method === "PATCH");
    expect(patchCalls).toHaveLength(1);
    const patchBody = JSON.parse(String(patchCalls[0][1]?.body));
    expect(patchBody.markdown).toContain("## Therapist Sign-off\nPending therapist edit and sign-off.");
    expect(patchBody.markdown).toContain("## Export Timestamp\n- Pending until therapist sign-off.");
    expect(patchBody.markdown).not.toMatch(/Signed by:|Sign-off status: Signed Off|2026-07-16T10:30:00Z/);
    await act(async () => {
      resolvePatch(jsonResponse({
        report_id: "report-revision",
        session_id: "session-signed",
        case_id: "case-signed",
        transcript_id: "transcript-signed",
        feature_result_id: "features-signed",
        feature_schema_version: "features-basic-v1",
        generated_from_versions: { transcript_version: "7", schema_version: "features-basic-v1" },
        markdown: "# Revision draft\n\nDecision-support only. Not diagnostic.\n\n## Therapist Sign-off\nPending therapist edit and sign-off.\n\n## Export Timestamp\n- Pending until therapist sign-off.",
        status: "Draft",
        version: 1,
        revision_number: 3,
        supersedes_report_id: "report-signed",
      }));
      await patchResponse;
    });
    await waitFor(() => expect(screen.getByTestId("report-preview")).not.toHaveAttribute("readonly"));
    expect((screen.getByTestId("report-preview") as HTMLTextAreaElement).value).toContain("Revision draft");
    expect(screen.getByRole("textbox", { name: "Therapist notes" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Therapy goals" })).toBeInTheDocument();
    expect(screen.getByLabelText("Drafting Provider")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Overall Progress" })).not.toBeInTheDocument();
    expect(window.location.pathname).toBe("/sessions/session-signed");
    expect(window.location.search).toBe("?view=report&case_id=case-signed&transcript_id=transcript-signed&report_id=report-revision");
    digestSpy.mockRestore();
  });

  test("fails closed when a signed snapshot payload does not match its persisted hash", async () => {
    const signedFixture = signedSnapshotFixture({
      markdown: "# Original signed content",
      report_version: 6,
      signed_by: "Verified signer",
      signed_at: "2026-07-16T11:00:00Z",
      generated_from_versions: { transcript_version: 6, schema_version: "verified-schema" },
      provider: {
        requested_provider: "verified-requested",
        actual_provider: "verified-actual",
        provider_version: "verified-provider-version",
      },
      finalized_safety_result: {
        status: "passed",
        validator_version: "verified-validator",
        rule_set_version: "verified-rules",
      },
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/session-invalid-snapshot")) return jsonResponse({ session_id: "session-invalid-snapshot", case_id: "case-invalid-snapshot", transcript_id: "transcript-invalid-snapshot", report_id: "report-invalid-snapshot" });
      if (url.endsWith("/reports/report-invalid-snapshot")) return jsonResponse({
        report_id: "report-invalid-snapshot",
        session_id: "session-invalid-snapshot",
        case_id: "case-invalid-snapshot",
        markdown: "# Mutable signed row must remain hidden",
        therapist_notes: "Mutable therapist notes must remain hidden",
        session_goals: ["Mutable therapy goal must remain hidden"],
        status: "Signed Off",
        version: 6,
        requested_provider: "mutable-row-provider",
        actual_provider: "mutable-row-actual",
        generated_from_versions: { transcript_version: 99, schema_version: "mutable-row-schema" },
        finalized_safety_result: { status: "failed", validator_version: "mutable-row-validator" },
        safety_validation_result: {
          issues: [{ issue_id: "mutable-warning", severity: "warning", message: "Mutable safety warning must remain hidden" }],
        },
        signed_snapshot_version: 6,
        signed_snapshot_hash: signedFixture.reportHash,
        signed_by: "Mutable row signer",
        signed_at: "2026-07-16T11:00:00Z",
        signed_snapshot: {
          ...signedFixture.snapshot,
          markdown: "# Tampered signed content",
          signed_by: "Tampered signer",
          generated_from_versions: { transcript_version: 88, schema_version: "tampered-schema" },
          provider: {
            requested_provider: "tampered-requested",
            actual_provider: "tampered-actual",
            provider_version: "tampered-provider-version",
          },
          finalized_safety_result: {
            status: "failed",
            validator_version: "tampered-validator",
            rule_set_version: "tampered-rules",
          },
        },
      });
      if (url.endsWith("/transcripts/transcript-invalid-snapshot")) return jsonResponse({ transcript_id: "transcript-invalid-snapshot", session_id: "session-invalid-snapshot", therapist_attested: true, version: 9 });
      if (url.endsWith("/cases/case-invalid-snapshot")) return jsonResponse({ case_id: "case-invalid-snapshot", child_code: "Case Invalid", primary_therapist_user_id: "therapist-demo" });
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<SessionReportView sessionId="session-invalid-snapshot" reportId="report-invalid-snapshot" />);

    const integrityAlert = await screen.findByRole("alert");
    expect(integrityAlert).toHaveTextContent(/signed snapshot integrity/i);
    expect(integrityAlert).toHaveTextContent(/does not match its persisted SHA-256 hash/i);
    expect(screen.queryByText("Signed snapshot · immutable")).not.toBeInTheDocument();
    expect(screen.queryByText("Eligible", { selector: "dd" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create report revision" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Copy local demo share link" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Mark caregiver share recorded" })).toBeDisabled();
    expect(screen.getByTestId("report-preview")).toHaveValue("");
    expect(screen.queryByText("Mutable signed row must remain hidden")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Report provenance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Report source and safety" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Tampered signer|tampered-(?:requested|actual|provider-version|schema|validator|rules)/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Mutable row signer|mutable-row-(?:provider|actual|schema|validator)/)).not.toBeInTheDocument();
    expect(screen.queryByText("Mutable safety warning must remain hidden")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("Mutable therapist notes must remain hidden")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("Mutable therapy goal must remain hidden")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Therapist notes" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Therapy goals" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Drafting Provider")).not.toBeInTheDocument();
  });
});

describe("Reports Library", () => {
  test("groups report status and exposes exactly one canonical next action per report", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse([
      {
        report_id: "report-draft",
        session_id: "session-draft",
        case_id: "case-draft",
        title: "Draft report",
        status: "Draft",
      },
      {
        report_id: "report-stale",
        session_id: "session-stale",
        case_id: "case-stale",
        title: "Stale report",
        status: "stale",
      },
      {
        report_id: "report-signed",
        session_id: "session-signed",
        case_id: "case-signed",
        title: "Signed report",
        status: "Signed Off",
      },
    ])));

    render(<ReportsWorkspaceClient />);

    expect(await screen.findByRole("heading", { name: "Needs review" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Needs regeneration" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Signed reports" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /report/i })).not.toBeInTheDocument();

    for (const row of screen.getAllByTestId("report-library-row")) {
      const links = within(row).getAllByRole("link");
      expect(links).toHaveLength(1);
      expect(links[0]).toHaveAttribute("href", expect.stringMatching(/^\/sessions\/[^?]+\?view=report/));
    }
  });
});
