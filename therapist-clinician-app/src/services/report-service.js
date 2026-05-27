import { store } from "../store/state.js";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { generateSessionReportFromData, buildProgressReportMarkdown } from "@shared/services/report-service.js";

export function generateSessionReport(sessionId) {
  const { sessions, cases, transcripts, extractedFeatureOutputs, aiDecisionOutputs, generatedReports } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");

  const childCase = cases.find(c => c.case_id === session.case_id);
  const featureRecord = extractedFeatureOutputs[sessionId] || {};
  const features = featureRecord.features || {};
  const aiOutput = aiDecisionOutputs[sessionId] || {};
  const transcript = transcripts[sessionId] || {};

  const newReport = generateSessionReportFromData({
    session,
    childCase,
    features,
    featureRecord,
    aiOutput,
    transcript,
    totalReportsCount: generatedReports.length
  });

  store.setState({
    generatedReports: [...generatedReports, newReport]
  });

  updateSessionStatus(sessionId, { report_status: "completed" });
  addAudit("generate_report", "AIReport", newReport.report_id, `Generated progress report ${newReport.report_id} for session ${sessionId}`);

  return newReport;
}

export { buildProgressReportMarkdown };
