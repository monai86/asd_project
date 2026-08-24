import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  isSpeakerMappingComplete,
  SpeakerMappingPanel,
} from "@/features/sessions/transcript/speaker-mapping-panel";
import type { SpeakerMapping, TranscriptLine } from "@/lib/workflow";

const lines: TranscriptLine[] = [
  { lineId: "utt-0", speaker: "UNK", text: "Synthetic zero", startMs: 0, endMs: 1250, temporarySpeakerId: "speaker-0" },
  { lineId: "utt-1", speaker: "UNK", text: "Synthetic one", startMs: 1300, endMs: 2200, temporarySpeakerId: "speaker-1" },
];

function mappingDraft(overrides: Partial<SpeakerMapping> = {}): SpeakerMapping {
  return {
    mapping_id: "spmap-synthetic",
    organization_id: "org-synthetic",
    transcript_id: "tr-synthetic",
    source_transcript_version: 1,
    applied_transcript_version: null,
    mapping_version: 1,
    status: "draft",
    required: true,
    persisted: false,
    effective_status: "draft",
    issue_code: null,
    issue_message: null,
    confirmed_by_user_id: null,
    confirmed_by_role: null,
    confirmed_at: null,
    created_at: "2026-08-24T00:00:00Z",
    updated_at: "2026-08-24T00:00:00Z",
    entries: [
      {
        temporary_speaker_id: "speaker-0",
        source_speaker_label: "Provider speaker zero",
        provider_metadata: { provider_id: "synthetic" },
        affected_utterance_ids: ["utt-0"],
        reviewed_utterance_ids: [],
        confirmed_chat_code: null,
        participant_role: null,
      },
      {
        temporary_speaker_id: "speaker-1",
        source_speaker_label: null,
        provider_metadata: { provider_id: "synthetic" },
        affected_utterance_ids: ["utt-1"],
        reviewed_utterance_ids: [],
        confirmed_chat_code: null,
        participant_role: null,
      },
    ],
    ...overrides,
  };
}

function completeMapping(overrides: Partial<SpeakerMapping> = {}): SpeakerMapping {
  const draft = mappingDraft();
  return {
    ...draft,
    entries: draft.entries.map((entry, index) => ({
      ...entry,
      confirmed_chat_code: index === 0 ? "CHI" : "THER",
      participant_role: index === 0 ? "target_child" : "therapist",
      reviewed_utterance_ids: [...entry.affected_utterance_ids],
    })),
    ...overrides,
  };
}

function renderPanel(mapping = mappingDraft(), options: { dirty?: boolean; busy?: boolean } = {}) {
  const onChange = vi.fn();
  const onSave = vi.fn();
  const onConfirm = vi.fn();
  const onStartNewReview = vi.fn();
  const rendered = render(
    <SpeakerMappingPanel
      mapping={mapping}
      lines={lines}
      dirty={options.dirty ?? true}
      busy={options.busy ?? false}
      onChange={onChange}
      onSave={onSave}
      onConfirm={onConfirm}
      onStartNewReview={onStartNewReview}
    />,
  );
  return { onChange, onSave, onConfirm, onStartNewReview, ...rendered };
}

