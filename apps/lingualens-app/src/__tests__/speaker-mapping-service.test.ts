import { afterEach, describe, expect, it, vi } from "vitest";

import {
  backendTranscriptLines,
  buildReplacementSpeakerMappingEntries,
  type BackendTranscript,
} from "@/lib/workflow";
import { sessionWorkflowService } from "@/features/sessions/services/session-workflow-service";

const mappingResponse = {
  mapping_id: "spmap-synthetic-1",
  organization_id: "org-synthetic",
  transcript_id: "tr-synthetic-1",
  source_transcript_version: 4,
  applied_transcript_version: null,
  mapping_version: 2,
  status: "draft" as const,
  required: true,
  persisted: true,
  effective_status: "draft" as const,
  issue_code: null,
  issue_message: null,
  confirmed_by_user_id: null,
  confirmed_by_role: null,
  confirmed_at: null,
  created_at: "2026-08-24T00:00:00Z",
  updated_at: "2026-08-24T00:00:00Z",
  entries: [{
    temporary_speaker_id: "speaker-0",
    confirmed_chat_code: null,
    participant_role: null,
    source_speaker_label: "Provider 0",
    provider_metadata: { provider_id: "synthetic-asr" },
    affected_utterance_ids: ["utt-synthetic-1"],
    reviewed_utterance_ids: [],
  }],
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function transcriptFixture(overrides: Partial<BackendTranscript> = {}): BackendTranscript {
  return {
    transcript_id: "tr-synthetic-1",
    session_id: "session-synthetic-1",
    source: "asr_draft:synthetic",
    version: 4,
    utterances: [{
      utterance_id: "utt-synthetic-1",
      speaker: "UNK",
      text: "Synthetic utterance.",
      temporary_speaker_id: "speaker-0",
      source_speaker_label: "Provider 0",
    }],
    ...overrides,
  };
}

function installLoadFetch(transcript: BackendTranscript, options: { mappingStatus?: number } = {}) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/sessions/session-synthetic-1")) {
      return json({ session_id: "session-synthetic-1", case_id: "case-synthetic", transcript_id: transcript.transcript_id });
    }
    if (url.endsWith(`/transcripts/${transcript.transcript_id}`)) return json(transcript);
    if (url.endsWith(`/transcripts/${transcript.transcript_id}/speaker-mapping`)) {
      if ((options.mappingStatus ?? 200) >= 400) return json({ detail: "Mapping service unavailable" }, options.mappingStatus);
      return json(mappingResponse);
    }
    throw new Error(`Unexpected request: ${url} (${init?.method ?? "GET"})`);
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("speaker mapping workflow service", () => {
  it("loads speaker mapping after the current transcript activates the ASR draft gate", async () => {
    const fetchMock = installLoadFetch(transcriptFixture());
    vi.stubGlobal("fetch", fetchMock);

    const loaded = await sessionWorkflowService.load({ sessionId: "session-synthetic-1" });

    expect(loaded.speakerMapping).toMatchObject({
      mapping_id: "spmap-synthetic-1",
      required: true,
      effective_status: "draft",
    });
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      expect.stringMatching(/\/sessions\/session-synthetic-1$/),
      expect.stringMatching(/\/transcripts\/tr-synthetic-1$/),
      expect.stringMatching(/\/transcripts\/tr-synthetic-1\/speaker-mapping$/),
    ]);
  });

  it.each([
    ["manual", "speaker-0"],
    ["cha_upload:synthetic.cha", "speaker-0"],
    ["mock_asr_draft:synthetic", "speaker-0"],
    ["asr_draft:synthetic", undefined],
    ["asr_draft:synthetic", "   "],
  ])("does not add a mapping request for %s with temporary id %s", async (source, temporarySpeakerId) => {
    const fetchMock = installLoadFetch(transcriptFixture({
      source,
      utterances: [{
        utterance_id: "utt-synthetic-1",
        speaker: "UNK",
        text: "Synthetic utterance.",
        temporary_speaker_id: temporarySpeakerId,
      }],
    }));
    vi.stubGlobal("fetch", fetchMock);

    const loaded = await sessionWorkflowService.load({ sessionId: "session-synthetic-1" });

    expect(loaded.speakerMapping).toBeUndefined();
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toHaveLength(2);
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/speaker-mapping"))).toBe(false);
  });

  it("preserves backend utterance speaker provenance in transcript lines", () => {
    expect(backendTranscriptLines(transcriptFixture())).toEqual([expect.objectContaining({
      lineId: "utt-synthetic-1",
      temporarySpeakerId: "speaker-0",
      sourceSpeakerLabel: "Provider 0",
    })]);
  });

  it("builds replacement edits from current temporary IDs and carries only compatible assignments", () => {
    const previous = {
      ...mappingResponse,
      effective_status: "stale" as const,
      entries: [
        {
          ...mappingResponse.entries[0],
          confirmed_chat_code: "CHI" as const,
          participant_role: "target_child" as const,
          reviewed_utterance_ids: ["utt-synthetic-1"],
        },
        {
          ...mappingResponse.entries[0],
          temporary_speaker_id: "speaker-unsafe",
          source_speaker_label: "Old provider label",
          confirmed_chat_code: "THER" as const,
          participant_role: "therapist" as const,
          affected_utterance_ids: ["utt-old"],
          reviewed_utterance_ids: ["utt-old"],
        },
      ],
    };
    const current = transcriptFixture({
      version: 5,
      utterances: [
        ...transcriptFixture().utterances!,
        {
          utterance_id: "utt-new",
          speaker: "UNK",
          text: "Synthetic current utterance.",
          temporary_speaker_id: "speaker-unsafe",
          source_speaker_label: "Changed provider label",
        },
      ],
    });

    expect(buildReplacementSpeakerMappingEntries(current, previous)).toEqual([
      {
        temporary_speaker_id: "speaker-0",
        confirmed_chat_code: "CHI",
        participant_role: "target_child",
        reviewed_utterance_ids: [],
      },
      {
        temporary_speaker_id: "speaker-unsafe",
        confirmed_chat_code: null,
        participant_role: null,
        reviewed_utterance_ids: [],
      },
    ]);
  });

  it("sends only editable draft fields and exact expected versions", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toMatch(/\/transcripts\/tr-synthetic-1\/speaker-mapping$/);
      expect(init?.method).toBe("PUT");
      expect(JSON.parse(String(init?.body))).toEqual({
        expected_transcript_version: 4,
        expected_mapping_version: 2,
        entries: [{
          temporary_speaker_id: "speaker-0",
          confirmed_chat_code: "CHI",
          participant_role: "target_child",
          reviewed_utterance_ids: ["utt-synthetic-1"],
        }],
      });
      return json(mappingResponse);
    });
    vi.stubGlobal("fetch", fetchMock);

    await sessionWorkflowService.saveSpeakerMappingDraft("tr-synthetic-1", {
      expected_transcript_version: 4,
      expected_mapping_version: 2,
      entries: [{
        temporary_speaker_id: "speaker-0",
        confirmed_chat_code: "CHI",
        participant_role: "target_child",
        reviewed_utterance_ids: ["utt-synthetic-1"],
        source_speaker_label: "forged provider label",
        provider_metadata: { provider_id: "forged" },
        affected_utterance_ids: ["utt-synthetic-1"],
      }],
      mapping_id: "forged-mapping-id",
      organization_id: "forged-organization-id",
    } as unknown as Parameters<typeof sessionWorkflowService.saveSpeakerMappingDraft>[1]);
  });

  it("posts only exact expected transcript and mapping versions to confirm", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toMatch(/\/transcripts\/tr-synthetic-1\/speaker-mapping\/confirm$/);
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        expected_transcript_version: 4,
        expected_mapping_version: 2,
      });
      return json({ ...mappingResponse, status: "confirmed", effective_status: "confirmed" });
    });
    vi.stubGlobal("fetch", fetchMock);

    await sessionWorkflowService.confirmSpeakerMapping("tr-synthetic-1", {
      expected_transcript_version: 4,
      expected_mapping_version: 2,
      confirmed_by_user_id: "forged-user-id",
    } as Parameters<typeof sessionWorkflowService.confirmSpeakerMapping>[1]);
  });

  it("propagates mapping API failures after an activated transcript load", async () => {
    const fetchMock = installLoadFetch(transcriptFixture(), { mappingStatus: 409 });
    vi.stubGlobal("fetch", fetchMock);

    await expect(sessionWorkflowService.load({ sessionId: "session-synthetic-1" })).rejects.toMatchObject({
      status: 409,
      body: JSON.stringify({ detail: "Mapping service unavailable" }),
    });
  });
});
