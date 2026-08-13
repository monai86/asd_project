import type { TranscriptLine } from "../../src/lib/workflow";

export function makeTranscriptLines(count: number): TranscriptLine[] {
  return Array.from({ length: count }, (_, index) => ({
    lineId: `benchmark-line-${index}`,
    speaker: index % 2 === 0 ? "CHI" : "THER",
    text: `Non-identifying benchmark utterance ${index}`,
    startMs: index * 1200,
    endMs: index * 1200 + 900,
    unclear: false,
  }));
}

export function makeTranscriptText(count: number): string {
  return makeTranscriptLines(count)
    .map((line) => `${line.speaker}: ${line.text}`)
    .join("\n");
}
