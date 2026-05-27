const SAFETY_DISCLAIMER =
  "This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.";

export function getSafetyLabels() {
  return [
    "AI-assisted language analysis",
    "clinical decision-support prototype",
    "requires therapist review",
    "does not diagnose ASD",
    "qualified clinical judgment"
  ];
}

export function checkTranscriptQuality(transcriptText, utterances = []) {
  const warnings = [];

  if (!transcriptText || transcriptText.trim().length === 0) {
    warnings.push({
      code: "EMPTY_TRANSCRIPT",
      severity: "error",
      message: "Transcript is empty. Please upload a valid .cha transcript or record audio."
    });
    return { quality: "fail", score: 0, warnings };
  }

  if (!transcriptText.includes("@Begin")) {
    warnings.push({
      code: "MISSING_BEGIN_HEADER",
      severity: "error",
      message: "Missing @Begin header in CHAT transcript."
    });
  }
  if (!transcriptText.includes("@End")) {
    warnings.push({
      code: "MISSING_END_HEADER",
      severity: "error",
      message: "Missing @End footer in CHAT transcript."
    });
  }

  if (utterances.length > 0 && utterances.length < 5) {
    warnings.push({
      code: "SHORT_SAMPLE",
      severity: "warning",
      message: "Short language sample. The transcript has less than 5 utterances, which may reduce analysis reliability."
    });
  }

  const lowConfidence = utterances.filter(u => u.confidence < 0.65);
  if (lowConfidence.length > 0) {
    warnings.push({
      code: "LOW_CONFIDENCE_UTTERANCES",
      severity: "warning",
      message: `Contains ${lowConfidence.length} low-confidence transcription segment(s). Please review and correct labels.`
    });
  }

  const hasErrors = warnings.some(w => w.severity === "error");
  const score = Math.max(0, 100 - warnings.reduce((sum, w) => sum + (w.severity === "error" ? 25 : 10), 0));

  return {
    quality: hasErrors ? "fail" : warnings.length ? "needs_review" : "pass",
    score,
    warnings
  };
}

export function wrapWithDisclaimer(content) {
  return `${content}\n\n---\n**Clinical Safety Warning:** ${SAFETY_DISCLAIMER}`;
}