describe("SpeakerMappingPanel", () => {
  it("requires explicit code, role, and every affected utterance review before saving", () => {
    const { onChange } = renderPanel();

    expect(screen.getByRole("group", { name: "Provider speaker zero" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "speaker-1" })).toBeInTheDocument();
    expect(screen.getByLabelText("CHAT code for speaker-0")).toHaveValue("");
    expect(screen.getByLabelText("Participant role for speaker-0")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("CHAT code for speaker-0"), { target: { value: "CHI" } });
    fireEvent.change(screen.getByLabelText("Participant role for speaker-0"), { target: { value: "target_child" } });
    fireEvent.click(screen.getByLabelText("Reviewed utterance utt-0 for speaker-0"));

    expect(onChange).toHaveBeenCalledTimes(3);
  });

  it("uses only valid progressive mapping entries for completeness", () => {
    const partial = mappingDraft({
      entries: [{
        ...mappingDraft().entries[0],
        confirmed_chat_code: "CHI",
        participant_role: "target_child",
      }],
    });

    expect(isSpeakerMappingComplete(mappingDraft())).toBe(false);
    expect(isSpeakerMappingComplete(partial)).toBe(false);
    expect(isSpeakerMappingComplete(completeMapping())).toBe(true);
  });

  it("requires a unique code and exactly one CHI target-child pair with no more than three entries", () => {
    const complete = completeMapping();
    expect(isSpeakerMappingComplete({ ...complete, entries: complete.entries.map((entry) => ({ ...entry, confirmed_chat_code: "CHI" })) })).toBe(false);
    expect(isSpeakerMappingComplete({ ...complete, entries: complete.entries.map((entry) => ({ ...entry, participant_role: "therapist" })) })).toBe(false);
    expect(isSpeakerMappingComplete({ ...complete, entries: [...complete.entries, complete.entries[0], complete.entries[1]] })).toBe(false);
  });

  it("requires the canonical code and role pair for every speaker", () => {
    const complete = completeMapping();
    expect(isSpeakerMappingComplete({
      ...complete,
      entries: [{ ...complete.entries[0], participant_role: "therapist" }, { ...complete.entries[1], participant_role: "target_child" }],
    })).toBe(false);
    expect(isSpeakerMappingComplete({
      ...complete,
      entries: [{ ...complete.entries[0], confirmed_chat_code: "OTH", participant_role: "other" }, complete.entries[1]],
    })).toBe(false);
  });

  it("fails closed for duplicate or extraneous reviewed utterance ids", () => {
    const complete = completeMapping();
    expect(isSpeakerMappingComplete({
      ...complete,
      entries: [{ ...complete.entries[0], reviewed_utterance_ids: ["utt-0", "utt-0"] }, complete.entries[1]],
    })).toBe(false);
    expect(isSpeakerMappingComplete({
      ...complete,
      entries: [{ ...complete.entries[0], reviewed_utterance_ids: ["utt-0", "not-an-affected-id"] }, complete.entries[1]],
    })).toBe(false);
  });

  it("fails closed for malformed speaker and affected-utterance identifiers", () => {
    const complete = completeMapping();
    expect(isSpeakerMappingComplete({ ...complete, entries: [{ ...complete.entries[0], temporary_speaker_id: " " }, complete.entries[1]] })).toBe(false);
    expect(isSpeakerMappingComplete({ ...complete, entries: [{ ...complete.entries[0], temporary_speaker_id: complete.entries[1].temporary_speaker_id }, complete.entries[1]] })).toBe(false);
    expect(isSpeakerMappingComplete({ ...complete, entries: [{ ...complete.entries[0], affected_utterance_ids: [] }, complete.entries[1]] })).toBe(false);
    expect(isSpeakerMappingComplete({ ...complete, entries: [{ ...complete.entries[0], affected_utterance_ids: ["utt-0", "utt-0"] }, complete.entries[1]] })).toBe(false);
    expect(isSpeakerMappingComplete({ ...complete, entries: [{ ...complete.entries[0], affected_utterance_ids: [" "] }, complete.entries[1]] })).toBe(false);
  });

  it("requires every speaker entry to cover a nonempty, globally unique utterance set", () => {
    const complete = completeMapping();
    expect(isSpeakerMappingComplete({
      ...complete,
      entries: [{ ...complete.entries[0], affected_utterance_ids: [], reviewed_utterance_ids: [] }, complete.entries[1]],
    })).toBe(false);
    expect(isSpeakerMappingComplete({
      ...complete,
      entries: [{ ...complete.entries[0], affected_utterance_ids: ["utt-0", "utt-1"], reviewed_utterance_ids: ["utt-0", "utt-1"] }, complete.entries[1]],
    })).toBe(false);
  });

  it("emits immutable edits while preserving server-owned entry fields", () => {
    const mapping = mappingDraft();
    const { onChange } = renderPanel(mapping);

    fireEvent.change(screen.getByLabelText("CHAT code for speaker-0"), { target: { value: "CHI" } });
    const codeUpdate = onChange.mock.calls[0][0] as SpeakerMapping;
    expect(codeUpdate).not.toBe(mapping);
    expect(codeUpdate.entries).not.toBe(mapping.entries);
    expect(codeUpdate.entries[0]).toEqual({ ...mapping.entries[0], confirmed_chat_code: "CHI" });
    expect(codeUpdate.entries[1]).toBe(mapping.entries[1]);

    fireEvent.click(screen.getByLabelText("Reviewed utterance utt-0 for speaker-0"));
    const reviewUpdate = onChange.mock.calls[1][0] as SpeakerMapping;
    expect(reviewUpdate.entries[0]).toEqual({ ...mapping.entries[0], reviewed_utterance_ids: ["utt-0"] });
  });

  it("enforces save before confirmation", () => {
    const incomplete = renderPanel(mappingDraft(), { dirty: true });
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();

    incomplete.unmount();
    const saved = renderPanel(completeMapping({ persisted: true }), { dirty: false });
    fireEvent.click(screen.getByRole("button", { name: "Confirm speaker mapping" }));
    expect(saved.onConfirm).toHaveBeenCalledOnce();
    expect(incomplete.onSave).not.toHaveBeenCalled();
  });

  it("enables save only for a complete dirty draft and confirmation only after persistence", () => {
    const { onSave } = renderPanel(completeMapping(), { dirty: true });
    fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));
    expect(onSave).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
  });

  it("blocks actions while busy or stale and announces only mapping issue details assertively", () => {
    const { onStartNewReview } = renderPanel(completeMapping({
      persisted: true,
      effective_status: "stale",
      issue_code: "SPEAKER_MAPPING_STALE",
      issue_message: "Transcript version changed. Reload before continuing.",
    }), { dirty: false, busy: true });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveTextContent("The speaker mapping changed. Reload and review it before continuing.");
    expect(alert).not.toHaveTextContent("Synthetic zero");
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
    const restart = screen.getByRole("button", { name: "Start new mapping review" });
    expect(restart).toBeDisabled();
    expect(restart).toHaveClass("min-h-11", "focus-visible:ring-2");
    fireEvent.click(restart);
    expect(onStartNewReview).not.toHaveBeenCalled();
  });

  it("offers one explicit accessible restart action only for a non-busy stale mapping", () => {
    const { onStartNewReview, unmount } = renderPanel(completeMapping({
      persisted: true,
      effective_status: "stale",
      issue_code: "SPEAKER_MAPPING_STALE",
      issue_message: "Unsafe provider detail.",
    }), { dirty: false });

    const restart = screen.getByRole("button", { name: "Start new mapping review" });
    expect(restart).toBeEnabled();
    expect(restart).toHaveAttribute("aria-describedby", "speaker-mapping-issue");
    fireEvent.click(restart);
    expect(onStartNewReview).toHaveBeenCalledOnce();

    unmount();
    renderPanel(mappingDraft());
    expect(screen.queryByRole("button", { name: "Start new mapping review" })).not.toBeInTheDocument();
  });

  it("renders fixed safe guidance instead of an issue payload", () => {
    const unsafeIssue = "Provider label and Synthetic zero must never be announced.";
    renderPanel(completeMapping({
      persisted: true,
      effective_status: "stale",
      issue_code: "SPEAKER_MAPPING_VERSION_CONFLICT",
      issue_message: unsafeIssue,
    }), { dirty: false });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("The speaker mapping changed. Reload and review it before continuing.");
    expect(alert).not.toHaveTextContent(unsafeIssue);
    expect(alert).not.toHaveTextContent("Synthetic zero");
  });

  it("uses generic safe guidance for an unknown mapping issue", () => {
    renderPanel(completeMapping({
      issue_code: "UNRECOGNIZED_MAPPING_FAILURE",
      issue_message: "Synthetic one and provider metadata are unsafe to display.",
    }), { dirty: false });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("The speaker mapping needs attention. Reload and review it before continuing.");
    expect(alert).not.toHaveTextContent("Synthetic one");
  });

  it("shows the affected utterance text and timestamp, while safely handling a missing line", () => {
    renderPanel(mappingDraft({
      entries: [{
        ...mappingDraft().entries[0],
        affected_utterance_ids: ["utt-0", "missing-utterance"],
      }],
    }));

    expect(screen.getByText("Synthetic zero")).toBeInTheDocument();
    expect(screen.getByText("00:00.000 – 00:01.250")).toBeInTheDocument();
    expect(screen.getByText("Utterance missing-utterance is unavailable in the current transcript.")).toBeInTheDocument();
  });

  it("does not complete or review an affected utterance that is unavailable", () => {
    const mapping = completeMapping({
      entries: [{
        ...completeMapping().entries[0],
        affected_utterance_ids: ["missing-utterance"],
        reviewed_utterance_ids: [],
      }, completeMapping().entries[1]],
    });
    const { onChange } = renderPanel(mapping, { dirty: true });

    expect(screen.getByLabelText("Reviewed utterance missing-utterance for speaker-0")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Reviewed utterance missing-utterance for speaker-0"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("does not complete or review a line assigned to a different temporary speaker", () => {
    const mapping = completeMapping();
    const mismatchedLines = lines.map((line, index) => (
      index === 0 ? { ...line, temporarySpeakerId: "speaker-1" } : line
    ));
    const onChange = vi.fn();
    render(
      <SpeakerMappingPanel
        mapping={mapping}
        lines={mismatchedLines}
        dirty
        busy={false}
        onChange={onChange}
        onSave={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Reviewed utterance utt-0 for speaker-0")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Reviewed utterance utt-0 for speaker-0"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("keeps confirmed mappings read-only and assigns distinct accessible names to malformed duplicate ids", () => {
    const confirmed = completeMapping({ status: "confirmed", effective_status: "confirmed", persisted: true });
    const { unmount } = renderPanel(confirmed, { dirty: true });

    expect(screen.getByLabelText("CHAT code for speaker-0")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
    unmount();

    const malformed = completeMapping({
      entries: completeMapping().entries.map((entry) => ({ ...entry, temporary_speaker_id: "speaker-0" })),
    });
    renderPanel(malformed);
    expect(screen.getByLabelText("CHAT code for speaker-0")).toBeInTheDocument();
    expect(screen.getByLabelText("CHAT code for speaker-0 (entry 2)")).toBeInTheDocument();
  });

  it("contains long unbroken provider, temporary-id, and utterance values", () => {
    const longValue = "unbroken".repeat(30);
    renderPanel(mappingDraft({
      entries: [{
        ...mappingDraft().entries[0],
        temporary_speaker_id: longValue,
        source_speaker_label: longValue,
      }],
    }), { dirty: false });

    expect(screen.getByText(longValue)).toHaveClass("break-words");
    expect(screen.getByText(`Temporary speaker ID: ${longValue}`)).toHaveClass("break-words");
  });

  it("uses native, keyboard-focusable controls with visible focus styling and labelled guidance", () => {
    renderPanel();
    const code = screen.getByLabelText("CHAT code for speaker-0");
    const review = screen.getByLabelText("Reviewed utterance utt-0 for speaker-0");

    expect(code.tagName).toBe("SELECT");
    expect(review).toHaveAttribute("type", "checkbox");
    expect(code).toHaveClass("min-h-11", "focus-visible:ring-2");
    fireEvent.keyDown(code, { key: "Tab" });
    code.focus();
    expect(code).toHaveFocus();
    expect(within(screen.getByRole("status")).getByText(/Select a CHAT code/)).toBeInTheDocument();
  });
});
