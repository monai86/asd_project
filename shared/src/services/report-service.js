import { createAIReport } from "../models/AIReport.js";
import {
  GUIDELINE_SOURCES,
  SAFETY_PLACEHOLDER,
  getGuidelineSource,
  getReportableFeatureMappings
} from "./guideline-mapping-catalog.js";

export function generateSessionReportFromData({ session, childCase, features, featureRecord = {}, aiOutput, transcript = {}, totalReportsCount, therapistThaiSummary = "", observationReviews = {} }) {
  const reportId = `REPORT-${String(totalReportsCount + 1).padStart(3, "0")}`;
  const title = `Progress Report: ${childCase ? childCase.anonymized_child_code : session.case_id}`;

  const md = buildProgressReportMarkdown(
    childCase,
    [session],
    { [session.session_id]: { ...featureRecord, features } },
    { [session.session_id]: toReportableAiOutput(aiOutput) },
    { [session.session_id]: transcript },
    therapistThaiSummary,
    observationReviews
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

export function buildProgressReportMarkdown(caseItem, childSessions, featuresMap, aiOutputs, transcripts = {}, therapistThaiSummary = "", observationReviews = {}) {
  const reportableAiOutputs = Object.fromEntries(
    Object.entries(aiOutputs || {})
      .map(([sessionId, output]) => [sessionId, toReportableAiOutput(output)])
      .filter(([, output]) => Boolean(output))
  );
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
    const score = formatAiSupportScore(reportableAiOutputs[s.session_id]);
    const transcriptStatus = transcripts[s.session_id]?.review_status || s.therapist_review_status || "not_started";
    const featureStatus = featuresMap[s.session_id]?.extraction_status || "mock/prototype";
    const aiStatus = reportableAiOutputs[s.session_id]?.therapist_review_status || "not_started";
    markdown += `| ${s.session_id} | ${s.session_date} | ${s.session_type.replaceAll("_", " ")} | ${transcriptStatus} | ${featureStatus} | ${score} | ${aiStatus} |\n`;
  });

  markdown += `\n\n## Transcript Quality / Human Review Status\n\n`;
  childSessions.forEach(s => {
    const transcript = transcripts[s.session_id] || {};
    const transcriptStatus = transcript.review_status || s.therapist_review_status || "not_started";
    const isSignedOff = isTranscriptSignedOff(s, transcript);
    markdown += `### Session ${s.session_id}\n`;
    markdown += `- **Transcript version used:** ${formatMarkdownNote(transcript.transcript_id || transcript.version || transcript.source || "current workspace transcript")}\n`;
    markdown += `- **Transcript review status:** ${formatMarkdownNote(transcriptStatus)}\n`;
    markdown += `- **Clinical sign-off status:** ${isSignedOff ? "signed off / reviewed" : "not signed off"}\n`;
    markdown += `- **Report eligibility:** ${isSignedOff ? "eligible for reviewed Progress Report sections" : "draft preview only; guideline-linked interpretation is withheld"}\n\n`;
  });

  markdown += `\n\n## Key Feature Trends\n\n`;
  markdown += `| Session ID | Child Utterances | MLU (words) | TTR (lexical diversity) | Echolalia Ratio |\n`;
  markdown += `|---|---|---|---|---|\n`;

  childSessions.forEach(s => {
    const feat = featuresMap[s.session_id]?.features || {};
    markdown += `| ${s.session_id} | ${feat.total_utterances ?? 0} | ${feat.mlu ?? 0} | ${feat.ttr ?? 0} | ${feat.echolalia_ratio ?? 0} |\n`;
  });

  markdown += `\n\n## Guideline-Linked Interpretation\n\n`;
  childSessions.forEach(s => {
    const transcript = transcripts[s.session_id] || {};
    const isSignedOff = isTranscriptSignedOff(s, transcript);
    markdown += `### Session ${s.session_id}\n`;

    if (!isSignedOff) {
      markdown += `This is a Draft Report Preview. Guideline-linked interpretation is withheld until whole-transcript sign-off is complete.\n\n`;
      return;
    }

    const findings = buildGuidelineFindings(featuresMap[s.session_id]?.features || {});
    if (!findings.length) {
      markdown += `No reportable feature-to-guideline mappings are available for this session yet.\n\n`;
      return;
    }

    markdown += `| Feature | Observed Value | Clinical Construct | Source | Interpretation Boundary |\n`;
    markdown += `|---|---:|---|---|---|\n`;
    findings.forEach(finding => {
      markdown += `| ${formatMarkdownNote(finding.label)} | ${formatMarkdownNote(formatFeatureValue(finding.value))} | ${formatMarkdownNote(finding.clinical_construct)} | ${formatMarkdownNote(finding.source_title)} | ${formatMarkdownNote(finding.interpretation_note)} |\n`;
    });
    markdown += `\n`;
  });

  markdown += `## Guideline Sources Used\n\n`;
  const reportSources = collectGuidelineSources(childSessions, featuresMap, transcripts);
  if (reportSources.length) {
    reportSources.forEach(source => {
      const url = source.source_url && source.source_url !== SAFETY_PLACEHOLDER ? source.source_url : "TODO: verify source";
      markdown += `- **${source.id}:** ${source.title} (${source.source_type}; open access: ${source.is_open_access ? "yes" : "no"}) - ${url}\n`;
    });
  } else {
    markdown += `- No guideline sources are used in report-eligible findings yet.\n`;
  }
  markdown += `\n`;

  markdown += `\n\n## Therapist Session Notes\n\n`;
  childSessions.forEach(s => {
    markdown += `### Session ${s.session_id} (${s.session_date})\n`;
    markdown += `${formatMarkdownNote(s.notes) || "_No therapist notes recorded._"}\n\n`;
    const reviewNotes = Object.entries(observationReviews?.[s.session_id] || {})
      .filter(([, review]) => review?.note || (review?.status && review.status !== "pending"));
    if (reviewNotes.length) {
      markdown += `#### Observation Review Notes\n`;
      reviewNotes.forEach(([key, review]) => {
        const status = formatMarkdownNote(review.status || "pending");
        const note = formatMarkdownNote(review.note || "");
        markdown += `- **${formatMarkdownNote(key)}** (${status})${note ? `: ${note}` : ""}\n`;
      });
      markdown += `\n`;
    }
  });

  markdown += `## AI-Assisted Explanation\n\n`;
  markdown += `Prototype support label: rule-based/mock screening support, not a validated medical model.\n\n`;
  childSessions.forEach(s => {
    const ai = reportableAiOutputs[s.session_id];
    if (ai) {
      markdown += `### Session ${s.session_id} Decision Support:\n`;
      if (isReferenceCohortSimilarityOutput(ai)) {
        markdown += `- **Output Type:** Reviewed Reference Cohort Similarity\n`;
        markdown += `- **Most Similar Reference Cohort:** ${ai.most_similar_reference_cohort || "N/A"}\n`;
        markdown += `- **Reference Cohort Probability:** ${formatProbability(ai.similarity_probability)}\n`;
        markdown += `- **Report Eligibility:** reviewed transcript only\n`;
      } else {
        markdown += `- **Concern Level:** ${String(ai.concern_level || "review_support").replaceAll("_", " ")}\n`;
        markdown += `- **Screening Support Score:** ${ai.screening_support_score}\n`;
        markdown += `- **Confidence Interval:** ${formatConfidenceInterval(ai.confidence_interval)}\n`;
      }
      markdown += `- **Top Contributing Features:** ${(ai.top_contributing_features || []).join(", ")}\n`;
      markdown += `- **Explanation:** ${ai.plain_language_explanation || ai.explanation}\n\n`;
    }
  });

  markdown += `## Evidence Highlights\n\n`;
  childSessions.forEach(s => {
    const ai = reportableAiOutputs[s.session_id];
    const evidence = ai?.evidence_items || [];
    markdown += `### Session ${s.session_id}\n`;
    markdown += evidence.length
      ? evidence.map(item => `- ${formatEvidenceItem(item)}`).join("\n")
      : "- No evidence highlights recorded yet.";
    markdown += `\n\n`;
  });

  markdown += `## บทสรุปทางคลินิกภาษาไทย (Safe Thai Summary)\n\n`;
  markdown += `> [!IMPORTANT]\n`;
  markdown += `> **ข้อความเตือนความปลอดภัยเชิงคลินิก:** ระบบนี้เป็นระบบสนับสนุนการตัดสินใจทางคลินิกจำลองในขั้นวิจัย (Research Prototype) ไม่ใช่เครื่องมือทางการแพทย์และไม่สามารถใช้แทนการวินิจฉัยโรคได้ ผลลัพธ์ทั้งหมดต้องได้รับตรวจทานและแปรผลร่วมโดยนักบำบัดภาษาและบุคลากรทางการแพทย์ที่เชี่ยวชาญ\n\n`;
  if (therapistThaiSummary) {
    markdown += `${therapistThaiSummary}\n\n`;
  } else {
    markdown += `**สรุปแนวโน้มพัฒนาการจากข้อมูลเชิงพรรณนาเบื้องต้น:**\n`;
    markdown += generateAutoThaiSummary(childSessions, featuresMap) + `\n\n`;
  }

  markdown += `## Recommended Follow-Up\n\n`;
  markdown += `Review this report with qualified professionals where appropriate, especially when concern level, transcript QA, consent status, or feature status indicates review priority.\n\n`;
  markdown += `## Limitations and Clinical Caution\n\n`;
  markdown += `- This report is non-diagnostic and cannot confirm or rule out ASD.\n`;
  markdown += `- Guideline-linked findings show construct linkage and review cues only; they do not provide automated normal/abnormal labels.\n`;
  markdown += `- No project-verified Thai thresholds or norms are applied unless explicitly stated.\n`;
  markdown += `- The audio-to-CHAT workflow is experimental and requires therapist transcript review before report-eligible interpretation.\n`;
  markdown += `- Acoustic/prosody values, when present, are exploratory/display-only unless separately validated.\n\n`;
  markdown += `${disclaimerText}\n`;

  return markdown;
}

