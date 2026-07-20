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
    <div className="mt-4 min-w-0 overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] xl:col-start-1 xl:row-start-4">
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
          const rowStatus = getRowStatus(line, qaStatus);
          const confidence = getLineConfidence(line);
          const hasTiming = line.startMs !== undefined && line.endMs !== undefined;
          const isLineActive = line.lineId === activeLineId;
          const isLineSelected = line.lineId === selectedLineId;
          return (
            <TranscriptRowBoundary
              key={line.lineId}
              line={line}
              index={index}
              totalLines={lines.length}
              qaStatus={qaStatus}
              active={isLineActive}
              selected={isLineSelected}
              menuOpen={openMenuLineId === line.lineId}
              audioLinked={Boolean(audioUrl)}
            >
              <article
                ref={(node) => registerLineRow(line.lineId, node)}
                role="option"
                aria-label={`Transcript line ${index + 1}`}
                aria-selected={isLineSelected}
                className={`px-4 py-4 transition motion-reduce:transition-none ${isLineActive || isLineSelected ? "bg-[color:var(--color-accent-soft)]" : "bg-transparent"}`}
                onClick={() => selectLine(line.lineId)}
              >
                <div className="grid min-w-0 gap-4 min-[1380px]:grid-cols-[7rem_6rem_minmax(16rem,1fr)_5.5rem_5.5rem] min-[1380px]:items-start">
                  <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
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
                      className="min-h-20 w-full min-w-0 resize-y rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-3 py-2 text-sm font-normal normal-case leading-6 tracking-normal text-ink outline-none focus:ring-2 focus:ring-clinical"
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
                  <div className="flex flex-wrap gap-2 min-[1380px]:col-span-3 min-[1380px]:col-start-3 min-[1380px]:justify-start">
                    {hasTiming && audioUrl ? (
                      <button
                        type="button"
                        aria-label={`Play line ${index + 1}`}
                        onClick={() => playLine(line)}
                        className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-line bg-[color:var(--color-surface-reading)] px-2.5 py-2 text-xs font-semibold text-slate-700 hover:border-clinical hover:bg-clinical/5 hover:text-clinical"
                      >
                        <Play size={13} fill="currentColor" aria-hidden="true" />
                        Play Turn
                      </button>
                    ) : null}
                    <div className="relative">
                      <button
                        ref={(node) => registerMenuButton(line.lineId, node)}
                        type="button"
                        aria-label={`More actions for line ${index + 1}`}
                        aria-haspopup="menu"
                        aria-expanded={openMenuLineId === line.lineId}
                        onClick={(event) => {
                          event.stopPropagation();
                          toggleLineMenu(line.lineId);
                        }}
                        className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-line bg-[color:var(--color-surface-reading)] text-slate-700"
                      >
                        <MoreHorizontal size={18} aria-hidden="true" />
                      </button>
                      {openMenuLineId === line.lineId ? (
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
                          <LineMenuItem label="Split line" onClick={() => { splitLine(index); closeLineMenu(line.lineId); }} disabled={!line.text.trim()} autoFocus>
                            <GitPullRequest size={15} aria-hidden="true" />
                          </LineMenuItem>
                          <LineMenuItem label="Merge with previous" onClick={() => { mergeLine(index, "previous"); closeLineMenu(line.lineId); }} disabled={index === 0}>
                            <GitMerge size={15} aria-hidden="true" />
                          </LineMenuItem>
                          <LineMenuItem label="Merge with next" onClick={() => { mergeLine(index, "next"); closeLineMenu(line.lineId); }} disabled={index === lines.length - 1}>
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
        })}
      </div>
    </div>
  );
}

const speakers = ["CHI", "THER", "PAR", "INV", "MOT", "FAT", "UNK"];
