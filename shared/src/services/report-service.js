import { createAIReport } from "../models/AIReport.js";

export function generateSessionReportFromData({ session, childCase, features, featureRecord = {}, aiOutput, transcript = {}, totalReportsCount }) {
  const reportId = `REPORT-${String(totalReportsCount + 1).padStart(3, "0")}`;
  const title = `Progress Report: ${childCase ? childCase.anonymized_child_code : session.case_id}`;

  const md = buildProgressReportMarkdown(
    childCase,
    [session],
    { [session.session_id]: { ...featureRecord, features } },
    { [session.session_id]: aiOutput },
    { [session.session_id]: transcript }
  );

  return createAIReport({
    report_id: reportId,
    session_id: session.session_id,
    case_id: session.case_id,
    owner_user_id: session.owner_user_id,
    title,
    ai_summary: md,
    export_status: "completed"
  });
}

export function buildProgressReportMarkdown(caseItem, childSessions, featuresMap, aiOutputs, transcripts = {}) {
  const disclaimerText = "This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.";
  const disclaimer = `> [!IMPORTANT]
> **Clinical Decision-Support Statement:** ${disclaimerText} This report is for progress tracking and clinical decision support only, and for clinician review support. All metrics must be interpreted in clinical context by a qualified speech-language professional.`;

  let markdown = `# ASD Clinical Decision-Support Progress Report\n\n`;
  markdown += `## Child Profile Summary\n`;
  markdown += `**Case ID:** ${caseItem?.case_id || "Unknown"}\n`;
  markdown += `**Anonymized Child Code:** ${caseItem?.anonymized_child_code || "Unknown"}\n`;
  markdown += `**Age (months):** ${caseItem?.age_months || "N/A"}\n`;
  markdown += `**Sex:** ${caseItem?.sex || "N/A"}\n`;
  markdown += `**Consent Status:** ${caseItem?.consent_status || "not_recorded"}\n`;
  markdown += `**Anonymization Status:** ${caseItem?.anonymization_status || "needs_review"}\n`;
  markdown += `**Generated At:** ${new Date().toLocaleDateString()}\n\n`;
  if (!caseItem?.consent_status || ["not_recorded", "pending", "declined"].includes(caseItem.consent_status)) {
    markdown += `> Consent status needs review before real clinical upload or interpretation.\n\n`;
  }

  markdown += `${disclaimer}\n\n`;

  markdown += `## Caseload Goals\n`;
  markdown += `- Spontaneous speech sample quality monitoring\n`;
  markdown += `- Progress tracking and clinical decision support only\n\n`;

  markdown += `## Session History & AI Screening Support Scores\n\n`;
  markdown += `| Session ID | Date | Session Type | Transcript Review Status | Feature Status | AI Support Score | AI Support Status |\n`;
  markdown += `|---|---|---|---|---|---|---|\n`;

  childSessions.forEach(s => {
    const score = aiOutputs[s.session_id]?.screening_support_score ?? "N/A";
    const transcriptStatus = transcripts[s.session_id]?.review_status || s.therapist_review_status || "not_started";
    const featureStatus = featuresMap[s.session_id]?.extraction_status || "mock/prototype";
    const aiStatus = aiOutputs[s.session_id]?.therapist_review_status || "not_started";
    markdown += `| ${s.session_id} | ${s.session_date} | ${s.session_type.replaceAll("_", " ")} | ${transcriptStatus} | ${featureStatus} | ${score} | ${aiStatus} |\n`;
  });

  markdown += `\n\n## Key Feature Trends\n\n`;
  markdown += `| Session ID | Child Utterances | MLU (words) | TTR (lexical diversity) | Echolalia Ratio |\n`;
  markdown += `|---|---|---|---|---|\n`;

  childSessions.forEach(s => {
    const feat = featuresMap[s.session_id]?.features || {};
    markdown += `| ${s.session_id} | ${feat.total_utterances ?? 0} | ${feat.mlu ?? 0} | ${feat.ttr ?? 0} | ${feat.echolalia_ratio ?? 0} |\n`;
  });

  markdown += `\n\n## Therapist Session Notes\n\n`;
  childSessions.forEach(s => {
    markdown += `### Session ${s.session_id} (${s.session_date})\n`;
    markdown += `${s.notes || "_No therapist notes recorded._"}\n\n`;
  });

  markdown += `## AI-Assisted Explanation\n\n`;
  markdown += `Prototype support label: rule-based/mock screening support, not a validated medical model.\n\n`;
  childSessions.forEach(s => {
    const ai = aiOutputs[s.session_id];
    if (ai) {
      markdown += `### Session ${s.session_id} Decision Support:\n`;
      markdown += `- **Concern Level:** ${ai.concern_level.replaceAll("_", " ")}\n`;
      markdown += `- **Screening Support Score:** ${ai.screening_support_score}\n`;
      markdown += `- **Top Contributing Features:** ${(ai.top_contributing_features || []).join(", ")}\n`;
      markdown += `- **Explanation:** ${ai.explanation}\n\n`;
    }
  });

  markdown += `## Evidence Highlights\n\n`;
  childSessions.forEach(s => {
    const ai = aiOutputs[s.session_id];
    const evidence = ai?.evidence_items || [];
    markdown += `### Session ${s.session_id}\n`;
    markdown += evidence.length
      ? evidence.map(item => `- ${item}`).join("\n")
      : "- No evidence highlights recorded yet.";
    markdown += `\n\n`;
  });

  markdown += `## Recommended Follow-Up\n\n`;
  markdown += `Review this report with qualified professionals where appropriate, especially when concern level, transcript QA, consent status, or feature status indicates review priority.\n\n`;
  markdown += `${disclaimerText}\n`;

  return markdown;
}
