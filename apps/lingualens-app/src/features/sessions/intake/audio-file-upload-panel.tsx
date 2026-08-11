"use client";

import { AlertTriangle, CheckCircle2, FileAudio, Loader2, RefreshCw, UploadCloud } from "lucide-react";

import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";

export type AudioCapabilities = {
  milestone: "v1.7.0-testbed";
  max_size_bytes: number;
  max_duration_seconds: number;
  supported_formats: string[];
  processing_state: "available" | "unavailable";
  unavailable_reason?: string | null;
  browser_recording: {
    state: "experimental_unavailable";
    blocks_milestone: false;
  };
};

export type AudioFileUploadState =
  | { state: "idle" }
  | { state: "selected"; file: File }
  | { state: "uploading"; file: File; progress: number }
  | { state: "verifying"; audioFileId: string }
  | { state: "normalizing"; audioFileId: string }
  | { state: "transcribing"; audioFileId: string; jobId: string }
  | { state: "needs_review"; transcriptId: string }
  | { state: "failed"; code: string; message: string; retryable: boolean };

type Props = {
  capabilities: AudioCapabilities;
  state: AudioFileUploadState;
  onSelectFile: (file: File) => void;
  onConfirmUpload: () => void;
  onRetry: () => void;
  onReset: () => void;
  onOpenTranscript: (transcriptId: string) => void;
};

const MIME_BY_FORMAT: Record<string, string> = {
  wav: "audio/wav",
  mp3: "audio/mpeg",
  m4a: "audio/mp4",
  webm: "audio/webm",
};

export function AudioFileUploadPanel({
  capabilities,
  state,
  onSelectFile,
  onConfirmUpload,
  onRetry,
  onReset,
  onOpenTranscript,
}: Props) {
  const formats = capabilities.supported_formats.map((format) => format.toLowerCase());
  const accept = formats
    .flatMap((format) => [`.${format}`, MIME_BY_FORMAT[format]])
    .filter((value): value is string => Boolean(value))
    .join(",");
  const durationMinutes = capabilities.max_duration_seconds / 60;
  const maxMegabytes = capabilities.max_size_bytes / (1024 * 1024);
  const unavailable = capabilities.processing_state !== "available" || formats.length === 0;

  return (
    <WorkspacePanel className="space-y-5 p-5" role="region" aria-label="Synthetic audio upload">
      <div className="flex items-start gap-3">
        <FileAudio className="mt-0.5 text-clinical" aria-hidden="true" />
        <div>
          <h2 className="font-bold text-ink">Upload synthetic audio</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Maximum {formatNumber(durationMinutes)} minutes and {formatNumber(maxMegabytes)} MB per file.
            Supported formats: {formatList(formats)}. The server decodes and verifies the actual duration,
            size, checksum, and format before transcription.
          </p>
        </div>
      </div>

      {unavailable ? (
        <div role="alert" className="rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle size={18} aria-hidden="true" /> Audio processing unavailable
          </div>
          <p className="mt-2">The verified decoder capability is unavailable. Ask an administrator to restore the pinned audio runtime before retrying.</p>
          {capabilities.unavailable_reason ? <p className="mt-1 text-xs">Reason: {capabilities.unavailable_reason}</p> : null}
        </div>
      ) : null}

      {(state.state === "idle" || state.state === "failed") ? (
        <div>
          <label htmlFor="synthetic-audio-file" className="mb-2 block text-sm font-semibold text-ink">
            Synthetic audio file
          </label>
          <input
            id="synthetic-audio-file"
            type="file"
            accept={accept}
            disabled={unavailable}
            className="block w-full rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-3 py-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onSelectFile(file);
            }}
          />
        </div>
      ) : null}

      {state.state === "selected" ? (
        <div className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-muted)] p-4">
          <p className="font-semibold text-ink">{state.file.name}</p>
          <p className="mt-1 text-sm text-slate-600">{formatBytes(state.file.size)} selected. Audio bytes remain in memory until you confirm upload.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <PrimaryActionButton icon={UploadCloud} onClick={onConfirmUpload}>
              Confirm and upload
            </PrimaryActionButton>
            <button type="button" onClick={onReset} className="rounded-[var(--radius-card)] border border-line px-4 py-2 text-sm font-semibold text-slate-700">
              Choose another file
            </button>
          </div>
        </div>
      ) : null}

      {state.state === "uploading" ? (
        <ProgressState label="Uploading source audio" helper={`${Math.max(0, Math.min(100, state.progress))}%`} />
      ) : null}
      {state.state === "verifying" ? (
        <ProgressState label="Verifying source asset" helper="Checking the server-owned size and checksum." />
      ) : null}
      {state.state === "normalizing" ? (
        <ProgressState label="Decoding and normalizing" helper="The server is validating decoded duration and creating a deterministic mono working copy." />
      ) : null}
      {state.state === "transcribing" ? (
        <ProgressState label="Creating real transcription draft" helper="Local faster-whisper is processing the verified normalized asset." />
      ) : null}

      {state.state === "failed" ? (
        <div role="alert" className="rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-950">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle size={18} aria-hidden="true" /> Upload workflow stopped
          </div>
          <p className="mt-2">{state.message}</p>
          <p className="mt-1 text-xs">Error code: {state.code}</p>
          <div className="mt-4 flex flex-wrap gap-3">
            {state.retryable ? (
              <button type="button" onClick={onRetry} className="inline-flex items-center gap-2 rounded-[var(--radius-card)] border border-rose-300 bg-white px-4 py-2 font-semibold">
                <RefreshCw size={15} aria-hidden="true" /> Retry transcription
              </button>
            ) : null}
            <button type="button" onClick={onReset} className="rounded-[var(--radius-card)] border border-rose-300 bg-white px-4 py-2 font-semibold">
              Choose another file
            </button>
          </div>
        </div>
      ) : null}

      {state.state === "needs_review" ? (
        <div className="rounded-[var(--radius-card)] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle2 size={18} aria-hidden="true" /> Real draft ready for therapist review
          </div>
          <p className="mt-2">Review and correct all wording, timestamps, and temporary speaker labels before QA.</p>
          <PrimaryActionButton className="mt-4" onClick={() => onOpenTranscript(state.transcriptId)}>
            Review transcript
          </PrimaryActionButton>
        </div>
      ) : null}
    </WorkspacePanel>
  );
}

function ProgressState({ label, helper }: { label: string; helper: string }) {
  return (
    <div role="status" aria-live="polite" className="rounded-[var(--radius-card)] border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
      <div className="flex items-center gap-2 font-semibold">
        <Loader2 size={18} className="animate-spin" aria-hidden="true" /> {label}
      </div>
      <p className="mt-2">{helper}</p>
    </div>
  );
}

function formatList(formats: string[]): string {
  return formats.length > 0 ? formats.map((format) => format.toUpperCase()).join(", ") : "none verified";
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.ceil(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
