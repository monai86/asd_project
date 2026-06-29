import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RecordPage from "@/app/record/page";

beforeEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("session intake flow", () => {
  it("renders the four-step session intake flow and supports step navigation", async () => {
    render(<RecordPage />);

    expect(screen.getByRole("heading", { name: "Session Intake" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Session Details" })).toBeInTheDocument();
    expect(screen.getAllByText("Source Material").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Transcript Setup").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Review & Start").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.change(screen.getByLabelText("Session goals"), { target: { value: "Support joint attention" } });

    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    expect(await screen.findByRole("heading", { name: "Source Material" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Continue to Transcript Setup" }));

    expect(await screen.findByRole("heading", { name: "Transcript Setup" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Back to Source Material" }));
    expect(await screen.findByRole("heading", { name: "Source Material" })).toBeInTheDocument();
  });

  it("switches between source material types without breaking the existing workflows", async () => {
    render(<RecordPage />);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    await screen.findByRole("heading", { name: "Source Material" });

    fireEvent.click(screen.getByRole("button", { name: "Paste transcript" }));
    expect(screen.getByRole("textbox", { name: "Pasted transcript text" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Upload .cha" }));
    expect(screen.getByLabelText("CHA transcript file")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Upload audio" }));
    expect(screen.getByRole("button", { name: "Mark audio upload as experimental" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Record in browser" }));
    expect(screen.getByRole("button", { name: "Start recording" })).toBeInTheDocument();
  });

  it("keeps Start Transcript Review disabled until required intake fields are valid", async () => {
    render(<RecordPage />);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.change(screen.getByLabelText("Session goals"), { target: { value: "Support turn-taking" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    await screen.findByRole("heading", { name: "Source Material" });
    fireEvent.click(screen.getByRole("button", { name: "Paste transcript" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Pasted transcript text" }), {
      target: { value: "THER: hello\nCHI: hi" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Transcript Setup" }));

    await screen.findByRole("heading", { name: "Transcript Setup" });
    fireEvent.change(screen.getByLabelText("Speaker labels"), { target: { value: "THER = Therapist\nCHI = Child" } });
    fireEvent.change(screen.getByLabelText("Session metadata"), { target: { value: "Collected in clinic with caregiver present." } });
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "eng" } });
    fireEvent.change(screen.getByLabelText("Sample type"), { target: { value: "conversation" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Review & Start" }));

    expect(await screen.findByRole("button", { name: "Start Transcript Review" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Back to Transcript Setup" }));
    fireEvent.click(await screen.findByLabelText("I will review speaker labels and transcript wording before attestation."));
    fireEvent.click(screen.getByLabelText("I understand feature extraction stays locked until transcript review, QA, and attestation are complete."));
    fireEvent.click(screen.getByRole("button", { name: "Continue to Review & Start" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Start Transcript Review" })).toBeEnabled();
    });
  });

  it("requires explicit confirmation before audio upload transcription begins", async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
      getAudioTracks: () => [{ addEventListener: vi.fn(), removeEventListener: vi.fn() }]
    } as unknown as MediaStream;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => stream) }
    });

    class TestMediaRecorder {
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

    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: TestMediaRecorder });
    Object.defineProperty(globalThis, "MediaRecorder", { configurable: true, value: TestMediaRecorder });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:session-intake") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });

    render(<RecordPage />);

    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Ava M." } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));

    await screen.findByRole("heading", { name: "Source Material" });
    fireEvent.click(screen.getByRole("button", { name: "Record in browser" }));
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));

    await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));

    expect(await screen.findByRole("region", { name: "Audio upload confirmation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload for transcription" })).toBeInTheDocument();
  });
});
