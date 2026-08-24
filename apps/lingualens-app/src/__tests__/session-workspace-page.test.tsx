import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";

const setBackendUnavailableMock = vi.hoisted(() => vi.fn());

vi.mock("@/components/backend-availability-banner", () => ({
  BackendAvailabilityBanner: () => null,
  useBackendAvailability: () => ({
    backendUnavailable: false,
    setBackendUnavailable: setBackendUnavailableMock,
  }),
}));

vi.mock("@/components/app-shell", () => ({
  AppShell: ({ active, children }: { active: string; children: ReactNode }) => (
    <main data-active={active}>{children}</main>
  ),
}));

vi.mock("@/features/sessions/components/session-workspace", () => ({
  SessionWorkspace: (props: Record<string, string | undefined>) => (
    <section
      data-testid="session-workspace"
      data-view={props.view}
      data-session-id={props.sessionId}
      data-case-id={props.caseId}
      data-transcript-id={props.transcriptId}
      data-report-id={props.reportId}
      data-mode={props.mode}
    />
  ),
}));

import SessionWorkspacePage from "@/app/sessions/[sessionId]/page";
import { SessionWorkflowWorkspace } from "@/features/sessions/components/session-workspace-model";
import { ApiError } from "@/lib/api";
import { updateBackendTranscript, updateBackendTranscriptUtterances } from "@/lib/workflow";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
});

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

type WorkflowFixtureOptions = {
  mappingRequired?: boolean;
  saveMappingStatus?: number;
  confirmMappingStatus?: number;
  deferSave?: boolean;
  confirmTranscriptRefreshStatus?: number;
  confirmMappingRefreshStatus?: number;
};

