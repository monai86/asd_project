import { createAIReport } from "../models/AIReport.js";

export function generateSessionReportFromData({ session, childCase, features, aiOutput, totalReportsCount }) {
  const reportId = `REPORT-${String(totalReportsCount + 1).padStart(3, "0")}`;
  const title = `Progress Report: ${childCase ? childCase.anonymized_child_code : session.case_id}`;

  const md = buildProgressReportMarkdown(childCase, [session], { [session.session_id]: { features } }, { [session.session_id]: aiOutput });

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

export function buildProgressReportMarkdown(caseItem, childSessions, featuresMap, aiOutputs) {
  const disclaimer = `> [!IMPORTANT]
> **Clinical Decision-Support Statement:** This is an AI-assisted language analysis report for clinical decision-support and progress tracking and clinical decision support only. It **does not diagnose ASD** and does not replace qualified clinical judgment. All metrics must be interpreted in clinical context by a speech-language professional.`;

  let markdown = `# ASD Clinical Decision-Support Progress Report\n\n`;
  markdown += `**Anonymized Child Code:** ${caseItem?.anonymized_child_code || "Unknown"}\n`;
  markdown += `**Age (months):** ${caseItem?.age_months || "N/A"}\n`;
  markdown += `**Sex:** ${caseItem?.sex || "N/A"}\n`;
  markdown += `**Generated At:** ${new Date().toLocaleDateString()}\n\n`;

  markdown += `${disclaimer}\n\n`;

  markdown += `## Caseload Goals\n`;
  markdown += `- Spontaneous speech sample quality monitoring\n`;
  markdown += `- Progress tracking and clinical decision support only\n\n`;

  markdown += `## Session History & AI Screening Support Scores\n\n`;
  markdown += `| Session ID | Date | Session Type | AI Support Score | Status |\n`;
  markdown += `|---|---|---|---|---|\n`;

  childSessions.forEach(s => {
    const score = aiOutputs[s.session_id]?.screening_support_score ?? "N/A";
    markdown += `| ${s.session_id} | ${s.session_date} | ${s.session_type.replaceAll("_", " ")} | ${score} | ${s.therapist_review_status} |\n`;
  });

  markdown += `\n\n## Extracted Feature Trends\n\n`;
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

  markdown += `## AI Summary & Decision-Support Explanation\n\n`;
  childSessions.forEach(s => {
    const ai = aiOutputs[s.session_id];
    if (ai) {
      markdown += `### Session ${s.session_id} Decision Support:\n`;
      markdown += `- **Concern Level:** ${ai.concern_level.replaceAll("_", " ")}\n`;
      markdown += `- **Score:** ${ai.screening_support_score}\n`;
      markdown += `- **Top Contributing Features:** ${ai.top_contributing_features.join(", ")}\n`;
      markdown += `- **Explanation:** ${ai.explanation}\n\n`;
    }
  });

  return markdown;
}
