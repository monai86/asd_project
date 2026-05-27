import { store } from "../store/state.js";
import { createTherapistReview } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";

export function updateUtterance(sessionId, lineIndex, text, speaker) {
  const { transcriptLines } = store.getState();
  const lines = transcriptLines[sessionId];
  if (!lines || !lines[lineIndex]) return;

  const original = { ...lines[lineIndex] };
  lines[lineIndex].text = text;
  lines[lineIndex].speaker = speaker;

  store.setState({
    transcriptLines: {
      ...transcriptLines,
      [sessionId]: [...lines]
    }
  });

  addAudit(
    "edit_utterance",
    "Utterance",
    `${sessionId}_L${lineIndex}`,
    `Edited utterance index ${lineIndex} in session ${sessionId}. Speaker changed from ${original.speaker} to ${speaker}, text from "${original.text}" to "${text}"`
  );
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
