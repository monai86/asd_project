import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TranscriptEditorPanel } from "@/components/transcript-editor-panel";
import type { TranscriptLine } from "@/lib/workflow";

const lines: TranscriptLine[] = [
  { lineId: "line-1", speaker: "THER", text: "What do you see?", startMs: 100, endMs: 900 },
  { lineId: "line-2", speaker: "CHI", text: "A blue car.", startMs: 950, endMs: 1600 }
];

describe("TranscriptEditorPanel", () => {
  it("renders line fields and supports editing, adding, deleting, and unclear status", () => {
    const onChange = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={onChange}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByLabelText("Timestamp for line 1")).toHaveValue("00:00.100 – 00:00.900");
    expect(screen.getByLabelText("Speaker for line 1")).toHaveValue("THER");
    expect(screen.getByLabelText("Utterance text 1")).toHaveValue("What do you see?");
    expect(screen.getAllByText("Not checked").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Timestamp for line 1"), { target: { value: "00:00.200 – 00:01.100" } });
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ lineId: "line-1", startMs: 200, endMs: 1100 }),
      lines[1]
    ]);

    fireEvent.change(screen.getByLabelText("Utterance text 1"), { target: { value: "What can you see?" } });
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ lineId: "line-1", text: "What can you see?" }),
      lines[1]
    ]);

    fireEvent.change(screen.getByLabelText("Speaker for line 2"), { target: { value: "PAR" } });
    expect(onChange).toHaveBeenLastCalledWith([
      lines[0],
      expect.objectContaining({ lineId: "line-2", speaker: "PAR" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Mark line 2 unclear" }));
    expect(onChange).toHaveBeenLastCalledWith([
      lines[0],
      expect.objectContaining({ lineId: "line-2", unclear: true })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Add line" }));
    expect(onChange).toHaveBeenLastCalledWith([
      ...lines,
      expect.objectContaining({ speaker: "UNK", text: "" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Delete line 2" }));
    expect(onChange).toHaveBeenLastCalledWith([lines[0]]);
  });

  it("supports split and adjacent merge actions", () => {
    const onChange = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={[
          { lineId: "line-1", speaker: "CHI", text: "blue car goes fast" },
          { lineId: "line-2", speaker: "CHI", text: "down the road" }
        ]}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={onChange}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Split line 1" }));
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ speaker: "CHI" }),
      expect.objectContaining({ speaker: "CHI" }),
      expect.objectContaining({ lineId: "line-2" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Merge line 1 with next" }));
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ text: "blue car goes fast down the road" })
    ]);
  });

  it("exposes draft, QA, attestation, and export actions with report gate context", () => {
    const onSaveDraft = vi.fn();
    const onRunQa = vi.fn();
    const onAttest = vi.fn();
    const onExport = vi.fn();
    const { rerender } = render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={onSaveDraft}
        onRunQa={onRunQa}
        onAttest={onAttest}
        onExport={onExport}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    fireEvent.click(screen.getByRole("button", { name: "Export reviewed .cha" }));
    expect(onSaveDraft).toHaveBeenCalled();
    expect(onRunQa).toHaveBeenCalled();
    expect(onExport).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeDisabled();

    rerender(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="warning"
        qaIssues={["Child sample has fewer than 3 utterances."]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={onSaveDraft}
        onRunQa={onRunQa}
        onAttest={onAttest}
        onExport={onExport}
      />
    );

    expect(screen.getByText("Warning")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    expect(onAttest).toHaveBeenCalled();
  });
});
