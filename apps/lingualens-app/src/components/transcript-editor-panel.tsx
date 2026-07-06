"use client";

import { useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileCheck2,
  GitMerge,
  GitPullRequest,
  MessageSquarePlus,
  Plus,
  Play,
  Save,
  ShieldCheck,
  SlidersHorizontal,
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
  const [selectedLineId, setSelectedLineId] = useState<string | null>(lines[0]?.lineId ?? null);
  const [selectedFilter, setSelectedFilter] = useState<TranscriptFilter>("all");

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

  function addNoteLine() {
    const line = {
      lineId: createLineId(),
      speaker: "THER",
      text: "[note] ",
      unclear: false
    } satisfies TranscriptLine;
    onChange([...lines, line]);
    setSelectedFilter("notes");
    setSelectedLineId(line.lineId);
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
  const visibleLines = useMemo(
    () => lines.filter((line) => lineMatchesFilter(line, selectedFilter, qaStatus)),
    [lines, qaStatus, selectedFilter]
  );
  const qaBlockedReason = getQaBlockedReason(lines, saveStatus);
  const waveformHeights = useMemo(
    () => buildWaveformHeights(lines),
    [lines]
  );
  const activeSelectedLineId = activeLineId ?? selectedLineId;
  const selectedLineIndex = lines.findIndex((line) => line.lineId === activeSelectedLineId);

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

      <div className="mt-4 overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[linear-gradient(135deg,rgba(59,130,246,0.09),rgba(255,255,255,0.86))] p-4 shadow-soft backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="font-bold text-ink">Session Audio Playback</h3>
            <p className="text-xs text-slate-500">
              {audioUrl ? "Waveform review bar with timestamp-based line sync." : "Waveform preview only. Audio playback becomes interactive when a linked recording is available."}
            </p>
          </div>
          {audioUrl ? (
            <audio
              ref={audioRef}
              src={audioUrl}
              controls
              onTimeUpdate={handleTimeUpdate}
              className="w-full max-w-md outline-none"
              aria-label="Workspace audio playback"
            />
          ) : (
            <span className="rounded-full border border-[color:var(--color-border)] bg-white/75 px-3 py-1 text-xs font-semibold text-slate-600">
              Audio not linked
            </span>
          )}
        </div>
        <div className="mt-4 grid h-20 grid-cols-24 items-end gap-1 rounded-2xl bg-[color:rgba(255,255,255,0.72)] px-3 py-3">
          {waveformHeights.map((height, index) => (
            <span
              key={`wave-${index}`}
              className="rounded-full bg-[linear-gradient(180deg,#60A5FA,#3B82F6)] motion-reduce:transition-none"
              style={{ height: `${height}%` }}
              aria-hidden="true"
            />
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {transcriptFilters.map((filter) => {
          const count = lines.filter((line) => lineMatchesFilter(line, filter.id, qaStatus)).length;
          const active = selectedFilter === filter.id;
          return (
            <button
              key={filter.id}
              type="button"
              onClick={() => setSelectedFilter(filter.id)}
              className={`inline-flex min-h-11 items-center gap-2 rounded-full border px-3 py-2 text-sm font-semibold transition motion-reduce:transition-none ${
                active
                  ? "border-[color:var(--color-accent-subtle)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
                  : "border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-muted)]"
              }`}
              aria-pressed={active}
            >
              <span>{filter.label}</span>
              <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs text-slate-600">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-4 overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] shadow-soft">
        <div className="hidden grid-cols-[9rem_7rem_minmax(0,1fr)_7rem_7rem_17rem] gap-3 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-[color:var(--color-text-muted)] lg:grid">
          <span>Time</span>
          <span>Speaker</span>
          <span>Utterance</span>
          <span>QA</span>
          <span>Confidence</span>
          <span>Actions</span>
        </div>
        <div className="divide-y divide-[color:var(--color-border)]">
          {visibleLines.map((line) => {
            const index = lines.findIndex((entry) => entry.lineId === line.lineId);
            const rowStatus = getRowStatus(line, qaStatus);
            const confidence = getLineConfidence(line);
            const hasTiming = line.startMs !== undefined && line.endMs !== undefined;
            const isLineActive = line.lineId === activeLineId;
            const isLineSelected = line.lineId === selectedLineId;
            return (
              <article
                key={line.lineId}
                className={`px-4 py-4 transition motion-reduce:transition-none ${isLineActive || isLineSelected ? "bg-[color:var(--color-accent-soft)]/60" : "bg-transparent"}`}
                onClick={() => setSelectedLineId(line.lineId)}
              >
                <div className="grid gap-4 lg:grid-cols-[9rem_7rem_minmax(0,1fr)_7rem_7rem_17rem] lg:items-start">
                  <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <span className="lg:sr-only">Time</span>
                    <input
                      value={formatTimestampRange(line)}
                      onChange={(event) => {
                        const timing = parseTimestampRange(event.target.value);
                        if (timing) updateLine(index, timing);
                      }}
                      onFocus={() => setSelectedLineId(line.lineId)}
                      aria-label={`Timestamp for line ${index + 1}`}
                      placeholder="00:00.000 – 00:01.000"
                      className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-700"
                    />
                  </label>
                  <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <span className="lg:sr-only">Speaker</span>
                    <select
                      value={line.speaker}
                      onChange={(event) => updateLine(index, { speaker: event.target.value })}
                      onFocus={() => setSelectedLineId(line.lineId)}
                      aria-label={`Speaker for line ${index + 1}`}
                      className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-semibold normal-case tracking-normal text-ink"
                    >
                      {[...new Set([...speakers, line.speaker])].map((speaker) => (
                        <option key={speaker} value={speaker}>{speaker}</option>
                      ))}
                    </select>
                  </label>
                  <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <span className="lg:sr-only">Utterance</span>
                    <textarea
                      value={line.text}
                      onChange={(event) => updateLine(index, { text: event.target.value })}
                      onFocus={() => setSelectedLineId(line.lineId)}
                      aria-label={`Utterance text ${index + 1}`}
                      className="min-h-20 resize-y rounded-xl border border-line bg-white px-3 py-2 text-sm font-normal normal-case leading-6 tracking-normal text-ink outline-none focus:ring-2 focus:ring-clinical"
                    />
                  </label>
                  <div className="flex items-start lg:justify-center">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${rowStatus.className}`}>
                      {rowStatus.label}
                    </span>
                  </div>
                  <div className="flex items-start lg:justify-center">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${confidence.className}`}>
                      {confidence.label}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 lg:justify-end">
                    {hasTiming && audioUrl ? (
                      <button
                        type="button"
                        aria-label={`Play line ${index + 1}`}
                        onClick={() => {
                          setSelectedLineId(line.lineId);
                          if (!audioRef.current) return;
                          audioRef.current.currentTime = line.startMs! / 1000;
                          audioRef.current.play();
                        }}
                        className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-2 text-xs font-semibold text-slate-700 hover:border-clinical hover:text-clinical hover:bg-clinical/5"
                      >
                        <Play size={13} fill="currentColor" aria-hidden="true" />
                        Play Turn
                      </button>
                    ) : null}
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
      </div>

      {lines.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-white/45 p-5 text-center text-sm text-slate-600">
          Add a transcript line to begin review.
        </div>
      ) : null}
      {lines.length > 0 && visibleLines.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-white/45 p-5 text-center text-sm text-slate-600">
          No lines match the current review filter.
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_auto]">
        <div className="rounded-2xl border border-line bg-white/55 p-4" data-testid="transcript-qa-panel">
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
          <p className="mt-3 text-xs text-slate-500">QA supports transcript review and requires therapist interpretation.</p>
          {qaBlockedReason ? (
            <p id="transcript-qa-blocked-reason" className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900" role="status">
              {qaBlockedReason}
            </p>
          ) : null}
        </div>
      </div>

      <div className="sticky bottom-4 z-10 mt-5 rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:rgba(255,255,255,0.92)] p-3 shadow-[0_18px_42px_rgba(15,23,42,0.12)] backdrop-blur-xl">
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-semibold text-slate-600" role="status">
              {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved" : saveStatus === "failed" ? "Failed to save" : saveStatus === "unsaved" ? "Unsaved changes" : "Not saved"}
            </p>
            <p className="text-xs text-slate-500">
              {selectedLineIndex >= 0 ? `Selected line ${selectedLineIndex + 1}` : "Select a line to use speaker tools and notes."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSelectedFilter("missing_speaker")}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink"
            >
              <SlidersHorizontal size={16} aria-hidden="true" />
              Speaker Tools
            </button>
            <button
              type="button"
              onClick={addNoteLine}
              disabled={busy}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
            >
              <MessageSquarePlus size={16} aria-hidden="true" />
              Add Note
            </button>
            <button
              type="button"
              onClick={onSaveDraft}
              disabled={busy}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
              data-testid="save-transcript-draft-button"
            >
              <Save size={17} aria-hidden="true" />
              Save draft
            </button>
            <button
              type="button"
              onClick={onRunQa}
              disabled={busy || Boolean(qaBlockedReason)}
              title={qaBlockedReason}
              aria-describedby={qaBlockedReason ? "transcript-qa-blocked-reason" : undefined}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-clinical bg-white px-4 py-2 text-sm font-semibold text-clinical disabled:opacity-50"
              data-testid="run-transcript-qa-button"
            >
              <FileCheck2 size={17} aria-hidden="true" />
              Run QA
            </button>
            <button
              type="button"
              onClick={onAttest}
              disabled={busy || !canAttest || attested || backendUnavailable}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-clinical px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
              data-testid="attest-transcript-button"
            >
              {attested ? <CheckCircle2 size={17} aria-hidden="true" /> : <ShieldCheck size={17} aria-hidden="true" />}
              {attested ? "Transcript attested" : backendUnavailable ? "Attest transcript (Online only)" : "Attest transcript"}
            </button>
            <button type="button" onClick={onExport} disabled={busy || lines.length === 0} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50">
              <Download size={17} aria-hidden="true" />
              Export reviewed .cha
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

type TranscriptFilter = "all" | "needs_review" | "low_confidence" | "missing_speaker" | "possible_error" | "notes";

const transcriptFilters: Array<{ id: TranscriptFilter; label: string }> = [
  { id: "all", label: "All Lines" },
  { id: "needs_review", label: "Needs Review" },
  { id: "low_confidence", label: "Low Confidence" },
  { id: "missing_speaker", label: "Missing Speaker" },
  { id: "possible_error", label: "Possible Error" },
  { id: "notes", label: "Notes" }
];

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

function getQaBlockedReason(lines: TranscriptLine[], saveStatus: PersistenceStatus) {
  if (lines.length === 0) return "Add at least one transcript line before running QA.";
  if (saveStatus === "saving") return "Wait for the transcript draft to finish saving before running QA.";
  if (saveStatus === "failed") return "Save the transcript draft again before running QA.";
  if (saveStatus === "unsaved") return "Save transcript edits before running QA.";
  if (saveStatus !== "saved") return "Save the transcript draft before running QA.";
  return "";
}

function lineMatchesFilter(line: TranscriptLine, filter: TranscriptFilter, qaStatus: TranscriptQaStatus) {
  if (filter === "all") return true;
  if (filter === "needs_review") return hasReviewRisk(line) || qaStatus === "warning" || qaStatus === "fail";
  if (filter === "low_confidence") return getLineConfidence(line).label !== "High";
  if (filter === "missing_speaker") return !line.speaker.trim() || line.speaker === "UNK";
  if (filter === "possible_error") return lineHasPossibleError(line);
  if (filter === "notes") return isNoteLine(line);
  return true;
}

function hasReviewRisk(line: TranscriptLine) {
  return line.unclear || !line.text.trim() || line.speaker === "UNK" || lineHasPossibleError(line);
}

function isNoteLine(line: TranscriptLine) {
  return /^\s*\[note\]/i.test(line.text);
}

function lineHasPossibleError(line: TranscriptLine) {
  return /\b(?:xxx|yyy|www|\[unclear\])\b/i.test(line.text) || (line.startMs !== undefined && line.endMs !== undefined && line.endMs < line.startMs);
}

function getLineConfidence(line: TranscriptLine) {
  if (line.unclear || line.speaker === "UNK") {
    return { label: "Low", className: "bg-red-100 text-red-700" };
  }
  if (lineHasPossibleError(line) || line.startMs === undefined || line.endMs === undefined) {
    return { label: "Review", className: "bg-orange-100 text-orange-700" };
  }
  return { label: "High", className: "bg-emerald-100 text-emerald-700" };
}

function buildWaveformHeights(lines: TranscriptLine[]) {
  const base = Array.from({ length: 24 }, (_, index) => {
    const line = lines[index % Math.max(lines.length, 1)];
    const textSize = line?.text?.trim().length ?? 6;
    const derived = 18 + ((textSize + index * 7) % 52);
    return Math.max(14, Math.min(78, derived));
  });
  return base;
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
