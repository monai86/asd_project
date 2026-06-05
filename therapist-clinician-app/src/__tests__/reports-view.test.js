import { beforeEach, describe, expect, it, vi } from "vitest";
import { store } from "../store/state.js";
import { bindReportsView, renderReportsView, __setReportsViewStateForTest } from "../views/reports-view.js";

function seedReportState(overrides = {}) {
  store.persistenceAdapter = null;
  store.setState({
    currentUser: { user_id: "user-test", role: "therapist", name: "Test Clinician" },
    dataMode: "mock",
    cases: [{
      case_id: "CASE-XSS",
      owner_user_id: "user-test",
      display_label: "น้อง<script>alert(1)</script>",
      anonymized_child_code: "CHI-<img src=x onerror=alert(1)>",
      age_months: 48,
      sex: "male",
      primary_concerns: "<b>unsafe concern</b>",
      notes: "<img src=x onerror=alert(1)>",
      external_clinical_status: "under_evaluation",
      consent_status: "granted",
      support_level: "Medium",
      latest_score: 0.42
    }],
    sessions: [{
      session_id: "SESSION-XSS",
      case_id: "CASE-XSS",
      owner_user_id: "user-test",
      session_date: "2026-06-03",
      session_type: "free_play",
      feature_extraction_status: "completed",
      therapist_review_status: "reviewed"
    }],
    transcripts: {
      "SESSION-XSS": {
        qa_status: "pass",
        qa_score: 98
      }
    },
    extractedFeatureOutputs: {
      "SESSION-XSS": {
        feature_schema_version: "14-feature-schema",
        features: {
          total_utterances: 10,
          total_words: 35,
          mlu: 2.5,
          mluw: 2.1,
          ttr: 0.61,
          echolalia_ratio: 0.03,
          pronoun_reversal_count: 0,
          unintelligible_ratio: 0.01,
          zero_vocalization_count: 0
        }
      }
    },
    aiDecisionOutputs: {
      "SESSION-XSS": {
        screening_support_score: 0.42,
        concern_level: "watchful_review",
        top_contributing_features: ["mlu"],
        evidence_items: [{ feature_key: "mlu", value: 2.5, explanation: "<script>alert(2)</script>" }],
        explanation: "<b>unsafe explanation</b>"
      }
    },
    developmentalNorms: {
      "48-59": {
        mlu: { mean: 3.0, sd: 0.4 },
        ttr: { mean: 0.55, sd: 0.1 }
      }
    },
    users: [{ user_id: "user-test", name: "Test Clinician", credentials: "SLP", organization: "Demo Clinic" }],
    goals: [],
    generatedReports: [],
    auditLogs: [],
    therapistThaiSummaries: {},
    ...overrides
  });
  __setReportsViewStateForTest("detail", "CASE-XSS", "SESSION-XSS");
}

describe("Progress Report View", () => {
  beforeEach(() => {
    seedReportState();
  });

  it("renders printable progress reports with escaped clinical text", () => {
    const html = renderReportsView();

    expect(html).toContain("Speech-Language Progress Report");
    expect(html).toContain("Progress Tracking and Clinical Decision-Support Document");
    expect(html).not.toContain("Speech-Language Assessment Report");
    expect(html).not.toContain("<script>alert(1)</script>");
    expect(html).not.toContain("<img src=x onerror=alert(1)>");
    expect(html).not.toContain("<b>unsafe concern</b>");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).toContain("&lt;b&gt;unsafe concern&lt;/b&gt;");
  });

  it("hides preliminary reference cohort similarity from printable report preview", () => {
    seedReportState({
      aiDecisionOutputs: {
        "SESSION-XSS": {
          output_kind: "reference_cohort_similarity",
          inference_status: "preliminary",
          report_eligible: false,
          most_similar_reference_cohort: "ASD",
          similarity_probability: 0.72,
          plain_language_explanation: "PRELIMINARY_REFERENCE_TEXT"
        }
      }
    });

    const html = renderReportsView();

    expect(html).not.toContain("PRELIMINARY_REFERENCE_TEXT");
    expect(html).toContain("No reviewed AI output");
  });

  it("persists and audits printable progress report before printing", () => {
    let printHandler = null;
    const printButton = {
      addEventListener: (event, handler) => {
        if (event === "click") printHandler = handler;
      }
    };

    vi.stubGlobal("document", {
      querySelectorAll: () => [],
      getElementById: (id) => (id === "report-print-btn" ? printButton : null)
    });
    vi.stubGlobal("window", { print: vi.fn() });

    bindReportsView(() => {});
    printHandler();

    const state = store.getState();
    expect(state.generatedReports).toHaveLength(1);
    expect(state.generatedReports[0]).toMatchObject({
      case_id: "CASE-XSS",
      session_id: "SESSION-XSS",
      title: "Progress Report: CHI-<img src=x onerror=alert(1)>",
      export_status: "completed"
    });
    expect(state.auditLogs[0].event_type).toBe("print_report");
    expect(window.print).toHaveBeenCalledTimes(1);

    vi.unstubAllGlobals();
  });
});
