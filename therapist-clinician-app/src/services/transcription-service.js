import { store } from "../store/state.js";
import { MockASRProvider } from "@shared/providers/mock-asr-provider";
import { createTranscript } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { segmentTranscript } from "@shared/services/segmentation-service.js";
import { PROCESSING_MODE } from "../constants.js";
import {
  getProcessingJobStatus,
  mapBackendProcessingResultToFrontend,
  mapBackendJobToProcessingJob,
  processingJobToSessionUpdates,
  submitAudioProcessingJob
} from "./audio-processing-api.js";
import { buildFeatureAndAiOutputs, detectClinicalReviewFlags } from "./transcript-workflow-service.js";
import { api } from "./api-client.js";

const asrProvider = new MockASRProvider();

export async function startTranscription(sessionId, language = "en", speakerCount = null) {
  if (PROCESSING_MODE !== "mock") {
    return startBackendAudioProcessing(sessionId);
  }

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
    const transcriptLines = [];
    utterances.forEach((utt, index) => {
      const line = {
        line_number: index + 1,
        speaker: utt.speaker_label === "CHILD" ? "CHI" : (utt.speaker_label === "CAREGIVER" ? "MOT" : "INV"),
        text: utt.text,
        timing: { start_time: utt.start_time, end_time: utt.end_time },
        confidence: utt.confidence,
        clinical_flags: [],
        review_status: "needs_review",
        reviewed: false,
        interpretation_note: ""
      };
      line.clinical_flags = detectClinicalReviewFlags(line, index > 0 ? transcriptLines[index - 1] : null);
      transcriptLines.push(line);
    });

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

    const { featuresSet, aiOutput } = buildFeatureAndAiOutputs({
      session: {
        ...session,
        owner_user_id: currentUser ? currentUser.user_id : session.owner_user_id
      },
      childCase,
      transcriptLines,
      reviewed: false
    });

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
      feature_extraction_status: "preliminary",
      ai_analysis_status: "requires_transcript_review",
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

export async function startBackendAudioProcessing(sessionId) {
  const { sessions, dataMode } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");
  if (!session.audio_file_id) {
    throw new Error("Audio file metadata is required before submitting backend processing.");
  }

  addAudit("backend_processing_submit", "Session", sessionId, `Submitted backend audio processing request for session ${sessionId}`);
  updateSessionStatus(sessionId, { processing_status: "processing_submitted" });

  let job;
  if (dataMode === "api") {
    job = await api.post(`/api/sessions/${sessionId}/process-audio`, { audio_file_id: session.audio_file_id });
  } else {
    job = await submitAudioProcessingJob(sessionId, session.audio_file_id);
  }

  if (job.status === "not_configured") {
    updateSessionStatus(sessionId, { processing_status: "failed" });
    addAudit("backend_processing_unavailable", "Session", sessionId, job.message);
    throw new Error(job.message);
  }

  updateSessionStatus(sessionId, {
    processing_status: "processing",
    processing_job_id: job.job_id || job.id
  });
  return applyProcessingJobUpdate(mapBackendJobToProcessingJob(job));
}

export async function pollProcessingJobStatus(jobId) {
  const { dataMode } = store.getState();

  let payload;
  if (dataMode === "api") {
    payload = await api.get(`/api/jobs/${jobId}`);
  } else {
    payload = await getProcessingJobStatus(jobId);
  }

  const job = mapBackendJobToProcessingJob(payload);
  const result = applyProcessingJobUpdate(job);

  if (job.status === "completed" && job.session_id && dataMode === "api") {
    const sessionId = job.session_id;
    const [transcript, features, aiOutput, qa] = await Promise.all([
      api.get(`/api/sessions/${sessionId}/transcript`),
      api.get(`/api/sessions/${sessionId}/features`),
      api.get(`/api/sessions/${sessionId}/ai-output`),
      api.get(`/api/sessions/${sessionId}/qa`)
    ]);
    applyBackendProcessingResult(sessionId, {
      transcript,
      features,
      ai_screening_output: aiOutput,
      qa
    });
  }

  return result;
}

export function applyProcessingJobUpdate(job) {
  const state = store.getState();
  const existingJobs = state.processingJobs || [];
  store.setState({
    processingJobs: [
      ...existingJobs.filter(item => item.job_id !== job.job_id),
      job
    ]
  });
  updateSessionStatus(job.session_id, processingJobToSessionUpdates(job));
  if (job.status === "failed") {
    addAudit(
      "backend_processing_failed",
      "ProcessingJob",
      job.job_id,
      job.error_message || `Backend audio processing failed at ${job.stage}.`
    );
  }
  return job;
}

export function applyBackendProcessingResult(sessionId, backendPayload) {
  const state = store.getState();
  const session = state.sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");
  const childCase = state.cases.find(c => c.case_id === session.case_id);
  const mapped = mapBackendProcessingResultToFrontend(backendPayload, {
    session,
    childCase,
    currentUser: state.currentUser,
    transcriptCount: Object.keys(state.transcripts || {}).length
  });

  store.setState({
    transcripts: {
      ...state.transcripts,
      [sessionId]: mapped.transcriptRecord
    },
    transcriptLines: {
      ...state.transcriptLines,
      [sessionId]: mapped.transcriptLines
    },
    extractedFeatureOutputs: {
      ...state.extractedFeatureOutputs,
      [sessionId]: mapped.featuresSet
    },
    aiDecisionOutputs: mapped.aiOutput
      ? {
          ...state.aiDecisionOutputs,
          [sessionId]: mapped.aiOutput
        }
      : state.aiDecisionOutputs
  });

  updateSessionStatus(sessionId, mapped.sessionUpdates);
  addAudit(
    "backend_transcript_generated",
    "Session",
    sessionId,
    "Backend audio-to-CHAT result mapped for therapist review."
  );

  return mapped;
}
