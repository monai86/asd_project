import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BrowserAudioRecorder } from "@/components/browser-audio-recorder";
import { SessionIntakeSteps } from "@/features/sessions/intake/session-intake-steps";
import type { SessionIntakeViewModel } from "@/features/sessions/intake/session-intake-view";

class FakeMediaRecorder {
  static isTypeSupported = vi.fn(() => true);
  state: RecordingState = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public stream: MediaStream) {}

  start() {
    this.state = "recording";
  }

  pause() {
    this.state = "paused";
  }

  resume() {
    this.state = "recording";
  }

  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio"], { type: this.mimeType }) } as BlobEvent);
    this.onstop?.();
  }
}

function streamStub() {
  return {
    getTracks: () => [{ stop: vi.fn() }],
    getAudioTracks: () => [{ addEventListener: vi.fn(), removeEventListener: vi.fn() }]
  } as unknown as MediaStream;
}

beforeEach(() => {
  Object.defineProperty(window, "MediaRecorder", { configurable: true, value: FakeMediaRecorder });
  Object.defineProperty(globalThis, "MediaRecorder", { configurable: true, value: FakeMediaRecorder });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn(async () => streamStub()) }
  });
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:recording") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("BrowserAudioRecorder", () => {
  it("records, pauses, resumes, stops, and exposes in-memory playback", async () => {
    vi.useFakeTimers();
    const onMetadataChange = vi.fn();
    const onRecordingReady = vi.fn();
    render(
      <BrowserAudioRecorder
        initialDurationSeconds={0}
        hadUnsavedRecording={false}
        onMetadataChange={onMetadataChange}
        onRecordingReady={onRecordingReady}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await act(async () => { await Promise.resolve(); });
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(screen.getByText("Recording")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(2000));
    expect(screen.getByText("00:00:02")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pause recording" }));
    expect(screen.getByRole("button", { name: "Resume recording" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Resume recording" }));
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));

    expect(screen.getByLabelText("Recorded audio playback")).toHaveAttribute("src", "blob:recording");
    expect(onMetadataChange).toHaveBeenLastCalledWith(expect.objectContaining({
      recordingStatus: "stopped",
      mimeType: "audio/webm",
      hasUnsavedRecording: true
    }));
    expect(onRecordingReady).toHaveBeenCalledWith(
      expect.any(Blob),
      expect.objectContaining({ recordingStatus: "stopped", mimeType: "audio/webm" })
    );
  });

  it("deletes and replaces recordings while revoking object URLs", async () => {
    const { unmount } = render(<BrowserAudioRecorder initialDurationSeconds={0} hadUnsavedRecording={false} onMetadataChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("Recording")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
    expect(screen.getByLabelText("Recorded audio playback")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Re-record" }));
    await act(async () => { await Promise.resolve(); });
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:recording");
    expect(screen.getByText("Recording")).toBeInTheDocument();
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
    expect(screen.getByLabelText("Recorded audio playback")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete recording" }));
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await act(async () => { await Promise.resolve(); });
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
    unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(3);
  });

  it("reports unsupported and denied microphone failures", async () => {
    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: undefined });
    const { unmount } = render(<BrowserAudioRecorder initialDurationSeconds={0} hadUnsavedRecording={false} onMetadataChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Audio recording is not supported in this browser.");
    unmount();

    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: FakeMediaRecorder });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => { throw new DOMException("Denied", "NotAllowedError"); }) }
    });
    render(<BrowserAudioRecorder initialDurationSeconds={0} hadUnsavedRecording={false} onMetadataChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByRole("alert")).toHaveTextContent("Microphone permission was denied.");
  });

  it("reports interrupted and empty recording failures", async () => {
    let ended: (() => void) | undefined;
    const interruptedStream = {
      getTracks: () => [{ stop: vi.fn() }],
      getAudioTracks: () => [{
        addEventListener: (_name: string, handler: () => void) => { ended = handler; },
        removeEventListener: vi.fn()
      }]
    } as unknown as MediaStream;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => interruptedStream) }
    });
    const { unmount } = render(<BrowserAudioRecorder initialDurationSeconds={0} hadUnsavedRecording={false} onMetadataChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await act(async () => { await Promise.resolve(); });
    act(() => ended?.());
    expect(screen.getByRole("alert")).toHaveTextContent("Recording was interrupted. Please record again.");
    unmount();

    class EmptyMediaRecorder extends FakeMediaRecorder {
      stop() {
        this.state = "inactive";
        this.onstop?.();
      }
    }
    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: EmptyMediaRecorder });
    Object.defineProperty(globalThis, "MediaRecorder", { configurable: true, value: EmptyMediaRecorder });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => streamStub()) }
    });
    render(<BrowserAudioRecorder initialDurationSeconds={0} hadUnsavedRecording={false} onMetadataChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    await act(async () => { await Promise.resolve(); });
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
    expect(screen.getByRole("alert")).toHaveTextContent("The recording was empty. Please record again.");
  });

  it("shows the privacy refresh message without restoring audio bytes", () => {
    render(<BrowserAudioRecorder initialDurationSeconds={12} hadUnsavedRecording onMetadataChange={vi.fn()} />);
    expect(screen.getByText("Unsaved recording was cleared for privacy. Please record again.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Recorded audio playback")).not.toBeInTheDocument();
  });

  describe("ASR pipeline integration", () => {
    function createMockModel(overrides?: Partial<SessionIntakeViewModel>): SessionIntakeViewModel {
      return {
        sessionContext: { childClient: "Test Child" },
        pipelineStatusValue: "idle",
        intakeStep: "source",
        setIntakeStep: vi.fn(),
        caseConsent: "granted",
        intakeError: "",
        setIntakeError: vi.fn(),
        consentChecked: true,
        setConsentChecked: vi.fn(),
        consentSigner: "Parent",
        setConsentSigner: vi.fn(),
        busy: false,
        handleGrantConsent: vi.fn(),
        sessionDetails: {
          childClient: "Test Child",
          sessionDate: "2026-08-12",
          sessionTime: "10:00",
          setting: "clinic",
          durationMinutes: "30",
          clinician: "Dr. Smith",
          sessionGoals: "Goal 1",
        },
        setSessionDetails: vi.fn(),
        sessionDetailsComplete: true,
        selectedSource: "recording",
        selectSource: vi.fn(),
        state: { recordingSeconds: 0, recordingClearedForPrivacy: false } as any,
        setState: vi.fn(),
        recordedAudio: null,
        setRecordedAudio: vi.fn(),
        handleRecordingMetadata: vi.fn(),
        handleRecordingReady: vi.fn(),
        browserRecordingEnabled: true,
        audioCapabilities: {
          milestone: "v1.7.0-testbed",
          max_size_bytes: 100 * 1024 * 1024,
          max_duration_seconds: 15 * 60,
          supported_formats: ["wav", "mp3"],
          processing_state: "available",
          unavailable_reason: null,
          normalization: {} as any,
          browser_recording: { state: "experimental_unavailable", blocks_milestone: false },
        },
        audioFileUploadState: { state: "idle" },
        handleAudioFileSelected: vi.fn(() => true),
        handleAudioFileUpload: vi.fn(),
        handleAudioJobRetry: vi.fn(),
        resetAudioFileUpload: vi.fn(),
        openAudioDraftTranscript: vi.fn(),
        backendUnavailable: false,
        draftTranscript: "",
        setDraftTranscript: vi.fn(),
        setSourceFilename: vi.fn(),
        intakeWarnings: [],
        setIntakeWarnings: vi.fn(),
        intakeValidationIssues: [],
        setIntakeValidationIssues: vi.fn(),
        handleTranscriptSubmit: vi.fn(),
        transcriptLines: [],
        transcriptSetup: {
          speakerLabels: "",
          sessionMetadata: "",
          language: "tha",
          sampleType: "conversation",
          reviewSpeakerLabels: false,
          reviewFeatureLock: false,
        },
        setTranscriptSetup: vi.fn(),
        sourceReadyForReview: false,
        canStartTranscriptReview: false,
        saveSessionIntakeDraft: vi.fn(),
        handleAnalyze: vi.fn(),
        handleGenerateReport: vi.fn(),
        router: { push: vi.fn() },
        ...overrides,
      };
    }

    it("renders 'ส่งวิเคราะห์ด้วย ASR Pipeline' button when recordedAudio is ready and invokes upload handlers", () => {
      const handleAudioFileSelected = vi.fn(() => true);
      const handleAudioFileUpload = vi.fn();
      const recordedBlob = new Blob(["test audio content"], { type: "audio/webm" });
      const model = createMockModel({
        recordedAudio: {
          blob: recordedBlob,
          metadata: { durationSeconds: 5, mimeType: "audio/webm", recordingStatus: "stopped", hasUnsavedRecording: true },
        },
        handleAudioFileSelected,
        handleAudioFileUpload,
      });

      render(<SessionIntakeSteps model={model} />);

      const actionBtn = screen.getByRole("button", { name: "ส่งวิเคราะห์ด้วย ASR Pipeline" });
      expect(actionBtn).toBeInTheDocument();
      expect(actionBtn).not.toBeDisabled();

      fireEvent.click(actionBtn);

      expect(handleAudioFileSelected).toHaveBeenCalledTimes(1);
      const passedFile = handleAudioFileSelected.mock.calls[0][0] as File;
      expect(passedFile).toBeInstanceOf(File);
      expect(passedFile.name).toBe("recording.wav");
      expect(handleAudioFileUpload).toHaveBeenCalledWith(passedFile);
    });

    it("disables the ASR analysis button during audio upload and processing", () => {
      const model = createMockModel({
        recordedAudio: {
          blob: new Blob(["test audio"], { type: "audio/wav" }),
          metadata: { durationSeconds: 3, mimeType: "audio/wav", recordingStatus: "stopped", hasUnsavedRecording: true },
        },
        audioFileUploadState: { state: "uploading", file: new File([], "recording.wav"), progress: 45 },
      });

      render(<SessionIntakeSteps model={model} />);

      const actionBtn = screen.getByRole("button", { name: "กำลังส่งวิเคราะห์..." });
      expect(actionBtn).toBeDisabled();
    });
  });
});
