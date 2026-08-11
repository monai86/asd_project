import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  AudioFileUploadPanel,
  type AudioCapabilities,
} from "@/features/sessions/intake/audio-file-upload-panel";

const capabilities: AudioCapabilities = {
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
  browser_recording: {
    state: "experimental_unavailable",
    blocks_milestone: false,
  },
};

describe("AudioFileUploadPanel", () => {
  it("shows authoritative limits and verified formats before selection", () => {
    render(
      <AudioFileUploadPanel
        capabilities={capabilities}
        state={{ state: "idle" }}
        onSelectFile={vi.fn()}
        onConfirmUpload={vi.fn()}
        onRetry={vi.fn()}
        onReset={vi.fn()}
        onOpenTranscript={vi.fn()}
      />,
    );

    expect(screen.getByText(/15 minutes/i)).toBeInTheDocument();
    expect(screen.getByText(/100 MB/i)).toBeInTheDocument();
    expect(screen.getByText(/WAV, MP3/i)).toBeInTheDocument();
    expect(
      new Set(screen.getByLabelText("Synthetic audio file").getAttribute("accept")?.split(",")),
    ).toEqual(new Set([".wav", ".mp3", "audio/wav", "audio/mpeg"]));
  });

  it("passes the selected File without reading or persisting its bytes", () => {
    const onSelectFile = vi.fn();
    render(
      <AudioFileUploadPanel
        capabilities={capabilities}
        state={{ state: "idle" }}
        onSelectFile={onSelectFile}
        onConfirmUpload={vi.fn()}
        onRetry={vi.fn()}
        onReset={vi.fn()}
        onOpenTranscript={vi.fn()}
      />,
    );
    const file = new File(["synthetic-audio"], "thai_sample.wav", {
      type: "audio/wav",
    });

    fireEvent.change(screen.getByLabelText("Synthetic audio file"), {
      target: { files: [file] },
    });

    expect(onSelectFile).toHaveBeenCalledWith(file);
    expect(JSON.stringify(window.sessionStorage)).not.toContain("synthetic-audio");
  });

  it("shows actionable server failure and retry only when explicitly retryable", () => {
    const { rerender } = render(
      <AudioFileUploadPanel
        capabilities={capabilities}
        state={{
          state: "failed",
          code: "audio_duration_limit_exceeded",
          message: "Audio is longer than 15 minutes. Choose a shorter file.",
          retryable: false,
        }}
        onSelectFile={vi.fn()}
        onConfirmUpload={vi.fn()}
        onRetry={vi.fn()}
        onReset={vi.fn()}
        onOpenTranscript={vi.fn()}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Audio is longer than 15 minutes",
    );
    expect(screen.queryByRole("button", { name: "Retry transcription" })).not.toBeInTheDocument();

    rerender(
      <AudioFileUploadPanel
        capabilities={capabilities}
        state={{
          state: "failed",
          code: "provider_unavailable",
          message: "Local faster-whisper is unavailable. Install the pinned model and retry.",
          retryable: true,
        }}
        onSelectFile={vi.fn()}
        onConfirmUpload={vi.fn()}
        onRetry={vi.fn()}
        onReset={vi.fn()}
        onOpenTranscript={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Retry transcription" })).toBeInTheDocument();
    expect(screen.queryByText(/manual paste instead/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/use mock/i)).not.toBeInTheDocument();
  });

  it("opens only a real backend draft from needs_review", () => {
    const onOpenTranscript = vi.fn();
    render(
      <AudioFileUploadPanel
        capabilities={capabilities}
        state={{ state: "needs_review", transcriptId: "tr_synthetic_001" }}
        onSelectFile={vi.fn()}
        onConfirmUpload={vi.fn()}
        onRetry={vi.fn()}
        onReset={vi.fn()}
        onOpenTranscript={onOpenTranscript}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Review transcript" }));
    expect(onOpenTranscript).toHaveBeenCalledWith("tr_synthetic_001");
  });
});
