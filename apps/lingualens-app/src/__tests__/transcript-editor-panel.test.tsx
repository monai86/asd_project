import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
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

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 2" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Mark unclear" }));
    expect(onChange).toHaveBeenLastCalledWith([
      lines[0],
      expect.objectContaining({ lineId: "line-2", unclear: true })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Add line" }));
    expect(onChange).toHaveBeenLastCalledWith([
      ...lines,
      expect.objectContaining({ speaker: "UNK", text: "" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 2" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete line" }));
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

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 1" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Split line" }));
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ speaker: "CHI" }),
      expect.objectContaining({ speaker: "CHI" }),
      expect.objectContaining({ lineId: "line-2" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 1" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Merge with next" }));
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
    fireEvent.click(screen.getByText("More review actions"));
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

  it("explains why attestation is blocked until QA has run, via an inline reason linked with aria-describedby", () => {
    const { rerender } = render(
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

    fireEvent.click(screen.getByText("More review actions"));
    const attestButton = screen.getByRole("button", { name: "Attest transcript" });
    expect(attestButton).toBeDisabled();
    expect(attestButton).toHaveAttribute("aria-describedby", "transcript-attest-reason");
    expect(screen.getByText("Run transcript QA before attesting.")).toBeInTheDocument();

    rerender(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="pass"
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

    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeEnabled();
    expect(screen.queryByText("Run transcript QA before attesting.")).not.toBeInTheDocument();
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

  it("uses one compact filter control, keeps desktop review columns, and filters rows by review state", () => {
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

    const filter = screen.getByRole("combobox", { name: "Transcript line filter" });
    expect(filter).toHaveValue("all");
    expect(within(filter).getByRole("option", { name: "All Lines (4)" })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: "Needs Review (4)" })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: "Low Confidence (2)" })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: "Missing Speaker (1)" })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: "Possible Error (1)" })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: "Notes (1)" })).toBeInTheDocument();

    expect(screen.getAllByText("Time").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Speaker").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Utterance").length).toBeGreaterThan(0);
    expect(screen.getAllByText("QA").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Confidence").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /Mark line/ })).not.toBeInTheDocument();

    fireEvent.change(filter, { target: { value: "missing_speaker" } });
    expect(screen.getByLabelText("Speaker for line 2")).toBeInTheDocument();
    expect(screen.queryByLabelText("Speaker for line 1")).not.toBeInTheDocument();

    fireEvent.change(filter, { target: { value: "notes" } });
    expect(screen.getByDisplayValue("[note] Verify timestamp with caregiver context.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Speaker for line 2")).not.toBeInTheDocument();

    fireEvent.change(filter, { target: { value: "all" } });
    expect(screen.getByLabelText("Speaker for line 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Speaker for line 2")).toBeInTheDocument();
  });

  it("reuses filter counts across filter-only updates and refreshes them when their inputs change", () => {
    let speakerReads = 0;
    const instrumentedLines = Array.from({ length: 20 }, (_, index) => {
      const line: TranscriptLine = {
        lineId: `instrumented-line-${index}`,
        speaker: "THER",
        text: `Non-identifying transcript line ${index}`,
        startMs: index * 1_000,
        endMs: index * 1_000 + 800,
        unclear: false,
      };
      Object.defineProperty(line, "speaker", {
        enumerable: true,
        get() {
          speakerReads += 1;
          return index % 2 === 0 ? "CHI" : "THER";
        },
      });
      return line;
    });
    const commonProps = {
      qaIssues: [],
      attested: false,
      busy: false,
      saveStatus: "saved" as const,
      onChange: vi.fn(),
      onSaveDraft: vi.fn(),
      onRunQa: vi.fn(),
      onAttest: vi.fn(),
      onExport: vi.fn(),
    };
    const { rerender } = render(
      <TranscriptEditorPanel lines={instrumentedLines} qaStatus="not_run" {...commonProps} />
    );

    const filter = screen.getByRole("combobox", { name: "Transcript line filter" });
    speakerReads = 0;
    fireEvent.change(filter, { target: { value: "missing_speaker" } });

    // The selected predicate classifies each line once. Filter-option counts
    // are independent of selectedFilter and must stay cached.
    expect(speakerReads).toBe(instrumentedLines.length);

    rerender(<TranscriptEditorPanel lines={instrumentedLines} qaStatus="warning" {...commonProps} />);
    expect(within(filter).getByRole("option", { name: `Needs Review (${instrumentedLines.length})` })).toBeInTheDocument();

    const nextLines = [
      ...instrumentedLines,
      { lineId: "instrumented-line-new", speaker: "UNK", text: "Review speaker", unclear: false },
    ];
    rerender(<TranscriptEditorPanel lines={nextLines} qaStatus="warning" {...commonProps} />);
    expect(within(filter).getByRole("option", { name: `All Lines (${nextLines.length})` })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: "Missing Speaker (1)" })).toBeInTheDocument();
  });

  it("classifies each line once when a controlled keystroke refreshes filter counts", () => {
    let speakerReads = 0;
    const instrumentedLines = Array.from({ length: 20 }, (_, index) => {
      const line: TranscriptLine = {
        lineId: `keystroke-line-${index}`,
        speaker: "THER",
        text: `Non-identifying transcript line ${index}`,
        startMs: index * 1_000,
        endMs: index * 1_000 + 800,
        unclear: false,
      };
      Object.defineProperty(line, "speaker", {
        enumerable: true,
        get() {
          speakerReads += 1;
          return index % 2 === 0 ? "CHI" : "THER";
        },
      });
      return line;
    });

    function ControlledEditor() {
      const [controlledLines, setControlledLines] = useState(instrumentedLines);
      return (
        <TranscriptEditorPanel
          lines={controlledLines}
          qaStatus="not_run"
          qaIssues={[]}
          attested={false}
          busy={false}
          saveStatus="saved"
          onChange={setControlledLines}
          onSaveDraft={vi.fn()}
          onRunQa={vi.fn()}
          onAttest={vi.fn()}
          onExport={vi.fn()}
        />
      );
    }

    render(<ControlledEditor />);
    speakerReads = 0;
    fireEvent.change(screen.getByLabelText("Utterance text 1"), {
      target: { value: "Updated non-identifying transcript line" },
    });

    // One getter read clones the edited line; the count derivation then reads
    // each unchanged line once. The selected All filter needs no extra scan.
    expect(speakerReads).toBe(instrumentedLines.length);
    expect(screen.getByRole("combobox", { name: "Transcript line filter" })).toHaveValue("all");
    expect(screen.getByLabelText("Utterance text 1")).toHaveValue("Updated non-identifying transcript line");
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

    fireEvent.click(screen.getByText("More review actions"));
    expect(screen.getByRole("button", { name: "Speaker Tools" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Note" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeDisabled();
    const exportButton = screen.getByRole("button", { name: "Export reviewed .cha" });
    expect(exportButton).toBeDisabled();
    expect(exportButton).toHaveAttribute("aria-describedby", "transcript-export-reason");
    expect(screen.getByText("Add transcript lines before exporting.")).toBeInTheDocument();
  });

  it("keeps the mobile primary bar focused on save and QA while secondary review actions are collapsed", () => {
    render(
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

    const primaryBar = screen.getByTestId("mobile-transcript-primary-actions");
    expect(within(primaryBar).getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(within(primaryBar).getByRole("button", { name: "Run QA" })).toBeInTheDocument();
    expect(within(primaryBar).queryByRole("button", { name: "Attest transcript" })).not.toBeInTheDocument();
    expect(within(primaryBar).queryByRole("button", { name: "Export reviewed .cha" })).not.toBeInTheDocument();

    const qaDetails = screen.getByTestId("mobile-transcript-qa-details");
    const secondaryActions = screen.getByTestId("mobile-transcript-secondary-actions");
    expect(qaDetails).not.toHaveAttribute("open");
    expect(secondaryActions).not.toHaveAttribute("open");
    fireEvent.click(within(secondaryActions).getByText("More review actions"));
    expect(within(secondaryActions).getByRole("button", { name: "Attest transcript" })).toBeInTheDocument();
    expect(within(secondaryActions).getByRole("button", { name: "Export reviewed .cha" })).toBeInTheDocument();
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

  it("marks the directly editable selected line and moves secondary actions into an overflow menu", async () => {
    render(
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

    const firstLine = screen.getByRole("option", { name: "Transcript line 1" });
    fireEvent.focus(screen.getByLabelText("Utterance text 1"));
    expect(firstLine).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("button", { name: "Split line 1" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 1" }));
    expect(screen.getByRole("menuitem", { name: "Split line" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Merge with next" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Mark unclear" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Delete line" })).toBeVisible();
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
    await waitFor(() => expect(screen.getByRole("button", { name: "More actions for line 1" })).toHaveFocus());
  });

  it("scrolls a newly selected line into view without moving focus from its editor", async () => {
    const scrollIntoView = vi.fn();
    const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView
    });

    try {
      render(
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

      const secondLineEditor = screen.getByLabelText("Utterance text 2");
      act(() => secondLineEditor.focus());

      await waitFor(() => {
        expect(scrollIntoView).toHaveBeenCalledWith({ block: "nearest", inline: "nearest" });
      });
      expect(secondLineEditor).toHaveFocus();
      expect(screen.getByRole("option", { name: "Transcript line 2" })).toHaveAttribute("aria-selected", "true");
    } finally {
      Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
        configurable: true,
        value: originalScrollIntoView
      });
    }
  });

  it("does not intercept browser-default keyboard shortcuts", () => {
    const onSaveDraft = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="unsaved"
        onChange={vi.fn()}
        onSaveDraft={onSaveDraft}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    fireEvent.keyDown(window, { key: "s", metaKey: true });
    fireEvent.keyDown(window, { key: "l", metaKey: true });

    expect(onSaveDraft).not.toHaveBeenCalled();
  });

  it("lets tablet and desktop users switch or collapse the Audio and QA inspector", () => {
    render(
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

    fireEvent.click(screen.getByRole("button", { name: "QA" }));
    expect(screen.getByRole("button", { name: "QA" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Hide inspector" }));
    expect(screen.getByTestId("transcript-audio-inspector")).toHaveClass("hidden");
    fireEvent.click(screen.getByRole("button", { name: "Show Audio and QA" }));
    expect(screen.getByRole("button", { name: "Hide inspector" })).toBeInTheDocument();
  });

  it("announces save state changes through a polite live region", () => {
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy
        saveStatus="saving"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByRole("status", { name: "Transcript save status" })).toHaveTextContent("Saving transcript");
  });
});
