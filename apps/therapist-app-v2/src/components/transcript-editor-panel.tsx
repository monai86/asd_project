"use client";

import { useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileCheck2,
  GitMerge,
  GitPullRequest,
  Plus,
  Play,
  Save,
  ShieldCheck,
  Trash2
} from "lucide-react";

import type { PersistenceStatus, TranscriptLine, TranscriptQaStatus } from "@/lib/workflow";

const speakers = ["CHI", "THER", "PAR", "INV", "MOT", "FAT", "UNK"];

type TranscriptEditorPanelProps = {
  lines: TranscriptLine[];
  qaStatus: TranscriptQaStatus;
  qaIssues: string[];
  attested: boolean;
  busy: boolean;
  saveStatus?: PersistenceStatus;
  onChange: (lines: TranscriptLine[]) => void;
  onSaveDraft: () => void;
  onRunQa: () => void;
  onAttest: () => void;
  onExport: () => void;
  backendUnavailable?: boolean;
  audioUrl?: string;
};

export function TranscriptEditorPanel({
  lines,
  qaStatus,
  qaIssues,
  attested,
  busy,
  saveStatus = "idle",
  onChange,
  onSaveDraft,
  onRunQa,
  onAttest,
  onExport,
  backendUnavailable,
  audioUrl
}: TranscriptEditorPanelProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [activeLineId, setActiveLineId] = useState<string | null>(null);

  function handleTimeUpdate() {
    if (!audioRef.current) return;
    const timeMs = Math.round(audioRef.current.currentTime * 1000);
    const active = lines.find(
      (line) =>
        line.startMs !== undefined &&
        line.endMs !== undefined &&
        timeMs >= line.startMs &&
        timeMs <= line.endMs
    );
    if (active) {
      if (active.lineId !== activeLineId) {
        setActiveLineId(active.lineId);
      }
    } else {
      if (activeLineId !== null) {
        setActiveLineId(null);
      }
    }
  }
  function updateLine(index: number, patch: Partial<TranscriptLine>) {
    onChange(lines.map((line, lineIndex) => lineIndex === index ? { ...line, ...patch } : line));
  }

  function addLine() {
    onChange([
      ...lines,
      {
        lineId: createLineId(),
        speaker: "UNK",
        text: "",
        unclear: false
      }
    ]);
  }

  function deleteLine(index: number) {
    onChange(lines.filter((_, lineIndex) => lineIndex !== index));
  }

  function splitLine(index: number) {
    const line = lines[index];
    const splitAt = findSplitPoint(line.text);
    const left = line.text.slice(0, splitAt).trim();
    const right = line.text.slice(splitAt).trim();
    const midpoint = midpointTimestamp(line);

    onChange([
      ...lines.slice(0, index),
      {
        ...line,
        text: left,
        ...(midpoint === undefined ? {} : { endMs: midpoint })
      },
      {
        ...line,
        lineId: createLineId(),
        text: right,
        ...(midpoint === undefined ? {} : { startMs: midpoint })
      },
      ...lines.slice(index + 1)
    ]);
  }

  function mergeLine(index: number, direction: "previous" | "next") {
    const adjacentIndex = direction === "previous" ? index - 1 : index + 1;
    if (adjacentIndex < 0 || adjacentIndex >= lines.length) return;

    const firstIndex = Math.min(index, adjacentIndex);
    const secondIndex = Math.max(index, adjacentIndex);
    const first = lines[firstIndex];
    const second = lines[secondIndex];
    const merged: TranscriptLine = {
      ...first,
      text: `${first.text.trim()} ${second.text.trim()}`.trim(),
      unclear: Boolean(first.unclear || second.unclear),
      startMs: first.startMs ?? second.startMs,
      endMs: second.endMs ?? first.endMs
    };

    onChange([
      ...lines.slice(0, firstIndex),
      merged,
      ...lines.slice(secondIndex + 1)
    ]);
  }

  const canAttest = lines.length > 0 && qaStatus !== "not_run" && qaStatus !== "fail";

  return (
    <section aria-labelledby="transcript-editor-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="transcript-editor-title" className="text-lg font-bold text-ink">Transcript lines</h2>
          <p className="mt-1 text-sm text-slate-600">Review each speaker turn. Editing after QA clears the prior QA result and attestation.</p>
        </div>
        <button
          type="button"
          onClick={addLine}
          disabled={busy}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-clinical bg-white/70 px-3 py-2 text-sm font-semibold text-clinical disabled:opacity-50"
        >
          <Plus size={16} aria-hidden="true" />
          Add line
        </button>
      </div>

      {audioUrl && (
        <div className="mt-4 rounded-2xl border border-line bg-white/80 p-4 shadow-sm backdrop-blur-md">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-ink">Session Audio Playback</h3>
              <p className="text-xs text-slate-500">Synchronized TalkBank review session</p>
            </div>
            <audio
              ref={audioRef}
              src={audioUrl}
              controls
              onTimeUpdate={handleTimeUpdate}
              className="w-full max-w-md outline-none"
              aria-label="Workspace audio playback"
            />
          </div>
        </div>
      )}

      <div className="mt-4 space-y-3">
        {lines.map((line, index) => {
          const rowStatus = getRowStatus(line, qaStatus);
          const isLineActive = line.lineId === activeLineId;
          const hasTiming = line.startMs !== undefined && line.endMs !== undefined;
          const activeStyle = isLineActive
            ? "border-clinical bg-clinical/5 ring-2 ring-clinical/20 shadow-md transition-all duration-200"
            : "border-line bg-white/65";
          return (
            <article key={line.lineId} className={`rounded-2xl border p-3 ${activeStyle}`}>
              <div className="grid gap-3 md:grid-cols-[9.5rem_8rem_1fr]">
                <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Timestamp
                  <input
                    value={formatTimestampRange(line)}
                    onChange={(event) => {
                      const timing = parseTimestampRange(event.target.value);
                      if (timing) updateLine(index, timing);
                    }}
                    aria-label={`Timestamp for line ${index + 1}`}
                    placeholder="00:00.000 – 00:01.000"
                    className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-700"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Speaker
                  <select
                    value={line.speaker}
                    onChange={(event) => updateLine(index, { speaker: event.target.value })}
                    aria-label={`Speaker for line ${index + 1}`}
                    className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-semibold normal-case tracking-normal text-ink"
                  >
                    {[...new Set([...speakers, line.speaker])].map((speaker) => (
                      <option key={speaker} value={speaker}>{speaker}</option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Utterance
                  <textarea
                    value={line.text}
                    onChange={(event) => updateLine(index, { text: event.target.value })}
                    aria-label={`Utterance text ${index + 1}`}
                    className="min-h-20 resize-y rounded-xl border border-line bg-white px-3 py-2 text-sm font-normal normal-case leading-6 tracking-normal text-ink outline-none focus:ring-2 focus:ring-clinical"
                  />
                </label>
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">QA</span>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${rowStatus.className}`}>
                    {rowStatus.label}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {hasTiming && audioUrl && (
                    <button
                      type="button"
                      aria-label={`Play line ${index + 1}`}
                      onClick={() => {
                        if (!audioRef.current) return;
                        audioRef.current.currentTime = line.startMs! / 1000;
                        audioRef.current.play();
                      }}
                      className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-2 text-xs font-semibold text-slate-700 hover:border-clinical hover:text-clinical hover:bg-clinical/5"
                    >
                      <Play size={13} fill="currentColor" aria-hidden="true" />
                      Play Turn
                    </button>
                  )}
                  <ActionButton label={`Mark line ${index + 1} unclear`} onClick={() => updateLine(index, { unclear: !line.unclear })} active={line.unclear}>
                    <AlertTriangle size={15} aria-hidden="true" />
                    {line.unclear ? "Unclear" : "Mark unclear"}
                  </ActionButton>
                  <ActionButton label={`Split line ${index + 1}`} onClick={() => splitLine(index)} disabled={!line.text.trim()}>
                    <GitPullRequest size={15} aria-hidden="true" />
                    Split
                  </ActionButton>
                  <ActionButton label={`Merge line ${index + 1} with previous`} onClick={() => mergeLine(index, "previous")} disabled={index === 0}>
                    <GitMerge size={15} aria-hidden="true" />
                    Previous
                  </ActionButton>
                  <ActionButton label={`Merge line ${index + 1} with next`} onClick={() => mergeLine(index, "next")} disabled={index === lines.length - 1}>
                    <GitMerge size={15} aria-hidden="true" />
                    Next
                  </ActionButton>
                  <ActionButton label={`Delete line ${index + 1}`} onClick={() => deleteLine(index)} tone="danger">
                    <Trash2 size={15} aria-hidden="true" />
                    Delete
                  </ActionButton>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {lines.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-white/45 p-5 text-center text-sm text-slate-600">
          Add a transcript line to begin review.
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_auto]">
        <div className="rounded-2xl border border-line bg-white/55 p-4">
          <div className="flex items-center gap-2">
            <FileCheck2 size={18} aria-hidden="true" className="text-clinical" />
            <h3 className="font-bold text-ink">Transcript QA</h3>
            <QaBadge status={qaStatus} />
          </div>
          {qaIssues.length > 0 ? (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-orange-800">
              {qaIssues.map((issue) => <li key={issue}>{issue}</li>)}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-slate-600">
              {qaStatus === "not_run" ? "Run QA after saving your edits." : "No QA issues were found."}
            </p>
          )}
          <p className="mt-3 text-xs text-slate-500">QA supports transcript review; it does not produce a diagnosis.</p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row lg:w-[25rem] lg:flex-col">
          <p className="text-center text-xs font-semibold text-slate-600" role="status">
            {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved" : saveStatus === "failed" ? "Failed to save" : saveStatus === "unsaved" ? "Unsaved changes" : "Not saved"}
          </p>
          <button type="button" onClick={onSaveDraft} disabled={busy} className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50">
            <Save size={17} aria-hidden="true" />
            Save draft
          </button>
          <button type="button" onClick={onRunQa} disabled={busy || lines.length === 0 || saveStatus !== "saved"} className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl border border-clinical bg-white px-4 py-2 text-sm font-semibold text-clinical disabled:opacity-50">
            <FileCheck2 size={17} aria-hidden="true" />
            Run QA
          </button>
          <button type="button" onClick={onAttest} disabled={busy || !canAttest || attested || backendUnavailable} className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-clinical px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300">
            {attested ? <CheckCircle2 size={17} aria-hidden="true" /> : <ShieldCheck size={17} aria-hidden="true" />}
            {attested ? "Transcript attested" : backendUnavailable ? "Attest transcript (Online only)" : "Attest transcript"}
          </button>
          <button type="button" onClick={onExport} disabled={busy || lines.length === 0} className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50">
            <Download size={17} aria-hidden="true" />
            Export reviewed .cha
          </button>
        </div>
      </div>
    </section>
  );
}

function ActionButton({
  label,
  children,
  onClick,
  disabled = false,
  active = false,
  tone = "default"
}: {
  label: string;
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  tone?: "default" | "danger";
}) {
  const color = tone === "danger"
    ? "text-red-700 hover:border-red-300"
    : active
      ? "border-orange-300 bg-orange-50 text-orange-800"
      : "text-slate-700 hover:border-clinical hover:text-clinical";
  return (
    <button type="button" aria-label={label} onClick={onClick} disabled={disabled} className={`inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-2 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-35 ${color}`}>
      {children}
    </button>
  );
}

function QaBadge({ status }: { status: TranscriptQaStatus }) {
  const styles: Record<TranscriptQaStatus, string> = {
    not_run: "bg-slate-100 text-slate-600",
    pass: "bg-emerald-100 text-emerald-700",
    warning: "bg-orange-100 text-orange-700",
    fail: "bg-red-100 text-red-700"
  };
  const labels: Record<TranscriptQaStatus, string> = {
    not_run: "Not checked",
    pass: "Pass",
    warning: "Warning",
    fail: "Needs changes"
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status]}`}>{labels[status]}</span>;
}

function parseTimestampRange(value: string): Pick<TranscriptLine, "startMs" | "endMs"> | null {
  const parts = value.split(/\s*[–-]\s*/);
  if (parts.length !== 2) return null;
  const startMs = parseTimestamp(parts[0]);
  const endMs = parseTimestamp(parts[1]);
  if (startMs === undefined || endMs === undefined || endMs < startMs) return null;
  return { startMs, endMs };
}

function parseTimestamp(value: string): number | undefined {
  const match = value.trim().match(/^(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?$/);
  if (!match) return undefined;
  const hours = Number(match[1] ?? 0);
  const minutes = Number(match[2]);
  const seconds = Number(match[3]);
  const milliseconds = Number((match[4] ?? "0").padEnd(3, "0"));
  if (minutes > 59 || seconds > 59) return undefined;
  return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds;
}

function getRowStatus(line: TranscriptLine, qaStatus: TranscriptQaStatus) {
  if (line.unclear || !line.text.trim() || line.speaker === "UNK") {
    return { label: line.unclear ? "Unclear" : "Review", className: "bg-orange-100 text-orange-700" };
  }
  if (qaStatus === "not_run") {
    return { label: "Not checked", className: "bg-slate-100 text-slate-600" };
  }
  return { label: "Checked", className: "bg-emerald-100 text-emerald-700" };
}

function findSplitPoint(text: string) {
  const midpoint = Math.max(1, Math.floor(text.length / 2));
  const nextSpace = text.indexOf(" ", midpoint);
  const previousSpace = text.lastIndexOf(" ", midpoint);
  if (nextSpace === -1 && previousSpace === -1) return midpoint;
  if (nextSpace === -1) return previousSpace;
  if (previousSpace === -1) return nextSpace;
  return midpoint - previousSpace <= nextSpace - midpoint ? previousSpace : nextSpace;
}

function midpointTimestamp(line: TranscriptLine) {
  if (line.startMs === undefined || line.endMs === undefined) return undefined;
  return Math.round((line.startMs + line.endMs) / 2);
}

function formatTimestampRange(line: TranscriptLine) {
  if (line.startMs === undefined || line.endMs === undefined) return "—";
  return `${formatTimestamp(line.startMs)} – ${formatTimestamp(line.endMs)}`;
}

function formatTimestamp(milliseconds: number) {
  const minutes = Math.floor(milliseconds / 60_000);
  const seconds = Math.floor((milliseconds % 60_000) / 1000);
  const remainder = milliseconds % 1000;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(remainder).padStart(3, "0")}`;
}

function createLineId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `line-${crypto.randomUUID()}`;
  }
  return `line-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}
