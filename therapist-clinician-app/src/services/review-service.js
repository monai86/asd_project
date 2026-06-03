import { store } from "../store/state.js";
import { createTherapistReview, createTranscriptLine } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { detectClinicalReviewFlags, markTranscriptLinesReviewed } from "./transcript-workflow-service.js";
import { api } from "./api-client.js";

export class TranscriptLineConflictError extends Error {
  constructor({ lineId, expectedVersion, actualVersion }) {
    super(`Transcript line ${lineId} has version ${actualVersion}; expected ${expectedVersion}.`);
    this.name = "TranscriptLineConflictError";
    this.code = "TRANSCRIPT_LINE_VERSION_CONFLICT";
    this.line_id = lineId;
    this.expected_version = expectedVersion;
    this.actual_version = actualVersion;
  }
}

export function makeTranscriptLineId(sessionId, lineNumber, transcriptId = sessionId) {
  return `${transcriptId}_L${String(lineNumber).padStart(4, "0")}`;
}

export function normalizeTranscriptLineForPersistence(line, { session, transcript, currentUser, now = new Date().toISOString() } = {}) {
  const lineNumber = line.line_number ?? 1;
  const transcriptId = line.transcript_id || transcript?.transcript_id || session?.transcript_id || session?.session_id;
  return createTranscriptLine({
    ...line,
    line_id: line.line_id || makeTranscriptLineId(session?.session_id || line.session_id || transcriptId, lineNumber, transcriptId),
    transcript_id: transcriptId,
    session_id: line.session_id || session?.session_id || transcript?.session_id,
    case_id: line.case_id || session?.case_id || transcript?.case_id,
    owner_user_id: line.owner_user_id || session?.owner_user_id || transcript?.owner_user_id,
    speaker_code: line.speaker,
    utterance_text: line.text,
    version: Number(line.version || 1),
    updated_at: now,
    updated_by_user_id: currentUser?.user_id || line.updated_by_user_id || null
  });
}

