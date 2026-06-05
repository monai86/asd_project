import { describe, expect, it, beforeEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { store } from "../store/state.js";
import {
  mockAiDecisionOutputs,
  mockCases,
  mockExtractedFeatureOutputs,
  mockSessions,
  mockTranscriptRecords,
  mockUsers
} from "../store/mock-data.js";
import { renderDashboard } from "../views/dashboard-view.js";
import { renderCases } from "../views/cases-view.js";
import { renderSessionView } from "../views/session-view.js";
import { buildProgressReportMarkdown } from "../services/report-service.js";
import { buildTranscriptWorkflowArtifacts } from "../services/transcript-workflow-service.js";
import { SAFETY_DISCLAIMER } from "../constants.js";

const unsafePhrases = [
  ["diagnosis", "result"].join(" "),
  ["detected", "autism"].join(" "),
  ["confirmed", "ASD"].join(" "),
  ["prediction", "means", "ASD"].join(" "),
  ["automatic", "diagnosis"].join(" ")
];

function expectUnsafePhrasesAbsent(text) {
  const lower = text.toLowerCase();
  unsafePhrases.forEach(phrase => {
    expect(lower).not.toContain(phrase.toLowerCase());
  });
}

function resetGuardrailState() {
  store.persistenceAdapter = null;
  store.setState({
    currentUser: mockUsers[0],
    cases: mockCases,
    sessions: mockSessions,
    transcripts: mockTranscriptRecords,
    transcriptLines: {},
    extractedFeatureOutputs: mockExtractedFeatureOutputs,
    aiDecisionOutputs: mockAiDecisionOutputs,
    audioFiles: [],
    goals: [],
    notes: [],
    generatedReports: [],
    auditLogs: [],
    selectedCaseId: "CASE-001",
    selectedSessionId: "SESSION-001",
    users: mockUsers,
    dataMode: "mock"
  });
}

describe("safety, privacy, and validation guardrails", () => {
  beforeEach(() => {
    resetGuardrailState();
  });

  it("shows the persistent disclaimer, consent, anonymization, and prototype labels in key therapist UI surfaces", () => {
    const dashboard = renderDashboard();
    const cases = renderCases();
    const session = renderSessionView();
    const combined = `${dashboard}\n${cases}\n${session}`;

    expect(combined).toContain(SAFETY_DISCLAIMER);
    expect(combined).toContain("Consent:");
    expect(combined).toContain("Anonymization:");
    expect(combined).toContain("Prototype support");
    expect(combined).toContain("mock/prototype feature extraction support");
    expectUnsafePhrasesAbsent(combined);
  });

  it("warns when a case lacks completed consent status", () => {
    store.setState({ selectedCaseId: "CASE-002", selectedSessionId: "SESSION-002" });

    expect(renderDashboard()).toContain("Consent status needs review");
    expect(renderCases()).toContain("Consent status needs review");
    expect(renderSessionView()).toContain("Consent status needs review");
  });

  it("keeps unreviewed transcript-derived outputs preliminary", () => {
    const session = mockSessions[0];
    const childCase = mockCases[0];
    const artifacts = buildTranscriptWorkflowArtifacts({
      session,
      childCase,
      transcriptText: "@Begin\n*CHI:\twant car .\n*MOT:\twhich car ?\n@End",
      filename: "sample.cha",
      transcriptCount: 0
    });

    expect(artifacts.transcriptRecord.review_status).toBe("awaiting_review");
    expect(artifacts.featuresSet.extraction_status).toBe("preliminary");
    expect(artifacts.aiOutput.therapist_review_status).toBe("requires_transcript_review");
  });

  it("renders report safety content, evidence highlights, and case ID without full child names", () => {
    const report = buildProgressReportMarkdown(
      mockCases[0],
      [mockSessions[0]],
      mockExtractedFeatureOutputs,
      mockAiDecisionOutputs,
      mockTranscriptRecords
    );

    expect(report).toContain(SAFETY_DISCLAIMER);
    expect(report).toContain("**Case ID:** CASE-001");
    expect(report).toContain("Transcript Review Status");
    expect(report).toContain("Key Feature Trends");
    expect(report).toContain("Therapist Session Notes");
    expect(report).toContain("AI-Assisted Explanation");
    expect(report).toContain("Evidence Highlights");
    expect(report).toContain("qualified professionals");
    expect(report).not.toContain("Jane Smith");
    expectUnsafePhrasesAbsent(report);
  });

  it("keeps the public screening result surface aligned with the shared disclaimer", () => {
    const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
    const index = fs.readFileSync(path.join(root, "public-screening/index.html"), "utf8");
    const results = fs.readFileSync(path.join(root, "public-screening/src/js/results-display.js"), "utf8");
    const pdfExport = fs.readFileSync(path.join(root, "public-screening/src/js/pdf-export.js"), "utf8");

    expect(index).toContain(SAFETY_DISCLAIMER);
    expect(results).toContain(SAFETY_DISCLAIMER);
    expect(pdfExport).toContain(SAFETY_DISCLAIMER);
  });

  it("does not expose diagnostic probability wording in reference similarity surfaces", () => {
    const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
    const forbidden = [
      "ASD Risk Probability",
      "probability of ASD",
      "diagnosis probability",
      "predicted diagnosis"
    ];
    const files = [
      path.join(root, "therapist-clinician-app/src/views/transcript-view.js"),
      path.join(root, "therapist-clinician-app/src/views/reports-view.js"),
      path.join(root, "shared/src/services/report-service.js")
    ];

    for (const file of files) {
      const body = fs.readFileSync(file, "utf8");
      for (const phrase of forbidden) {
        expect(body).not.toContain(phrase);
      }
    }
  });
});
