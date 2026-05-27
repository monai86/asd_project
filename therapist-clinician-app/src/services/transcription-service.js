import { store } from "../store/state.js";
import { MockASRProvider } from "@shared/providers/mock-asr-provider";
import { createTranscript } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { segmentTranscript } from "@shared/services/segmentation-service.js";
import { extractAllFeatures } from "@shared/services/feature-extraction-service.js";
import { generateDecisionSupport } from "./review-service.js"; // or similar helper

const asrProvider = new MockASRProvider();

export async function startTranscription(sessionId, language = "en", speakerCount = null) {
  const { currentUser, sessions, cases } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");

  const childCase = cases.find(c => c.case_id === session.case_id);

  addAudit("transcription_start", "Session", sessionId, `Started ASR transcription for session ${sessionId}`);
  updateSessionStatus(sessionId, { processing_status: "transcribing" });

  try {
    const result = await asrProvider.transcribeAudio({ name: "session_audio.wav" }, language, speakerCount);

    // Segment transcript into utterances (Module 3)
    const utterances = segmentTranscript(result.fullText);

    // Mapped lines for line-by-line view
    const transcriptLines = utterances.map(utt => ({
      speaker: utt.speaker_label === "CHILD" ? "CHI" : (utt.speaker_label === "CAREGIVER" ? "MOT" : "INV"),
      text: utt.text,
      confidence: utt.confidence
    }));

    // Create transcript record
    const transcriptId = `TRANSCRIPT-${String(Object.keys(store.getState().transcripts).length + 1).padStart(3, "0")}`;
    const transcriptRecord = createTranscript({
      transcript_id: transcriptId,
      session_id: sessionId,
      case_id: session.case_id,
      owner_user_id: currentUser ? currentUser.user_id : session.owner_user_id,
      original_filename: "generated_mock.cha",
      transcript_text: result.fullText,
      review_status: "awaiting_review",
      qa_status: "pass",
      qa_score: 100,
      qa_issues: []
    });

    // Extract features (Module 7)
    const featuresSet = extractAllFeatures(utterances, childCase?.age_months || 48);

    // Generate clinical decision support
    const aiOutput = generateDecisionSupport(featuresSet.features);

    // Update store
    const state = store.getState();
    const updatedTranscripts = { ...state.transcripts, [sessionId]: transcriptRecord };
    const updatedTranscriptLines = { ...state.transcriptLines, [sessionId]: transcriptLines };
    const updatedFeatures = { ...state.extractedFeatureOutputs, [sessionId]: featuresSet };
    const updatedAIOutputs = { ...state.aiDecisionOutputs, [sessionId]: aiOutput };

    store.setState({
      transcripts: updatedTranscripts,
      transcriptLines: updatedTranscriptLines,
      extractedFeatureOutputs: updatedFeatures,
      aiDecisionOutputs: updatedAIOutputs
    });

    updateSessionStatus(sessionId, {
      transcript_id: transcriptId,
      processing_status: "transcript_ready",
      feature_extraction_status: "completed",
      ai_analysis_status: "completed",
      therapist_review_status: "awaiting_review"
    });

    // Sync child case latest score
    if (childCase) {
      const updatedCases = state.cases.map(c => {
        if (c.case_id === childCase.case_id) {
          const trend = [...(c.score_trend || []), aiOutput.screening_support_score];
          return {
            ...c,
            latest_score: aiOutput.screening_support_score,
            score_trend: trend,
            updated_at: new Date().toISOString()
          };
        }
        return c;
      });
      store.setState({ cases: updatedCases });
    }

    addAudit("transcription_complete", "Session", sessionId, `Transcription and analysis pipeline complete for session ${sessionId}`);

  } catch (error) {
    updateSessionStatus(sessionId, { processing_status: "failed" });
    addAudit("transcription_failed", "Session", sessionId, `Transcription failed: ${error.message}`);
    throw error;
  }
}