export function updateUtterance(sessionId, lineIndex, text, speaker, options = {}) {
  const { currentUser, sessions, transcripts, transcriptLines, extractedFeatureOutputs, aiDecisionOutputs, dataMode } = store.getState();
  const lines = transcriptLines[sessionId];
  if (!lines || !lines[lineIndex]) return null;

  const original = { ...lines[lineIndex] };
  const expectedVersion = options.expectedVersion ?? options.expected_version;
  const actualVersion = Number(original.version || 1);
  const lineId = original.line_id || makeTranscriptLineId(sessionId, original.line_number ?? lineIndex + 1, original.transcript_id);
  if (expectedVersion != null && Number(expectedVersion) !== actualVersion) {
    throw new TranscriptLineConflictError({
      lineId,
      expectedVersion: Number(expectedVersion),
      actualVersion
    });
  }

  if (dataMode === "api") {
    const transcriptId = original.transcript_id || sessionId;
    return api.patch(`/api/transcripts/${transcriptId}/lines/${lineId}`, {
      speaker_code: speaker,
      text: text,
      reviewed: Boolean(options.reviewed),
      interpretation_note: options.interpretation_note || "",
      expected_version: expectedVersion
    }).then(updatedBackendLine => {
      const normalizedLine = createTranscriptLine(updatedBackendLine);
      const { transcriptLines: currentLinesMap, extractedFeatureOutputs: currentFeaturesMap, aiDecisionOutputs: currentAiMap } = store.getState();
      const updatedLines = [...(currentLinesMap[sessionId] || [])];
      updatedLines[lineIndex] = normalizedLine;

      const previousFeatures = currentFeaturesMap[sessionId];
      const previousAiOutput = currentAiMap[sessionId];

      store.setState({
        transcriptLines: {
          ...currentLinesMap,
          [sessionId]: updatedLines
        },
        extractedFeatureOutputs: previousFeatures
          ? {
              ...currentFeaturesMap,
              [sessionId]: {
                ...previousFeatures,
                extraction_status: "stale",
                review_status: "stale",
                stale_reason: "transcript_edited",
                updated_at: new Date().toISOString()
              }
            }
          : currentFeaturesMap,
        aiDecisionOutputs: previousAiOutput
          ? {
              ...currentAiMap,
              [sessionId]: {
                ...previousAiOutput,
                therapist_review_status: "requires_transcript_review",
                explanation: "AI-assisted explanation requires transcript review and feature re-run after transcript edits.",
                updated_at: new Date().toISOString()
              }
            }
          : currentAiMap
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

      return normalizedLine;
    }).catch(err => {
      if (err.status === 409 || (err.payload && err.payload.detail && err.payload.detail.code === "TRANSCRIPT_LINE_VERSION_CONFLICT")) {
        const detail = err.payload.detail;
        throw new TranscriptLineConflictError({
          lineId: detail.line_id || lineId,
          expectedVersion: detail.expected_version,
          actualVersion: detail.actual_version
        });
      }
      throw err;
    });
  }

  const session = sessions.find(item => item.session_id === sessionId);
  const transcript = transcripts[sessionId];
  const now = new Date().toISOString();
  const editedLine = normalizeTranscriptLineForPersistence({
    ...lines[lineIndex],
    line_id: lineId,
    text,
    speaker,
    reviewed: Boolean(options.reviewed),
    review_status: options.reviewed ? "reviewed" : "needs_review",
    interpretation_note: options.interpretation_note || "",
    version: actualVersion + 1
  }, { session, transcript, currentUser, now });
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

  return editedLine;
}

export function saveTranscriptLine(sessionId, lineIndex, patch = {}, options = {}) {
  const { transcriptLines } = store.getState();
  const currentLine = transcriptLines[sessionId]?.[lineIndex];
  if (!currentLine) return null;

  return updateUtterance(
    sessionId,
    lineIndex,
    patch.text ?? currentLine.text,
    patch.speaker ?? currentLine.speaker,
    {
      reviewed: patch.reviewed ?? currentLine.reviewed,
      interpretation_note: patch.interpretation_note ?? currentLine.interpretation_note,
      expectedVersion: options.expectedVersion ?? options.expected_version
    }
  );
}

export function markTranscriptReviewed(sessionId, notes = "") {
  const { currentUser, transcripts, transcriptLines, aiDecisionOutputs, extractedFeatureOutputs } = store.getState();
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
      [sessionId]: markTranscriptLinesReviewed(lines, { currentUser, now })
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
  const { currentUser, sessions, transcripts, clinicalSignoffs = [], dataMode } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");

  if (dataMode === "api") {
    return api.post(`/api/sessions/${sessionId}/transcript/signoff`, { notes }).then(signoff => {
      markTranscriptReviewed(sessionId, notes);

      const { clinicalSignoffs: currentSignoffs, sessions: currentSessions } = store.getState();

      const updatedSessions = currentSessions.map(s =>
        s.session_id === sessionId
          ? {
              ...s,
              therapist_review_status: "reviewed",
              notes: notes,
              report_status: "pending",
              updated_at: new Date().toISOString()
            }
          : s
      );

      store.setState({
        sessions: updatedSessions,
        clinicalSignoffs: [...currentSignoffs, signoff]
      });

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

      addAudit("save_review", "TherapistReview", reviewId, `Therapist saved review for session ${sessionId}`);
      addAudit("clinical_signoff_created", "ClinicalSignoff", signoff.signoff_id, `Created transcript sign-off for session ${sessionId}`);

      return review;
    });
  }

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

  const transcript = transcripts[sessionId];
  const signoff = {
    signoff_id: `SIGNOFF-${String(clinicalSignoffs.length + 1).padStart(3, "0")}`,
    target_type: "transcript",
    target_id: transcript?.transcript_id || sessionId,
    session_id: sessionId,
    case_id: session.case_id,
    owner_user_id: session.owner_user_id,
    signed_by_user_id: currentUser ? currentUser.user_id : "anonymous",
    notes,
    created_at: new Date().toISOString()
  };

  updateSessionStatus(sessionId, {
    therapist_review_status: "reviewed",
    notes: notes,
    report_status: "pending"
  });

  store.setState({
    clinicalSignoffs: [...clinicalSignoffs, signoff]
  });

  addAudit("save_review", "TherapistReview", reviewId, `Therapist saved review for session ${sessionId}`);
  addAudit("clinical_signoff_created", "ClinicalSignoff", signoff.signoff_id, `Created transcript sign-off for session ${sessionId}`);

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
    model_version: "screening-support-v0.2.0",
    concern_level: score >= 0.67 ? "moderate_concern" : score >= 0.4 ? "watchful_review" : "low_concern",
    screening_support_score: Number(score.toFixed(2)),
    confidence_interval: null,
    top_contributing_features: contributions,
    evidence_items: contributions.map(feature => ({
      type: "feature",
      feature_key: feature,
      value: features[feature] ?? null,
      explanation: `${feature} should be interpreted with transcript QA and session context.`
    })),
    plain_language_explanation:
      "This output highlights speech-language patterns that may warrant closer clinical review. It is not a diagnosis.",
    explanation:
      "Decision-support only. This is not a diagnosis and must be interpreted with qualified clinical judgment."
  };
}
