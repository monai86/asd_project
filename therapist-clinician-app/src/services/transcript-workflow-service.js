import { extractAllFeatures } from "@shared/services/feature-extraction-service.js";
import { checkTranscriptQuality } from "@shared/services/safety-service.js";
import { createTranscript } from "@shared/models";
import { generateDecisionSupport } from "./review-service.js";

export const SUPPORTED_SPEAKER_TIERS = ["CHI", "MOT", "FAT", "INV", "CLI", "PAR"];
export const CORE_14_FEATURE_KEYS = [
  "age_months",
  "total_utterances",
  "mlu",
  "mluw",
  "ttr",
  "total_words",
  "unintelligible_count",
  "unintelligible_ratio",
  "zero_vocalization_count",
  "nonverbal_vocalization_count",
  "question_ratio",
  "echolalia_count",
  "echolalia_ratio",
  "pronoun_reversal_count"
];

function speakerToRole(speaker) {
  if (speaker === "CHI") return "CHILD";
  if (["MOT", "FAT", "PAR"].includes(speaker)) return "CAREGIVER";
  if (["INV", "CLI"].includes(speaker)) return "THERAPIST";
  return "UNKNOWN";
}

function stripTimingMarkers(text) {
  return text
    .replace(/\u0015\d+_\d+\u0015/g, "")
    .replace(/\[(?:time|t)=?[^\]]+\]/gi, "")
    .trim();
}

function extractTiming(text) {
  const chatTiming = text.match(/\u0015(\d+)_(\d+)\u0015/);
  if (chatTiming) {
    return {
      raw: chatTiming[0],
      start_time: Number(chatTiming[1]) / 1000,
      end_time: Number(chatTiming[2]) / 1000
    };
  }

  const bracketTiming = text.match(/\[(?:time|t)=?([0-9.]+)[-_ ]+([0-9.]+)\]/i);
  if (bracketTiming) {
    return {
      raw: bracketTiming[0],
      start_time: Number(bracketTiming[1]),
      end_time: Number(bracketTiming[2])
    };
  }

  return null;
}

export function detectClinicalReviewFlags(line, previousLine = null) {
  const flags = [];
  const text = line.text || "";
  const lower = text.toLowerCase();

  if (/\b(?:xxx|yyy)\b/i.test(text)) {
    flags.push({
      marker_type: "unintelligible_marker",
      explanation: "Contains xxx/yyy unintelligible marker; review audio or context before interpretation."
    });
  }
  if (/&=[A-Za-zก-๙_-]+/.test(text)) {
    flags.push({
      marker_type: "nonverbal_vocalization",
      explanation: "Contains a nonverbal vocalization marker such as laugh, mumble, squeal, or grunt."
    });
  }
  if (text.includes("[/]")) {
    flags.push({
      marker_type: "repetition_marker",
      explanation: "Contains a CHAT repetition marker that may affect repeated-language feature review."
    });
  }
  if (line.speaker === "CHI" && /\b(\w+)\b[\s,.!?]+\1\b/i.test(lower)) {
    flags.push({
      marker_type: "possible_echolalia_like_repetition",
      explanation: "Child utterance repeats a word; review as a possible echolalia-like pattern."
    });
  }
  if (line.speaker === "CHI" && previousLine?.speaker !== "CHI") {
    const previousWords = new Set((previousLine?.text || "").toLowerCase().split(/\s+/).map(w => w.replace(/[.,?!]/g, "")).filter(Boolean));
    const currentWords = lower.split(/\s+/).map(w => w.replace(/[.,?!]/g, "")).filter(Boolean);
    const overlap = currentWords.filter(word => previousWords.has(word));
    if (overlap.length > 0 && currentWords.length <= 4) {
      flags.push({
        marker_type: "possible_echolalia_like_repetition",
        explanation: "Child utterance overlaps with the preceding adult line; review transcript context."
      });
    }
  }
  if (line.speaker === "CHI" && /^(you|your)\s+(want|like|need|have|go|play)\b/i.test(text.trim())) {
    flags.push({
      marker_type: "possible_pronoun_reversal",
      explanation: "Child utterance may contain a pronoun reversal pattern; confirm speaker and context."
    });
  }
  if (line.speaker === "CHI" && text.includes("?")) {
    flags.push({
      marker_type: "child_question",
      explanation: "Child question detected; review pragmatic context."
    });
  }
  if (line.speaker === "CHI" && /^(0|0\s+\.)$/.test(text.trim())) {
    flags.push({
      marker_type: "zero_spoken_response",
      explanation: "Zero spoken response marker detected; review activity context."
    });
  }

  return flags.map(flag => ({
    ...flag,
    line_number: line.line_number,
    speaker: line.speaker,
    text: line.text,
    reviewed: false,
    interpretation_note: ""
  }));
}

export function parseChatTranscript(chatText) {
  const metadata = [];
  const transcriptLines = [];
  const rawLines = String(chatText || "").split(/\r?\n/);

  rawLines.forEach((rawLine, index) => {
    const lineNumber = index + 1;
    const trimmed = rawLine.trim();
    if (!trimmed) return;

    if (trimmed.startsWith("@")) {
      metadata.push({ line_number: lineNumber, text: trimmed });
      return;
    }

    const match = trimmed.match(/^\*([A-Z]{3}):\s*(.*)$/);
    if (!match) return;

    const speaker = match[1].toUpperCase();
    if (!SUPPORTED_SPEAKER_TIERS.includes(speaker)) return;

    const rawText = match[2] || "";
    const timing = extractTiming(rawText);
    const line = {
      line_number: lineNumber,
      speaker,
      text: stripTimingMarkers(rawText),
      timing,
      confidence: 1.0,
      clinical_flags: [],
      review_status: "needs_review",
      reviewed: false,
      interpretation_note: ""
    };
    line.clinical_flags = detectClinicalReviewFlags(line, transcriptLines[transcriptLines.length - 1]);
    transcriptLines.push(line);
  });

  return { metadata, transcriptLines };
}