function installWorkflowResponses({
  mappingRequired = true,
  saveMappingStatus = 200,
  confirmMappingStatus = 200,
  deferSave = false,
  confirmTranscriptRefreshStatus = 200,
  confirmMappingRefreshStatus = 200,
}: WorkflowFixtureOptions = {}) {
  let mappingPersisted = false;
  let mappingConfirmed = false;
  let transcriptEditedAfterMapping = false;
  let transcriptVersion = 1;
  let currentEntries = mappingEntries();
  let currentTranscriptLines = transcriptUtterances(mappingRequired, false);
  let releaseSave: (() => void) | undefined;
  const saveBarrier = deferSave ? new Promise<void>((resolve) => { releaseSave = resolve; }) : undefined;

  const fetchMock = vi.fn(async (request: RequestInfo | URL, init?: RequestInit) => {
    const url = String(request);
    const method = init?.method ?? "GET";
    if (url.endsWith("/sessions/session-1")) {
      return json({ session_id: "session-1", case_id: "case-synthetic", transcript_id: "tr-1" });
    }
    if (url.endsWith("/sessions/session-2")) {
      return json({ session_id: "session-2", case_id: "case-synthetic-2", transcript_id: "tr-2" });
    }
    if (url.endsWith("/cases/case-synthetic") || url.endsWith("/cases/case-synthetic-2")) {
      return json({ case_id: url.endsWith("-2") ? "case-synthetic-2" : "case-synthetic", child_code: "C-SYNTHETIC", consent_status: "granted" });
    }
    if (url.endsWith("/sessions/session-1/audio-files") || url.endsWith("/sessions/session-2/audio-files")) return json([]);
    if (url.includes("/ml-readiness")) return json({ ready: false, provider_id: "reference", reason_codes: [], reasons: [] });
    if (url.endsWith("/sessions/session-1/ml-review") || url.endsWith("/sessions/session-1/ai-review")
      || url.endsWith("/sessions/session-2/ml-review") || url.endsWith("/sessions/session-2/ai-review")) {
      return json({ detail: "Not found" }, 404);
    }
    if (url.endsWith("/transcripts/tr-1/speaker-mapping/confirm") && method === "POST") {
      if (confirmMappingStatus >= 400) {
        return confirmMappingStatus === 409
          ? json({
              detail: {
                code: "SPEAKER_MAPPING_VERSION_CONFLICT",
                message: "secret transcript content must never render",
              },
            }, confirmMappingStatus)
          : json({ detail: "Mapping confirmation unavailable" }, confirmMappingStatus);
      }
      mappingConfirmed = true;
      transcriptVersion = 2;
      currentTranscriptLines = transcriptUtterances(mappingRequired, true);
      return json(mappingResponse({ confirmed: true, persisted: true, entries: currentEntries, transcriptVersion }));
    }
    if (url.endsWith("/transcripts/tr-1/speaker-mapping") && method === "PUT") {
      if (saveBarrier) await saveBarrier;
      if (saveMappingStatus >= 400) {
        return saveMappingStatus === 409
          ? json({ detail: { code: "SPEAKER_MAPPING_VERSION_CONFLICT", message: "secret body" } }, saveMappingStatus)
          : json({ detail: "Mapping save unavailable" }, saveMappingStatus);
      }
      const body = JSON.parse(String(init?.body)) as { entries: ReturnType<typeof editableMappingEntries> };
      currentEntries = currentEntries.map((entry, index) => ({ ...entry, ...body.entries[index] }));
      mappingPersisted = true;
      return json(mappingResponse({ persisted: true, entries: currentEntries }));
    }
    if (url.endsWith("/transcripts/tr-1/speaker-mapping")) {
      if (mappingConfirmed && confirmMappingRefreshStatus >= 400) {
        return json({ detail: "Mapping refresh unavailable" }, confirmMappingRefreshStatus);
      }
      return json(mappingResponse({
        confirmed: mappingConfirmed,
        persisted: mappingPersisted || mappingConfirmed,
        entries: currentEntries,
        transcriptVersion,
        stale: transcriptEditedAfterMapping,
      }));
    }
    if (url.endsWith("/transcripts/tr-1/qa") && method === "POST") {
      return json({ transcript_id: "tr-1", overall_status: "PASS", issues: [] });
    }
    if (url.endsWith("/transcripts/tr-1/attest") && method === "POST") return new Response("", { status: 200 });
    if (url.endsWith("/transcripts/tr-1") && method === "PATCH") {
      const payload = JSON.parse(String(init?.body)) as { utterance_edits?: typeof currentTranscriptLines; raw_text?: string };
      if (payload.utterance_edits) currentTranscriptLines = payload.utterance_edits.map((utterance, index) => ({
        ...currentTranscriptLines[index],
        ...utterance,
        temporary_speaker_id: currentTranscriptLines[index]?.temporary_speaker_id,
        source_speaker_label: currentTranscriptLines[index]?.source_speaker_label,
      }));
      transcriptVersion += 1;
      transcriptEditedAfterMapping = true;
      return json(transcriptResponse({ mappingRequired, confirmed: mappingConfirmed, version: transcriptVersion, utterances: currentTranscriptLines }));
    }
    if (url.endsWith("/transcripts/tr-1")) {
      if (mappingConfirmed && confirmTranscriptRefreshStatus >= 400) {
        return json({ detail: "Transcript refresh unavailable" }, confirmTranscriptRefreshStatus);
      }
      return json(transcriptResponse({ mappingRequired, confirmed: mappingConfirmed, version: transcriptVersion, utterances: currentTranscriptLines }));
    }
    if (url.endsWith("/transcripts/tr-2")) return json({
      transcript_id: "tr-2",
      session_id: "session-2",
      case_id: "case-synthetic-2",
      source: "manual",
      version: 1,
      raw_text: "",
      qa_status: "NOT_RUN",
      utterances: [{ utterance_id: "utt-2", speaker: "CHI", text: "Synthetic manual line." }],
    });
    throw new Error(`Unexpected request: ${url} (${method})`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, releaseSave: () => releaseSave?.() };
}

function mappingEntries() {
  return [
    { temporary_speaker_id: "speaker-0", source_speaker_label: "speaker-0", provider_metadata: { provider_id: "synthetic" }, affected_utterance_ids: ["utt-0"], reviewed_utterance_ids: [] as string[], confirmed_chat_code: null as "CHI" | "THER" | null, participant_role: null as "target_child" | "therapist" | null },
    { temporary_speaker_id: "speaker-1", source_speaker_label: "speaker-1", provider_metadata: { provider_id: "synthetic" }, affected_utterance_ids: ["utt-1"], reviewed_utterance_ids: [] as string[], confirmed_chat_code: null as "CHI" | "THER" | null, participant_role: null as "target_child" | "therapist" | null },
  ];
}

function editableMappingEntries() {
  return mappingEntries().map(({ temporary_speaker_id, confirmed_chat_code, participant_role, reviewed_utterance_ids }) => ({
    temporary_speaker_id,
    confirmed_chat_code,
    participant_role,
    reviewed_utterance_ids,
  }));
}

function mappingResponse({
  confirmed = false,
  persisted = false,
  entries = mappingEntries(),
  transcriptVersion = confirmed ? 2 : 1,
  stale = false,
}: {
  confirmed?: boolean;
  persisted?: boolean;
  entries?: ReturnType<typeof mappingEntries>;
  transcriptVersion?: number;
  stale?: boolean;
} = {}) {
  return {
    mapping_id: "spmap-1",
    organization_id: "org-synthetic",
    transcript_id: "tr-1",
    source_transcript_version: stale ? Math.max(1, transcriptVersion - 1) : confirmed ? 1 : transcriptVersion,
    applied_transcript_version: confirmed ? 2 : null,
    mapping_version: persisted ? 2 : 1,
    status: confirmed ? "confirmed" : "draft",
    required: true,
    persisted,
    effective_status: stale ? "stale" : confirmed ? "confirmed" : "draft",
    issue_code: stale ? "SPEAKER_MAPPING_STALE" : null,
    issue_message: stale ? "Reload the current mapping." : null,
    confirmed_by_user_id: confirmed ? "therapist-synthetic" : null,
    confirmed_by_role: confirmed ? "therapist" : null,
    confirmed_at: confirmed ? "2026-08-24T00:00:00Z" : null,
    created_at: "2026-08-24T00:00:00Z",
    updated_at: "2026-08-24T00:00:00Z",
    entries,
  };
}

function transcriptUtterances(mappingRequired: boolean, confirmed: boolean) {
  const entries = mappingEntries();
  return entries.map((entry, index) => ({
    utterance_id: `utt-${index}`,
    speaker: confirmed ? (index === 0 ? "CHI" : "THER") : (mappingRequired ? "UNK" : index === 0 ? "CHI" : "THER"),
    text: `Synthetic ${index}.`,
    temporary_speaker_id: mappingRequired ? entry.temporary_speaker_id : null,
    source_speaker_label: mappingRequired ? entry.source_speaker_label : null,
  }));
}

function transcriptResponse({
  mappingRequired,
  confirmed,
  version = confirmed ? 2 : 1,
  utterances = transcriptUtterances(mappingRequired, confirmed),
}: {
  mappingRequired: boolean;
  confirmed: boolean;
  version?: number;
  utterances?: ReturnType<typeof transcriptUtterances>;
}) {
  return {
    transcript_id: "tr-1",
    session_id: "session-1",
    case_id: "case-synthetic",
    source: mappingRequired ? "asr_draft:synthetic" : "manual",
    version,
    raw_text: confirmed ? "@Begin\n*CHI:\tSynthetic zero.\n*THER:\tSynthetic one.\n@End" : "",
    qa_status: "NOT_RUN",
    therapist_attested: false,
    utterances,
  };
}

function completeMappingForm() {
  fireEvent.change(screen.getByLabelText("CHAT code for speaker-0"), { target: { value: "CHI" } });
  fireEvent.change(screen.getByLabelText("Participant role for speaker-0"), { target: { value: "target_child" } });
  fireEvent.click(screen.getByLabelText("Reviewed utterance utt-0 for speaker-0"));
  fireEvent.change(screen.getByLabelText("CHAT code for speaker-1"), { target: { value: "THER" } });
  fireEvent.change(screen.getByLabelText("Participant role for speaker-1"), { target: { value: "therapist" } });
  fireEvent.click(screen.getByLabelText("Reviewed utterance utt-1 for speaker-1"));
}

async function persistAndConfirmMapping() {
  completeMappingForm();
  fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));
  fireEvent.click(await screen.findByRole("button", { name: "Confirm speaker mapping" }));
}

