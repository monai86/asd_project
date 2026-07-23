import { memo } from "react";
import { AlertTriangle, GitMerge, GitPullRequest, MoreHorizontal, Play, Trash2 } from "lucide-react";

import {
  LineMenuItem,
  TranscriptRowBoundary,
  formatTimestampRange,
  getLineConfidence,
  getRowStatus,
  parseTimestampRange,
} from "@/components/transcript-editor-support";
import type { TranscriptLine, TranscriptQaStatus } from "@/lib/workflow";

type TranscriptLineListProps = {
  lines: TranscriptLine[];
  visibleLines: TranscriptLine[];
  lineIndexById: Map<string, number>;
  qaStatus: TranscriptQaStatus;
  activeLineId: string | null;
  selectedLineId: string | null;
  openMenuLineId: string | null;
  audioUrl?: string;
  updateLine: (index: number, patch: Partial<TranscriptLine>) => void;
  selectLine: (lineId: string) => void;
  playLine: (line: TranscriptLine) => void;
  registerLineRow: (lineId: string, node: HTMLElement | null) => void;
  registerMenuButton: (lineId: string, node: HTMLButtonElement | null) => void;
  toggleLineMenu: (lineId: string) => void;
  closeLineMenu: (lineId: string, restoreFocus?: boolean) => void;
  splitLine: (index: number) => void;
  mergeLine: (index: number, direction: "previous" | "next") => void;
  deleteLine: (index: number) => void;
};

export function TranscriptLineList({
  lines,
  visibleLines,
  lineIndexById,
  qaStatus,
  activeLineId,
  selectedLineId,
  openMenuLineId,
  audioUrl,
  updateLine,
  selectLine,
  playLine,
  registerLineRow,
  registerMenuButton,
  toggleLineMenu,
  closeLineMenu,
  splitLine,
  mergeLine,
  deleteLine,
}: TranscriptLineListProps) {
  return (
    <div className="mt-4 min-w-0 overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] lg:col-start-1 lg:row-start-4">
      <div className="hidden grid-cols-[7rem_6rem_minmax(16rem,1fr)_5.5rem_5.5rem] gap-3 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--color-text-muted)] min-[1380px]:grid">
        <span>Time</span>
        <span>Speaker</span>
        <span>Utterance</span>
        <span>QA</span>
        <span>Confidence</span>
      </div>
      <div className="divide-y divide-[color:var(--color-border)]" role="listbox" aria-label="Transcript lines">
        {visibleLines.map((line) => {
          const index = lineIndexById.get(line.lineId) ?? -1;
          return (
            <TranscriptLineRow
              key={line.lineId}
              line={line}
              index={index}
              totalLines={lines.length}
              qaStatus={qaStatus}
              active={line.lineId === activeLineId}
              selected={line.lineId === selectedLineId}
              menuOpen={openMenuLineId === line.lineId}
              audioLinked={Boolean(audioUrl)}
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
          );
        })}
      </div>
    </div>
  );
}

type TranscriptLineRowProps = {
  line: TranscriptLine;
  index: number;
  totalLines: number;
  qaStatus: TranscriptQaStatus;
  active: boolean;
  selected: boolean;
  menuOpen: boolean;
  audioLinked: boolean;
  updateLine: (index: number, patch: Partial<TranscriptLine>) => void;
  selectLine: (lineId: string) => void;
  playLine: (line: TranscriptLine) => void;
  registerLineRow: (lineId: string, node: HTMLElement | null) => void;
  registerMenuButton: (lineId: string, node: HTMLButtonElement | null) => void;
  toggleLineMenu: (lineId: string) => void;
  closeLineMenu: (lineId: string, restoreFocus?: boolean) => void;
  splitLine: (index: number) => void;
  mergeLine: (index: number, direction: "previous" | "next") => void;
  deleteLine: (index: number) => void;
};