function toReportableAiOutput(output) {
  if (!output) return null;
  if (!isReferenceCohortSimilarityOutput(output)) return output;
  if (output.inference_status !== "reviewed") return null;
  if (output.report_eligible !== true) return null;
  return output;
}

function isReferenceCohortSimilarityOutput(output) {
  if (!output) return false;
  return (
    output.output_kind === "reference_cohort_similarity" ||
    output.inference_status === "preliminary" ||
    output.inference_status === "reviewed" ||
    Boolean(output.reference_cohort_probabilities) ||
    Boolean(output.most_similar_reference_cohort)
  );
}

function formatAiSupportScore(output) {
  if (!output) return "N/A";
  if (isReferenceCohortSimilarityOutput(output)) {
    const cohort = output.most_similar_reference_cohort || "reference cohort";
    return `${cohort} ${formatProbability(output.similarity_probability)}`;
  }
  return output.screening_support_score ?? "N/A";
}

function formatProbability(value) {
  if (value == null || Number.isNaN(Number(value))) return "N/A";
  return `${Math.round(Number(value) * 100)}%`;
}

function generateAutoThaiSummary(childSessions, featuresMap) {
  if (!childSessions || childSessions.length < 2) {
    return `- ข้อมูลเซสชันไม่เพียงพอสำหรับการวิเคราะห์แนวโน้มพัฒนาการข้ามเซสชัน (ต้องการอย่างน้อย 2 เซสชัน)`;
  }

  const sortedSessions = [...childSessions].sort((a, b) => {
    return new Date(a.session_date || a.date) - new Date(b.session_date || b.date);
  });

  const sessA = sortedSessions[0];
  const sessB = sortedSessions[sortedSessions.length - 1];

  const featA = featuresMap[sessA.session_id]?.features || {};
  const featB = featuresMap[sessB.session_id]?.features || {};

  const mluA = featA.mlu ?? 0;
  const mluB = featB.mlu ?? 0;
  const ttrA = featA.ttr ?? 0;
  const ttrB = featB.ttr ?? 0;
  const echoA = featA.echolalia_ratio ?? 0;
  const echoB = featB.echolalia_ratio ?? 0;

  const mluChange = mluB - mluA;
  const ttrChange = ttrB - ttrA;
  const echoChange = echoB - echoA;

  let mluDesc = "";
  if (mluChange > 0.2) {
    mluDesc = `มีความก้าวหน้าขึ้นในการเพิ่มความยาวประโยคเฉลี่ย (MLU) (เพิ่มขึ้น ${mluChange.toFixed(2)} คำ จากเซสชันแรกที่ ${mluA.toFixed(2)} คำ เป็น ${mluB.toFixed(2)} คำ)`;
  } else if (mluChange < -0.2) {
    mluDesc = `ความยาวประโยคเฉลี่ย (MLU) ลดลงเล็กน้อย (ลดลง ${Math.abs(mluChange).toFixed(2)} คำ จาก ${mluA.toFixed(2)} คำ เป็น ${mluB.toFixed(2)} คำ) ควรติดตามและกระตุ้นการสื่อสารอย่างต่อเนื่อง`;
  } else {
    mluDesc = `ความยาวประโยคเฉลี่ย (MLU) ค่อนข้างคงที่ (อยู่ที่ประมาณ ${mluB.toFixed(2)} คำ)`;
  }

  let ttrDesc = "";
  if (ttrChange > 0.05) {
    ttrDesc = `มีความหลากคำและคลังคำศัพท์ที่กว้างขวางมากขึ้น (TTR เพิ่มขึ้น ${ttrChange.toFixed(2)} จาก ${ttrA.toFixed(2)} เป็น ${ttrB.toFixed(2)})`;
  } else {
    ttrDesc = `ความหลากหลายในการใช้คำศัพท์ค่อนข้างคงที่ (TTR ล่าสุดอยู่ที่ ${ttrB.toFixed(2)})`;
  }

  let echoDesc = "";
  if (echoChange < -0.05) {
    echoDesc = `มีอัตราการพูดซ้ำเลียนแบบ (Echolalia) ลดลงอย่างเห็นได้ชัด (ลดลง ${(Math.abs(echoChange) * 100).toFixed(0)}% จาก ${(echoA * 100).toFixed(0)}% เป็น ${(echoB * 100).toFixed(0)}%) แสดงถึงการตอบสนองที่ตรงวัตถุประสงค์ขึ้น`;
  } else if (echoChange > 0.05) {
    echoDesc = `พบพฤติกรรมการพูดซ้ำเลียนแบบ (Echolalia) เพิ่มขึ้นเล็กน้อย (เพิ่มขึ้น ${(echoChange * 100).toFixed(0)}% จาก ${(echoA * 100).toFixed(0)}% เป็น ${(echoB * 100).toFixed(0)}%) ควรส่งเสริมการพูดตอบโต้ที่เป็นธรรมชาติมากขึ้น`;
  } else {
    echoDesc = `อัตราการพูดซ้ำเลียนแบบค่อนข้างคงที่ (อยู่ที่ประมาณ ${(echoB * 100).toFixed(0)}%)`;
  }

  return `- **แนวโน้มความยาวประโยคเฉลี่ย (MLU Trend):** ${mluDesc}
- **ความหลากหลายของคำศัพท์ (TTR Trend):** ${ttrDesc}
- **พฤติกรรมการสื่อสารเลียนแบบ (Echolalia Trend):** ${echoDesc}`;
}