export function transcriptLinesToUtterances(transcriptLines) {
  return transcriptLines.map((line, index) => {
    const startTime = line.timing?.start_time ?? index * 2.0;
    const endTime = line.timing?.end_time ?? startTime + 1.5;
    return {
      utterance_id: `UTT-${String(index + 1).padStart(3, "0")}`,
      session_id: line.session_id,
      speaker_label: speakerToRole(line.speaker),
      text: line.text,
      start_time: startTime,
      end_time: endTime,
      duration: Number((endTime - startTime).toFixed(2)),
      word_count: line.text.split(/\s+/).filter(Boolean).length,
      confidence: line.confidence ?? 1.0
    };
  });
}

export function extractCore14Features(features = {}) {
  return CORE_14_FEATURE_KEYS.reduce((rows, key) => {
    rows[key] = features[key] ?? 0;
    return rows;
  }, {});
}

export function buildFeatureAndAiOutputs({ session, childCase, transcriptLines, reviewed = false }) {
  const utterances = transcriptLinesToUtterances(transcriptLines);
  const rawFeatureSet = extractAllFeatures(utterances, childCase?.age_months || 48);
  const extractionStatus = reviewed ? "completed" : "preliminary";
  const featuresSet = {
    ...rawFeatureSet,
    session_id: session.session_id,
    case_id: session.case_id,
    owner_user_id: session.owner_user_id,
    features: extractCore14Features(rawFeatureSet.features),
    extraction_status: extractionStatus,
    review_status: extractionStatus,
    created_at: new Date().toISOString()
  };
  const aiOutput = {
    ...generateDecisionSupport(featuresSet.features),
    session_id: session.session_id,
    case_id: session.case_id,
    owner_user_id: session.owner_user_id,
    therapist_review_status: reviewed ? "awaiting_review" : "requires_transcript_review",
    explanation: reviewed
      ? "AI-assisted explanation must be interpreted with qualified clinical judgment."
      : "AI-assisted explanation requires transcript review before clinical interpretation.",
    created_at: new Date().toISOString()
  };

  return { featuresSet, aiOutput };
}

export function buildTranscriptWorkflowArtifacts({ session, childCase, transcriptText, filename, transcriptCount = 0 }) {
  const { metadata, transcriptLines } = parseChatTranscript(transcriptText);
  const validation = checkTranscriptQuality(transcriptText, transcriptLines);
  const transcriptId = `TRANSCRIPT-${String(transcriptCount + 1).padStart(3, "0")}`;
  const transcriptRecord = {
    ...createTranscript({
      transcript_id: transcriptId,
      session_id: session.session_id,
      case_id: session.case_id,
      owner_user_id: session.owner_user_id,
      original_filename: filename,
      transcript_text: transcriptText,
      review_status: "awaiting_review",
      qa_status: validation.quality,
      qa_score: validation.score,
      qa_issues: validation.warnings,
      reviewer_notes: "Transcript requires therapist review before clinical interpretation."
    }),
    chat_metadata: metadata,
    review_required: true
  };
  const { featuresSet, aiOutput } = buildFeatureAndAiOutputs({
    session,
    childCase,
    transcriptLines,
    reviewed: false
  });

  return {
    validation,
    transcriptRecord,
    transcriptLines,
    featuresSet,
    aiOutput,
    sessionUpdates: {
      transcript_id: transcriptId,
      processing_status: "transcript_ready",
      feature_extraction_status: "preliminary",
      ai_analysis_status: "requires_transcript_review",
      therapist_review_status: "awaiting_review"
    }
  };
}

export function markTranscriptLinesReviewed(transcriptLines) {
  return transcriptLines.map(line => ({
    ...line,
    reviewed: true,
    review_status: "reviewed",
    clinical_flags: (line.clinical_flags || []).map(flag => ({
      ...flag,
      reviewed: true
    }))
  }));
}

export function buildEvidenceItems(transcriptLines, aiOutput = {}) {
  const flagItems = transcriptLines.flatMap((line, lineIndex) =>
    (line.clinical_flags || []).map((flag, flagIndex) => ({
      line_index: lineIndex,
      flag_index: flagIndex,
      line_number: line.line_number,
      speaker: line.speaker,
      utterance_text: line.text,
      marker_type: flag.marker_type,
      explanation: flag.explanation,
      reviewed: flag.reviewed || false,
      interpretation_note: flag.interpretation_note || ""
    }))
  );

  const featureItems = (aiOutput.top_contributing_features || []).map(feature => ({
    line_index: null,
    flag_index: null,
    line_number: null,
    speaker: "feature",
    utterance_text: "",
    marker_type: feature,
    explanation: `${feature} contributes to screening support and should be reviewed with transcript context.`,
    reviewed: false,
    interpretation_note: ""
  }));

  return [...flagItems, ...featureItems];
}
