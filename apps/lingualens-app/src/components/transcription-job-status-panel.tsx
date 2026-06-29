"use client";
import { AlertTriangle, CheckCircle2, Clock, Loader2, RefreshCw, XCircle } from "lucide-react";

export type TranscriptionJobDisplayStatus =
  "queued" | "processing" | "completed" | "needs_review" | "failed" | "cancelled" | "unavailable";

type Props = {
  status: TranscriptionJobDisplayStatus;
  message: string;
  requestedProvider?: string;
  actualProvider?: string;
  fallbackReason?: string;
  onOpenTranscript?: () => void;
  onRetry?: () => void;
  onUsePaste?: () => void;
};

const CFG: Record<TranscriptionJobDisplayStatus, { icon: React.ReactNode; label: string; color: string }> = {
  queued:       { icon: <Clock size={18} />, label: "Queued", color: "text-slate-600" },
  processing:   { icon: <Loader2 size={18} className="animate-spin" />, label: "Processing", color: "text-blue-600" },
  completed:    { icon: <CheckCircle2 size={18} />, label: "Draft transcript ready", color: "text-green-700" },
  needs_review: { icon: <CheckCircle2 size={18} />, label: "Draft transcript ready — review required", color: "text-green-700" },
  failed:       { icon: <XCircle size={18} />, label: "Transcription failed", color: "text-red-700" },
  cancelled:    { icon: <XCircle size={18} />, label: "Cancelled", color: "text-slate-500" },
  unavailable:  { icon: <AlertTriangle size={18} />, label: "Provider unavailable", color: "text-amber-700" },
};

export function TranscriptionJobStatusPanel({
  status, message, requestedProvider, actualProvider, fallbackReason,
  onOpenTranscript, onRetry, onUsePaste,
}: Props) {
  const cfg = CFG[status] ?? CFG.queued;
  const isSuccess = status === "completed" || status === "needs_review";
  const isError = status === "failed" || status === "unavailable";

  return (
    <div role="region" aria-label="Transcription job status" aria-live="polite"
      className="rounded-2xl border border-slate-200 bg-white/80 p-5 space-y-4">
      <div className={`flex items-center gap-2 font-semibold ${cfg.color}`}>
        {cfg.icon}<span>{cfg.label}</span>
      </div>
      <p className="text-sm text-slate-700">{message}</p>
      {fallbackReason && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          ⚠️ Fallback: {fallbackReason}
        </p>
      )}
      {actualProvider && requestedProvider && actualProvider !== requestedProvider && (
        <p className="text-xs text-slate-500">Requested: {requestedProvider} · Used: {actualProvider}</p>
      )}
      {isSuccess && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <strong>Draft ASR transcript.</strong> Therapist review required before feature extraction.
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {isSuccess && onOpenTranscript && (
          <button type="button" id="btn-open-draft-transcript" onClick={onOpenTranscript}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-br from-[#7565ff] to-[#7854ef] px-5 py-2.5 text-sm font-semibold text-white shadow-md">
            Review transcript
          </button>
        )}
        {isError && onRetry && (
          <button type="button" onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
            <RefreshCw size={15} /> Retry
          </button>
        )}
        {isError && onUsePaste && (
          <button type="button" onClick={onUsePaste}
            className="inline-flex items-center gap-2 rounded-xl border border-clinical px-4 py-2 text-sm font-semibold text-clinical">
            Use manual paste instead
          </button>
        )}
      </div>
    </div>
  );
}
