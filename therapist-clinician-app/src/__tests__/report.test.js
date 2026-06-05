import { describe, it, expect } from "vitest";
import { buildProgressReportMarkdown } from "../services/report-service.js";

describe("AI Report Formatting & Safety Review", () => {
  it("should contain disclaimers and exclude diagnostic claims", () => {
    const caseItem = { case_id: "CASE-001", anonymized_child_code: "CHI-A01", age_months: 48, sex: "male" };
    const sessions = [{ session_id: "SESSION-001", session_date: "2026-05-20", session_type: "free_play", notes: "test", therapist_review_status: "reviewed" }];
    const featuresMap = { "SESSION-001": { features: { total_utterances: 10, mlu: 2.5, ttr: 0.6, echolalia_ratio: 0.1 } } };
    const aiOutputs = {
      "SESSION-001": {
        concern_level: "low_concern",
        screening_support_score: 0.35,
        confidence_interval: null,
        top_contributing_features: ["mlu"],
        plain_language_explanation: "This output highlights speech-language patterns for review. It is not a diagnosis.",
        explanation: "AI-assisted support",
        evidence_items: [{
          type: "feature",
          feature_key: "mlu",
          value: 2.5,
          explanation: "Mean length of utterance should be reviewed in context."
        }]
      }
    };

    const reportMd = buildProgressReportMarkdown(caseItem, sessions, featuresMap, aiOutputs);

    expect(reportMd).toContain("does not diagnose ASD");
    expect(reportMd).toContain("Confidence Interval");
    expect(reportMd).toContain("mlu = 2.5");
    expect(reportMd).toContain("progress tracking and clinical decision support only");
    
    // Safety check for diagnostic assertions
    const lower = reportMd.toLowerCase();
    expect(lower).not.toContain("diagnosed with");
    expect(lower).not.toContain(["definitive", "diagnosis"].join(" "));
  });

  it("excludes preliminary reference cohort similarity from reports", () => {
    const caseItem = { case_id: "CASE-001", anonymized_child_code: "CHI-A01", age_months: 48, sex: "male" };
    const sessions = [{ session_id: "SESSION-001", session_date: "2026-05-20", session_type: "free_play", notes: "test", therapist_review_status: "awaiting_review" }];
    const featuresMap = { "SESSION-001": { features: { total_utterances: 10, mlu: 2.5, ttr: 0.6, echolalia_ratio: 0.1 } } };
    const aiOutputs = {
      "SESSION-001": {
        output_kind: "reference_cohort_similarity",
        inference_status: "preliminary",
        report_eligible: false,
        most_similar_reference_cohort: "ASD",
        similarity_probability: 0.72,
        screening_support_score: 0.72,
        plain_language_explanation: "PRELIMINARY_REFERENCE_TEXT"
      }
    };

    const reportMd = buildProgressReportMarkdown(caseItem, sessions, featuresMap, aiOutputs);

    expect(reportMd).not.toContain("PRELIMINARY_REFERENCE_TEXT");
    expect(reportMd).not.toContain("Reviewed Reference Cohort Similarity");
    expect(reportMd).toContain("| SESSION-001 | 2026-05-20 | free play | awaiting_review | mock/prototype | N/A | not_started |");
  });

  it("includes reviewed report-eligible reference cohort similarity in reports", () => {
    const caseItem = { case_id: "CASE-001", anonymized_child_code: "CHI-A01", age_months: 48, sex: "male" };
    const sessions = [{ session_id: "SESSION-001", session_date: "2026-05-20", session_type: "free_play", notes: "test", therapist_review_status: "reviewed" }];
    const featuresMap = { "SESSION-001": { features: { total_utterances: 10, mlu: 2.5, ttr: 0.6, echolalia_ratio: 0.1 } } };
    const aiOutputs = {
      "SESSION-001": {
        output_kind: "reference_cohort_similarity",
        inference_status: "reviewed",
        report_eligible: true,
        therapist_review_status: "reviewed",
        most_similar_reference_cohort: "ASD",
        similarity_probability: 0.62,
        top_contributing_features: ["mluw"],
        plain_language_explanation: "Reviewed reference cohort comparison for clinician review.",
        evidence_items: [{ feature_key: "mluw", value: 2.1, explanation: "Review utterance length in context." }]
      }
    };

    const reportMd = buildProgressReportMarkdown(caseItem, sessions, featuresMap, aiOutputs);

    expect(reportMd).toContain("Reviewed Reference Cohort Similarity");
    expect(reportMd).toContain("Most Similar Reference Cohort:** ASD");
    expect(reportMd).toContain("Reference Cohort Probability:** 62%");
    expect(reportMd).toContain("Reviewed reference cohort comparison for clinician review.");
    expect(reportMd).not.toContain("diagnosed with");
  });
});
