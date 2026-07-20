"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import {
  CheckCircle2,
  Download,
  FileCheck2,
  MessageSquarePlus,
  Plus,
  Save,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";

import {
  QaBadge,
  buildWaveformHeights,
  createLineId,
  findSplitPoint,
  getQaBlockedReason,
  lineMatchesFilter,
  midpointTimestamp,
  transcriptFilters,
  type TranscriptFilter,
} from "@/components/transcript-editor-support";
import { TranscriptLineList } from "@/components/transcript-line-list";
import type { PersistenceStatus, TranscriptLine, TranscriptQaStatus } from "@/lib/workflow";


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
  const [openMenuLineId, setOpenMenuLineId] = useState<string | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [inspectorView, setInspectorView] = useState<"audio" | "qa">("audio");
  const menuButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const lineRowRefs = useRef(new Map<string, HTMLElement>());
  const linesRef = useRef(lines);
  const onChangeRef = useRef(onChange);
  linesRef.current = lines;
  onChangeRef.current = onChange;

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
  const updateLine = useCallback((index: number, patch: Partial<TranscriptLine>) => {
    onChangeRef.current(linesRef.current.map((line, lineIndex) => lineIndex === index ? { ...line, ...patch } : line));
  }, []);

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

  const deleteLine = useCallback((index: number) => {
    onChangeRef.current(linesRef.current.filter((_, lineIndex) => lineIndex !== index));
  }, []);

  const splitLine = useCallback((index: number) => {
    const currentLines = linesRef.current;
    const line = currentLines[index];
    const splitAt = findSplitPoint(line.text);
    const left = line.text.slice(0, splitAt).trim();
    const right = line.text.slice(splitAt).trim();
    const midpoint = midpointTimestamp(line);

    onChangeRef.current([
      ...currentLines.slice(0, index),
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
      ...currentLines.slice(index + 1)
    ]);
  }, []);

  const mergeLine = useCallback((index: number, direction: "previous" | "next") => {
    const currentLines = linesRef.current;
    const adjacentIndex = direction === "previous" ? index - 1 : index + 1;
    if (adjacentIndex < 0 || adjacentIndex >= currentLines.length) return;

    const firstIndex = Math.min(index, adjacentIndex);
    const secondIndex = Math.max(index, adjacentIndex);
    const first = currentLines[firstIndex];
    const second = currentLines[secondIndex];
    const merged: TranscriptLine = {
      ...first,
      text: `${first.text.trim()} ${second.text.trim()}`.trim(),
      unclear: Boolean(first.unclear || second.unclear),
      startMs: first.startMs ?? second.startMs,
      endMs: second.endMs ?? first.endMs
    };

    onChangeRef.current([
      ...currentLines.slice(0, firstIndex),
      merged,
      ...currentLines.slice(secondIndex + 1)
    ]);
  }, []);

  const canAttest = lines.length > 0 && qaStatus !== "not_run" && qaStatus !== "fail";
  const visibleLines = useMemo(
    () => lines.filter((line) => lineMatchesFilter(line, selectedFilter, qaStatus)),
    [lines, qaStatus, selectedFilter]
  );
  const lineIndexById = useMemo(
    () => new Map(lines.map((line, index) => [line.lineId, index])),
    [lines]
  );
  const qaBlockedReason = getQaBlockedReason(lines, saveStatus);
  const waveformHeights = useMemo(
    () => buildWaveformHeights(lines),
    [lines]
  );
  const activeSelectedLineId = activeLineId ?? selectedLineId;
  const selectedLineIndex = activeSelectedLineId ? (lineIndexById.get(activeSelectedLineId) ?? -1) : -1;

  const closeLineMenu = useCallback((lineId: string, restoreFocus = true) => {
    setOpenMenuLineId(null);
    if (restoreFocus) {
      queueMicrotask(() => menuButtonRefs.current.get(lineId)?.focus());
    }
  }, []);

  const selectLine = useCallback((lineId: string) => {
    setSelectedLineId(lineId);
    queueMicrotask(() => {
      const row = lineRowRefs.current.get(lineId);
      row?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    });
  }, []);
  const toggleLineMenu = useCallback((lineId: string) => {
    setSelectedLineId(lineId);
    setOpenMenuLineId((current) => current === lineId ? null : lineId);
  }, []);
  const registerMenuButton = useCallback((lineId: string, node: HTMLButtonElement | null) => {
    if (node) menuButtonRefs.current.set(lineId, node);
    else menuButtonRefs.current.delete(lineId);
  }, []);
  const registerLineRow = useCallback((lineId: string, node: HTMLElement | null) => {
    if (node) lineRowRefs.current.set(lineId, node);
    else lineRowRefs.current.delete(lineId);
  }, []);
  const playLine = useCallback((line: TranscriptLine) => {
    setSelectedLineId(line.lineId);
    if (!audioRef.current || line.startMs === undefined) return;
    audioRef.current.currentTime = line.startMs / 1000;
    void audioRef.current.play();
  }, []);

  return (
    <section
      aria-labelledby="transcript-editor-title"
      className={`min-w-0 max-md:pb-44 xl:grid xl:gap-x-5 ${inspectorOpen ? "xl:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]" : "xl:grid-cols-1"}`}
      data-testid="transcript-workbench"
    >
      <div className={inspectorOpen ? "flex flex-wrap items-start justify-between gap-3 xl:col-span-2" : "flex flex-wrap items-start justify-between gap-3"}>
        <div>
          <h2 id="transcript-editor-title" className="text-lg font-bold text-ink">Transcript lines</h2>
          <p className="mt-1 text-sm text-slate-600">Review each speaker turn. Editing after QA clears the prior QA result and attestation.</p>
        </div>
        <button
          type="button"
          onClick={addLine}
          disabled={busy}
          className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-clinical bg-[color:var(--color-surface-reading)] px-3 py-2 text-sm font-semibold text-clinical disabled:opacity-50"
        >
          <Plus size={16} aria-hidden="true" />
          Add line
        </button>
      </div>

      <div className={`mt-4 hidden items-center justify-between gap-3 md:flex ${inspectorOpen ? "xl:col-span-2" : ""}`}>
        {inspectorOpen ? (
          <div className="inline-flex rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-1" aria-label="Inspector view">
            {(["audio", "qa"] as const).map((view) => (
              <button
                key={view}
                type="button"
                aria-pressed={inspectorView === view}
                onClick={() => setInspectorView(view)}
                className={`min-h-11 rounded-md px-4 text-sm font-semibold ${inspectorView === view ? "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]" : "text-[color:var(--color-text-muted)]"}`}
              >
                {view === "audio" ? "Audio" : "QA"}
              </button>
            ))}
          </div>
        ) : <span />}
        <button
          type="button"
          aria-expanded={inspectorOpen}
          onClick={() => setInspectorOpen((current) => !current)}
          className="min-h-11 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm font-semibold text-[color:var(--color-text-muted)]"
        >
          {inspectorOpen ? "Hide inspector" : "Show Audio and QA"}
        </button>
      </div>

      <div className={`mt-4 overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-slate-50 p-4 max-md:sticky max-md:top-0 max-md:z-20 xl:col-start-2 xl:row-start-3 xl:self-start ${!inspectorOpen ? "hidden" : inspectorView === "qa" ? "md:hidden xl:block" : ""}`} data-testid="transcript-audio-inspector">
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
            <span className="rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 py-1 text-xs font-semibold text-slate-600">
              Audio not linked
            </span>
          )}
        </div>
        <div className="mt-4 grid h-20 grid-cols-24 items-end gap-1 rounded-lg bg-[color:var(--color-surface-reading)] border border-slate-100 px-3 py-3">
          {waveformHeights.map((height, index) => (
            <span
              key={`wave-${index}`}
              className="rounded-full bg-[color:var(--color-accent)] opacity-80 motion-reduce:transition-none"
              style={{ height: `${height}%` }}
              aria-hidden="true"
            />
          ))}
        </div>
      </div>

      <div className="mt-4 flex min-w-0 flex-wrap content-start items-start gap-2 self-start xl:col-start-1 xl:row-start-3">
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
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{count}</span>
            </button>
          );
        })}
      </div>

      <TranscriptLineList
        lines={lines}
        visibleLines={visibleLines}
        lineIndexById={lineIndexById}
        qaStatus={qaStatus}
        activeLineId={activeLineId}
        selectedLineId={selectedLineId}
        openMenuLineId={openMenuLineId}
        audioUrl={audioUrl}
        updateLine={updateLine}
        selectLine={selectLine}
        playLine={playLine}
        registerLineRow={registerLineRow}
        registerMenuButton={registerMenuButton}
        toggleLineMenu={toggleLineMenu}
        closeLineMenu={closeLineMenu}
        splitLine={splitLine}
        mergeLine={mergeLine}
        deleteLine={deleteLine}
      />

      {lines.length === 0 ? (
        <div className="mt-4 rounded-[var(--radius-panel)] border border-dashed border-line bg-slate-50 p-5 text-center text-sm text-slate-600">
          Add a transcript line to begin review.
        </div>
      ) : null}
      {lines.length > 0 && visibleLines.length === 0 ? (
        <div className="mt-4 rounded-[var(--radius-panel)] border border-dashed border-line bg-slate-50 p-5 text-center text-sm text-slate-600">
          No lines match the current review filter.
        </div>
      ) : null}

      <div className={`mt-5 grid gap-4 xl:col-start-2 xl:row-start-4 xl:self-start ${!inspectorOpen ? "hidden" : inspectorView === "audio" ? "md:hidden xl:grid" : ""}`}>
        <div className="rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4" data-testid="transcript-qa-panel">
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
            <p id="transcript-qa-blocked-reason" className="mt-3 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900" role="status">
              {qaBlockedReason}
            </p>
          ) : null}
        </div>
      </div>

      <div className={`mt-5 rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-3 max-md:sticky max-md:bottom-[calc(4rem+env(safe-area-inset-bottom,0px))] max-md:z-30 max-md:pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))] ${inspectorOpen ? "xl:col-span-2 xl:row-start-5" : ""}`}>
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-semibold text-slate-600" role="status" aria-live="polite" aria-label="Transcript save status">
              {saveStatus === "saving" ? "Saving transcript" : saveStatus === "saved" ? "Transcript saved" : saveStatus === "failed" ? "Failed to save transcript" : saveStatus === "unsaved" ? "Unsaved transcript changes" : "Transcript not saved"}
            </p>
            <p className="text-xs text-slate-500">
              {selectedLineIndex >= 0 ? `Selected line ${selectedLineIndex + 1}` : "Select a line to use speaker tools and notes."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 max-md:flex-nowrap max-md:overflow-x-auto max-md:pb-1 max-md:[&>button]:shrink-0">
            <button
              type="button"
              onClick={() => setSelectedFilter("missing_speaker")}
              className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-semibold text-ink max-md:order-4"
            >
              <SlidersHorizontal size={16} aria-hidden="true" />
              Speaker Tools
            </button>
            <button
              type="button"
              onClick={addNoteLine}
              disabled={busy}
              className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50 max-md:order-5"
            >
              <MessageSquarePlus size={16} aria-hidden="true" />
              Add Note
            </button>
            <button
              type="button"
              onClick={onSaveDraft}
              disabled={busy}
              className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50 max-md:order-1"
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
              className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-clinical bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-semibold text-clinical disabled:opacity-50 max-md:order-2"
              data-testid="run-transcript-qa-button"
            >
              <FileCheck2 size={17} aria-hidden="true" />
              Run QA
            </button>
            <button
              type="button"
              onClick={onAttest}
              disabled={busy || !canAttest || attested}
              className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] bg-clinical px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300 max-md:order-3"
              data-testid="attest-transcript-button"
            >
              {attested ? <CheckCircle2 size={17} aria-hidden="true" /> : <ShieldCheck size={17} aria-hidden="true" />}
              {attested ? "Transcript attested" : "Attest transcript"}
            </button>
            <button type="button" onClick={onExport} disabled={busy || lines.length === 0} className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50 max-md:order-6">
              <Download size={17} aria-hidden="true" />
              Export reviewed .cha
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
