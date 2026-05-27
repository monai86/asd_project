import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  AUDIO_PROCESSING_ROUTES,
  mapBackendProcessingResultToFrontend,
  submitAudioProcessingJob
} from "../services/audio-processing-api.js";
import {
  applyBackendProcessingResult,
  startTranscription
} from "../services/transcription-service.js";
import { store } from "../store/state.js";

function resetProcessingState() {
  store.persistenceAdapter = null;
  store.setState({
    currentUser: { user_id: "therapist_a", role: "therapist", name: "Therapist A" },
    cases: [{
      case_id: "CASE-001",
      owner_user_id: "therapist_a",
      anonymized_child_code: "CHI-A",
      display_label: "Case A",
      age_months: 56,
      score_trend: []
    }],
    sessions: [{
      session_id: "SESSION-001",
      case_id: "CASE-001",
      owner_user_id: "therapist_a",
      session_date: "2026-05-20",
      session_type: "free_play",
      audio_file_id: "AUDIO-001",
      processing_status: "uploaded",
      feature_extraction_status: "not_started",
      ai_analysis_status: "not_started",
      therapist_review_status: "not_started"
    }],
    selectedSessionId: "SESSION-001",
    transcripts: {},
    transcriptLines: {},
    extractedFeatureOutputs: {},
    aiDecisionOutputs: {},
    audioFiles: [{
      audio_file_id: "AUDIO-001",
      session_id: "SESSION-001",
      case_id: "CASE-001",
      owner_user_id: "therapist_a",
      original_filename: "sample.wav",
      stored_filename: "CASE-001_SESSION-001_AUDIO-001.wav",
      file_type: "wav",
      file_size: 1024,
      storage_mode: "metadata_only"
    }],
    auditLogs: []
  });
}

function backendPayload() {
  return {
    transcript: {
      transcript_id: "TRANSCRIPT-BACKEND-001",
      chat_text: "@Begin\n*CHI:\twant train .\n*MOT:\twhich train ?\n@End"
    },
    utterances: [
      { speaker_label: "CHILD", text: "want train .", confidence: 0.82, start_time: 1.1, end_time: 2.4 },
      { speaker_label: "CAREGIVER", text: "which train ?", confidence: 0.91, start_time: 2.8, end_time: 4.0 }
    ],
    qa: {
      status: "needs_review",
      score: 88,
      issues: [{ code: "LOW_CONFIDENCE_SEGMENT", message: "Review child utterance confidence." }]
    },
    features: {
      feature_schema_version: "14-feature-schema",
      features: {
        age_months: 56,
        total_utterances: 1,
        mlu: 2,
        mluw: 2,
        ttr: 1,
        total_words: 2,
        unintelligible_count: 0,
        unintelligible_ratio: 0,
        zero_vocalization_count: 0,
        nonverbal_vocalization_count: 0,
        question_ratio: 0,
        echolalia_count: 0,
        echolalia_ratio: 0,
        pronoun_reversal_count: 0
      },
      interaction_indicators: {
        turn_taking_count: 1
      },
      acoustic_indicators: {
        pause_ratio: 0.12
      }
    },
    ai_screening_output: {
      output_id: "AI-BACKEND-001",
      concern_level: "watchful_review",
      screening_support_score: 0.44,
      explanation: "AI-assisted explanation from backend."
    }
  };
}

describe("audio processing API boundary", () => {
  beforeEach(() => {
    resetProcessingState();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("documents the suggested backend routes", () => {
    expect(AUDIO_PROCESSING_ROUTES).toEqual([
      "POST /api/sessions/:sessionId/process-audio",
      "GET /api/jobs/:jobId/status",
      "GET /api/sessions/:sessionId/transcript",
      "GET /api/sessions/:sessionId/features",
      "GET /api/sessions/:sessionId/qa"
    ]);
  });

  it("returns a clear placeholder result when backend processing is not configured", async () => {
    const result = await submitAudioProcessingJob("SESSION-001", "AUDIO-001", {
      processingMode: "api_placeholder"
    });

    expect(result.status).toBe("not_configured");
    expect(result.message).toContain("Backend audio processing adapter is not configured yet");
  });

  it("maps backend output into frontend transcript, feature, QA, and AI support models", () => {
    const mapped = mapBackendProcessingResultToFrontend(backendPayload(), {
      session: store.getState().sessions[0],
      childCase: store.getState().cases[0],
      currentUser: store.getState().currentUser,
      transcriptCount: 0
    });

    expect(mapped.transcriptRecord).toMatchObject({
      transcript_id: "TRANSCRIPT-BACKEND-001",
      review_status: "awaiting_review",
      qa_status: "needs_review",
      review_required: true
    });
    expect(mapped.transcriptLines[0]).toMatchObject({
      speaker: "CHI",
      text: "want train .",
      start_time: 1.1,
      end_time: 2.4
    });
    expect(mapped.featuresSet).toMatchObject({
      extraction_status: "preliminary",
      review_status: "preliminary"
    });
    expect(mapped.featuresSet.features.turn_taking_count).toBe(1);
    expect(mapped.featuresSet.features.pause_ratio).toBe(0.12);
    expect(mapped.aiOutput.therapist_review_status).toBe("requires_transcript_review");
  });

  it("applies backend results with transcript review and preliminary feature status", () => {
    applyBackendProcessingResult("SESSION-001", backendPayload());
    const state = store.getState();

    expect(state.transcripts["SESSION-001"].review_status).toBe("awaiting_review");
    expect(state.sessions[0].therapist_review_status).toBe("awaiting_review");
    expect(state.sessions[0].feature_extraction_status).toBe("preliminary");
    expect(state.extractedFeatureOutputs["SESSION-001"].review_status).toBe("preliminary");
    expect(state.aiDecisionOutputs["SESSION-001"].therapist_review_status).toBe("requires_transcript_review");
  });

  it("keeps the mock transcription workflow working", async () => {
    vi.useFakeTimers();
    const transcription = startTranscription("SESSION-001");
    await vi.advanceTimersByTimeAsync(1500);
    await transcription;

    const state = store.getState();
    expect(state.transcripts["SESSION-001"].review_status).toBe("awaiting_review");
    expect(state.transcriptLines["SESSION-001"].length).toBeGreaterThan(0);
    expect(state.extractedFeatureOutputs["SESSION-001"].extraction_status).toBe("preliminary");
    expect(state.aiDecisionOutputs["SESSION-001"].therapist_review_status).toBe("requires_transcript_review");
  });
});
