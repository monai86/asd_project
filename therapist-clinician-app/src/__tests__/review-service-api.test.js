import { beforeEach, describe, expect, it, vi, afterEach } from "vitest";
import { store } from "../store/state.js";
import { updateUtterance, saveTherapistReview, TranscriptLineConflictError } from "../services/review-service.js";
import { api } from "../services/api-client.js";

const testUser = {
  user_id: "therapist_a",
  name: "Therapist A",
  email: "therapist-a@example.test",
  role: "therapist"
};

const testSession = {
  session_id: "SESSION-001",
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  session_date: "2026-06-03",
  session_type: "free_play",
  processing_status: "transcript_ready",
  therapist_review_status: "awaiting_review"
};

const testTranscript = {
  transcript_id: "TRANSCRIPT-001",
  session_id: "SESSION-001",
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  review_status: "awaiting_review"
};

const testLine = {
  line_id: "TRANSCRIPT-001_L0001",
  transcript_id: "TRANSCRIPT-001",
  session_id: "SESSION-001",
  case_id: "CASE-001",
  owner_user_id: "therapist_a",
  line_number: 1,
  speaker: "CHI",
  text: "I want train",
  version: 1
};

describe("review-service API integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    store.setState({
      currentUser: testUser,
      dataMode: "mock",
      sessions: [testSession],
      transcripts: { "SESSION-001": testTranscript },
      transcriptLines: { "SESSION-001": [testLine] },
      extractedFeatureOutputs: {},
      aiDecisionOutputs: {},
      clinicalSignoffs: [],
      auditLogs: []
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("API Mode", () => {
    beforeEach(() => {
      store.setState({ dataMode: "api" });
    });

    it("updateUtterance patches backend and updates store", async () => {
      const mockBackendLine = {
        line_id: "TRANSCRIPT-001_L0001",
        transcript_id: "TRANSCRIPT-001",
        session_id: "SESSION-001",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        line_number: 1,
        speaker_code: "CHI",
        utterance_text: "I want red train",
        reviewed: true,
        interpretation_note: "Review note",
        version: 2,
        updated_at: "2026-06-03T00:00:00.000Z",
        updated_by_user_id: "therapist_a"
      };

      const patchSpy = vi.spyOn(api, "patch").mockResolvedValue(mockBackendLine);

      const promise = updateUtterance("SESSION-001", 0, "I want red train", "CHI", {
        reviewed: true,
        interpretation_note: "Review note",
        expectedVersion: 1
      });

      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;

      expect(patchSpy).toHaveBeenCalledTimes(1);
      expect(patchSpy).toHaveBeenCalledWith(
        "/api/transcripts/TRANSCRIPT-001/lines/TRANSCRIPT-001_L0001",
        {
          speaker_code: "CHI",
          text: "I want red train",
          reviewed: true,
          interpretation_note: "Review note",
          expected_version: 1
        }
      );

      // Verify state was updated with returned line mapped correctly
      const state = store.getState();
      expect(state.transcriptLines["SESSION-001"][0]).toMatchObject({
        speaker: "CHI",
        text: "I want red train",
        reviewed: true,
        interpretation_note: "Review note",
        version: 2
      });

      expect(result).toMatchObject({
        speaker: "CHI",
        text: "I want red train",
        reviewed: true,
        version: 2
      });
    });

    it("updateUtterance throws TranscriptLineConflictError on 409 conflict", async () => {
      const errorPayload = {
        status: 409,
        payload: {
          detail: {
            code: "TRANSCRIPT_LINE_VERSION_CONFLICT",
            line_id: "TRANSCRIPT-001_L0001",
            expected_version: 1,
            actual_version: 2
          }
        }
      };

      const ApiError = new Error("API request failed with status 409.");
      ApiError.status = 409;
      ApiError.payload = errorPayload.payload;

      vi.spyOn(api, "patch").mockRejectedValue(ApiError);

      await expect(
        updateUtterance("SESSION-001", 0, "Conflicting edit", "CHI", {
          expectedVersion: 1
        })
      ).rejects.toThrow(TranscriptLineConflictError);
    });

    it("saveTherapistReview posts backend sign-off and updates store", async () => {
      const mockBackendSignoff = {
        signoff_id: "SIGNOFF-001",
        target_type: "transcript",
        target_id: "TRANSCRIPT-001",
        session_id: "SESSION-001",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        signed_by_user_id: "therapist_a",
        notes: "Clinical review sign-off notes",
        created_at: "2026-06-03T00:00:00.000Z"
      };

      const postSpy = vi.spyOn(api, "post").mockResolvedValue(mockBackendSignoff);

      const promise = saveTherapistReview({
        sessionId: "SESSION-001",
        notes: "Clinical review sign-off notes"
      });

      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;

      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith(
        "/api/sessions/SESSION-001/transcript/signoff",
        { notes: "Clinical review sign-off notes" }
      );

      // Verify state updates
      const state = store.getState();
      expect(state.clinicalSignoffs).toHaveLength(1);
      expect(state.clinicalSignoffs[0].signoff_id).toBe("SIGNOFF-001");
      expect(state.transcripts["SESSION-001"].review_status).toBe("reviewed");
      expect(state.sessions[0].therapist_review_status).toBe("reviewed");
      expect(state.sessions[0].notes).toBe("Clinical review sign-off notes");

      expect(result.review_status).toBe("reviewed");
    });
  });

  describe("Mock Mode", () => {
    beforeEach(() => {
      store.setState({ dataMode: "mock" });
    });

    it("updateUtterance operates synchronously and does not call backend", () => {
      const patchSpy = vi.spyOn(api, "patch");

      const result = updateUtterance("SESSION-001", 0, "Local edit", "CHI", {
        expectedVersion: 1
      });

      expect(result).not.toBeInstanceOf(Promise);
      expect(result.text).toBe("Local edit");
      expect(patchSpy).not.toHaveBeenCalled();

      const state = store.getState();
      expect(state.transcriptLines["SESSION-001"][0].text).toBe("Local edit");
    });
  });
});