function installMediaRecorderMock() {
  const stream = {
    getTracks: () => [{ stop: vi.fn() }],
    getAudioTracks: () => [{ addEventListener: vi.fn(), removeEventListener: vi.fn() }],
  } as unknown as MediaStream;
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn(async () => stream) },
  });
  class SyntheticMediaRecorder {
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
      this.ondataavailable?.({ data: new Blob(["synthetic audio"], { type: this.mimeType }) } as BlobEvent);
      this.onstop?.();
    }
  }
  vi.stubGlobal("MediaRecorder", SyntheticMediaRecorder);
}

function installBackgroundTranscriptionResponses(mappingRequired: boolean, deferJob = false) {
  let releaseJob!: () => void;
  const jobBarrier = new Promise<void>((resolve) => { releaseJob = resolve; });
  const fetchMock = vi.fn(async (request: RequestInfo | URL, init?: RequestInit) => {
    const url = String(request);
    if (url.includes("/audio/upload") && init?.method === "POST") {
      return json({
        details: {
          audio_file: { audio_file_id: "audio-synthetic" },
          upload_intent: { upload_url: "mock-signed-upload://audio-synthetic" },
        },
      });
    }
    if (url.endsWith("/audio/audio-synthetic/upload-file") && init?.method === "PUT") return json({ ok: true });
    if (url.includes("/audio/process") && init?.method === "POST") return json({ job_id: "job-synthetic" });
    if (url.endsWith("/jobs/job-synthetic")) {
      if (deferJob) await jobBarrier;
      return json({
        status: "needs_review",
        message: "Synthetic transcription complete.",
        details: { asr_draft: { transcript_id: "tr-background" } },
      });
    }
    if (/\/sessions\/local_[^/]+\/transcript$/.test(url)) {
      return json({
        transcript_id: "tr-background",
        session_id: "session-background",
        source: mappingRequired ? "asr_draft:synthetic" : "mock_asr_draft:synthetic",
        version: 1,
        raw_text: "",
        utterances: [{
          utterance_id: "utt-background",
          speaker: "UNK",
          text: "Synthetic background utterance.",
          temporary_speaker_id: "speaker-background",
        }],
      });
    }
    if (url.endsWith("/transcripts/tr-background/speaker-mapping")) {
      return json({
        ...mappingResponse(),
        transcript_id: "tr-background",
        entries: [{
          temporary_speaker_id: "speaker-background",
          source_speaker_label: "speaker-background",
          provider_metadata: { provider_id: "synthetic" },
          affected_utterance_ids: ["utt-background"],
          reviewed_utterance_ids: [],
          confirmed_chat_code: null,
          participant_role: null,
        }],
      });
    }
    throw new Error(`Unexpected background request: ${url} (${init?.method ?? "GET"})`);
  });
  Object.assign(fetchMock, { releaseJob });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock as typeof fetchMock & { releaseJob: () => void };
}

