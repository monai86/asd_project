"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { ListFilter, Plus } from "lucide-react";

import {
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
import { TranscriptQaDetails, TranscriptReviewControls } from "@/components/transcript-review-controls";
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
  const [qaDetailsOpen, setQaDetailsOpen] = useState(false);
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
      className={`min-w-0 max-md:pb-44 lg:grid lg:gap-x-4 ${inspectorOpen ? "lg:grid-cols-[minmax(0,13fr)_minmax(17rem,7fr)]" : "lg:grid-cols-1"}`}
      data-testid="transcript-workbench"
    >
      <div className={inspectorOpen ? "flex items-center justify-between gap-3 lg:col-span-2" : "flex items-center justify-between gap-3"}>
        <div className="min-w-0">
          <h2 id="transcript-editor-title" className="text-lg font-bold text-ink">Transcript editor</h2>
          <p className="text-xs text-slate-600">{lines.length} {lines.length === 1 ? "line" : "lines"} · directly editable</p>
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2">
          <span
            className={`inline-flex min-h-8 items-center rounded-[var(--radius-card)] border px-2.5 text-xs font-semibold ${attested ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-900"}`}
            data-testid="transcript-attestation-badge"
            aria-label={attested ? "Transcript attested" : "Transcript review required"}
          >
            {attested ? "Attested" : "Review required"}
          </span>
          <button
            type="button"
            onClick={addLine}
            disabled={busy}
            aria-label="Add line"
            className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-[var(--radius-card)] border border-clinical bg-[color:var(--color-surface-reading)] px-2 py-2 text-sm font-semibold text-clinical disabled:opacity-50 sm:px-3"
          >
            <Plus size={16} aria-hidden="true" />
            <span className="hidden sm:inline">Add line</span>
          </button>
        </div>
      </div>

      <div className={`mt-4 hidden items-center justify-between gap-3 md:flex ${inspectorOpen ? "lg:col-span-2" : ""}`}>
        {inspectorOpen ? (
          <div className="inline-flex rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-1" aria-label="Inspector view">
            {(["audio", "qa"] as const).map((view) => (
              <button
                key={view}
                type="button"
                aria-pressed={inspectorView === view}
                onClick={() => {
                  setInspectorView(view);
                  setQaDetailsOpen(view === "qa");
                }}
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

      <div className={`mt-4 overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-text-strong)] p-3 text-white max-md:sticky max-md:top-0 max-md:z-20 lg:col-start-2 lg:row-start-3 lg:self-start lg:bg-slate-50 lg:p-4 lg:text-ink ${!inspectorOpen ? "hidden" : inspectorView === "qa" ? "md:hidden" : ""}`} data-testid="transcript-audio-inspector">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold">Session audio</h3>
            <p className="hidden text-xs text-slate-500 md:block">
              {audioUrl ? "Waveform review bar with timestamp-based line sync." : "Waveform preview only. Audio playback becomes interactive when a linked recording is available."}
            </p>
          </div>
          {audioUrl ? (
            <audio
              ref={audioRef}
              src={audioUrl}
              controls
              onTimeUpdate={handleTimeUpdate}
              className="w-full min-w-0 max-w-md outline-none"
              aria-label="Workspace audio playback"
            />
          ) : (
            <span className="rounded-full border border-white/25 px-3 py-1 text-xs font-semibold text-white lg:border-[color:var(--color-border)] lg:bg-[color:var(--color-surface-reading)] lg:text-slate-600">
              Audio not linked
            </span>
          )}
        </div>
        <div className="mt-4 hidden h-20 grid-cols-24 items-end gap-1 rounded-[var(--radius-card)] border border-slate-100 bg-[color:var(--color-surface-reading)] px-3 py-3 md:grid">
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

      <div className="min-w-0 lg:col-start-1 lg:row-start-3">
        <div className="mt-4 flex min-w-0 items-center gap-2 self-start">
          <ListFilter size={17} aria-hidden="true" className="shrink-0 text-[color:var(--color-text-muted)]" />
          <label className="sr-only" htmlFor="transcript-line-filter">Transcript line filter</label>
          <select
            id="transcript-line-filter"
            aria-label="Transcript line filter"
            value={selectedFilter}
            onChange={(event) => setSelectedFilter(event.target.value as TranscriptFilter)}
            className="min-h-11 min-w-0 max-w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 text-sm font-semibold text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
          >
            {transcriptFilters.map((filter) => {
              const count = lines.filter((line) => lineMatchesFilter(line, filter.id, qaStatus)).length;
              return <option key={filter.id} value={filter.id}>{filter.label} ({count})</option>;
            })}
          </select>
          <span className="text-xs text-[color:var(--color-text-subtle)]" aria-live="polite">{visibleLines.length} shown</span>
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
      </div>

      <TranscriptQaDetails
        qaStatus={qaStatus}
        qaIssues={qaIssues}
        qaBlockedReason={qaBlockedReason}
        inspectorOpen={inspectorOpen}
        inspectorView={inspectorView}
        open={qaDetailsOpen}
        onToggle={setQaDetailsOpen}
      />

      <TranscriptReviewControls
        busy={busy}
        linesCount={lines.length}
        selectedLineIndex={selectedLineIndex}
        saveStatus={saveStatus}
        qaBlockedReason={qaBlockedReason}
        canAttest={canAttest}
        attested={attested}
        inspectorOpen={inspectorOpen}
        onSpeakerTools={() => setSelectedFilter("missing_speaker")}
        onAddNote={addNoteLine}
        onSaveDraft={onSaveDraft}
        onRunQa={onRunQa}
        onAttest={onAttest}
        onExport={onExport}
      />
    </section>
  );
}
