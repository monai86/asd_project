import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CaseDetailPage from "@/app/cases/[caseId]/page";
import CasesPage from "@/app/cases/page";
import Home from "@/app/page";
import RecordPage from "@/app/record/page";
import ReportSummaryPage from "@/app/report-summary/page";
import ResultsPage from "@/app/results/page";
import ReviewTranscriptPage from "@/app/review-transcript/page";
import TranscriptAliasPage from "@/app/transcript/page";
import SettingsPage from "@/app/settings/page";
import TodayPage from "@/app/today/page";
import LoginPage from "@/app/login/page";
import { routerPush } from "@/__tests__/setup";
import {
  WORKFLOW_STORAGE_KEY,
  createInitialWorkflowState,
  loadWorkflowState,
  saveWorkflowState
} from "@/lib/workflow";

beforeEach(() => {
  window.sessionStorage.clear();
  routerPush.mockClear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Therapist App v2 pages", () => {
  it("routes mock login by selected role without browser storage", () => {
    render(<LoginPage />);
    const enterWorkspace = screen.getByRole("link", { name: "Enter workspace" });
    expect(enterWorkspace).toHaveAttribute("href", "/today?role=therapist");

    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "admin" } });

    expect(enterWorkspace).toHaveAttribute("href", "/settings?scope=admin&role=admin");
    expect(screen.getByText("Admin opens role-scoped runtime controls.")).toBeInTheDocument();
  });

  it("opens to Quick Start with Start Recording as the primary action", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "Quick Start" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start Recording" })).toHaveAttribute("href", "/record");
    expect(screen.getByRole("link", { name: /Upload audio/ })).toHaveAttribute("href", "/record?mode=audio");
    expect(screen.getByRole("link", { name: /Upload \.cha/ })).toHaveAttribute("href", "/record?mode=cha");
    expect(screen.getByRole("link", { name: /Paste transcript/ })).toHaveAttribute("href", "/record?mode=paste");
    expect(screen.getAllByRole("link", { name: "Reports" }).every((link) => link.getAttribute("href") === "/report-summary")).toBe(true);
    expect(screen.getAllByRole("link", { name: "View all" }).some((link) => link.getAttribute("href") === "/report-summary")).toBe(true);
    expect(screen.getByText("For clinician use only. Not a diagnostic tool.")).toBeInTheDocument();
  });

  it("renders Today's Sessions with a focused expanded session card", () => {
    render(<TodayPage />);
    expect(screen.getByRole("heading", { name: "Today's Sessions" })).toBeInTheDocument();
    expect(screen.getAllByText("Ava M.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ethan L.").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Start Session" })).toHaveAttribute("href", "/record");
    expect(screen.getByRole("link", { name: "Record" })).toHaveAttribute("href", "/record");
    expect(screen.getByRole("link", { name: "Add Note" })).toHaveAttribute("href", "/record?mode=paste");
    expect(screen.queryByRole("button", { name: "Notifications" })).not.toBeInTheDocument();
  });

  it("renders case cards with consent and session context", () => {
    render(<CasesPage />);
    expect(screen.getByRole("heading", { name: "Cases" })).toBeInTheDocument();
    expect(screen.getAllByText("Consent").length).toBeGreaterThan(0);
    expect(screen.getByText("Granted")).toBeInTheDocument();
    expect(screen.getByText("Demo child")).toBeInTheDocument();
  });

  it("keeps existing case detail workflow available", () => {
    render(<CaseDetailPage params={{ caseId: "case_demo_001" }} />);
    expect(screen.getByRole("heading", { name: "Case C-1024" })).toBeInTheDocument();
    expect(screen.getByText("Consent status")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create new session" })).toHaveAttribute("href", "/record");
  });

  it("renders the Record & Analyze screen", () => {
    render(<RecordPage />);
    expect(screen.getByRole("heading", { name: "Record & Analyze" })).toBeInTheDocument();
    expect(screen.getByText("Ready to record")).toBeInTheDocument();
    expect(screen.getByText("00:00:00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start recording" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop recording" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeInTheDocument();
    expect(screen.getByText("Transcript ready")).toBeInTheDocument();
    expect(screen.getByText("ASR/transcription is experimental and uses a local mock processing API after explicit upload.")).toBeInTheDocument();
    expect(screen.getAllByText("Experimental").length).toBeGreaterThan(0);
    expect(screen.getByText("No transcript available yet")).toBeInTheDocument();
  });

  it.each([
    ["record", () => render(<RecordPage />)],
    ["results", () => render(<ResultsPage />)],
    ["review transcript", () => render(<ReviewTranscriptPage />)],
    ["report summary", () => render(<ReportSummaryPage />)]
  ])("shows explicit local workspace mode on %s when the backend is unreachable", async (_name, renderPage) => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    renderPage();

    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    expect(screen.getByText("Changes are stored locally only and may not persist across devices or server restarts.")).toBeInTheDocument();
  });

  it("keeps safe local demo input available while backend-required actions remain gated offline", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    render(<RecordPage searchParams={{ mode: "paste" }} />);

    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Pasted transcript text" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeDisabled();
  });

  it("shows a useful empty result state with a working next action", () => {
    render(<ResultsPage />);
    expect(screen.getByRole("heading", { name: "No analysis results yet" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Record or add a transcript" })).toHaveAttribute("href", "/record");
  });

  it("persists only recording metadata while audio remains memory-only", async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
      getAudioTracks: () => [{ addEventListener: vi.fn(), removeEventListener: vi.fn() }]
    } as unknown as MediaStream;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => stream) }
    });
    class PageMediaRecorder {
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
    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: PageMediaRecorder });
    Object.defineProperty(globalThis, "MediaRecorder", { configurable: true, value: PageMediaRecorder });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:page-recording") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });

    render(<RecordPage />);

    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));

    await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled());
    const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
    expect(stored.sessionId).toMatch(/^local_/);
    expect(stored.caseInfo).toEqual(expect.objectContaining({ clientLabel: "Ethan L." }));
    expect(stored.recordingStatus).toBe("recording");
    expect(stored.audioMimeType).toBe("audio/webm");
    expect(stored.analysisStatus).toBe("not_started");
    expect(stored.reportStatus).toBe("Not started");
    expect(JSON.stringify(stored)).not.toContain("blob:page-recording");
    expect(JSON.stringify(stored)).not.toContain("audio bytes");

    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
    const stopped = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
    expect(stopped.sessionId).toBe(stored.sessionId);
    expect(stopped.recordingStatus).toBe("stopped");
    expect(stopped.hasUnsavedRecording).toBe(true);
    expect(screen.getByLabelText("Recorded audio playback")).toBeInTheDocument();
  });

  it("uploads a recording explicitly, shows processing states, and routes the draft to transcript review", async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
      getAudioTracks: () => [{ addEventListener: vi.fn(), removeEventListener: vi.fn() }]
    } as unknown as MediaStream;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => stream) }
    });
    class TranscriptionMediaRecorder {
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
    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: TranscriptionMediaRecorder });
    Object.defineProperty(globalThis, "MediaRecorder", { configurable: true, value: TranscriptionMediaRecorder });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:transcription-recording") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });

    render(<RecordPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await waitFor(() => expect(screen.getByText("Recording")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));

    fireEvent.click(screen.getByRole("button", { name: "Upload for transcription" }));
    expect(screen.getByText("Queued")).toBeInTheDocument();
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/review-transcript"), { timeout: 3000 });

    const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
    expect(stored.transcriptionJobStatus).toBe("completed");
    expect(stored.transcriptReviewStatus).toBe("draft");
    expect(stored.transcriptAttested).toBe(false);
    expect(stored.featuresExtracted).toBe(false);
    expect(stored.transcriptText).toContain("*UNK:");
    expect(stored.transcriptDraftLabel).toBe("Draft transcript — therapist review required.");
  });

  it("restores the active workflow session after a page refresh", async () => {
    const saved = saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local_persisted_session",
      sessionCreatedAt: "2026-06-18T08:00:00.000Z",
      childName: "Persisted client",
      caseInfo: {
        caseId: "case_persisted",
        clientLabel: "Persisted client"
      },
      source: "paste-transcript",
      transcriptText: "@Begin\n*CHI:\thello .\n@End",
      transcriptReady: true,
      transcriptReviewStatus: "draft",
      analysisStatus: "completed",
      reportStatus: "Draft"
    });

    expect(loadWorkflowState()).toEqual(saved);

    render(<ResultsPage />);
    await waitFor(() => {
      expect(screen.getByText("Persisted client")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Transcript Ready").length).toBeGreaterThan(0);
  });

  it("renders clean session results and transcript review routes", () => {
    render(<ResultsPage />);
    expect(screen.getAllByRole("heading", { name: "Session Results" }).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Transcript Ready").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Feature Summary").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Review Needed").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Review Transcript" })[0]).toHaveAttribute("href", "/review-transcript");
    expect(screen.getAllByRole("button", { name: "Generate Report" }).length).toBeGreaterThan(0);

    cleanup();
    render(<ReviewTranscriptPage />);
    expect(screen.getByRole("heading", { name: "Review Transcript" })).toBeInTheDocument();
    expect(screen.getByText("Confirm speaker labels and transcript quality before report generation.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeInTheDocument();

    cleanup();
    render(<TranscriptAliasPage />);
    expect(screen.getByRole("heading", { name: "Review Transcript" })).toBeInTheDocument();
  });

  it("keeps report generation locked until transcript attestation", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      transcriptReady: true,
      transcriptReviewStatus: "in_review",
      transcriptAttested: false,
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "I see it." }]
    });

    render(<ReportSummaryPage />);
    await waitFor(() => expect(screen.getByText("Transcript review and attestation are required before report generation.")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Generate draft" })).toBeDisabled();
  });

  it("labels ASR output as a draft and keeps review actions required", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      source: "recording",
      transcriptText: "@Begin\n*UNK:\tMock ASR output.\n@End",
      transcriptLines: [{ lineId: "line-1", speaker: "UNK", text: "Mock ASR output." }],
      transcriptReady: true,
      transcriptReviewStatus: "draft",
      transcriptAttested: false,
      transcriptDraftLabel: "Draft transcript — therapist review required.",
      transcriptionJobStatus: "completed"
    });

    render(<ReviewTranscriptPage />);
    await waitFor(() => {
      expect(screen.getByText("Draft transcript — therapist review required.")).toBeInTheDocument();
    });
    expect(screen.getByText("Experimental ASR can be inaccurate. Verify wording, timestamps, and speaker labels before attestation.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeDisabled();
  });

  it("warns when feature extraction is locked before attestation", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-unattested",
      source: "paste-transcript",
      transcriptReady: true,
      transcriptReviewStatus: "in_review",
      transcriptAttested: false,
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "I see it." }]
    });

    render(<RecordPage />);
    await waitFor(() => {
      expect(screen.getByText("Feature extraction requires a saved, reviewed, and attested transcript.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeDisabled();
  });

  it("shows extracted language-sample cues on results without prediction claims", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEWED/extract-features")) {
        return jsonResponse({ features: [
          { name: "total_utterance_count", value: 3 },
          { name: "mean_length_of_utterance_words", value: 3.5 },
          { name: "number_of_different_words", value: 8 },
          { name: "question_ratio", value: 0.2 }
        ] });
      }
      return jsonResponse({});
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-reviewed",
      backendSessionId: "SESSION-REVIEWED",
      backendTranscriptSessionId: "SESSION-REVIEWED",
      backendTranscriptId: "TRANSCRIPT-REVIEWED",
      source: "paste-transcript",
      transcriptReady: true,
      transcriptReviewStatus: "reviewed",
      transcriptAttested: true,
      qaStatus: "pass",
      transcriptLines: [
        { lineId: "line-1", speaker: "THER", text: "What do you see?" },
        { lineId: "line-2", speaker: "CHI", text: "I see a blue car." },
        { lineId: "line-3", speaker: "CHI", text: "Blue car car." }
      ]
    });

    render(<RecordPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Extract language-sample features" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/results?")));

    cleanup();
    render(<ResultsPage />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Language-sample cues" })).toBeInTheDocument());
    expect(screen.getByText("MLU words")).toBeInTheDocument();
    expect(screen.getByText("Different words")).toBeInTheDocument();
    expect(screen.getByText("Question ratio")).toBeInTheDocument();
    expect(screen.getByText("Descriptive language-sample cues only. No diagnosis or ML prediction.")).toBeInTheDocument();
  });

  it("shows editable and dismissible ML decision support without diagnostic labels or report gating", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-ml-support",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      featuresExtracted: true,
      featureSummary: [
        { label: "MLU words", value: "3.4" },
        { label: "Question ratio", value: "12%" },
        { label: "Repetition cue", value: "2" }
      ]
    });

    render(<ResultsPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Generate ML decision support" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Generate ML decision support" }));

    expect(await screen.findByRole("heading", { name: "ML decision-support draft" })).toBeInTheDocument();
    expect(screen.getByText("Pattern cues")).toBeInTheDocument();
    expect(screen.getByText("Review suggestions")).toBeInTheDocument();
    expect(screen.getByText("Confidence and limitations")).toBeInTheDocument();
    expect(screen.getByText("This model is trained on limited/public datasets and is not clinically validated for diagnosis.")).toBeInTheDocument();
    expect(screen.queryByText(/ASD positive|ASD negative/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Editable ML review suggestions" }), {
      target: { value: "Therapist-edited suggestion." }
    });
    expect(loadWorkflowState().mlDecisionSupport?.reviewSuggestions).toEqual(["Therapist-edited suggestion."]);
    expect(screen.getAllByRole("button", { name: "Generate Report" })[0]).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Dismiss ML decision support" }));
    expect(screen.queryByRole("heading", { name: "ML decision-support draft" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Generate Report" })[0]).toBeEnabled();
  });

  it("saves review edits, runs QA, and attests before report generation unlocks", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEW") && init?.method === "PATCH") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-REVIEW", session_id: "SESSION-REVIEW", utterances: [] });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEW/qa")) {
        return jsonResponse({ overall_status: "warning", issues: [{ message: "Short transcript." }], transcript_id: "TRANSCRIPT-REVIEW" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEW/attest")) {
        return jsonResponse({ transcript_id: "TRANSCRIPT-REVIEW", therapist_attested: true });
      }
      if (url.endsWith("/sessions/SESSION-REVIEW/reports/draft")) {
        return jsonResponse({ report_id: "REPORT-REVIEW", markdown: "# Draft", status: "Draft" });
      }
      return jsonResponse({});
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-review-session",
      backendSessionId: "SESSION-REVIEW",
      backendTranscriptSessionId: "SESSION-REVIEW",
      backendTranscriptId: "TRANSCRIPT-REVIEW",
      source: "paste-transcript",
      transcriptReady: true,
      transcriptReviewStatus: "draft",
      transcriptText: "@Begin\n*THER:\tHello.\n*CHI:\tHi.\n@End",
      transcriptLines: [
        { lineId: "line-1", speaker: "THER", text: "Hello." },
        { lineId: "line-2", speaker: "CHI", text: "Hi." }
      ],
      transcriptSaveStatus: "saved"
    });

    render(<ReviewTranscriptPage />);
    expect(screen.queryByRole("textbox", { name: "Reviewed transcript text" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Utterance text 2"), { target: { value: "Hi there." } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() => {
      expect(loadWorkflowState()).toEqual(expect.objectContaining({
        transcriptReviewStatus: "in_review",
        transcriptAttested: false,
        transcriptLines: expect.arrayContaining([
          expect.objectContaining({ speaker: "CHI", text: "Hi there." })
        ])
      }));
    });

    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    await waitFor(() => expect(screen.getByText("Warning")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));

    await waitFor(() => expect(loadWorkflowState()).toEqual(expect.objectContaining({
        transcriptReviewStatus: "reviewed",
        transcriptAttested: true,
        transcriptLines: expect.arrayContaining([
          expect.objectContaining({ speaker: "CHI" })
        ])
      })));
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeEnabled();
    expect(routerPush).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Generate Report" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/report-summary?")));
  });

  it("connects paste transcript, analysis, and report actions to backend endpoints", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        return jsonResponse([{ case_id: "CASE-001", consent_status: "granted" }]);
      }
      if (url.endsWith("/cases/CASE-001/sessions") && init?.method === "POST") {
        return jsonResponse({ session_id: "SESSION-NEW", case_id: "CASE-001" });
      }
      if (url.endsWith("/sessions/SESSION-NEW/transcripts/manual") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-NEW", session_id: "SESSION-NEW", raw_text: "@Begin\n*CHI:\tHi.\n@End", review_status: "needs_review" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-NEW/qa") && init?.method === "POST") {
        return jsonResponse({ overall_status: "pass", issues: [], transcript_id: "TRANSCRIPT-NEW", can_extract_features: true });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-NEW/attest") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-NEW" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-NEW/extract-features")) {
        return jsonResponse({ feature_id: "FEATURE-001", features: { mean_length_of_utterance_words: 3.4, number_of_different_words: 82, question_ratio: "7%" } });
      }
      if (url.endsWith("/sessions/SESSION-NEW/reports/draft") && init?.method === "POST") {
        return jsonResponse({ report_id: "REPORT-001", markdown: "# Draft Report Preview\n\nDecision-support only.", export_status: "draft" });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<RecordPage searchParams={{ mode: "paste" }} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Pasted transcript text" }), {
      target: { value: "Therapist: Hello.\nChild: Hi." }
    });

    fireEvent.click(screen.getByRole("button", { name: "Save transcript" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-NEW/transcripts/manual"), expect.objectContaining({ method: "POST" })));
    expect(loadWorkflowState()).toEqual(expect.objectContaining({
      backendSessionId: "SESSION-NEW",
      backendTranscriptId: "TRANSCRIPT-NEW"
    }));

    cleanup();
    render(<ReviewTranscriptPage />);
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run QA" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-NEW/qa"), expect.any(Object)));
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-NEW/attest"), expect.objectContaining({ method: "POST" })));

    cleanup();
    render(<RecordPage />);
    fireEvent.click(screen.getByRole("button", { name: "Extract language-sample features" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-NEW/extract-features"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/results?"));

    cleanup();
    render(<ResultsPage />);
    fireEvent.click(screen.getAllByRole("button", { name: "Generate Report" })[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-NEW/reports/draft"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/report-summary?"));
  });

  it("reloads a transcript from backend route IDs instead of stale browser state", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "STALE-SESSION",
      backendTranscriptId: "STALE-TRANSCRIPT",
      transcriptText: "@Begin\n*CHI:\tStale text.\n@End",
      transcriptLines: [{ lineId: "stale", speaker: "CHI", text: "Stale text." }]
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-REOPEN")) {
        return jsonResponse({ session_id: "SESSION-REOPEN", case_id: "CASE-REOPEN", transcript_id: "TRANSCRIPT-REOPEN" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-REOPEN")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-REOPEN",
          session_id: "SESSION-REOPEN",
          case_id: "CASE-REOPEN",
          raw_text: "@Begin\n@Languages:\teng\n*CHI:\tPersisted text.\n@End",
          utterances: [{ utterance_id: "utt-1", speaker: "CHI", text: "Persisted text." }],
          qa_status: "PASS",
          therapist_attested: true
        });
      }
      if (url.endsWith("/cases/CASE-REOPEN")) {
        return jsonResponse({ case_id: "CASE-REOPEN", child_code: "C-REOPEN", nickname: "Reopened case" });
      }
      return jsonResponse({});
    }));

    render(<ReviewTranscriptPage searchParams={{
      case_id: "CASE-REOPEN",
      session_id: "SESSION-REOPEN",
      transcript_id: "TRANSCRIPT-REOPEN"
    }} />);

    expect(await screen.findByRole("textbox", { name: "Utterance text 1" })).toHaveValue("Persisted text.");
    expect(loadWorkflowState()).toEqual(expect.objectContaining({
      backendSessionId: "SESSION-REOPEN",
      backendTranscriptId: "TRANSCRIPT-REOPEN",
      transcriptAttested: true,
      transcriptSaveStatus: "saved"
    }));
  });

  it("reloads a finalized report from backend and keeps it read-only", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-FINAL")) {
        return jsonResponse({ session_id: "SESSION-FINAL", case_id: "CASE-FINAL", transcript_id: "TRANSCRIPT-FINAL", report_id: "REPORT-FINAL" });
      }
      if (url.endsWith("/reports/REPORT-FINAL")) {
        return jsonResponse({
          report_id: "REPORT-FINAL",
          session_id: "SESSION-FINAL",
          case_id: "CASE-FINAL",
          markdown: "# Finalized persisted report",
          status: "Signed Off"
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-FINAL")) {
        return jsonResponse({ transcript_id: "TRANSCRIPT-FINAL", session_id: "SESSION-FINAL", therapist_attested: true });
      }
      if (url.endsWith("/cases/CASE-FINAL")) {
        return jsonResponse({ case_id: "CASE-FINAL", child_code: "C-FINAL" });
      }
      return jsonResponse({});
    }));

    render(<ReportSummaryPage searchParams={{
      case_id: "CASE-FINAL",
      session_id: "SESSION-FINAL",
      transcript_id: "TRANSCRIPT-FINAL",
      report_id: "REPORT-FINAL"
    }} />);

    expect(await screen.findByRole("textbox", { name: "Finalized report" })).toHaveValue("# Finalized persisted report");
    expect(screen.getByRole("button", { name: "Report Finalized" })).toBeDisabled();
    expect(loadWorkflowState().backendReportId).toBe("REPORT-FINAL");
  });

  it("keeps pasted transcript input locally without claiming backend save success", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("offline");
    }));

    render(<RecordPage searchParams={{ mode: "paste" }} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Pasted transcript text" }), {
      target: {
        value: [
          "Therapist: What do you see?",
          "Child: A blue car.",
          "Parent: It is his favorite."
        ].join("\n")
      }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save transcript" }));

    await waitFor(() => {
      const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
      expect(stored.sessionId).toMatch(/^local_/);
      expect(stored.source).toBe("paste-transcript");
      expect(stored.transcriptReviewStatus).toBe("draft");
      expect(stored.transcriptSaveStatus).toBe("failed");
      expect(stored.transcriptReady).toBe(false);
      expect(stored.transcriptLines).toEqual([
        expect.objectContaining({ speaker: "THER", text: "What do you see?" }),
        expect.objectContaining({ speaker: "CHI", text: "A blue car." }),
        expect.objectContaining({ speaker: "PAR", text: "It is his favorite." })
      ]);
      expect(stored.transcriptText).toContain("*THER:\tWhat do you see?");
      expect(stored.transcriptText).toContain("*CHI:\tA blue car.");
    });

    cleanup();
    render(<ReviewTranscriptPage />);
    expect(await screen.findByRole("textbox", { name: "Utterance text 2" })).toHaveValue("A blue car.");
    expect(screen.getByText("Failed to save")).toBeInTheDocument();
  });

  it("parses uploaded CHA speaker tiers and preserves media timestamps", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("offline");
    }));
    const chaText = [
      "@Begin",
      "@Languages:\teng",
      "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
      "@ID:\teng|Demo|CHI|4;00.00|female|||Target_Child|||",
      "@Media:\tdemo_audio, audio",
      "*THER:\tShow me the car. \u0015100_900\u0015",
      "%mor:\tv|show pro:obj|me det|the n|car",
      "*CHI:\tBlue car. \u0015950_1600\u0015",
      "@End"
    ].join("\n");
    const file = new File([chaText], "sample.cha", { type: "text/plain" });
    Object.defineProperty(file, "text", { value: async () => chaText });

    render(<RecordPage searchParams={{ mode: "cha" }} />);
    fireEvent.change(screen.getByLabelText("CHA transcript file"), {
      target: { files: [file] }
    });
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: "CHA transcript text" })).toHaveValue(chaText);
    });
    expect(screen.getByText("Unsupported dependent tier %mor was not imported.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save transcript" }));

    await waitFor(() => {
      const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
      expect(stored.sourceFilename).toBe("sample.cha");
      expect(stored.transcriptLines).toEqual([
        expect.objectContaining({ speaker: "THER", text: "Show me the car.", startMs: 100, endMs: 900 }),
        expect.objectContaining({ speaker: "CHI", text: "Blue car.", startMs: 950, endMs: 1600 })
      ]);
      expect(stored.transcriptText).toContain("\u0015100_900\u0015");
      expect(stored.transcriptText).toContain("\u0015950_1600\u0015");
      expect(stored.chatMetadata).toEqual(expect.objectContaining({
        languages: ["eng"],
        media: { name: "demo_audio", type: "audio" }
      }));
      expect(stored.chatWarnings).toContain("Unsupported dependent tier %mor was not imported.");
    });

    cleanup();
    render(<ReviewTranscriptPage />);
    expect(await screen.findByRole("textbox", { name: "Utterance text 1" })).toHaveValue("Show me the car.");
    expect(screen.getByLabelText("Timestamp for line 1")).toHaveValue("00:00.100 – 00:00.900");
  });

  it("shows a clear error and does not save an invalid CHA file", async () => {
    const invalidText = "This file has no CHAT headers or speaker tiers.";
    const file = new File([invalidText], "invalid.cha", { type: "text/plain" });
    Object.defineProperty(file, "text", { value: async () => invalidText });

    render(<RecordPage searchParams={{ mode: "cha" }} />);
    fireEvent.change(screen.getByLabelText("CHA transcript file"), {
      target: { files: [file] }
    });

    expect(await screen.findByText("Invalid .cha file: expected @Begin, @End, and at least one speaker line such as *CHI:.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save transcript" })).toBeDisabled();
    expect(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY)).toBeNull();
  });

  it("generates, reviews, exports, shares, and finalizes an editable report", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn(async () => undefined) }
    });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:report") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-001/reports/draft") && init?.method === "POST") {
        return jsonResponse({
          report_id: "REPORT-001",
          session_id: "SESSION-001",
          case_id: "CASE-001",
          report_type: "Session Review Report",
          title: "Session Review Report",
          markdown: "# Draft Report Preview\n\nCaregiver reports improved turn-taking.\n\nIncrease spontaneous questions\n\nDecision-support only.",
          html: "<p>Draft Report Preview</p>"
        });
      }
      if (url.endsWith("/reports/REPORT-001") && init?.method === "PATCH") {
        return jsonResponse({ report_id: "REPORT-001", markdown: "# Edited report\n\nTherapist review required.\n\nDecision-support only. Not diagnostic.", status: "Draft" });
      }
      if (url.endsWith("/reports/REPORT-001/sign-off") && init?.method === "POST") {
        return jsonResponse({ report_id: "REPORT-001", markdown: "# Edited report\n\nSigned by: Demo Therapist", status: "Signed Off" });
      }
      if (url.includes("/reports/REPORT-001/export")) {
        return jsonResponse({ filename: "REPORT-001.md", content: "# Edited report", content_type: "text/markdown" });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-report-session",
      backendSessionId: "SESSION-001",
      backendTranscriptSessionId: "SESSION-001",
      backendTranscriptId: "TRANSCRIPT-001",
      sessionCreatedAt: "2026-06-19T08:00:00.000Z",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      featuresExtracted: true,
      featureSummary: [{ label: "MLU words", value: "3.4" }],
      therapistNotes: "Caregiver reports improved turn-taking.",
      therapyGoals: ["Increase spontaneous questions", "Expand two-word combinations"]
    });

    render(<ReportSummaryPage />);
    expect(screen.getByRole("heading", { name: "Report Summary" })).toBeInTheDocument();
    expect(screen.getByText("Ethan L.")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Overall Progress" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: "Strengths" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: "Needs Support" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: "Next Steps" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("textbox", { name: "Therapist notes" })).toHaveValue("Caregiver reports improved turn-taking.");
    expect(screen.getByRole("textbox", { name: "Therapy goals" })).toHaveValue("Increase spontaneous questions\nExpand two-word combinations");
    expect(screen.getByRole("textbox", { name: "Editable draft report preview" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate draft" }));
    await waitFor(() => {
      expect((screen.getByRole("textbox", { name: "Editable draft report preview" }) as HTMLTextAreaElement).value).toContain("Caregiver reports improved turn-taking.");
    });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Working" })).not.toBeInTheDocument());
    expect((screen.getByRole("textbox", { name: "Editable draft report preview" }) as HTMLTextAreaElement).value).toContain("Increase spontaneous questions");
    expect((screen.getByRole("textbox", { name: "Editable draft report preview" }) as HTMLTextAreaElement).value).toContain("Decision-support only.");

    fireEvent.change(screen.getByRole("textbox", { name: "Editable draft report preview" }), {
      target: { value: "# Edited report\n\nTherapist review required.\n\nDecision-support only. Not diagnostic." }
    });
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Export PDF later" })).toBeDisabled();

    expect(screen.getByText("Not shared")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy secure link" }));
    await waitFor(() => expect(screen.getByText("Secure link copied")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Mark sent to caregiver" }));
    expect(screen.getByText("Sent to caregiver")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Finalize Report" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Finalize Report" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Report Finalized" })).toBeInTheDocument());
    expect(screen.getByRole("textbox", { name: "Finalized report" })).toHaveAttribute("readonly");
    expect(screen.getByRole("button", { name: "Generate draft" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Export Markdown" }));
    fireEvent.click(screen.getByRole("button", { name: "Export HTML" }));
  });

  it("exports the reviewed line-first transcript as basic CHAT", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/transcripts/TRANSCRIPT-EXPORT/export-cha")) {
        return jsonResponse({
          filename: "TRANSCRIPT-EXPORT_reviewed.cha",
          cha_text: "@Languages:\teng\n*INV:\tTell me more.\n*GRM:\tBlue car."
        });
      }
      return jsonResponse({});
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-export-session",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      backendTranscriptId: "TRANSCRIPT-EXPORT",
      transcriptLines: [
        { lineId: "line-1", speaker: "INV", text: "Tell me more.", startMs: 100, endMs: 900 },
        { lineId: "line-2", speaker: "GRM", text: "Blue car.", startMs: 950, endMs: 1600 }
      ],
      chatMetadata: {
        languages: ["eng"],
        participants: [
          { code: "INV", name: "Investigator", role: "Investigator" },
          { code: "GRM", name: "Grandmother", role: "Adult" }
        ],
        ids: [],
        media: { name: "session_audio", type: "audio" },
        headers: {}
      }
    });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:chat-export") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    render(<ReportSummaryPage />);
    fireEvent.click(screen.getByRole("button", { name: "Export reviewed .cha" }));

    const exported = await screen.findByRole("textbox", { name: "Exported reviewed CHA" }) as HTMLTextAreaElement;
    expect(exported.value).toContain("@Languages:\teng");
    expect(exported.value).toContain("*GRM:\tBlue car.");
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("keeps admin runtime controls role-scoped in settings", () => {
    render(<SettingsPage searchParams={{}} />);
    expect(screen.getByRole("heading", { name: "Settings / Admin" })).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Owned privacy requests" })).toBeInTheDocument();
    expect(screen.queryByText("Model version")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Admin" }));

    expect(screen.getByText("Model version")).toBeInTheDocument();
    expect(screen.getByText("Runtime diagnostics")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Privacy operation queue" })).toBeInTheDocument();
  });

  it("opens settings in admin scope from mock admin login query", () => {
    render(<SettingsPage searchParams={{ scope: "admin" }} />);

    expect(screen.getByText("Model version")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Owned privacy requests" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Privacy operation queue" })).toBeInTheDocument();
  });

  it("walks through the complete simplified flow: Home -> Paste -> Review -> Results -> Report Summary -> Export .cha", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        return jsonResponse([{ case_id: "CASE-123", consent_status: "granted" }]);
      }
      if (url.endsWith("/cases/CASE-123/sessions") && init?.method === "POST") {
        return jsonResponse({ session_id: "SESSION-123", case_id: "CASE-123" });
      }
      if (url.endsWith("/sessions/SESSION-123/transcripts/manual") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-123", session_id: "SESSION-123", raw_text: "@Begin\n*CHI:\tHi.\n@End", review_status: "needs_review" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/qa") && init?.method === "POST") {
        return jsonResponse({ overall_status: "pass", issues: [], transcript_id: "TRANSCRIPT-123", can_extract_features: true });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/attest") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-123" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/export-cha")) {
        return jsonResponse({ filename: "TRANSCRIPT-123_reviewed.cha", cha_text: "@Begin\n*CHI:\tA blue ball.\n@End" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/extract-features")) {
        return jsonResponse({ feature_id: "FEAT-123", features: { mean_length_of_utterance_words: 3.2, number_of_different_words: 78, question_ratio: "5%" } });
      }
      if (url.endsWith("/sessions/SESSION-123/reports/draft") && init?.method === "POST") {
        return jsonResponse({ report_id: "REP-123", markdown: "# Draft Report Preview\n\nDecision-support only.", export_status: "draft" });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:reviewed-cha") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    render(<Home />);
    expect(screen.getByRole("heading", { name: "Quick Start" })).toBeInTheDocument();

    cleanup();
    render(<RecordPage searchParams={{ mode: "paste" }} />);
    expect(screen.getByRole("heading", { name: "Record & Analyze" })).toBeInTheDocument();
    
    const textarea = screen.getByRole("textbox", { name: "Pasted transcript text" });
    fireEvent.change(textarea, {
      target: { value: "Therapist: What is that?\nChild: A red ball.\nChild: I want it.\nChild: Yes it is." }
    });

    const saveButton = screen.getByRole("button", { name: "Save transcript" });
    fireEvent.click(saveButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-123/transcripts/manual"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/review-transcript?"));

    cleanup();
    render(<ReviewTranscriptPage />);
    expect(screen.getByRole("heading", { name: "Review Transcript" })).toBeInTheDocument();

    expect(await screen.findByRole("textbox", { name: "Utterance text 2" })).toHaveValue("A red ball.");
    fireEvent.change(screen.getByRole("textbox", { name: "Utterance text 2" }), {
      target: { value: "A blue ball." }
    });

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => {
      const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
      expect(stored.transcriptLines[1].text).toBe("A blue ball.");
    });

    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    await waitFor(() => expect(screen.getByText("Pass")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Export reviewed .cha" }));
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    await waitFor(() => expect(screen.getByText("Transcript attested")).toBeInTheDocument());

    cleanup();
    render(<RecordPage />);
    const extractButton = screen.getByRole("button", { name: "Extract language-sample features" });
    expect(extractButton).toBeEnabled();
    fireEvent.click(extractButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-123/extract-features"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/results?"));

    cleanup();
    render(<ResultsPage />);
    expect(screen.getByRole("heading", { name: "Language-sample cues" })).toBeInTheDocument();
    expect(screen.getByText("MLU words")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Generate Report" })[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-123/reports/draft"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/report-summary?"));

    cleanup();
    render(<ReportSummaryPage />);
    expect(screen.getByRole("heading", { name: "Report Summary" })).toBeInTheDocument();
  });

  it("strictly overrides stale sessionStorage transcript if transcript_id is in URL", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "STALE-SESSION",
      backendTranscriptId: "STALE-TRANSCRIPT",
      transcriptText: "@Begin\n*CHI:\tStale sessionStorage text.\n@End",
      transcriptLines: [{ lineId: "stale", speaker: "CHI", text: "Stale sessionStorage text." }]
    });
    
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-OK")) {
        return jsonResponse({ session_id: "SESSION-OK", case_id: "CASE-OK", transcript_id: "TRANSCRIPT-OK" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-OK")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-OK",
          session_id: "SESSION-OK",
          case_id: "CASE-OK",
          raw_text: "@Begin\n@Languages:\teng\n*CHI:\tWinner backend text.\n@End",
          utterances: [{ utterance_id: "utt-1", speaker: "CHI", text: "Winner backend text." }],
          qa_status: "PASS",
          therapist_attested: true
        });
      }
      if (url.endsWith("/cases/CASE-OK")) {
        return jsonResponse({ case_id: "CASE-OK", child_code: "C-OK" });
      }
      return jsonResponse({});
    }));

    render(<ReviewTranscriptPage searchParams={{
      case_id: "CASE-OK",
      session_id: "SESSION-OK",
      transcript_id: "TRANSCRIPT-OK"
    }} />);

    // Backend text must win
    expect(await screen.findByRole("textbox", { name: "Utterance text 1" })).toHaveValue("Winner backend text.");
    expect(loadWorkflowState().transcriptText).toContain("Winner backend text.");
  });

  it("enters offline mode, disables clinical-final buttons with Online only label, and hides success messages", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "SESSION-OFFLINE",
      backendTranscriptId: "TRANSCRIPT-OFFLINE",
      transcriptText: "@Begin\n*CHI:\thello .\n@End",
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "hello" }],
      transcriptReady: true,
      qaStatus: "pass",
      statusMessage: "Transcript draft saved." // Stale success message
    });

    render(<ReviewTranscriptPage searchParams={{
      case_id: "CASE-OFFLINE",
      session_id: "SESSION-OFFLINE",
      transcript_id: "TRANSCRIPT-OFFLINE"
    }} />);

    // Shows banner
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    
    // Suppresses the success status message
    expect(screen.queryByText("Transcript draft saved.")).not.toBeInTheDocument();
    
    // Button is disabled and renamed
    const attestBtn = screen.getByRole("button", { name: "Attest transcript (Online only)" });
    expect(attestBtn).toBeDisabled();
  });

  it("strictly disables report finalization inputs and save actions when finalized", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-FIN")) {
        return jsonResponse({ session_id: "SESSION-FIN", case_id: "CASE-FIN", transcript_id: "TRANSCRIPT-FIN", report_id: "REPORT-FIN" });
      }
      if (url.endsWith("/reports/REPORT-FIN")) {
        return jsonResponse({
          report_id: "REPORT-FIN",
          session_id: "SESSION-FIN",
          case_id: "CASE-FIN",
          markdown: "# Finalized report markdown",
          status: "Signed Off"
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-FIN")) {
        return jsonResponse({ transcript_id: "TRANSCRIPT-FIN", session_id: "SESSION-FIN", therapist_attested: true });
      }
      if (url.endsWith("/cases/CASE-FIN")) {
        return jsonResponse({ case_id: "CASE-FIN", child_code: "C-FIN" });
      }
      return jsonResponse({});
    }));

    render(<ReportSummaryPage searchParams={{
      case_id: "CASE-FIN",
      session_id: "SESSION-FIN",
      transcript_id: "TRANSCRIPT-FIN",
      report_id: "REPORT-FIN"
    }} />);

    const reportArea = await screen.findByRole("textbox", { name: "Finalized report" });
    expect((reportArea as HTMLTextAreaElement).readOnly).toBe(true);
    
    const finalizeBtn = screen.getByRole("button", { name: "Report Finalized" });
    expect(finalizeBtn).toBeDisabled();
    
    const saveBtn = screen.getByRole("button", { name: "Save draft" });
    expect(saveBtn).toBeDisabled();
    
    const generateBtn = screen.getByRole("button", { name: "Generate draft" });
    expect(generateBtn).toBeDisabled();
  });

  it("renders backend unavailable banner on /record, /results, and /report-summary pages in offline mode", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    
    // Test for /record page (RecordPage)
    const recordRes = render(<RecordPage searchParams={{ case_id: "OFFLINE-CASE" }} />);
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    recordRes.unmount();

    // Test for /results page (ResultsPage)
    const resultsRes = render(<ResultsPage searchParams={{ case_id: "OFFLINE-CASE" }} />);
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    resultsRes.unmount();

    // Test for /report-summary page (ReportSummaryPage)
    const reportRes = render(<ReportSummaryPage searchParams={{ case_id: "OFFLINE-CASE" }} />);
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    reportRes.unmount();
  });
});

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init
  }));
}
