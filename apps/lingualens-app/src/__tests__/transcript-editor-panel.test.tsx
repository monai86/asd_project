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

    expect(screen.getAllByText("Warning").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    expect(onAttest).toHaveBeenCalled();
  });

  it("keeps attestation retry available after a transient backend unavailable state", () => {
    const onAttest = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="pass"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        backendUnavailable
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={onAttest}
        onExport={vi.fn()}
      />
    );

    const attestButton = screen.getByRole("button", { name: "Attest transcript" });
    expect(attestButton).toBeEnabled();
    fireEvent.click(attestButton);
    expect(onAttest).toHaveBeenCalled();
  });

  it("renders filter chips, desktop review columns, and filters rows by review state", () => {
    render(
      <TranscriptEditorPanel
        lines={[
          { lineId: "line-1", speaker: "THER", text: "What do you see?", startMs: 0, endMs: 800 },
          { lineId: "line-2", speaker: "UNK", text: "maybe this line needs a speaker", startMs: 810, endMs: 1500 },
          { lineId: "line-3", speaker: "CHI", text: "[note] Verify timestamp with caregiver context.", startMs: 1510, endMs: 1900 },
          { lineId: "line-4", speaker: "CHI", text: "xxx", unclear: true }
        ]}
        qaStatus="warning"
        qaIssues={["Short transcript."]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: /All Lines/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Needs Review/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Low Confidence/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Missing Speaker/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Possible Error/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Notes/ })).toBeInTheDocument();

    expect(screen.getAllByText("Time").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Speaker").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Utterance").length).toBeGreaterThan(0);
    expect(screen.getAllByText("QA").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Confidence").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /Mark line/ }).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /Missing Speaker/ }));
    expect(screen.getByLabelText("Speaker for line 2")).toBeInTheDocument();
    expect(screen.queryByLabelText("Speaker for line 1")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Notes/ }));
    expect(screen.getByDisplayValue("[note] Verify timestamp with caregiver context.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Speaker for line 2")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /All Lines/ }));
    expect(screen.getByLabelText("Speaker for line 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Speaker for line 2")).toBeInTheDocument();
  });

  it("shows the sticky bottom review actions and keeps export disabled when there are no lines", () => {
    render(
      <TranscriptEditorPanel
        lines={[]}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="idle"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Speaker Tools" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Note" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export reviewed .cha" })).toBeDisabled();
  });

  it("explains why QA is blocked until transcript edits are saved", () => {
    const { rerender } = render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="unsaved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByText("Save transcript edits before running QA.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();

    rerender(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.queryByText("Save transcript edits before running QA.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeEnabled();
  });
});
