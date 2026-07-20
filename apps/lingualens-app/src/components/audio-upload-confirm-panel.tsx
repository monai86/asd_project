"use client";
import { AlertTriangle, Upload, X } from "lucide-react";

type AudioUploadConfirmPanelProps = {
  blob: Blob;
  durationSeconds: number;
  onUpload: () => void;
  onCancel: () => void;
  backendAvailable: boolean;
  uploading?: boolean;
};

export function AudioUploadConfirmPanel({
  blob, durationSeconds, onUpload, onCancel, backendAvailable, uploading = false,
}: AudioUploadConfirmPanelProps) {
  const mins = Math.floor(durationSeconds / 60);
  const secs = durationSeconds % 60;
  const duration = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  const sizeMb = (blob.size / 1024 / 1024).toFixed(1);

  return (
    <div role="region" aria-label="Audio upload confirmation"
      className="rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-5 space-y-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 shrink-0 text-amber-600" size={20} aria-hidden="true" />
        <div>
          <p className="font-semibold text-amber-900">Ready to upload for transcription</p>
          <p className="mt-1 text-sm text-amber-800">Recording: {duration} · {sizeMb} MB</p>
        </div>
      </div>
      <div className="rounded-[var(--radius-card)] border border-amber-300 bg-[color:var(--color-surface-reading)] p-4 text-sm text-amber-900 space-y-2">
        <p>
          <strong>Privacy notice:</strong> Audio will be sent to the backend for transcription.
          The transcript must be reviewed by a therapist before any features are extracted.
        </p>
        <p>Audio bytes are not stored in your browser. They are uploaded once and processed server-side.</p>
        <p className="font-semibold">
          ASR transcription is experimental and not clinically validated. Therapist review required.
        </p>
      </div>
      {!backendAvailable && (
        <p className="rounded-[var(--radius-card)] border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800" role="alert">
          Backend unavailable — upload disabled. Use manual paste or .cha import instead.
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button type="button" id="btn-upload-for-transcription"
          onClick={onUpload} disabled={!backendAvailable || uploading}
          aria-busy={uploading}
          className="inline-flex items-center gap-2 rounded-[var(--radius-card)] bg-[color:var(--color-accent)] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40 disabled:cursor-not-allowed">
          <Upload size={16} aria-hidden="true" />
          {uploading ? "Uploading…" : "Upload for transcription"}
        </button>
        <button type="button" onClick={onCancel} disabled={uploading}
          className="inline-flex items-center gap-2 rounded-[var(--radius-card)] border border-slate-300 bg-[color:var(--color-surface-reading)] px-5 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-40">
          <X size={16} aria-hidden="true" /> Cancel
        </button>
      </div>
    </div>
  );
}
