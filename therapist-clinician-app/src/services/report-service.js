import { store } from "../store/state.js";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { generateSessionReportFromData, buildProgressReportMarkdown } from "@shared/services/report-service.js";

export function generateSessionReport(sessionId) {
  const { sessions, cases, extractedFeatureOutputs, aiDecisionOutputs, generatedReports } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");

  const childCase = cases.find(c => c.case_id === session.case_id);
  const features = extractedFeatureOutputs[sessionId]?.features || {};
  const aiOutput = aiDecisionOutputs[sessionId] || {};

  const newReport = generateSessionReportFromData({
    session,
    childCase,
    features,
    aiOutput,
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
