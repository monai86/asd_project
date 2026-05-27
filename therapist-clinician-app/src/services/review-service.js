import { store } from "../store/state.js";
import { createTherapistReview } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { detectClinicalReviewFlags, markTranscriptLinesReviewed } from "./transcript-workflow-service.js";

export function updateUtterance(sessionId, lineIndex, text, speaker, options = {}) {
  const { transcriptLines, extractedFeatureOutputs, aiDecisionOutputs } = store.getState();
  const lines = transcriptLines[sessionId];
  if (!lines || !lines[lineIndex]) return;

  const original = { ...lines[lineIndex] };
  const editedLine = {
    ...lines[lineIndex],
    text,
    speaker,
    reviewed: Boolean(options.reviewed),
    review_status: options.reviewed ? "reviewed" : "needs_review",
    interpretation_note: options.interpretation_note || ""
  };
  editedLine.clinical_flags = detectClinicalReviewFlags(editedLine, lines[lineIndex - 1]);
  const updatedLines = [...lines];
  updatedLines[lineIndex] = editedLine;

  const previousFeatures = extractedFeatureOutputs[sessionId];
  const previousAiOutput = aiDecisionOutputs[sessionId];

  store.setState({
    transcriptLines: {
      ...transcriptLines,
      [sessionId]: updatedLines
    },
    extractedFeatureOutputs: previousFeatures
      ? {
          ...extractedFeatureOutputs,
          [sessionId]: {
            ...previousFeatures,
            extraction_status: "stale",
            review_status: "stale",
            stale_reason: "transcript_edited",
            updated_at: new Date().toISOString()
          }
        }
      : extractedFeatureOutputs,
    aiDecisionOutputs: previousAiOutput
      ? {
          ...aiDecisionOutputs,
          [sessionId]: {
            ...previousAiOutput,
            therapist_review_status: "requires_transcript_review",
            explanation: "AI-assisted explanation requires transcript review and feature re-run after transcript edits.",
            updated_at: new Date().toISOString()
          }
        }
      : aiDecisionOutputs
  });

  updateSessionStatus(sessionId, {
    feature_extraction_status: previousFeatures ? "stale" : "not_started",
    ai_analysis_status: previousAiOutput ? "requires_transcript_review" : "not_started",
    therapist_review_status: "awaiting_review"
  });

  addAudit(
    "edit_utterance",
    "Utterance",
    `${sessionId}_L${lineIndex}`,
    `Edited utterance index ${lineIndex} in session ${sessionId}. Speaker changed from ${original.speaker} to ${speaker}, text from "${original.text}" to "${text}"`
  );
}

export function markTranscriptReviewed(sessionId, notes = "") {
  const { transcripts, transcriptLines, aiDecisionOutputs, extractedFeatureOutputs } = store.getState();
  const transcriptRecord = transcripts[sessionId];
  const lines = transcriptLines[sessionId] || [];
  if (!transcriptRecord) throw new Error("Transcript not found");

  const now = new Date().toISOString();
  const updatedFeatures = extractedFeatureOutputs[sessionId]
    ? {
        ...extractedFeatureOutputs[sessionId],
        review_status: extractedFeatureOutputs[sessionId].extraction_status === "stale" ? "stale" : "reviewed",
        updated_at: now
      }
    : null;
  const updatedAiOutput = aiDecisionOutputs[sessionId]
    ? {
        ...aiDecisionOutputs[sessionId],
        therapist_review_status:
          updatedFeatures?.extraction_status === "stale" ? "requires_feature_rerun" : "awaiting_review",
        updated_at: now
      }
    : null;

  store.setState({
    transcripts: {
      ...transcripts,
      [sessionId]: {
        ...transcriptRecord,
        review_status: "reviewed",
        reviewer_notes: notes,
        updated_at: now
      }
    },
    transcriptLines: {
      ...transcriptLines,
      [sessionId]: markTranscriptLinesReviewed(lines)
    },
    extractedFeatureOutputs: updatedFeatures
      ? { ...extractedFeatureOutputs, [sessionId]: updatedFeatures }
      : extractedFeatureOutputs,
    aiDecisionOutputs: updatedAiOutput
      ? { ...aiDecisionOutputs, [sessionId]: updatedAiOutput }
      : aiDecisionOutputs
  });
}

export function saveTherapistReview({ sessionId, notes, approvedSummary = "", rejectedReason = "" }) {
  const { currentUser, sessions } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");

  const reviewId = `REV-${String(Math.random()).slice(2, 6)}`;
  const review = createTherapistReview({
    review_id: reviewId,
    session_id: sessionId,
    reviewer_id: currentUser ? currentUser.user_id : "anonymous",
    review_status: "reviewed",
    therapist_notes: notes,
    approved_summary: approvedSummary,
    rejected_summary_reason: rejectedReason
  });

  markTranscriptReviewed(sessionId, notes);

  updateSessionStatus(sessionId, {
    therapist_review_status: "reviewed",
    notes: notes,
    report_status: "pending"
  });

  addAudit("save_review", "TherapistReview", reviewId, `Therapist saved review for session ${sessionId}`);

  return review;
}

export function generateDecisionSupport(features) {
  const markerLoad =
    (features.unintelligible_ratio || 0) * 0.22 +
    Math.min(features.echolalia_ratio || 0, 1) * 0.2 +
    Math.min(features.zero_vocalization_count || 0, 4) * 0.035;
  const languageSupport = Math.max(0, 0.22 - Math.min(features.mlu || 0, 5) * 0.025);
  const score = Math.min(0.9, Math.max(0.12, 0.38 + markerLoad + languageSupport));

  const contributions = [
    ["unintelligible_ratio", features.unintelligible_ratio || 0],
    ["echolalia_ratio", features.echolalia_ratio || 0],
    ["zero_vocalization_count", (features.zero_vocalization_count || 0) / 4],
    ["mlu", Math.max(0, 3.5 - (features.mlu || 0)) / 3.5],
    ["ttr", Math.max(0, 0.55 - (features.ttr || 0))]
  ]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([key]) => key);

  return {
    output_id: `AI-OUTPUT-${String(Math.random()).slice(2, 5)}`,
    concern_level: score >= 0.67 ? "moderate_concern" : score >= 0.4 ? "watchful_review" : "low_concern",
    screening_support_score: Number(score.toFixed(2)),
    top_contributing_features: contributions,
    evidence_items: contributions.map(
      feature => `${feature} should be interpreted with transcript QA and session context.`
    ),
    explanation:
      "Decision-support only. This is not a diagnosis and must be interpreted with qualified clinical judgment."
  };
}
