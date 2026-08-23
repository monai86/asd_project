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
  const rendered = render(
    <SpeakerMappingPanel
      mapping={mapping}
      lines={lines}
      dirty={options.dirty ?? true}
      busy={options.busy ?? false}
      onChange={onChange}
      onSave={onSave}
      onConfirm={onConfirm}
    />,
  );
  return { onChange, onSave, onConfirm, ...rendered };
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
    renderPanel(completeMapping({
      persisted: true,
      effective_status: "stale",
      issue_code: "SPEAKER_MAPPING_STALE",
      issue_message: "Transcript version changed. Reload before continuing.",
    }), { dirty: false, busy: true });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveTextContent("Transcript version changed. Reload before continuing.");
    expect(alert).not.toHaveTextContent("Synthetic zero");
    expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
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
