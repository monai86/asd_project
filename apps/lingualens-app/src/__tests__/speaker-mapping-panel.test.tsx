import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  SpeakerMappingPanel,
  type SpeakerMappingResponse,
} from "@/features/sessions/transcript/speaker-mapping-panel";

const draftMapping: SpeakerMappingResponse = {
  transcript_id: "TRANSCRIPT-ASR",
  transcript_version: 3,
  mapping_id: null,
  mapping_version: 0,
  status: "draft",
  confirmed_by_user_id: null,
  confirmed_by_role: null,
  confirmed_at: null,
  issues: [],
  entries: [
    {
      temporary_speaker_id: "SPK_01",
      confirmed_chat_code: null,
      participant_role: "unknown",
      disposition: "unknown",
      merged_into_temporary_speaker_id: null,
      affected_utterance_ids: ["utt_1", "utt_3"],
      source_speaker_label: "speaker_0",
      source_provider: "optional_diarizer",
      source_provider_metadata: { cluster: "speaker_0" },
      reviewed_utterance_ids: [],
    },
    {
      temporary_speaker_id: "SPK_02",
      confirmed_chat_code: null,
      participant_role: "unknown",
      disposition: "unknown",
      merged_into_temporary_speaker_id: null,
      affected_utterance_ids: ["utt_2"],
      source_speaker_label: "speaker_1",
      source_provider: "optional_diarizer",
      source_provider_metadata: { cluster: "speaker_1" },
      reviewed_utterance_ids: [],
    },
  ],
};

describe("SpeakerMappingPanel", () => {
  it("requires therapist role/code review before saving and confirming a mapping", () => {
    const onSaveDraft = vi.fn();
    const onConfirm = vi.fn();

    const { rerender } = render(
      <SpeakerMappingPanel
        mapping={draftMapping}
        busy={false}
        onSaveDraft={onSaveDraft}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByRole("heading", { name: "Speaker mapping" })).toBeInTheDocument();
    expect(screen.getByText("SPK_01")).toBeInTheDocument();
    const firstRow = screen.getByTestId("speaker-mapping-SPK_01");
    expect(within(firstRow).getByText("speaker_0")).toBeInTheDocument();
    expect(within(firstRow).getByText("optional_diarizer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm mapping" })).toBeDisabled();

    fireEvent.change(within(firstRow).getByLabelText("CHAT code for SPK_01"), { target: { value: "CHI" } });
    fireEvent.change(within(firstRow).getByLabelText("Role for SPK_01"), { target: { value: "target_child" } });
    fireEvent.change(within(firstRow).getByLabelText("Disposition for SPK_01"), { target: { value: "target" } });

    const secondRow = screen.getByTestId("speaker-mapping-SPK_02");
    fireEvent.change(within(secondRow).getByLabelText("CHAT code for SPK_02"), { target: { value: "THE" } });
    fireEvent.change(within(secondRow).getByLabelText("Role for SPK_02"), { target: { value: "therapist" } });
    fireEvent.change(within(secondRow).getByLabelText("Disposition for SPK_02"), { target: { value: "non_target" } });

    fireEvent.click(screen.getByRole("button", { name: "Save mapping draft" }));

    const savedEntries = onSaveDraft.mock.calls[0][0];
    expect(onSaveDraft).toHaveBeenCalledWith(expect.arrayContaining([
      expect.objectContaining({
        temporary_speaker_id: "SPK_01",
        confirmed_chat_code: "CHI",
        participant_role: "target_child",
        disposition: "target",
        affected_utterance_ids: ["utt_1", "utt_3"],
      }),
      expect.objectContaining({
        temporary_speaker_id: "SPK_02",
        confirmed_chat_code: "THE",
        participant_role: "therapist",
        disposition: "non_target",
        affected_utterance_ids: ["utt_2"],
      }),
    ]));
    expect(screen.getByRole("button", { name: "Confirm mapping" })).toBeDisabled();

    rerender(
      <SpeakerMappingPanel
        mapping={{
          ...draftMapping,
          mapping_id: "mapping_saved",
          mapping_version: 1,
          entries: savedEntries,
        }}
        busy={false}
        onSaveDraft={onSaveDraft}
        onConfirm={onConfirm}
      />,
    );
    expect(screen.getByRole("button", { name: "Confirm mapping" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Confirm mapping" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("shows stale mapping blockers and keeps confirmation disabled", () => {
    render(
      <SpeakerMappingPanel
        mapping={{
          ...draftMapping,
          status: "stale",
          issues: [{
            code: "SPEAKER_MAPPING_STALE",
            severity: "error",
            message: "Speaker mapping belongs to an older transcript version.",
            blocking: true,
          }],
        }}
        busy={false}
        onSaveDraft={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("SPEAKER_MAPPING_STALE");
    expect(alert).toHaveTextContent("Speaker mapping belongs to an older transcript version.");
    expect(screen.getByRole("button", { name: "Confirm mapping" })).toBeDisabled();
  });
});