const TranscriptLineRow = memo(function TranscriptLineRow({
  line,
  index,
  totalLines,
  qaStatus,
  active,
  selected,
  menuOpen,
  audioLinked,
  updateLine,
  selectLine,
  playLine,
  registerLineRow,
  registerMenuButton,
  toggleLineMenu,
  closeLineMenu,
  splitLine,
  mergeLine,
  deleteLine,
}: TranscriptLineRowProps) {
  const rowStatus = getRowStatus(line, qaStatus);
  const confidence = getLineConfidence(line);
  const hasTiming = line.startMs !== undefined && line.endMs !== undefined;

  return (
    <TranscriptRowBoundary
      line={line}
      index={index}
      totalLines={totalLines}
      qaStatus={qaStatus}
      active={active}
      selected={selected}
      menuOpen={menuOpen}
      audioLinked={audioLinked}
    >
      <article
        ref={(node) => registerLineRow(line.lineId, node)}
        role="option"
        aria-label={`Transcript line ${index + 1}`}
        aria-selected={selected}
        className={`transcript-line-row px-3 py-3 transition motion-reduce:transition-none sm:px-4 ${active || selected ? "bg-[color:var(--color-accent-soft)]" : "bg-transparent"}`}
        onClick={() => selectLine(line.lineId)}
      >
        <div className="grid min-w-0 grid-cols-2 gap-2 md:grid-cols-[7rem_6rem_minmax(0,1fr)] min-[1380px]:grid-cols-[7rem_6rem_minmax(16rem,1fr)_5.5rem_5.5rem] min-[1380px]:items-start">
          <label className="col-span-2 grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500 md:col-span-1">
            <span className="min-[1380px]:sr-only">Time</span>
            <input
              value={formatTimestampRange(line)}
              onChange={(event) => {
                const timing = parseTimestampRange(event.target.value);
                if (timing) updateLine(index, timing);
              }}
              onFocus={() => selectLine(line.lineId)}
              aria-label={`Timestamp for line ${index + 1}`}
              placeholder="00:00.000 – 00:01.000"
              className="min-h-11 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm font-normal normal-case tracking-normal text-slate-700"
            />
          </label>
          <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span className="min-[1380px]:sr-only">Speaker</span>
            <select
              value={line.speaker}
              onChange={(event) => updateLine(index, { speaker: event.target.value })}
              onFocus={() => selectLine(line.lineId)}
              aria-label={`Speaker for line ${index + 1}`}
              className="min-h-11 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-3 text-sm font-semibold normal-case tracking-normal text-ink"
            >
              {[...new Set([...speakers, line.speaker])].map((speaker) => (
                <option key={speaker} value={speaker}>{speaker}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span className="min-[1380px]:sr-only">Utterance</span>
            <textarea
              value={line.text}
              onChange={(event) => updateLine(index, { text: event.target.value })}
              onFocus={() => selectLine(line.lineId)}
              aria-label={`Utterance text ${index + 1}`}
              className="min-h-14 w-full min-w-0 resize-y rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-3 py-2 text-sm font-normal normal-case leading-6 tracking-normal text-ink outline-none focus:ring-2 focus:ring-clinical"
            />
          </label>
          <div className="flex items-start min-[1380px]:justify-center">
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${rowStatus.className}`}>
              {rowStatus.label}
            </span>
          </div>
          <div className="flex items-start min-[1380px]:justify-center">
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${confidence.className}`}>
              {confidence.label}
            </span>
          </div>
          <div className="col-span-2 flex flex-wrap gap-2 md:col-span-1 min-[1380px]:col-span-3 min-[1380px]:col-start-3 min-[1380px]:justify-start">
            <div className="relative">
              <button
                ref={(node) => registerMenuButton(line.lineId, node)}
                type="button"
                aria-label={`More actions for line ${index + 1}`}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={(event) => {
                  event.stopPropagation();
                  toggleLineMenu(line.lineId);
                }}
                className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-line bg-[color:var(--color-surface-reading)] text-slate-700"
              >
                <MoreHorizontal size={18} aria-hidden="true" />
              </button>
              {menuOpen ? (
                <div
                  role="menu"
                  aria-label={`Actions for transcript line ${index + 1}`}
                  className="motion-popover absolute right-0 z-20 mt-1 w-52 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-1 shadow-lg"
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") {
                      event.preventDefault();
                      closeLineMenu(line.lineId);
                    }
                  }}
                >
                  {hasTiming && audioLinked ? (
                    <LineMenuItem label="Play line" onClick={() => { playLine(line); closeLineMenu(line.lineId); }} autoFocus>
                      <Play size={15} fill="currentColor" aria-hidden="true" />
                    </LineMenuItem>
                  ) : null}
                  <LineMenuItem label="Split line" onClick={() => { splitLine(index); closeLineMenu(line.lineId); }} disabled={!line.text.trim()} autoFocus={!hasTiming || !audioLinked}>
                    <GitPullRequest size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label="Merge with previous" onClick={() => { mergeLine(index, "previous"); closeLineMenu(line.lineId); }} disabled={index === 0}>
                    <GitMerge size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label="Merge with next" onClick={() => { mergeLine(index, "next"); closeLineMenu(line.lineId); }} disabled={index === totalLines - 1}>
                    <GitMerge size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label={line.unclear ? "Mark clear" : "Mark unclear"} onClick={() => { updateLine(index, { unclear: !line.unclear }); closeLineMenu(line.lineId); }}>
                    <AlertTriangle size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label="Delete line" onClick={() => { deleteLine(index); closeLineMenu(line.lineId, false); }} tone="danger">
                    <Trash2 size={15} aria-hidden="true" />
                  </LineMenuItem>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </article>
    </TranscriptRowBoundary>
  );
});

const speakers = ["CHI", "THER", "PAR", "INV", "MOT", "FAT", "UNK"];
