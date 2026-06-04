import { store } from "../store/state.js";
import { createTherapistReview, createTranscriptLine } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { detectClinicalReviewFlags, markTranscriptLinesReviewed } from "./transcript-workflow-service.js";
import { createActiveClinicalRepository, isRemoteDataMode } from "../persistence/active-repository.js";
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

  if (isRemoteDataMode(dataMode)) {
    const transcriptId = original.transcript_id || sessionId;
    const repository = createActiveClinicalRepository(dataMode);
    return repository.patchTranscriptLine(transcriptId, lineId, {
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

  if (isRemoteDataMode(dataMode)) {
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
  const featureKeys = [
    "age_months", "total_utterances", "mlu", "mluw", "ttr", "total_words",
    "unintelligible_count", "unintelligible_ratio", "zero_vocalization_count",
    "nonverbal_vocalization_count", "question_ratio", "echolalia_count",
    "echolalia_ratio", "pronoun_reversal_count"
  ];
  
  const medians = {
    "age_months": 48.215, "total_utterances": 135.0, "mlu": 2.38, "mluw": 2.395,
    "ttr": 0.3896, "total_words": 314.5, "unintelligible_count": 9.0,
    "unintelligible_ratio": 0.06435, "zero_vocalization_count": 0.0,
    "nonverbal_vocalization_count": 7.5, "question_ratio": 0.03125,
    "echolalia_count": 2.0, "echolalia_ratio": 0.01335, "pronoun_reversal_count": 0.0
  };
  
  const means = {
    "age_months": 49.3177869, "total_utterances": 143.418033, "mlu": 2.29769672,
    "mluw": 2.40151639, "ttr": 0.366644262, "total_words": 324.860656,
    "unintelligible_count": 12.3196721, "unintelligible_ratio": 0.0968614754,
    "zero_vocalization_count": 0.581967213, "nonverbal_vocalization_count": 19.8770492,
    "question_ratio": 0.0555581967, "echolalia_count": 3.62295082,
    "echolalia_ratio": 0.0214122951, "pronoun_reversal_count": 0.0655737705
  };
  
  const scales = {
    "age_months": 14.1992667, "total_utterances": 72.1617991, "mlu": 1.37620052,
    "mluw": 1.06738829, "ttr": 0.104924007, "total_words": 228.125408,
    "unintelligible_count": 12.034286, "unintelligible_ratio": 0.0960321663,
    "zero_vocalization_count": 2.07182569, "nonverbal_vocalization_count": 27.7221513,
    "question_ratio": 0.0615545644, "echolalia_count": 5.97580898,
    "echolalia_ratio": 0.0287674383, "pronoun_reversal_count": 0.247535555
  };
  
  const coefs = {
    "age_months": 1.78276795, "total_utterances": -0.07146712, "mlu": -0.39394373,
    "mluw": -0.27608502, "ttr": -0.22178841, "total_words": -0.1965565,
    "unintelligible_count": 0.46093466, "unintelligible_ratio": 0.0826481,
    "zero_vocalization_count": -0.25510421, "nonverbal_vocalization_count": 0.4611388,
    "question_ratio": -1.39286885, "echolalia_count": 0.50644538,
    "echolalia_ratio": 0.48021253, "pronoun_reversal_count": -0.53491666
  };
  
  const intercept = 0.31832555;
  
  let z = intercept;
  const contributions = [];
  
  featureKeys.forEach(k => {
    let val = features[k];
    if (val === undefined || val === null || isNaN(val)) {
      val = medians[k];
    }
    const scaled = (val - means[k]) / scales[k];
    const contrib = scaled * coefs[k];
    z += contrib;
    contributions.push({ key: k, value: contrib });
  });
  
  const score = 1.0 / (1.0 + Math.exp(-z));

  const multiclassCoefs = {
    "ASD": { intercept: 1.23930257, age_months: 1.23811430, total_utterances: 0.01925123, mlu: -0.34435076, mluw: -0.22595731, ttr: -0.54580713, total_words: -0.30171761, unintelligible_count: 0.39521484, unintelligible_ratio: 0.12235206, zero_vocalization_count: 0.19276645, nonverbal_vocalization_count: 0.40237295, question_ratio: -1.09344521, echolalia_count: 0.56915281, echolalia_ratio: 0.24874344, pronoun_reversal_count: -0.44519369 },
    "DD": { intercept: -1.13479453, age_months: 1.02134742, total_utterances: 0.05913869, mlu: 0.06479095, mluw: -0.08064159, ttr: 0.65606793, total_words: 0.32108373, unintelligible_count: 0.34958220, unintelligible_ratio: -0.24009617, zero_vocalization_count: -1.06036380, nonverbal_vocalization_count: -0.76784960, question_ratio: 0.86319480, echolalia_count: -0.64516503, echolalia_ratio: 0.34307443, pronoun_reversal_count: 0.35196894 },
    "TD": { intercept: -0.10450804, age_months: -2.25946172, total_utterances: -0.07838991, mlu: 0.27955981, mluw: 0.30659890, ttr: -0.11026080, total_words: -0.01936612, unintelligible_count: -0.74479704, unintelligible_ratio: 0.11774411, zero_vocalization_count: 0.86759735, nonverbal_vocalization_count: 0.36547666, question_ratio: 0.23025042, echolalia_count: 0.07601222, echolalia_ratio: -0.59181787, pronoun_reversal_count: 0.09322475 }
  };

  const zs = {};
  Object.keys(multiclassCoefs).forEach(cls => {
    let cz = multiclassCoefs[cls].intercept;
    featureKeys.forEach(k => {
      let val = features[k];
      if (val === undefined || val === null || isNaN(val)) {
        val = medians[k];
      }
      const scaled = (val - means[k]) / scales[k];
      cz += scaled * (multiclassCoefs[cls][k] ?? 0.0);
    });
    zs[cls] = cz;
  });

  const expSum = Math.exp(zs.ASD) + Math.exp(zs.DD) + Math.exp(zs.TD);
  const diffProbas = {
    ASD: Number((Math.exp(zs.ASD) / expSum).toFixed(2)),
    DD: Number((Math.exp(zs.DD) / expSum).toFixed(2)),
    TD: Number((Math.exp(zs.TD) / expSum).toFixed(2))
  };
  
  // Sort contributions descending (highest positive impact first)
  contributions.sort((a, b) => b.value - a.value);
  const topFeatures = contributions.slice(0, 3).map(c => c.key);
  
  return {
    output_id: `AI-OUTPUT-${String(Math.random()).slice(2, 5)}`,
    model_version: "screening-support-v0.2.1-logistic-regression",
    concern_level: score >= 0.67 ? "moderate_concern" : score >= 0.4 ? "watchful_review" : "low_concern",
    screening_support_score: Number(score.toFixed(2)),
    confidence_interval: null,
    top_contributing_features: topFeatures,
    evidence_items: topFeatures.map(feature => ({
      type: "feature",
      feature_key: feature,
      value: features[feature] ?? null,
      explanation: `${feature} should be interpreted with transcript QA and session context.`
    })),
    differential_probabilities: diffProbas,
    plain_language_explanation:
      "This output highlights speech-language patterns that may warrant closer clinical review. It is not a diagnosis.",
    explanation:
      "Decision-support only. This is not a diagnosis and must be interpreted with qualified clinical judgment."
  };
}
