import { memo, type ReactNode } from "react";

import type { PersistenceStatus, TranscriptLine, TranscriptQaStatus } from "@/lib/workflow";

export type TranscriptRowBoundaryProps = {
  line: TranscriptLine;
  index: number;
  totalLines: number;
  qaStatus: TranscriptQaStatus;
  active: boolean;
  selected: boolean;
  menuOpen: boolean;
  audioLinked: boolean;
  children: ReactNode;
};

export const TranscriptRowBoundary = memo(function TranscriptRowBoundary({ children }: TranscriptRowBoundaryProps) {
  return children;
}, (previous, next) => (
  previous.line === next.line
  && previous.index === next.index
  && previous.totalLines === next.totalLines
  && previous.qaStatus === next.qaStatus
  && previous.active === next.active
  && previous.selected === next.selected
  && previous.menuOpen === next.menuOpen
  && previous.audioLinked === next.audioLinked
));

export type TranscriptFilter = "all" | "needs_review" | "low_confidence" | "missing_speaker" | "possible_error" | "notes";

export const transcriptFilters: Array<{ id: TranscriptFilter; label: string }> = [
  { id: "all", label: "All Lines" },
  { id: "needs_review", label: "Needs Review" },
  { id: "low_confidence", label: "Low Confidence" },
  { id: "missing_speaker", label: "Missing Speaker" },
  { id: "possible_error", label: "Possible Error" },
  { id: "notes", label: "Notes" }
];

export function LineMenuItem({
  label,
  children,
  onClick,
  disabled = false,
  autoFocus = false,
  tone = "default"
}: {
  label: string;
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  autoFocus?: boolean;
  tone?: "default" | "danger";
}) {
  return (
    <button
      type="button"
      role="menuitem"
      autoFocus={autoFocus}
      disabled={disabled}
      onClick={onClick}
      className={`flex min-h-11 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold disabled:opacity-40 ${
        tone === "danger" ? "text-red-700 hover:bg-red-50" : "text-slate-700 hover:bg-[color:var(--color-surface-muted)]"
      }`}
    >
      {children}
      {label}
    </button>
  );
}

export function QaBadge({ status }: { status: TranscriptQaStatus }) {
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

export function getQaBlockedReason(lines: TranscriptLine[], saveStatus: PersistenceStatus) {
  if (lines.length === 0) return "Add at least one transcript line before running QA.";
  if (saveStatus === "saving") return "Wait for the transcript draft to finish saving before running QA.";
  if (saveStatus === "failed") return "Save the transcript draft again before running QA.";
  if (saveStatus === "unsaved") return "Save transcript edits before running QA.";
  if (saveStatus !== "saved") return "Save the transcript draft before running QA.";
  return "";
}

export function lineMatchesFilter(line: TranscriptLine, filter: TranscriptFilter, qaStatus: TranscriptQaStatus) {
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

export function getLineConfidence(line: TranscriptLine) {
  if (line.unclear || line.speaker === "UNK") {
    return { label: "Low", className: "bg-red-100 text-red-700" };
  }
  if (lineHasPossibleError(line) || line.startMs === undefined || line.endMs === undefined) {
    return { label: "Review", className: "bg-orange-100 text-orange-700" };
  }
  return { label: "High", className: "bg-emerald-100 text-emerald-700" };
}

export function buildWaveformHeights(lines: TranscriptLine[]) {
  const base = Array.from({ length: 24 }, (_, index) => {
    const line = lines[index % Math.max(lines.length, 1)];
    const textSize = line?.text?.trim().length ?? 6;
    const derived = 18 + ((textSize + index * 7) % 52);
    return Math.max(14, Math.min(78, derived));
  });
  return base;
}

export function parseTimestampRange(value: string): Pick<TranscriptLine, "startMs" | "endMs"> | null {
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

export function getRowStatus(line: TranscriptLine, qaStatus: TranscriptQaStatus) {
  if (line.unclear || !line.text.trim() || line.speaker === "UNK") {
    return { label: line.unclear ? "Unclear" : "Review", className: "bg-orange-100 text-orange-700" };
  }
  if (qaStatus === "not_run") {
    return { label: "Not checked", className: "bg-slate-100 text-slate-600" };
  }
  return { label: "Checked", className: "bg-emerald-100 text-emerald-700" };
}

export function findSplitPoint(text: string) {
  const midpoint = Math.max(1, Math.floor(text.length / 2));
  const nextSpace = text.indexOf(" ", midpoint);
  const previousSpace = text.lastIndexOf(" ", midpoint);
  if (nextSpace === -1 && previousSpace === -1) return midpoint;
  if (nextSpace === -1) return previousSpace;
  if (previousSpace === -1) return nextSpace;
  return midpoint - previousSpace <= nextSpace - midpoint ? previousSpace : nextSpace;
}

export function midpointTimestamp(line: TranscriptLine) {
  if (line.startMs === undefined || line.endMs === undefined) return undefined;
  return Math.round((line.startMs + line.endMs) / 2);
}

export function formatTimestampRange(line: TranscriptLine) {
  if (line.startMs === undefined || line.endMs === undefined) return "—";
  return `${formatTimestamp(line.startMs)} – ${formatTimestamp(line.endMs)}`;
}

function formatTimestamp(milliseconds: number) {
  const minutes = Math.floor(milliseconds / 60_000);
  const seconds = Math.floor((milliseconds % 60_000) / 1000);
  const remainder = milliseconds % 1000;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(remainder).padStart(3, "0")}`;
}

export function createLineId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `line-${crypto.randomUUID()}`;
  }
  return `line-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}
