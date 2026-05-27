import { describe, it, expect } from "vitest";
import { buildProgressReportMarkdown } from "../services/report-service.js";

describe("AI Report Formatting & Safety Review", () => {
  it("should contain disclaimers and exclude diagnostic claims", () => {
    const caseItem = { case_id: "CASE-001", anonymized_child_code: "CHI-A01", age_months: 48, sex: "male" };
    const sessions = [{ session_id: "SESSION-001", session_date: "2026-05-20", session_type: "free_play", notes: "test", therapist_review_status: "reviewed" }];
    const featuresMap = { "SESSION-001": { features: { total_utterances: 10, mlu: 2.5, ttr: 0.6, echolalia_ratio: 0.1 } } };
    const aiOutputs = { "SESSION-001": { concern_level: "low_concern", screening_support_score: 0.35, top_contributing_features: ["mlu"], explanation: "AI-assisted support" } };

    const reportMd = buildProgressReportMarkdown(caseItem, sessions, featuresMap, aiOutputs);

    expect(reportMd).toContain("does not diagnose ASD");
    expect(reportMd).toContain("progress tracking and clinical decision support only");
    
    // Safety check for diagnostic assertions
    const lower = reportMd.toLowerCase();
    expect(lower).not.toContain("diagnosed with");
    expect(lower).not.toContain("definitive diagnosis");
  });
});
