import { beforeEach, describe, expect, it, vi, afterEach } from "vitest";
import { store } from "../store/state.js";
import { api } from "../services/api-client.js";
import * as audioProcessingApi from "../services/audio-processing-api.js";
import { requestSecureUploadIntent } from "../services/audio-service.js";
import {
  startBackendAudioProcessing,
  pollProcessingJobStatus,
  applyBackendProcessingResult
} from "../services/transcription-service.js";

const testUser = {
  user_id: "therapist_a",
  name: "Therapist A",
  email: "therapist-a@example.test",
  role: "therapist"
};

const testCase = {
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  anonymized_child_code: "CHI-001",
  display_label: "Case A",
  consent_status: "granted",
  age_months: 48,
  sex: "female"
};

const testSession = {
  session_id: "SESSION-001",
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  session_date: "2026-06-03",
  session_type: "free_play",
  audio_file_id: "AUDIO-001",
  processing_status: "uploaded"
};

const testFile = {
  name: "test_recording.wav",
  size: 1024000,
  type: "audio/wav"
};

describe("Audio upload intent & transcription pipeline – API integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    store.setState({
      currentUser: testUser,
      dataMode: "mock",
      cases: [testCase],
      sessions: [testSession],
      selectedSessionId: "SESSION-001",
      audioFiles: [],
      auditLogs: [],
      transcripts: {},
      transcriptLines: {},
      extractedFeatureOutputs: {},
      aiDecisionOutputs: {},
      processingJobs: []
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── requestSecureUploadIntent ──────────────────────────────────────

  describe("requestSecureUploadIntent", () => {
    it("in api mode calls api.post with correct path and payload", async () => {
      store.setState({ dataMode: "api" });

      const mockIntentResponse = {
        audio_file: { audio_file_id: "AUDIO-API-001", storage_mode: "secure_private" },
        upload: { signed_upload_url: "https://storage.example.test/upload", expires_in_seconds: 600 }
      };

      const postSpy = vi.spyOn(api, "post").mockResolvedValue(mockIntentResponse);

      const result = await requestSecureUploadIntent(testFile, "SESSION-001", "CASE-001");

      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith(
        "/api/sessions/SESSION-001/audio/upload-intent",
        {
          original_filename: "test_recording.wav",
          file_size: 1024000,
          mime_type: "audio/wav",
          checksum_sha256: null,
          retention_days: 90,
          storage_provider: "supabase"
        }
      );
      expect(result).toEqual(mockIntentResponse);

      // Audit log should be created
      const state = store.getState();
      expect(state.auditLogs.some(log => log.event_type === "secure_upload_intent_requested")).toBe(true);
    });

    it("in non-api mode calls createSecureAudioUploadIntent (existing behavior)", async () => {
      store.setState({ dataMode: "mock" });

      const mockIntentResponse = {
        status: "not_configured",
        mode: "mock",
        message: "Secure backend upload is not configured yet."
      };

      const legacySpy = vi.spyOn(audioProcessingApi, "createSecureAudioUploadIntent").mockResolvedValue(mockIntentResponse);
      const postSpy = vi.spyOn(api, "post");

      const result = await requestSecureUploadIntent(testFile, "SESSION-001", "CASE-001");

      expect(legacySpy).toHaveBeenCalledTimes(1);
      expect(legacySpy).toHaveBeenCalledWith("SESSION-001", testFile);
      expect(postSpy).not.toHaveBeenCalled();
      expect(result).toEqual(mockIntentResponse);
    });
  });

  // ── startBackendAudioProcessing ────────────────────────────────────

  describe("startBackendAudioProcessing", () => {
    it("in api mode calls api.post to process-audio endpoint", async () => {
      store.setState({ dataMode: "api" });

      const mockJobResponse = {
        job_id: "JOB-API-001",
        session_id: "SESSION-001",
        status: "queued",
        stage: "submitted",
        progress: 0
      };

      const postSpy = vi.spyOn(api, "post").mockResolvedValue(mockJobResponse);
      const legacySpy = vi.spyOn(audioProcessingApi, "submitAudioProcessingJob");

      const result = await startBackendAudioProcessing("SESSION-001");

      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith(
        "/api/sessions/SESSION-001/process-audio",
        { audio_file_id: "AUDIO-001" }
      );

      // submitAudioProcessingJob should NOT have been called
      expect(legacySpy).not.toHaveBeenCalled();

      // Should return a mapped processing job
      expect(result.job_id).toBe("JOB-API-001");
      expect(result.status).toBe("queued");
    });

    it("in non-api mode calls submitAudioProcessingJob (existing behavior)", async () => {
      store.setState({ dataMode: "mock" });

      const mockJobResponse = {
        status: "not_configured",
        mode: "mock",
        message: "Backend audio processing adapter is not configured yet."
      };

      const legacySpy = vi.spyOn(audioProcessingApi, "submitAudioProcessingJob").mockResolvedValue(mockJobResponse);
      const postSpy = vi.spyOn(api, "post");

      await expect(startBackendAudioProcessing("SESSION-001")).rejects.toThrow(
        "Backend audio processing adapter is not configured yet."
      );

      expect(legacySpy).toHaveBeenCalledTimes(1);
      expect(legacySpy).toHaveBeenCalledWith("SESSION-001", "AUDIO-001");
      expect(postSpy).not.toHaveBeenCalled();
    });
  });

  // ── pollProcessingJobStatus ────────────────────────────────────────

  describe("pollProcessingJobStatus", () => {
    it("in api mode calls api.get to job endpoint", async () => {
      store.setState({ dataMode: "api" });

      const mockJobPayload = {
        job_id: "JOB-API-001",
        session_id: "SESSION-001",
        status: "processing",
        stage: "transcription",
        progress: 50
      };

      const getSpy = vi.spyOn(api, "get").mockResolvedValue(mockJobPayload);
      const legacySpy = vi.spyOn(audioProcessingApi, "getProcessingJobStatus");

      const result = await pollProcessingJobStatus("JOB-API-001");

      expect(getSpy).toHaveBeenCalledTimes(1);
      expect(getSpy).toHaveBeenCalledWith("/api/jobs/JOB-API-001");
      expect(legacySpy).not.toHaveBeenCalled();

      expect(result.job_id).toBe("JOB-API-001");
      expect(result.status).toBe("processing");
    });

    it("in non-api mode calls getProcessingJobStatus (existing behavior)", async () => {
      store.setState({ dataMode: "mock" });

      const mockJobPayload = {
        job_id: "JOB-001",
        session_id: "SESSION-001",
        status: "processing",
        stage: "transcription",
        progress: 50
      };

      const legacySpy = vi.spyOn(audioProcessingApi, "getProcessingJobStatus").mockResolvedValue(mockJobPayload);
      const getSpy = vi.spyOn(api, "get");

      const result = await pollProcessingJobStatus("JOB-001");

      expect(legacySpy).toHaveBeenCalledTimes(1);
      expect(legacySpy).toHaveBeenCalledWith("JOB-001");
      expect(getSpy).not.toHaveBeenCalled();

      expect(result.job_id).toBe("JOB-001");
    });

    it("when poll returns completed job in api mode, fetches transcript/features/ai-output/qa", async () => {
      store.setState({ dataMode: "api" });

      const completedJobPayload = {
        job_id: "JOB-API-002",
        session_id: "SESSION-001",
        case_id: "CASE-001",
        status: "completed",
        stage: "completed",
        progress: 100
      };

      const mockTranscript = {
        transcript_id: "TRANSCRIPT-API-001",
        transcript_text: "Test transcript text",
        transcript_lines: [
          { line_number: 1, speaker: "CHI", text: "hello", confidence: 0.95 }
        ]
      };
      const mockFeatures = {
        features: { mlu_words: 2.5, ttr: 0.6 }
      };
      const mockAiOutput = {
        screening_support_score: 0.45,
        model_version: "screening-support-v0.2.0"
      };
      const mockQa = {
        status: "pass",
        score: 95,
        issues: []
      };

      const getSpy = vi.spyOn(api, "get").mockImplementation(async (path) => {
        if (path.includes("/transcript")) return mockTranscript;
        if (path.includes("/features")) return mockFeatures;
        if (path.includes("/ai-output")) return mockAiOutput;
        if (path.includes("/qa")) return mockQa;
        if (path.includes("/jobs/")) return completedJobPayload;
        return {};
      });

      const result = await pollProcessingJobStatus("JOB-API-002");

      // Should have called: 1 job GET + 4 result GETs
      expect(getSpy).toHaveBeenCalledWith("/api/jobs/JOB-API-002");
      expect(getSpy).toHaveBeenCalledWith("/api/sessions/SESSION-001/transcript");
      expect(getSpy).toHaveBeenCalledWith("/api/sessions/SESSION-001/features");
      expect(getSpy).toHaveBeenCalledWith("/api/sessions/SESSION-001/ai-output");
      expect(getSpy).toHaveBeenCalledWith("/api/sessions/SESSION-001/qa");

      // The completed job should have applied results to the store
      const state = store.getState();
      expect(state.transcripts["SESSION-001"]).toBeDefined();
      expect(state.transcripts["SESSION-001"].transcript_id).toBe("TRANSCRIPT-API-001");
      expect(state.auditLogs.some(log => log.event_type === "backend_transcript_generated")).toBe(true);
    });

    it("when poll returns non-completed job in api mode, does NOT fetch result endpoints", async () => {
      store.setState({ dataMode: "api" });

      const processingJobPayload = {
        job_id: "JOB-API-003",
        session_id: "SESSION-001",
        status: "processing",
        stage: "feature_extraction",
        progress: 75
      };

      const getSpy = vi.spyOn(api, "get").mockResolvedValue(processingJobPayload);

      await pollProcessingJobStatus("JOB-API-003");

      // Should have called ONLY the job endpoint
      expect(getSpy).toHaveBeenCalledTimes(1);
      expect(getSpy).toHaveBeenCalledWith("/api/jobs/JOB-API-003");
    });
  });
});
