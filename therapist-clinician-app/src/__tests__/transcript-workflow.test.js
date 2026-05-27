import { beforeEach, describe, expect, it } from "vitest";
import { store } from "../store/state.js";
import {
  buildEvidenceItems,
  buildFeatureAndAiOutputs,
  buildTranscriptWorkflowArtifacts,
  parseChatTranscript
} from "../services/transcript-workflow-service.js";
import { updateUtterance } from "../services/review-service.js";

const user = { user_id: "therapist_a", name: "Therapist A", role: "therapist" };
const childCase = {
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  anonymized_child_code: "CHI-A",
  display_label: "Case A",
  age_months: 56,
  score_trend: []
};
const session = {
  session_id: "SESSION-001",
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  session_date: "2026-05-20",
  session_type: "free_play",
  processing_status: "transcript_ready",
  feature_extraction_status: "preliminary",
  ai_analysis_status: "requires_transcript_review",
  therapist_review_status: "awaiting_review"
};

function resetWorkflowState(overrides = {}) {
  store.persistenceAdapter = null;
  store.setState({
    currentUser: user,
    cases: [childCase],
    sessions: [session],
    selectedCaseId: "CASE-001",
    selectedSessionId: "SESSION-001",
    transcripts: {},
    transcriptLines: {},
    extractedFeatureOutputs: {},
    aiDecisionOutputs: {},
    audioFiles: [],
    auditLogs: [],
    users: [user],
    ...overrides
  });
}

function chatSample() {
  return `@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother, FAT Father Father, INV Investigator Investigator, CLI Clinician Clinician, PAR Parent Parent
*CHI:\tI want train \u00151000_2200\u0015
*MOT:\twhich train ?
*FAT:\the means red train .
*INV:\ttell me more .
*CLI:\tcan you say it again ?
*PAR:\twe can wait .
*CHI:\txxx &=mumble [/] train train ?
*CHI:\tYou want train .
*CHI:\t0 .
@End`;
}

describe("transcript review workflow", () => {
  beforeEach(() => {
    resetWorkflowState();
  });

  it("parses CHAT metadata, supported speaker tiers, line numbers, and timing markers", () => {
    const parsed = parseChatTranscript(chatSample());

    expect(parsed.metadata[0]).toEqual({ line_number: 1, text: "@Begin" });
    expect(parsed.transcriptLines.map(line => line.speaker)).toEqual([
      "CHI",
      "MOT",
      "FAT",
      "INV",
      "CLI",
      "PAR",
      "CHI",
      "CHI",
      "CHI"
    ]);
    expect(parsed.transcriptLines[0]).toMatchObject({
      line_number: 4,
      speaker: "CHI",
      text: "I want train",
      timing: { start_time: 1, end_time: 2.2 },
      review_status: "needs_review"
    });
  });

  it("detects clinical review markers without presenting them as conclusions", () => {
    const parsed = parseChatTranscript(chatSample());
    const flagged = parsed.transcriptLines.find(line => line.text.includes("xxx"));
    const flagTypes = flagged.clinical_flags.map(flag => flag.marker_type);

    expect(flagTypes).toContain("unintelligible_marker");
    expect(flagTypes).toContain("nonverbal_vocalization");
    expect(flagTypes).toContain("repetition_marker");
    expect(flagTypes).toContain("possible_echolalia_like_repetition");
    expect(flagTypes).toContain("child_question");
    expect(parsed.transcriptLines[7].clinical_flags.map(flag => flag.marker_type)).toContain("possible_pronoun_reversal");
    expect(parsed.transcriptLines[8].clinical_flags.map(flag => flag.marker_type)).toContain("zero_spoken_response");
  });

  it("creates preliminary feature and AI support outputs before transcript review", () => {
    const artifacts = buildTranscriptWorkflowArtifacts({
      session,
      childCase,
      transcriptText: chatSample(),
      filename: "sample.cha",
      transcriptCount: 0
    });

    expect(artifacts.transcriptRecord.review_status).toBe("awaiting_review");
    expect(artifacts.featuresSet.extraction_status).toBe("preliminary");
    expect(artifacts.featuresSet.features).toHaveProperty("pronoun_reversal_count");
    expect(artifacts.featuresSet.features).not.toHaveProperty("turn_taking_count");
    expect(artifacts.aiOutput.therapist_review_status).toBe("requires_transcript_review");
    expect(artifacts.sessionUpdates.feature_extraction_status).toBe("preliminary");
  });

  it("marks feature outputs stale after transcript edits", () => {
    const artifacts = buildTranscriptWorkflowArtifacts({
      session,
      childCase,
      transcriptText: chatSample(),
      filename: "sample.cha",
      transcriptCount: 0
    });
    store.setState({
      transcripts: { "SESSION-001": artifacts.transcriptRecord },
      transcriptLines: { "SESSION-001": artifacts.transcriptLines },
      extractedFeatureOutputs: { "SESSION-001": artifacts.featuresSet },
      aiDecisionOutputs: { "SESSION-001": artifacts.aiOutput }
    });

    updateUtterance("SESSION-001", 0, "I want red train .", "CHI", {
      reviewed: true,
      interpretation_note: "Corrected from audio review."
    });

    const state = store.getState();
    expect(state.transcriptLines["SESSION-001"][0]).toMatchObject({
      text: "I want red train .",
      review_status: "reviewed",
      interpretation_note: "Corrected from audio review."
    });
    expect(state.extractedFeatureOutputs["SESSION-001"].extraction_status).toBe("stale");
    expect(state.sessions[0].feature_extraction_status).toBe("stale");
    expect(state.aiDecisionOutputs["SESSION-001"].therapist_review_status).toBe("requires_transcript_review");
  });

  it("re-runs feature extraction as preliminary until transcript review is complete", () => {
    const parsed = parseChatTranscript(chatSample());
    const preliminary = buildFeatureAndAiOutputs({
      session,
      childCase,
      transcriptLines: parsed.transcriptLines,
      reviewed: false
    });
    const completed = buildFeatureAndAiOutputs({
      session,
      childCase,
      transcriptLines: parsed.transcriptLines.map(line => ({ ...line, reviewed: true, review_status: "reviewed" })),
      reviewed: true
    });

    expect(preliminary.featuresSet.extraction_status).toBe("preliminary");
    expect(preliminary.aiOutput.therapist_review_status).toBe("requires_transcript_review");
    expect(completed.featuresSet.extraction_status).toBe("completed");
    expect(completed.aiOutput.therapist_review_status).toBe("awaiting_review");
  });

  it("links evidence panel items back to transcript lines", () => {
    const parsed = parseChatTranscript(chatSample());
    const aiOutput = { top_contributing_features: ["unintelligible_ratio"] };
    const items = buildEvidenceItems(parsed.transcriptLines, aiOutput);

    expect(items.some(item => item.line_number === 10 && item.line_index === 6 && item.marker_type === "unintelligible_marker")).toBe(true);
    expect(items.some(item => item.line_number === null && item.marker_type === "unintelligible_ratio")).toBe(true);
  });
});