function formatConfidenceInterval(confidenceInterval) {
  if (!confidenceInterval) return "N/A";
  const lower = confidenceInterval.lower ?? "?";
  const upper = confidenceInterval.upper ?? "?";
  const method = confidenceInterval.method ? ` (${confidenceInterval.method})` : "";
  return `${lower}-${upper}${method}`;
}

function formatEvidenceItem(item) {
  if (typeof item === "string") return item;
  const key = item.feature_key || item.marker_type || item.type || "evidence";
  const value = item.value == null ? "" : ` = ${item.value}`;
  const explanation = item.explanation || "Review with transcript and session context.";
  return `**${key}${value}:** ${explanation}`;
}

function isTranscriptSignedOff(session, transcript = {}) {
  return transcript.review_status === "reviewed" || session?.therapist_review_status === "reviewed";
}

function buildGuidelineFindings(features = {}) {
  const mappings = getReportableFeatureMappings();
  return Object.entries(mappings)
    .filter(([feature]) => features[feature] !== null && features[feature] !== undefined)
    .map(([feature, mapping]) => {
      const source = getGuidelineSource(mapping.source_key) || {};
      return {
        feature,
        label: mapping.label_en || feature,
        value: features[feature],
        clinical_construct: mapping.clinical_construct || "review cue",
        source_id: source.id || SAFETY_PLACEHOLDER,
        source_title: source.title || SAFETY_PLACEHOLDER,
        source_type: source.source_type || "todo_verify_source",
        interpretation_note: mapping.interpretation_note || "No project-verified threshold or norm is available.",
        limitations: mapping.limitations || "Use for clinical review only."
      };
    });
}

function collectGuidelineSources(childSessions, featuresMap, transcripts) {
  const sources = new Map();
  childSessions.forEach(session => {
    if (!isTranscriptSignedOff(session, transcripts[session.session_id] || {})) return;
    buildGuidelineFindings(featuresMap[session.session_id]?.features || {}).forEach(finding => {
      const source = Object.values(GUIDELINE_SOURCES).find(item => item.id === finding.source_id);
      if (source) sources.set(source.id, source);
    });
  });
  return Array.from(sources.values());
}

function formatFeatureValue(value) {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }
  return String(value);
}

function formatMarkdownNote(value) {
  return String(value || "")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\|/g, "\\|")
    .trim();
}
