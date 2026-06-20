import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BrowserAudioRecorder } from "@/components/browser-audio-recorder";

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
});