describe("canonical Session workspace page", () => {
  test.each([
    ["intake"],
    ["transcript"],
    ["findings"],
    ["report"],
  ] as const)(
    "dispatches the validated %s view inside the Session shell",
    async (view) => {
      render(await SessionWorkspacePage({
        params: Promise.resolve({ sessionId: "SESSION-1" }),
        searchParams: Promise.resolve({
          view,
          case_id: "CASE-1",
          transcript_id: "TRANSCRIPT-1",
          report_id: "REPORT-1",
          mode: "paste",
        }),
      }));

      const implementation = screen.getByTestId("session-workspace");
      expect(implementation.closest("main")).toHaveAttribute("data-active", "Session");
      expect(implementation).toHaveAttribute("data-session-id", "SESSION-1");
      expect(implementation).toHaveAttribute("data-case-id", "CASE-1");
      expect(implementation).toHaveAttribute("data-transcript-id", "TRANSCRIPT-1");
      expect(implementation).toHaveAttribute("data-report-id", "REPORT-1");
      expect(implementation).toHaveAttribute("data-view", view);
      expect(implementation).toHaveAttribute("data-mode", "paste");
    },
  );
});

describe("Session transcript speaker mapping integration", () => {
  test("PATCHes structured ASR utterances with stable ids, expected version, and only editable contract fields", async () => {
    const fetchMock = vi.fn(async (_request: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.method).toBe("PATCH");
      expect(JSON.parse(String(init?.body))).toEqual({
        expected_version: 4,
        reviewer_note: "Therapist saved structured transcript edits.",
        utterance_edits: [{
          utterance_id: "utt-stable",
          speaker: "CHI",
          text: "Synthetic edited utterance.",
          start_ms: 100,
          end_ms: 900,
          unintelligible: true,
        }],
      });
      return json({ transcript_id: "tr-structured", version: 5, utterances: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    await updateBackendTranscriptUtterances("tr-structured", [{
      lineId: "utt-stable",
      speaker: "CHI",
      text: "Synthetic edited utterance.",
      startMs: 100,
      endMs: 900,
      unclear: true,
      temporarySpeakerId: "must-not-be-client-authored",
      sourceSpeakerLabel: "must-not-be-client-authored",
    }], 4, "Therapist saved structured transcript edits.");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/transcripts\/tr-structured$/),
      expect.any(Object),
    );
  });

  test("includes a manual transcript expected version when the caller has one", async () => {
    const fetchMock = vi.fn(async (_request: RequestInfo | URL, _init?: RequestInit) => (
      json({ transcript_id: "tr-manual", version: 5, utterances: [] })
    ));
    vi.stubGlobal("fetch", fetchMock);

    await updateBackendTranscript("tr-manual", "@Begin\n@End", "Synthetic manual edit.", 4);

    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      expected_version: 4,
      raw_text: "@Begin\n@End",
      reviewer_note: "Synthetic manual edit.",
    });
  });

  test("places required mapping before review controls and completes save, confirm, authoritative refresh, QA, and attestation", async () => {
    const { fetchMock } = installWorkflowResponses();
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);

    const mapping = await screen.findByRole("region", { name: "Speaker mapping review" });
    const runQa = await screen.findByRole("button", { name: /run qa/i });
    const saveTranscript = screen.getByRole("button", { name: "Save draft" });
    const transcriptText = screen.getByLabelText("Utterance text 1");
    expect(mapping.compareDocumentPosition(runQa) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(runQa).toBeDisabled();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export reviewed .cha" })).toBeDisabled();
    expect(saveTranscript).toBeEnabled();
    expect(transcriptText).toBeEnabled();

    completeMappingForm();
    fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));
    const confirm = await screen.findByRole("button", { name: "Confirm speaker mapping" });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);

    expect(await screen.findByText("Speaker mapping confirmed. Run transcript QA next.")).toBeInTheDocument();
    expect(runQa).toBeEnabled();
    expect(screen.getByRole("button", { name: "Export reviewed .cha" })).toBeEnabled();
    expect(screen.getByLabelText("Speaker for line 1")).toHaveValue("CHI");
    expect(screen.getByLabelText("Speaker for line 2")).toHaveValue("THER");

    const mutationCalls = fetchMock.mock.calls.filter(([, init]) => init?.method === "PUT" || init?.method === "POST");
    const saveCall = mutationCalls.find(([url, init]) => String(url).endsWith("/speaker-mapping") && init?.method === "PUT");
    expect(JSON.parse(String(saveCall?.[1]?.body))).toEqual({
      expected_transcript_version: 1,
      entries: [
        { temporary_speaker_id: "speaker-0", confirmed_chat_code: "CHI", participant_role: "target_child", reviewed_utterance_ids: ["utt-0"] },
        { temporary_speaker_id: "speaker-1", confirmed_chat_code: "THER", participant_role: "therapist", reviewed_utterance_ids: ["utt-1"] },
      ],
    });
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/transcripts/tr-1")).length).toBeGreaterThanOrEqual(2);
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/speaker-mapping")).length).toBeGreaterThanOrEqual(3);

    fireEvent.click(runQa);
    await waitFor(() => expect(screen.getByRole("button", { name: "Attest transcript" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    await waitFor(() => expect(screen.getByTestId("transcript-attestation-badge")).toHaveTextContent("Attested"));
  });

  test("saves pre-confirmation ASR edits through structured utterances and refetches stale mapping", async () => {
    const { fetchMock } = installWorkflowResponses();
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });

    fireEvent.change(screen.getByLabelText("Utterance text 1"), { target: { value: "Synthetic edited before confirmation." } });
    expect(screen.getByRole("button", { name: /run qa/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export reviewed .cha" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() => {
      const patchCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/transcripts/tr-1") && init?.method === "PATCH");
      expect(JSON.parse(String(patchCall?.[1]?.body))).toEqual(expect.objectContaining({
        expected_version: 1,
        reviewer_note: "Therapist saved structured transcript edits.",
        utterance_edits: expect.arrayContaining([expect.objectContaining({
          utterance_id: "utt-0",
          text: "Synthetic edited before confirmation.",
        })]),
      }));
      expect(JSON.parse(String(patchCall?.[1]?.body))).not.toHaveProperty("raw_text");
    });
    expect(await screen.findByText("The speaker mapping changed. Reload and review it before continuing.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/speaker-mapping")).length).toBeGreaterThanOrEqual(2);
  });

  test("immediately gates current visible content after a confirmed mapping is edited, then structured-saves and renders stale mapping", async () => {
    const { fetchMock } = installWorkflowResponses();
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    await persistAndConfirmMapping();
    await screen.findByText("Speaker mapping confirmed. Run transcript QA next.");

    fireEvent.change(screen.getByLabelText("Utterance text 1"), { target: { value: "Synthetic edited after confirmation." } });
    const gate = screen.getByText("Save the transcript and reload the current speaker mapping before continuing review.");
    expect(gate).toHaveAttribute("id", "speaker-mapping-gate-reason");
    expect(gate).toHaveAttribute("role", "status");
    expect(gate.compareDocumentPosition(screen.getByTestId("transcript-workbench")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    for (const button of [
      screen.getByRole("button", { name: /run qa/i }),
      screen.getByRole("button", { name: "Attest transcript" }),
      screen.getByRole("button", { name: "Export reviewed .cha" }),
      screen.getByRole("button", { name: /generate report/i }),
    ]) {
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute("aria-describedby", expect.stringContaining("speaker-mapping-gate-reason"));
    }
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();
    expect(screen.getByLabelText("Utterance text 1")).toBeEnabled();
    expect(screen.getAllByText("Save the transcript and reload the current speaker mapping before continuing review.")).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("The speaker mapping changed. Reload and review it before continuing.")).toBeInTheDocument();
    const structuredPatch = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/transcripts/tr-1") && init?.method === "PATCH");
    expect(JSON.parse(String(structuredPatch?.[1]?.body))).toEqual(expect.objectContaining({
      expected_version: 2,
      utterance_edits: expect.arrayContaining([expect.objectContaining({ utterance_id: "utt-0", text: "Synthetic edited after confirmation." })]),
    }));
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export reviewed .cha" })).toBeDisabled();
  });

  test.each([
    ["transcript", { confirmTranscriptRefreshStatus: 503 }],
    ["mapping", { confirmMappingRefreshStatus: 503 }],
  ] as const)("retains committed confirmation and prevents retry when %s refresh fails", async (_failedResource, options) => {
    const { fetchMock } = installWorkflowResponses(options);
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    await persistAndConfirmMapping();

    expect(await screen.findByText("Speaker mapping was confirmed, but the current transcript could not be refreshed. Reload before continuing.")).toBeInTheDocument();
    const confirm = screen.getByRole("button", { name: "Confirm speaker mapping" });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(fetchMock.mock.calls.filter(([url, init]) => String(url).endsWith("/speaker-mapping/confirm") && init?.method === "POST")).toHaveLength(1);
    expect(screen.getByRole("button", { name: /run qa/i })).toBeDisabled();
    expect(screen.queryByText(/Mapping refresh unavailable|Transcript refresh unavailable/i)).not.toBeInTheDocument();
  });

  test("does not request or mount mapping for an unaffected transcript", async () => {
    const { fetchMock } = installWorkflowResponses({ mappingRequired: false });
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);

    await screen.findByRole("heading", { name: "Review Transcript" });
    expect(screen.queryByRole("region", { name: "Speaker mapping review" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run qa/i })).toBeEnabled();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/speaker-mapping"))).toBe(false);
  });

  test("keeps mapping dirty, exposes busy state, and guards a double draft save", async () => {
    const { fetchMock, releaseSave } = installWorkflowResponses({ deferSave: true });
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    completeMappingForm();

    const save = screen.getByRole("button", { name: "Save speaker mapping draft" });
    fireEvent.click(save);
    expect(save).toBeDisabled();
    fireEvent.click(save);
    await waitFor(() => {
      expect(fetchMock.mock.calls.filter(([url, init]) => String(url).endsWith("/speaker-mapping") && init?.method === "PUT")).toHaveLength(1);
    });

    releaseSave();
    expect(await screen.findByRole("button", { name: "Confirm speaker mapping" })).toBeEnabled();
  });

  test("shows a privacy-safe stale alert and preserves the clean persisted draft when confirmation conflicts", async () => {
    installWorkflowResponses({ confirmMappingStatus: 409 });
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    completeMappingForm();
    fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirm speaker mapping" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The speaker mapping changed. Reload and review it before continuing.");
    expect(screen.queryByText(/secret transcript content/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /run qa/i })).toBeDisabled();
  });

  test("keeps edits retryable and reports a safe issue when draft saving fails", async () => {
    installWorkflowResponses({ saveMappingStatus: 409 });
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    completeMappingForm();
    fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The speaker mapping changed. Reload and review it before continuing.");
    expect(screen.queryByText(/secret body/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
  });

  test("does not swallow an ordinary save failure and leaves the dirty draft retryable", async () => {
    installWorkflowResponses({ saveMappingStatus: 503 });
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    completeMappingForm();
    fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));

    expect(await screen.findByText("Speaker mapping update did not finish.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
  });

  test("does not swallow an ordinary confirmation failure and leaves the persisted clean draft retryable", async () => {
    installWorkflowResponses({ confirmMappingStatus: 503 });
    render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    completeMappingForm();
    fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirm speaker mapping" }));

    expect(await screen.findByText("Speaker mapping update did not finish.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeEnabled();
    expect(screen.getByRole("button", { name: /run qa/i })).toBeDisabled();
  });

  test("clears mapping state before hydrating a different session identity", async () => {
    installWorkflowResponses();
    const rendered = render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
    await screen.findByRole("region", { name: "Speaker mapping review" });
    completeMappingForm();

    rendered.rerender(<SessionWorkflowWorkspace sessionId="session-2" view="transcript" />);
    await screen.findByText("Synthetic manual line.");
    expect(screen.queryByRole("region", { name: "Speaker mapping review" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("CHAT code for speaker-0")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run qa/i })).toBeEnabled();
  });

  test.each([
    [true, true],
    [false, false],
  ])("conditionally loads mapping after background ASR completion (required=%s)", async (mappingRequired, expectsMappingRequest) => {
    installMediaRecorderMock();
    const fetchMock = installBackgroundTranscriptionResponses(mappingRequired);
    render(<SessionWorkflowWorkspace view="intake" />);

    fireEvent.change(await screen.findByLabelText("Clinician"), { target: { value: "Synthetic Therapist" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));
    fireEvent.click(screen.getByRole("button", { name: "Record in browser" }));
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await screen.findByText("Recording");
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
    await screen.findByText(/sent to the backend for transcription/i);
    fireEvent.click(screen.getByRole("button", { name: "Upload for transcription" }));

    await screen.findByText(/Synthetic transcription complete/i);
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/transcripts/tr-background/speaker-mapping"))).toBe(expectsMappingRequest);
    });
  });

  test.each(["unmount", "identity change"] as const)(
    "cancels a deferred background ASR poll on workspace %s",
    async (action) => {
      installMediaRecorderMock();
      const fetchMock = installBackgroundTranscriptionResponses(true, true);
      const rendered = render(<SessionWorkflowWorkspace view="intake" />);

      fireEvent.change(await screen.findByLabelText("Clinician"), { target: { value: "Synthetic Therapist" } });
      fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));
      fireEvent.click(screen.getByRole("button", { name: "Record in browser" }));
      fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
      await screen.findByText("Recording");
      fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
      await screen.findByText(/sent to the backend for transcription/i);
      fireEvent.click(screen.getByRole("button", { name: "Upload for transcription" }));
      await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/jobs/job-synthetic"))).toBe(true));

      if (action === "unmount") rendered.unmount();
      else rendered.rerender(<SessionWorkflowWorkspace sessionId="session-new" view="intake" />);
      await act(async () => {
        fetchMock.releaseJob();
        await new Promise((resolve) => setTimeout(resolve, 25));
      });

      await waitFor(() => {
        expect(fetchMock.mock.calls.some(([url]) => /\/sessions\/local_[^/]+\/transcript$/.test(String(url)))).toBe(false);
        expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/transcripts/tr-background/speaker-mapping"))).toBe(false);
      });
    },
  );

  test("parses structured API detail codes without changing status or body compatibility", () => {
    const body = JSON.stringify({ detail: { code: "SPEAKER_MAPPING_STALE", message: "private response detail" } });
    const error = new ApiError(409, body);
    expect(error).toMatchObject({ status: 409, body, detailCode: "SPEAKER_MAPPING_STALE" });
    expect(new ApiError(500, "not json")).toMatchObject({ status: 500, body: "not json", detailCode: undefined });
    expect(new ApiError(400, JSON.stringify({ detail: { code: 17 } }))).toMatchObject({ detailCode: undefined });
  });
});
