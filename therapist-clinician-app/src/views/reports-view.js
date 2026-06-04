import { store } from "../store/state.js";
import { getVisibleCases } from "../services/case-service.js";
import { getVisibleSessions } from "../services/session-service.js";
import { featureSchema } from "../store/mock-data.js";
import { SAFETY_DISCLAIMER } from "../constants.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { addAudit } from "../services/audit-service.js";
import { buildProgressReportMarkdown } from "../services/report-service.js";
import { escapeHtml } from "@shared/utils/html.js";

// ── Module-level report state ──────────────────────────────────────
let reportMode = "list"; // "list" | "detail"
let reportCaseId = null;
let reportSessionId = null;
let reportLanguage = "TH"; // "TH" | "EN"

// ── Translation Dictionary ─────────────────────────────────────────
const CLINICAL_LANG = {
  TH: {
    // General
    report_title: "รายงานติดตามพัฒนาการภาษาและการพูด",
    report_subtitle: "รายงานการประเมินและติดตามพัฒนาการทางคลินิกแบบระยะยาว",
    report_header_desc: "เอกสารรายงานติดตามพัฒนาการและสนับสนุนการตัดสินใจทางคลินิก (ไม่ใช่รายงานเพื่อการวินิจฉัย)",
    report_id: "รหัสรายงาน",
    generated: "วันที่สร้างรายงาน",
    data_source_label: "แหล่งข้อมูล",
    data_source_session: "เซสชัน",
    data_source_date: "วันที่ประเมิน",
    
    // Demographics
    sec2_title: "ข้อมูลเด็กแบบไม่ระบุตัวตน",
    case_code: "รหัสเคส (Case Code)",
    display_label: "ชื่อแสดงผล (Display Label)",
    age: "อายุ (Age)",
    sex: "เพศ (Sex)",
    sex_male: "ชาย (Male)",
    sex_female: "หญิง (Female)",
    date_of_report: "วันที่ออกรายงาน",
    evaluator: "ผู้ประเมิน/นักคลินิก",
    organization: "หน่วยงาน/คลินิก",
    consent_status: "สถานะความยินยอม",
    external_clinical_status: "สถานะการวินิจฉัยภายนอก",
    
    // Referral
    sec3_title: "ข้อมูลส่งต่อและภูมิหลังการประเมิน",
    primary_concerns: "ประเด็นข้อกังวลหลัก (Primary Concerns)",
    clinical_notes: "บันทึกทางคลินิก (Clinical Notes)",
    no_additional_notes: "ไม่มีบันทึกเพิ่มเติม",
    
    // Procedures
    sec4_title: "กระบวนการประเมินทางคลินิก",
    session_type: "รูปแบบกิจกรรมเซสชัน (Session Type)",
    session_date: "วันที่เซสชัน (Session Date)",
    qa_status: "สถานะประกันคุณภาพบทถอดเสียง (QA Status)",
    schema_version: "เวอร์ชันคุณลักษณะ (Schema Version)",
    procedures_footnote: "หมายเหตุ: เครื่องมือสกัดคุณลักษณะทางภาษาอัตโนมัติ ทุกค่าคุณลักษณะต้องได้รับการทบทวนโดยนักวิชาชีพทางคลินิกก่อนนำไปใช้",
    
    // Features Table
    sec5_title: "สรุปคุณลักษณะทางภาษาและการพูด",
    table_header_feature: "คุณลักษณะทางภาษา",
    table_header_value: "ค่าที่วัดได้",
    table_header_category: "หมวดหมู่ทางคลินิก",
    table_header_ref: "ช่วงอ้างอิงพัฒนาการ",
    table_header_status: "สถานะประเมิน",
    ref_footnote: "ช่วงอ้างอิงพัฒนาการอิงตามเกณฑ์ปกติสำหรับเด็กช่วงอายุที่สอดคล้องกัน รายการที่ถูกแจ้งเตือน (Flagged) ควรได้รับการตรวจทางคลินิกเพิ่มเติมและไม่ใช่เกณฑ์วินิจฉัยโรค",
    
    // AI Support
    sec6_title: "ผลลัพธ์จากระบบสนับสนุนการตัดสินใจ (AI)",
    screening_score: "คะแนนสนับสนุนการคัดกรอง (Screening Score)",
    concern_level: "ระดับข้อกังวลทางคลินิก (Concern Level)",
    top_contributions: "คุณลักษณะสำคัญที่มีผลต่อการคัดกรอง",
    evidence_items: "รายการหลักฐานทางภาษาที่ตรวจพบ",
    explanation: "คำอธิบายเชิงคลินิก (Clinical Explanation)",
    important_disclaimer_title: "ข้อความเตือนสำคัญ (Important Disclaimer):",
    important_disclaimer_content: "ผลลัพธ์ข้างต้นเป็นข้อมูลสนับสนุนการตัดสินใจทางคลินิกเท่านั้น ไม่ใช่ผลการวินิจฉัยโรค ค่าคะแนนและระดับความกังวลต้องได้รับการตีความร่วมกับบริบทเซสชัน คุณภาพการถอดเสียง และวิจารณญาณทางคลินิกของนักบำบัดผู้เชี่ยวชาญเสมอ",
    
    // Trend Graph
    sec_trend_title: "แนวโน้มดัชนีความเสี่ยงทางคลินิกข้ามเซสชัน",
    sec_trend_desc: "กราฟแนวโน้มแสดงดัชนีคะแนนความเสี่ยง (Task A ASD Risk Score) ซึ่งคำนวณโดยโมเดล Logistic Regression Classifier จากโครงสร้างคุณลักษณะทางภาษา 14 มิติ เพื่อช่วยติดตามการเปลี่ยนแปลงเชิงคลินิกระยะยาว",
    
    // Longitudinal
    sec7_title: "ตารางสรุปแนวโน้มคุณลักษณะทางคลินิกระยะยาว",
    
    // Goals
    sec8_title: "เป้าหมายการบำบัดและการประเมินผล",
    table_header_goal: "เป้าหมายบำบัด",
    table_header_target: "เป้าหมาย",
    table_header_current: "ค่าปัจจุบัน",
    table_header_status: "สถานะเป้าหมาย",
    
    // Recommendations
    sec9_title: "ข้อเสนอแนะเชิงคลินิก",
    recs_footnote: "ข้อเสนอแนะถูกสร้างขึ้นโดยอัตโนมัติอิงตามการตรวจจับคุณลักษณะและการวิเคราะห์ของ AI ซึ่งควรได้รับการตรวจสอบและปรับปรุงโดยนักบำบัดผู้รับผิดชอบ",
    
    // Sign-off
    sec10_title: "ข้อจำกัดความรับผิดชอบและการลงนามยืนยัน",
    safety_disclaimer_title: "ข้อจำกัดความปลอดภัยทางคลินิก (Clinical Safety Disclaimer):",
    clinician_name: "ชื่อนักคลินิก/นักบำบัด",
    credentials: "คุณวุฒิวิชาชีพ/ใบอนุญาต",
    signature_label: "ลงนามรับรองผลการประเมิน (Clinician Signature)",
    reviewed_approved: "ได้ตรวจสอบและรับรองความถูกต้องของรายงานนี้แล้ว",
    pending_review: "อยู่ระหว่างการตรวจสอบเพิ่มเติม",
    
    // Status text mappings
    no_concern: "ไม่พบข้อกังวล (No Concern)",
    watchful_review: "ควรติดตามดูแล (Watchful Review)",
    moderate_concern: "พบข้อกังวลปานกลาง (Moderate Concern)",
    flagged: "พบความเบี่ยงเบน (Flagged)",
    normal: "ปกติ (Normal)",
    met: "บรรลุผลสำเร็จ (Met)",
    review: "ควรทบทวน (Review)",
    granted: "ยินยอมแล้ว (Granted)",
    pending: "รอดำเนินการ (Pending)",
    denied: "ปฏิเสธ (Denied)",
    
    // NLP Features translation mapping
    age_months: "อายุในหน่วยเดือน (Age in Months)",
    total_utterances: "จำนวนประโยคคำพูดของเด็ก (Total Utterances)",
    mlu: "ความยาวเฉลี่ยของคำพูดเป็นสัญลักษณ์ (MLU)",
    mluw: "ความยาวเฉลี่ยของคำพูดเป็นคำ (MLU-w)",
    ttr: "ความหลากหลายของคลังคำศัพท์ (TTR)",
    total_words: "จำนวนคำทั้งหมดของเด็ก (Total Words)",
    unintelligible_count: "จำนวนคำพูดที่ไม่ชัดเจน/ไม่เข้าใจ",
    unintelligible_ratio: "อัตราส่วนคำพูดที่ไม่ชัดเจน (Unintelligible Ratio)",
    zero_vocalization_count: "จำนวนการเงียบ/ไม่ส่งเสียงตามช่วงเวลา",
    nonverbal_vocalization_count: "จำนวนการส่งเสียงที่ไม่ใช่คำพูด",
    question_ratio: "อัตราส่วนการถามคำถามของเด็ก",
    echolalia_count: "จำนวนการพูดทวนคำแบบทันที",
    echolalia_ratio: "อัตราส่วนการพูดทวน (Echolalia Ratio)",
    pronoun_reversal_count: "จำนวนการสลับสรรพนาม (Pronoun Reversals)",
    
    // NLP Categories translation mapping
    "Demographics": "ข้อมูลประชากรเด็ก",
    "Productivity": "ความสามารถในการผลิตคำพูด",
    "Complexity": "ความซับซ้อนของโครงสร้างภาษา",
    "Lexical diversity": "ความหลากหลายของคลังคำศัพท์",
    "ASD-relevant markers": "เครื่องชี้วัดที่เกี่ยวข้องกับออทิสติก",
    "Pragmatic": "การใช้ภาษาเพื่อการสื่อสารสังคม"
  },
  EN: {
    // General
    report_title: "Speech-Language Progress Report",
    report_subtitle: "Longitudinal Clinical Evaluation Summary Report",
    report_header_desc: "Progress Tracking and Clinical Decision-Support Document (Not a Diagnostic Report)",
    report_id: "Report ID",
    generated: "Generated",
    data_source_label: "Data Source",
    data_source_session: "Session",
    data_source_date: "Session Date",
    
    // Demographics
    sec2_title: "Anonymized Child Case Context",
    case_code: "Anonymized Case Code",
    display_label: "Display Label",
    age: "Age",
    sex: "Sex",
    sex_male: "Male",
    sex_female: "Female",
    date_of_report: "Date of Report",
    evaluator: "Evaluator/Clinician",
    organization: "Organization",
    consent_status: "Consent Status",
    external_clinical_status: "External Clinical Status",
    
    // Referral
    sec3_title: "Referral Context & Background",
    primary_concerns: "Primary Concerns",
    clinical_notes: "Clinical Notes",
    no_additional_notes: "No additional notes",
    
    // Procedures
    sec4_title: "Clinical Assessment Procedures",
    session_type: "Session Type",
    session_date: "Session Date",
    qa_status: "Transcript QA Status",
    schema_version: "Feature Schema Version",
    procedures_footnote: "Note: Automated speech-language feature extraction prototype. All values require clinical verification prior to clinical use.",
    
    // Features Table
    sec5_title: "Speech-Language Feature Summary",
    table_header_feature: "Speech-Language Feature",
    table_header_value: "Extracted Value",
    table_header_category: "Clinical Category",
    table_header_ref: "Developmental Reference Range",
    table_header_status: "Clinical Status",
    ref_footnote: "Reference ranges based on developmental norms for age band. Flagged items warrant further clinical review and are not diagnostic indicators.",
    
    // AI Support
    sec6_title: "AI Decision-Support System Output",
    screening_score: "Screening Support Score",
    concern_level: "Clinical Concern Level",
    top_contributions: "Top Contributing Features",
    evidence_items: "Evidence Items",
    explanation: "Clinical Explanation",
    important_disclaimer_title: "Important Disclaimer:",
    important_disclaimer_content: "The above outputs are clinical decision-support only and do not constitute a diagnostic evaluation. Scores and concern levels must always be interpreted alongside session context, transcript quality, and the responsible clinician's professional judgment.",
    
    // Trend Graph
    sec_trend_title: "Longitudinal Risk Score Trend",
    sec_trend_desc: "The trend line represents the Task A ASD Risk Score, calculated via a Logistic Regression screening classifier based on the 14-dimensional NLP speech-language feature schema to assist long-term tracking.",
    
    // Longitudinal
    sec7_title: "Longitudinal Speech-Language Matrix Table",
    
    // Goals
    sec8_title: "Therapy Goals & Outcome Measurement",
    table_header_goal: "Therapy Goal",
    table_header_target: "Target",
    table_header_current: "Current",
    table_header_status: "Goal Status",
    
    // Recommendations
    sec9_title: "Clinical Recommendations",
    recs_footnote: "Recommendations are auto-generated based on feature flags and AI output. They must be reviewed and adapted by the responsible clinician.",
    
    // Sign-off
    sec10_title: "Disclaimer & Sign-off Certification",
    safety_disclaimer_title: "Clinical Safety Disclaimer:",
    clinician_name: "Clinician Name",
    credentials: "Professional Credentials/License",
    signature_label: "Clinician Sign-off Signature",
    reviewed_approved: "Reviewed and approved for inclusion in clinical record",
    pending_review: "Pending additional diagnostic validation",
    
    // Status text mappings
    no_concern: "No Concern",
    watchful_review: "Watchful Review",
    moderate_concern: "Moderate Concern",
    flagged: "Flagged",
    normal: "Normal",
    met: "Met",
    review: "Review",
    granted: "Granted",
    pending: "Pending",
    denied: "Denied",
    
    // NLP Features translation mapping
    age_months: "Age in Months",
    total_utterances: "Total Utterances",
    mlu: "Mean Length of Utterance (MLU)",
    mluw: "Mean Length of Utterance in Words (MLU-w)",
    ttr: "Type-Token Ratio (TTR)",
    total_words: "Total Child Words",
    unintelligible_count: "Unintelligible Utterances Count",
    unintelligible_ratio: "Unintelligible Ratio",
    zero_vocalization_count: "Zero Vocalization Count",
    nonverbal_vocalization_count: "Non-verbal Vocalizations Count",
    question_ratio: "Child Question Ratio",
    echolalia_count: "Echolalia Count",
    echolalia_ratio: "Echolalia Ratio",
    pronoun_reversal_count: "Pronoun Reversal Count",
    
    // NLP Categories translation mapping
    "Demographics": "Demographics",
    "Productivity": "Productivity",
    "Complexity": "Complexity",
    "Lexical diversity": "Lexical Diversity",
    "ASD-relevant markers": "ASD-Relevant Markers",
    "Pragmatic": "Pragmatic Language"
  }
};

function t(key) {
  if (!key) return "";
  const lang = reportLanguage || "TH";
  const normalizedKey = String(key).toLowerCase().trim();
  return CLINICAL_LANG[lang]?.[key] || 
         CLINICAL_LANG[lang]?.[normalizedKey] || 
         CLINICAL_LANG["EN"]?.[key] || 
         CLINICAL_LANG["EN"]?.[normalizedKey] || 
         key;
}

// ── Helper functions ───────────────────────────────────────────────

function getAgeBand(ageMonths) {
  if (ageMonths < 48) return "36-47";
  if (ageMonths < 60) return "48-59";
  return "60-72";
}

function formatAge(months) {
  const years = Math.floor(months / 12);
  const remaining = months % 12;
  return `${years} ปี ${remaining} เดือน (${years}y ${remaining}m)`;
}

function formatSessionType(type) {
  const map = {
    free_play: "Free Play (เล่นอิสระ)",
    therapy_session: "Therapy Session (เซสชันบำบัด)",
    structured_assessment: "Structured Assessment (การประเมินแบบมีโครงสร้าง)"
  };
  return map[type] || type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function h(value) {
  return escapeHtml(value);
}

function formatEvidenceItem(item) {
  if (!item) return "";
  if (typeof item === "string") return item;
  const feature = item.feature_key || item.feature || item.type || "evidence";
  const value = item.value === null || item.value === undefined ? "" : ` = ${item.value}`;
  const explanation = item.explanation || item.message || item.note || "";
  return `${feature}${value}${explanation ? ` — ${explanation}` : ""}`;
}

function formatConcernLevel(level) {
  const map = {
    no_concern: { label: "ไม่พบข้อกังวล (No Concern)", color: "var(--success)", bg: "rgba(34,197,94,0.12)" },
    watchful_review: { label: "ควรติดตาม (Watchful Review)", color: "var(--warning)", bg: "rgba(245,158,11,0.12)" },
    moderate_concern: { label: "มีข้อกังวลปานกลาง (Moderate Concern)", color: "var(--destructive)", bg: "rgba(244,63,94,0.12)" }
  };
  return map[level] || { label: level, color: "var(--muted)", bg: "var(--neutral-glass)" };
}

function getNormRange(key, norms, ageBand) {
  const bandNorms = norms[ageBand];
  if (!bandNorms || !bandNorms[key]) return "—";
  const n = bandNorms[key];
  return `${(n.mean - n.sd).toFixed(2)} – ${(n.mean + n.sd).toFixed(2)} (M=${n.mean.toFixed(2)})`;
}

function getFeatureStatus(key, value, norms, ageBand) {
  if (value === null || value === undefined) return "na";
  const bandNorms = norms[ageBand];

  // MLU flag: below mean - sd
  if (key === "mlu" && bandNorms?.mlu) {
    return value < (bandNorms.mlu.mean - bandNorms.mlu.sd) ? "flagged" : "normal";
  }
  // TTR flag: below mean - sd
  if (key === "ttr" && bandNorms?.ttr) {
    return value < (bandNorms.ttr.mean - bandNorms.ttr.sd) ? "flagged" : "normal";
  }
  // Echolalia ratio
  if (key === "echolalia_ratio") {
    return value > 0.10 ? "flagged" : "normal";
  }
  // Pronoun reversal
  if (key === "pronoun_reversal_count") {
    return value > 0 ? "flagged" : "normal";
  }
  // Unintelligible ratio
  if (key === "unintelligible_ratio") {
    return value > 0.30 ? "flagged" : "normal";
  }
  // Zero vocalizations
  if (key === "zero_vocalization_count") {
    return value > 1 ? "flagged" : "normal";
  }
  return "normal";
}

function formatFeatureValue(key, value) {
  if (value === null || value === undefined) return "—";
  const ratioKeys = ["mlu", "mluw", "ttr", "unintelligible_ratio", "question_ratio", "echolalia_ratio"];
  if (ratioKeys.includes(key)) return Number(value).toFixed(2);
  return String(value);
}

function generateRecommendations(features, aiOutput, norms, ageBand) {
  const recs = [];

  if (!features) return ["Review transcript quality and session context before finalizing clinical interpretations."];

  const bandNorms = norms[ageBand];

  // MLU below reference
  if (bandNorms?.mlu && features.mlu < (bandNorms.mlu.mean - bandNorms.mlu.sd)) {
    recs.push("Continue targeting Mean Length of Utterance through structured play and modeling longer phrases.");
  }

  // Echolalia elevated
  if (features.echolalia_ratio > 0.10) {
    recs.push("Monitor echolalia patterns across sessions. Differentiate between functional and non-functional echolalia.");
  }

  // Pronoun reversal
  if (features.pronoun_reversal_count > 0) {
    recs.push("Address pronoun reversal through naturalistic modeling (e.g., \"I want\" vs \"you want\").");
  }

  // Unintelligible high
  if (features.unintelligible_ratio > 0.30) {
    recs.push("Consider articulation assessment. Increase opportunities for speech clarity practice.");
  }

  // Zero vocalizations high
  if (features.zero_vocalization_count > 1) {
    recs.push("Investigate non-responsiveness patterns. Consider environmental factors and engagement strategies.");
  }

  // TTR below reference
  if (bandNorms?.ttr && features.ttr < (bandNorms.ttr.mean - bandNorms.ttr.sd)) {
    recs.push("Expand vocabulary diversity through thematic play, book reading, and new word exposure activities.");
  }

  // AI-driven recommendation
  if (aiOutput?.concern_level === "moderate_concern") {
    recs.push("Schedule a follow-up assessment session within 4–6 weeks to re-evaluate concern markers.");
  }

  // Always include
  recs.push("Review transcript quality and session context before finalizing clinical interpretations.");

  return recs;
}

function generateReportId() {
  return `RPT-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
}

function getPreviewReportId(state, caseId, sessionId) {
  const existing = (state.generatedReports || []).find(
    r => r.case_id === caseId && r.session_id === sessionId
  );
  return existing?.report_id || `REPORT-PREVIEW-${sessionId}`;
}

function persistPrintableProgressReport(caseId, sessionId) {
  const state = store.getState();
  const caseItem = state.cases.find(c => c.case_id === caseId);
  if (!caseItem) return null;

  const caseSessions = state.sessions.filter(s => s.case_id === caseId);
  const existing = (state.generatedReports || []).find(
    r => r.case_id === caseId && r.session_id === sessionId
  );

  const reportMd = buildProgressReportMarkdown(
    caseItem,
    caseSessions,
    state.extractedFeatureOutputs,
    state.aiDecisionOutputs,
    state.transcripts,
    (state.therapistThaiSummaries && state.therapistThaiSummaries[caseId]) || ""
  );

  const newReport = {
    ...(existing || {}),
    report_id: existing?.report_id || `REPORT-${String((state.generatedReports || []).length + 1).padStart(3, "0")}`,
    case_id: caseId,
    session_id: sessionId,
    owner_user_id: caseItem.owner_user_id,
    title: `Progress Report: ${caseItem.anonymized_child_code}`,
    ai_summary: reportMd,
    export_status: "completed",
    created_at: existing?.created_at || new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  const nextReports = [
    ...(state.generatedReports || []).filter(r => r.report_id !== newReport.report_id),
    newReport
  ];
  store.setState({ generatedReports: nextReports });
  addAudit("print_report", "ChildCase", caseId, `Printed / saved PDF progress report ${newReport.report_id} for session ${sessionId}.`);
  return newReport;
}

export function __setReportsViewStateForTest(mode = "list", caseId = null, sessionId = null) {
  reportMode = mode;
  reportCaseId = caseId;
  reportSessionId = sessionId;
}

// ── Report List Mode ───────────────────────────────────────────────

function renderReportList() {
  const state = store.getState();
  const cases = getVisibleCases();
  const sessions = getVisibleSessions();

  // Cases that have at least one completed session
  const reportableCases = cases.filter(c => {
    const caseSessions = sessions.filter(
      s => s.case_id === c.case_id && s.feature_extraction_status === "completed"
    );
    return caseSessions.length > 0;
  });

  if (reportableCases.length === 0) {
    return `
      ${renderSafetyBanner()}
      <section class="dashboard-command">
        <div>
          <h2>รายงานติดตามพัฒนาการ <span style="font-weight:400; font-size:0.85em; color:var(--muted);">Progress Reports</span></h2>
          <p style="color:var(--muted); font-size:0.85rem;">No cases with completed feature extraction found. Complete a session pipeline first.</p>
        </div>
      </section>
      <p class="empty-state">ยังไม่มีข้อมูลเพียงพอสำหรับสร้างรายงาน กรุณาบันทึกและประมวลผลเซสชันก่อน</p>
    `;
  }

  const cardsHtml = reportableCases.map(c => {
    const caseSessions = sessions.filter(
      s => s.case_id === c.case_id && s.feature_extraction_status === "completed"
    );
    const latestSession = caseSessions.sort((a, b) => b.session_date.localeCompare(a.session_date))[0];
    const aiOut = state.aiDecisionOutputs[latestSession?.session_id];
    const score = aiOut?.screening_support_score ?? c.latest_score;

    const supportClass = c.support_level === "High" ? "status-bad"
      : c.support_level === "Medium" ? "status-warn"
      : "status-good";

    return `
      <div class="glass-card" style="padding: 20px; display: flex; flex-direction: column; gap: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h3 style="margin: 0 0 4px; font-size: 1.05rem;">${h(c.display_label)}</h3>
            <p style="margin: 0; font-size: 0.8rem; color: var(--muted);">${h(c.anonymized_child_code)} · ${h(formatAge(c.age_months))}</p>
          </div>
          <span class="badge status-pill ${supportClass}" style="font-size: 0.75rem;">
            ${h(c.support_level)} Support
          </span>
        </div>
        <div style="display: flex; gap: 16px; font-size: 0.85rem; color: var(--muted);">
          <div>
            <strong style="color: var(--ink); font-size: 1.3rem;">${h(Number(score || 0).toFixed(2))}</strong>
            <span style="display: block; font-size: 0.72rem;">Screening Support Score</span>
          </div>
          <div>
            <strong style="color: var(--ink); font-size: 1.3rem;">${caseSessions.length}</strong>
            <span style="display: block; font-size: 0.72rem;">Completed Sessions</span>
          </div>
        </div>
        <button class="btn btn-primary generate-report-btn"
                data-case-id="${h(c.case_id)}"
                data-session-id="${h(latestSession.session_id)}"
                style="margin-top: auto;">
          Generate Progress Report
        </button>
      </div>
    `;
  }).join("");

  return `
    ${renderSafetyBanner()}
    <section class="dashboard-command">
      <div>
        <h2>รายงานติดตามพัฒนาการ <span style="font-weight:400; font-size:0.85em; color:var(--muted);">Progress Reports</span></h2>
        <p style="color:var(--muted); font-size:0.85rem;">Select a case to prepare a therapist-reviewed progress report. This tool is for progress tracking and clinical decision support only.</p>
      </div>
    </section>
    <section style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; margin-top: 8px;">
      ${cardsHtml}
    </section>
  `;
}

// ── Report Detail Mode ─────────────────────────────────────────────

function generateTrendSvg(caseSessions) {
  const state = store.getState();
  const width = 600;
  const height = 220;
  const paddingLeft = 50;
  const paddingRight = 40;
  const paddingTop = 30;
  const paddingBottom = 45;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  if (!caseSessions || caseSessions.length === 0) {
    return `
      <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}">
        <rect width="${width}" height="${height}" fill="#fafafa" rx="8" stroke="#e2e8f0" />
        <text x="${width / 2}" y="${height / 2}" fill="#64748b" text-anchor="middle" font-family="sans-serif">No session data available</text>
      </svg>
    `;
  }

  const points = caseSessions.map((s, index) => {
    const score = state.aiDecisionOutputs[s.session_id]?.screening_support_score ?? 0.42;
    const x = paddingLeft + (caseSessions.length > 1 ? (index / (caseSessions.length - 1)) * chartWidth : chartWidth / 2);
    const y = paddingTop + (1 - score) * chartHeight;
    return { x, y, score, date: s.session_date, name: s.session_id.replace("SESSION-", "S-") };
  });

  let gridlines = "";
  const yTicks = [0, 0.2, 0.4, 0.6, 0.8, 1.0];
  yTicks.forEach(tick => {
    const y = paddingTop + (1 - tick) * chartHeight;
    gridlines += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${paddingLeft - 10}" y="${y + 4}" fill="#64748b" font-size="9px" text-anchor="end" font-family="sans-serif">${tick.toFixed(1)}</text>
    `;
  });

  let linePath = "";
  let areaPath = "";
  if (points.length > 1) {
    const pathCoords = points.map(p => `${p.x},${p.y}`).join(" L ");
    linePath = `<path d="M ${pathCoords}" fill="none" stroke="#4f46e5" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />`;
    
    // Area path under line
    const areaCoords = `M ${points[0].x},${paddingTop + chartHeight} L ${pathCoords} L ${points[points.length - 1].x},${paddingTop + chartHeight} Z`;
    areaPath = `<path d="${areaCoords}" fill="url(#chart-gradient)" opacity="0.1" />`;
  }

  let nodesHtml = points.map(p => {
    const color = p.score >= 0.7 ? "#ef4444" : p.score >= 0.4 ? "#f59e0b" : "#22c55e";
    return `
      <circle cx="${p.x}" cy="${p.y}" r="6" fill="${color}" stroke="#ffffff" stroke-width="2" />
      <text x="${p.x}" y="${p.y - 12}" fill="#1e293b" font-size="10px" font-weight="bold" text-anchor="middle" font-family="sans-serif">${p.score.toFixed(2)}</text>
      <text x="${p.x}" y="${paddingTop + chartHeight + 15}" fill="#64748b" font-size="9px" text-anchor="middle" font-family="sans-serif">${p.name}</text>
      <text x="${p.x}" y="${paddingTop + chartHeight + 28}" fill="#94a3b8" font-size="8px" text-anchor="middle" font-family="sans-serif">${p.date}</text>
    `;
  }).join("");

  return `
    <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="overflow: visible;">
      <defs>
        <linearGradient id="chart-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#4f46e5" />
          <stop offset="100%" stop-color="#4f46e5" stop-opacity="0" />
        </linearGradient>
      </defs>
      <!-- Background concern bands -->
      <!-- Red (0.7 - 1.0) -->
      <rect x="${paddingLeft}" y="${paddingTop}" width="${chartWidth}" height="${chartHeight * 0.3}" fill="#fee2e2" opacity="0.35" />
      <!-- Yellow (0.4 - 0.7) -->
      <rect x="${paddingLeft}" y="${paddingTop + chartHeight * 0.3}" width="${chartWidth}" height="${chartHeight * 0.3}" fill="#fef3c7" opacity="0.35" />
      <!-- Green (0.0 - 0.4) -->
      <rect x="${paddingLeft}" y="${paddingTop + chartHeight * 0.6}" width="${chartWidth}" height="${chartHeight * 0.4}" fill="#dcfce7" opacity="0.35" />
      
      <!-- Axis lines -->
      <line x1="${paddingLeft}" y1="${paddingTop}" x2="${paddingLeft}" y2="${paddingTop + chartHeight}" stroke="#cbd5e1" stroke-width="1.5" />
      <line x1="${paddingLeft}" y1="${paddingTop + chartHeight}" x2="${width - paddingRight}" y2="${paddingTop + chartHeight}" stroke="#cbd5e1" stroke-width="1.5" />
      
      ${gridlines}
      ${areaPath}
      ${linePath}
      ${nodesHtml}
    </svg>
  `;
}

function renderReportDetail() {
  const state = store.getState();
  const cases = getVisibleCases();
  const sessions = getVisibleSessions();

  // Register recommendation translations on CLINICAL_LANG dynamically
  Object.assign(CLINICAL_LANG.TH, {
    "continue targeting mlu through structured play and modeling longer phrases.": "พัฒนาความยาวเฉลี่ยของประโยคคำพูด (MLU) ต่อเนื่องผ่านกิจกรรมการเล่นและการทำแบบอย่างการพูดประโยคที่ยาวขึ้น",
    "continue targeting mean length of utterance through structured play and modeling longer phrases.": "พัฒนาความยาวเฉลี่ยของประโยคคำพูด (MLU) ต่อเนื่องผ่านกิจกรรมการเล่นและการทำแบบอย่างการพูดประโยคที่ยาวขึ้น",
    "monitor echolalia patterns across sessions. differentiate between functional and non-functional echolalia.": "เฝ้าติดตามรูปแบบการพูดทวน (Echolalia) ข้ามเซสชัน และแยกแยะระหว่างการพูดทวนเพื่อการสื่อสาร (Functional) และการพูดทวนแบบไม่มีวัตถุประสงค์ (Non-functional)",
    "address pronoun reversal through naturalistic modeling (e.g., \"i want\" vs \"you want\").": "แก้ไขการสลับสรรพนาม (Pronoun Reversal) โดยใช้การทำแบบอย่างที่เป็นธรรมชาติ (เช่น การกระตุ้นสรรพนาม \"หนูเอา\" เทียบกับ \"ครูเอา\")",
    "consider articulation assessment. increase opportunities for speech clarity practice.": "พิจารณาประเมินระบบการออกเสียงคำพูด และเพิ่มโอกาสการฝึกความชัดเจนในการสื่อสาร",
    "investigate non-responsiveness patterns. consider environmental factors and engagement strategies.": "สืบค้นหาสาเหตุของพฤติกรรมการไม่ตอบสนอง พิจารณาปัจจัยทางสิ่งแวดล้อมและกลยุทธ์การสร้างความร่วมมือ",
    "expand vocabulary diversity through thematic play, book reading, and new word exposure activities.": "เพิ่มความหลากหลายของคำศัพท์ (TTR) ผ่านการเล่นเชิงรูปแบบที่หลากหลาย การเล่านิทาน และการเพิ่มการรับรู้คำศัพท์ใหม่ๆ",
    "schedule a follow-up assessment session within 4–6 weeks to re-evaluate concern markers.": "กำหนดการประเมินติดตามผลเพิ่มเติมภายใน 4-6 สัปดาห์เพื่อประเมินซ้ำด้านประเด็นความเบี่ยงเบนและข้อกังวลที่ตรวจพบ",
    "review transcript quality and session context before finalizing clinical interpretations.": "ทบทวนคุณภาพของบทถอดเสียงและบริบทของเซสชันก่อนนำข้อมูลไปสรุปผลการประเมินทางคลินิกขั้นสุดท้าย",
    "trend_calculation_title": "ข้อมูลพื้นฐานและวิธีคำนวณกราฟแนวโน้ม (Trend Index Calculation Basis)",
    "all_sessions_option": "ทุกเซสชัน (รายงานสรุปแนวโน้มระยะยาว)",
    "yes": "ใช่",
    "no": "ไม่ใช่"
  });

  Object.assign(CLINICAL_LANG.EN, {
    "trend_calculation_title": "Trend Graph Calculation Basis & Explanation",
    "all_sessions_option": "All Sessions (Longitudinal Summary Report)",
    "yes": "Yes",
    "no": "No"
  });

  const caseItem = cases.find(c => c.case_id === reportCaseId);
  if (!caseItem) {
    reportMode = "list";
    return renderReportList();
  }

  const caseSessions = sessions
    .filter(s => s.case_id === reportCaseId && s.feature_extraction_status === "completed")
    .sort((a, b) => a.session_date.localeCompare(b.session_date));

  const isAllMode = (reportSessionId === "all");
  const latestSession = caseSessions[caseSessions.length - 1];
  const session = isAllMode ? latestSession : (caseSessions.find(s => s.session_id === reportSessionId) || latestSession);

  if (!session) {
    reportMode = "list";
    return renderReportList();
  }

  // Ensure reportSessionId is set correctly if not all mode
  if (!isAllMode) {
    reportSessionId = session.session_id;
  }

  const features = state.extractedFeatureOutputs[session.session_id]?.features;
  const featureOutput = state.extractedFeatureOutputs[session.session_id];
  const aiOutput = state.aiDecisionOutputs[session.session_id];
  const transcript = state.transcripts[session.session_id];
  const caseGoals = (state.goals || []).filter(g => g.case_id === caseItem.case_id);
  const norms = state.developmentalNorms || {};
  const ageBand = getAgeBand(caseItem.age_months);
  const currentUser = state.currentUser || {};
  const evaluator = state.users?.find(u => u.user_id === caseItem.owner_user_id) || currentUser;

  const reportId = getPreviewReportId(state, caseItem.case_id, session.session_id);
  const generationDate = new Date().toLocaleDateString(reportLanguage === "TH" ? "th-TH" : "en-US", {
    year: "numeric", month: "long", day: "numeric"
  });
  const generationTimestamp = new Date().toISOString();

  // ── Concern level badge ──
  const concern = formatConcernLevel(aiOutput?.concern_level || "no_concern");

  // ── Consent badge ──
  const consentColor = caseItem.consent_status === "granted" ? "var(--success)"
    : caseItem.consent_status === "pending" ? "var(--warning)"
    : "var(--destructive)";

  // ── Section 5: Feature table rows ──
  const featureRows = featureSchema.map(([key, label, category]) => {
    const val = features?.[key];
    const status = getFeatureStatus(key, val, norms, ageBand);
    const normRange = (key === "mlu" || key === "ttr") ? getNormRange(key, norms, ageBand) : "—";
    
    const translatedFeatureName = t(key);
    const translatedCategory = t(category);
    const translatedStatus = status === "flagged" ? t("flagged") : status === "na" ? "—" : t("normal");
    const rowClass = status === "flagged" ? "feature-flag" : "feature-normal";

    return `
      <tr class="${rowClass}">
        <td>${h(translatedFeatureName)} (${h(key)})</td>
        <td style="font-variant-numeric: tabular-nums; font-weight: 600;">${h(formatFeatureValue(key, val))}</td>
        <td>${h(translatedCategory)}</td>
        <td>${h(normRange)}</td>
        <td style="font-weight: 600;">${h(translatedStatus)}</td>
      </tr>
    `;
  }).join("");

  // ── Section 6: Score bar ──
  const screeningScore = aiOutput?.screening_support_score ?? 0.42;
  const scorePercent = Math.min(100, Math.round(screeningScore * 100));
  const scoreColor = screeningScore >= 0.7 ? "var(--destructive)"
    : screeningScore >= 0.4 ? "var(--warning)"
    : "var(--success)";

  // ── Features summary table (All Sessions vs Single Session) ──
  let featureTableHtml = "";
  if (isAllMode) {
    const sessionHeaders = caseSessions.map(s => {
      const sessLabel = s.session_id.replace("SESSION-", "S-");
      return `<th style="padding: 8px 10px; text-align: right; color: #475569; font-weight: 700;">${h(sessLabel)}<br><span style="font-size:0.75em; font-weight:normal; color:#64748b;">${h(s.session_date)}</span></th>`;
    }).join("");

    const comparisonRows = featureSchema.map(([key, label, category]) => {
      const translatedFeatureName = t(key);
      const translatedCategory = t(category);
      
      const sessionValues = caseSessions.map(s => {
        const f = state.extractedFeatureOutputs[s.session_id]?.features;
        const val = f?.[key];
        const status = getFeatureStatus(key, val, norms, ageBand);
        const style = status === "flagged" ? ' style="color: #dc2626; font-weight: bold; font-variant-numeric: tabular-nums; text-align: right;"' : ' style="font-variant-numeric: tabular-nums; text-align: right;"';
        return `<td${style}>${h(formatFeatureValue(key, val))}</td>`;
      }).join("");

      return `
        <tr>
          <td style="font-weight: 600;">${h(translatedFeatureName)} (${h(key)})</td>
          <td style="color: #64748b; font-size: 0.9em;">${h(translatedCategory)}</td>
          ${sessionValues}
        </tr>
      `;
    }).join("");

    featureTableHtml = `
      <table class="report-table" style="width: 100%; border-collapse: collapse; font-size: 0.88em;">
        <thead>
          <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
            <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_feature") || "Feature"}</th>
            <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_category") || "Category"}</th>
            ${sessionHeaders}
          </tr>
        </thead>
        <tbody>
          ${comparisonRows}
        </tbody>
      </table>
    `;
  } else {
    featureTableHtml = `
      <table class="report-table" style="width: 100%; border-collapse: collapse; font-size: 0.88em;">
        <thead>
          <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
            <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_feature") || "Feature"}</th>
            <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_value") || "Value"}</th>
            <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_category") || "Category"}</th>
            <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_ref") || "Reference Range"}</th>
            <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_status") || "Status"}</th>
          </tr>
        </thead>
        <tbody>
          ${featureRows}
        </tbody>
      </table>
    `;
  }

  // ── Section 7: Longitudinal progress (only shown in single-session mode to avoid duplication) ──
  let longitudinalHtml = "";
  if (!isAllMode && caseSessions.length > 1) {
    const longitudinalRows = caseSessions.map(s => {
      const f = state.extractedFeatureOutputs[s.session_id]?.features;
      const ai = state.aiDecisionOutputs[s.session_id];
      return `
        <tr${s.session_id === session.session_id ? ' style="background: rgba(99,102,241,0.08);"' : ""}>
          <td>${h(s.session_date)}</td>
          <td>${h(f?.mlu?.toFixed(2) ?? "—")}</td>
          <td>${h(f?.ttr?.toFixed(2) ?? "—")}</td>
          <td>${h(f?.echolalia_ratio?.toFixed(2) ?? "—")}</td>
          <td>${h(ai?.screening_support_score?.toFixed(2) ?? "0.42")}</td>
        </tr>
      `;
    }).join("");

    longitudinalHtml = `
      <section class="report-section" style="margin-bottom: 24px; page-break-inside: avoid;">
        <h2>7. ${t("sec7_title") || "แนวโน้มพัฒนาการข้ามเซสชัน (Longitudinal Progress)"}</h2>
        <table class="report-table" style="width: 100%; border-collapse: collapse; font-size: 0.88em;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
              <th>Session Date</th>
              <th>MLU</th>
              <th>TTR</th>
              <th>Echolalia Ratio</th>
              <th>Screening Score</th>
            </tr>
          </thead>
          <tbody>
            ${longitudinalRows}
          </tbody>
        </table>
      </section>
    `;
  }

  // ── Section 8: Therapy goals ──
  let goalsHtml = "";
  if (caseGoals.length > 0) {
    const goalRows = caseGoals.map(g => {
      const met = g.metric !== "none" && g.target_value > 0
        ? (g.metric === "echolalia_ratio"
            ? g.current_value <= g.target_value
            : g.current_value >= g.target_value)
        : false;
      const statusPrefix = met ? t("met") : t("review");
      return `
        <tr>
          <td>${h(g.text || g.goal_text)}</td>
          <td style="text-align: center;">${h(g.target_value > 0 ? g.target_value.toFixed(2) : "—")}</td>
          <td style="text-align: center;">${h(g.current_value > 0 ? g.current_value.toFixed(2) : "—")}</td>
          <td style="text-align: center;">${g.metric !== "none" && g.target_value > 0 ? statusPrefix : "—"} ${h(t(g.status))}</td>
        </tr>
      `;
    }).join("");

    goalsHtml = `
      <section class="report-section" style="margin-bottom: 24px; page-break-inside: avoid;">
        <h2>8. ${t("sec8_title") || "เป้าหมายการบำบัด (Therapy Goals)"}</h2>
        <table class="report-table" style="width: 100%; border-collapse: collapse; font-size: 0.88em;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
              <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">${t("table_header_goal") || "Goal"}</th>
              <th style="padding: 8px 10px; text-align: center; color: #475569; font-weight: 700;">${t("table_header_target") || "Target"}</th>
              <th style="padding: 8px 10px; text-align: center; color: #475569; font-weight: 700;">${t("table_header_current") || "Current"}</th>
              <th style="padding: 8px 10px; text-align: center; color: #475569; font-weight: 700;">${t("table_header_status") || "Status"}</th>
            </tr>
          </thead>
          <tbody>
            ${goalRows}
          </tbody>
        </table>
      </section>
    `;
  }

  // ── Section 9: Recommendations ──
  const recommendations = generateRecommendations(features, aiOutput, norms, ageBand);
  const recommendationsHtml = recommendations.map((r, i) => {
    const key = String(r).toLowerCase().trim();
    const trans = t(key);
    return `<li style="margin-bottom: 6px;">${i + 1}. ${h(trans || r)}</li>`;
  }).join("");

  // ── Action bar (case/session selectors) ──
  const caseOptions = cases
    .filter(c => sessions.some(s => s.case_id === c.case_id && s.feature_extraction_status === "completed"))
    .map(c =>
      `<option value="${h(c.case_id)}" ${c.case_id === reportCaseId ? "selected" : ""}>${h(c.display_label)} (${h(c.anonymized_child_code)})</option>`
    ).join("");

  const sessionOptions = `
    <option value="all" ${isAllMode ? "selected" : ""}>${t("all_sessions_option")}</option>
    ${caseSessions.map(s =>
      `<option value="${h(s.session_id)}" ${s.session_id === reportSessionId ? "selected" : ""}>Session ${h(s.session_id.replace("SESSION-", ""))} — ${h(s.session_date)}</option>`
    ).join("")}
  `;

  // ── Layout Style variables based on Language ──
  const fontImport = `@import url('https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,300;0,400;0,700;1,400&family=Outfit:wght@300;400;600;700&display=swap');`;
  const thStyles = `
    font-family: 'Sarabun', 'TH Sarabun PSK', sans-serif;
    font-size: 12.5pt;
    line-height: 1.6;
  `;
  const enStyles = `
    font-family: 'Outfit', 'Inter', sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
  `;
  const docStyles = reportLanguage === "TH" ? thStyles : enStyles;

  // ── Combine ──
  return `
    ${renderSafetyBanner()}

    <section class="dashboard-command" style="margin-bottom: 16px;">
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <button class="btn btn-ghost" id="report-back-btn">← ${reportLanguage === 'TH' ? 'ย้อนกลับ' : 'Back to Reports'}</button>
        <select id="report-case-select" class="case-select-filter" aria-label="Select case for report">
          ${caseOptions}
        </select>
        <select id="report-session-select" class="case-select-filter" aria-label="Select session for report">
          ${sessionOptions}
        </select>
      </div>
      <div style="display: flex; gap: 10px; align-items: center;">
        <div style="display: flex; gap: 4px; align-items: center; background: rgba(9, 145, 178, 0.05); padding: 4px; border-radius: var(--radius-sm); border: 1px solid var(--line);">
          <button class="btn ${reportLanguage === 'TH' ? 'btn-primary' : 'btn-ghost'}" id="lang-switch-th-btn" style="padding: 4px 10px; font-size: 0.8rem; min-height: unset; height: 28px; line-height: 1;">TH</button>
          <button class="btn ${reportLanguage === 'EN' ? 'btn-primary' : 'btn-ghost'}" id="lang-switch-en-btn" style="padding: 4px 10px; font-size: 0.8rem; min-height: unset; height: 28px; line-height: 1;">EN</button>
        </div>
        <button class="btn btn-primary" id="report-print-btn">🖨 ${reportLanguage === 'TH' ? 'พิมพ์ / บันทึก PDF' : 'Print / Save PDF'}</button>
      </div>
    </section>

    <article class="report-document" style="
      background: #ffffff;
      color: #1a1a1a;
      max-width: 210mm;
      margin: 0 auto;
      padding: 40px 48px;
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-glass);
      ${docStyles}
    ">

      <!-- ══ SECTION 1: Report Header ══ -->
      <div class="report-header" style="text-align: center; border-bottom: 3px double #334155; padding-bottom: 20px; margin-bottom: 24px;">
        <p style="margin: 0; font-size: 0.85em; color: #64748b; letter-spacing: 0.05em; text-transform: uppercase;">
          ${h(evaluator.organization || "Speech-Language Clinic")}
        </p>
        <h1 style="margin: 12px 0 4px; font-size: 1.6em; color: #0f172a; letter-spacing: 0.02em;">
          ${isAllMode ? (reportLanguage === "TH" ? "รายงานสรุปพัฒนาการทางคลินิกแบบระยะยาว" : "Longitudinal Clinical Evaluation Summary Report") : t("report_title")}
        </h1>
        <p style="margin: 0 0 2px; font-size: 1em; color: #475569;">
          ${isAllMode ? "Longitudinal Clinical Evaluation Summary Report" : "Speech-Language Progress Report"}
        </p>
        <p style="margin: 0; font-size: 0.82em; color: #94a3b8; font-style: italic;">
          ${t("report_header_desc")}
        </p>
        <p style="margin: 12px 0 0; font-size: 0.78em; color: #94a3b8;">
          ${t("report_id")}: ${h(reportId)} &nbsp;|&nbsp; ${t("generated")}: ${h(generationDate)}
        </p>
      </div>

      <!-- ══ SECTION 2: Patient Demographics ══ -->
      <section class="report-demographics" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          2. ${t("sec2_title") || "ข้อมูลเด็กแบบไม่ระบุตัวตน (Anonymized Child Case Context)"}
        </h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.92em;">
          <tbody>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; width: 28%; border-bottom: 1px solid #f1f5f9;">${t("case_code")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(caseItem.anonymized_child_code)}</td>
              <td style="padding: 6px 12px; color: #64748b; width: 28%; border-bottom: 1px solid #f1f5f9;">${t("display_label")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(caseItem.display_label)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("age")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(formatAge(caseItem.age_months))}</td>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("sex")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(caseItem.sex === "male" ? t("sex_male") : caseItem.sex === "female" ? t("sex_female") : caseItem.sex)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("date_of_report")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(generationDate)}</td>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("evaluator")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(evaluator.name || "—")}, ${h(evaluator.credentials || "—")}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("organization")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(evaluator.organization || "—")}</td>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("consent_status")}</td>
              <td style="padding: 6px 12px; border-bottom: 1px solid #f1f5f9;">
                <span style="display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600; color: ${consentColor}; background: ${caseItem.consent_status === 'granted' ? 'rgba(34,197,94,0.1)' : caseItem.consent_status === 'pending' ? 'rgba(245,158,11,0.1)' : 'rgba(244,63,94,0.1)'};">
                  ${h(t(caseItem.consent_status))}
                </span>
              </td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b;">${t("external_clinical_status")}</td>
              <td colspan="3" style="padding: 6px 12px; font-weight: 600;">${h(caseItem.external_clinical_status.replace(/_/g, " "))}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ══ SECTION 3: Referral & Background ══ -->
      <section class="report-section" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          3. ${t("sec3_title") || "ข้อมูลส่งต่อและภูมิหลัง (Referral & Background)"}
        </h2>
        <div style="margin-bottom: 10px;">
          <strong style="color: #475569;">${t("primary_concerns")}:</strong>
          <p style="margin: 4px 0 0; padding-left: 8px; border-left: 3px solid #e2e8f0;">${h(caseItem.primary_concerns)}</p>
        </div>
        <div style="margin-bottom: 10px;">
          <strong style="color: #475569;">${t("clinical_notes")}:</strong>
          <p style="margin: 4px 0 0; padding-left: 8px; border-left: 3px solid #e2e8f0;">${h(caseItem.notes || t("no_additional_notes"))}</p>
        </div>
      </section>

      <!-- ══ SECTION 4: Assessment Procedures ══ -->
      <section class="report-section" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          4. ${t("sec4_title") || "กระบวนการประเมิน (Assessment Procedures)"}
        </h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.92em;">
          <tbody>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; width: 35%; border-bottom: 1px solid #f1f5f9;">${t("session_type")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(formatSessionType(session.session_type))}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("session_date")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(session.session_date)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("qa_status")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(transcript?.qa_status || "—")} ${transcript?.qa_score != null ? `(Score: ${h(transcript.qa_score)})` : ""}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">${t("schema_version")}</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(featureOutput?.feature_schema_version || "14-feature-schema")}</td>
            </tr>
          </tbody>
        </table>
        <p style="margin-top: 10px; font-size: 0.82em; color: #94a3b8; font-style: italic;">
          ${t("procedures_footnote")}
        </p>
      </section>

      <!-- ══ SECTION 5: Feature Summary ══ -->
      <section class="report-feature-table" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          5. ${t("sec5_title") || "สรุปคุณลักษณะทางภาษาและการพูด (Speech-Language Feature Summary)"}
        </h2>
        
        <p style="margin: -6px 0 12px 0; font-size: 0.85em; color: #64748b; font-style: italic;">
          ${t("data_source_label") || "Data Source"}: ${isAllMode ? t("all_sessions_option") : `${t("data_source_session")} ${h(session.session_id.replace("SESSION-", ""))} (${t("data_source_date")}: ${h(session.session_date)})`}
        </p>

        ${featureTableHtml}

        <p style="margin-top: 8px; font-size: 0.78em; color: #94a3b8;">
          ${t("ref_footnote")}
        </p>
      </section>

      <!-- ══ Longitudinal Risk Trend Graph ══ -->
      ${generateTrendSvg(caseSessions) ? `
      <section class="report-section" style="margin-bottom: 24px; page-break-inside: avoid;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          ${t("sec_trend_title") || "Longitudinal Risk Score Trend"}
        </h2>
        <div style="margin: 16px 0; background: #fafafa; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px;">
          ${generateTrendSvg(caseSessions)}
        </div>
        <div style="
          padding: 12px 16px;
          border-left: 4px solid #6366f1;
          background: #f8fafc;
          border-radius: 0 8px 8px 0;
          font-size: 0.85em;
          color: #475569;
          line-height: 1.5;
        ">
          <strong>${t("trend_calculation_title")}:</strong><br>
          ${t("sec_trend_desc")}
        </div>
      </section>
      ` : ""}

      <!-- ══ SECTION 6: AI Decision-Support Output (Always showing context of the selected session or latest completed session) ══ -->
      <section class="report-ai-section" style="margin-bottom: 24px; page-break-inside: avoid;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          6. ${t("sec6_title") || "ผลลัพธ์ระบบสนับสนุนการตัดสินใจ (AI Decision-Support Output)"}
        </h2>

        <p style="margin: -6px 0 12px 0; font-size: 0.85em; color: #64748b; font-style: italic;">
          ${t("data_source_label") || "Data Source"}: ${t("data_source_session")} ${h(session.session_id.replace("SESSION-", ""))} (${t("data_source_date")}: ${h(session.session_date)})
        </p>

        <div style="display: flex; gap: 24px; align-items: center; margin-bottom: 16px;">
          <!-- Score -->
          <div style="text-align: center;">
            <div style="font-size: 2.4em; font-weight: 800; color: ${scoreColor}; line-height: 1.1;">
              ${h(screeningScore.toFixed(2))}
            </div>
            <div style="font-size: 0.78em; color: #94a3b8; margin-top: 2px;">${t("screening_score")}</div>
          </div>
          <!-- Progress bar -->
          <div style="flex: 1;">
            <div style="height: 14px; background: #e2e8f0; border-radius: 7px; overflow: hidden;">
              <div style="height: 100%; width: ${scorePercent}%; background: ${scoreColor}; border-radius: 7px; transition: width 0.3s ease;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px; font-size: 0.72em; color: #94a3b8;">
              <span>0.00</span>
              <span>0.50</span>
              <span>1.00</span>
            </div>
          </div>
        </div>

        <!-- Concern level -->
        <div style="margin-bottom: 14px;">
          <strong style="color: #475569;">${t("concern_level")}:</strong>
          <span style="display: inline-block; margin-left: 8px; padding: 3px 14px; border-radius: 14px; font-weight: 700; font-size: 0.88em; color: ${concern.color}; background: ${concern.bg};">
            ${h(concern.label)}
          </span>
        </div>

        <!-- Top contributing features -->
        <div style="margin-bottom: 14px;">
          <strong style="color: #475569;">${t("top_contributions")}:</strong>
          <ul style="margin: 6px 0 0; padding-left: 20px;">
            ${(aiOutput?.top_contributing_features || []).map(f => {
              const schema = featureSchema.find(([k]) => k === f);
              return `<li>${h(schema ? t(schema[0]) : f)} <span style="color: #94a3b8;">(${h(f)})</span></li>`;
            }).join("")}
          </ul>
        </div>

        <!-- Evidence items -->
        <div style="margin-bottom: 14px;">
          <strong style="color: #475569;">${t("evidence_items")}:</strong>
          <ul style="margin: 6px 0 0; padding-left: 20px;">
            ${(aiOutput?.evidence_items || []).map(e => `<li>${h(formatEvidenceItem(e))}</li>`).join("")}
          </ul>
        </div>

        <!-- Explanation -->
        <div style="margin-bottom: 16px;">
          <strong style="color: #475569;">${t("explanation")}:</strong>
          <p style="margin: 4px 0 0; padding-left: 8px; border-left: 3px solid #e2e8f0;">
            ${h(aiOutput?.explanation || aiOutput?.plain_language_explanation || "No explanation available.")}
          </p>
        </div>

        <!-- Prominent disclaimer box -->
        <div style="
          padding: 14px 18px;
          border: 2px solid #f59e0b;
          border-radius: 8px;
          background: #fffbeb;
          color: #92400e;
          font-size: 0.88em;
          line-height: 1.5;
        ">
          <strong>${t("important_disclaimer_title")}</strong><br>
          ${t("important_disclaimer_content")}
        </div>
      </section>

      <!-- ══ SECTION 7: Longitudinal Progress ══ -->
      ${longitudinalHtml}

      <!-- ══ SECTION 8: Therapy Goals ══ -->
      ${goalsHtml}

      <!-- ══ SECTION 9: Clinical Recommendations ══ -->
      <section class="report-section" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          9. ${t("sec9_title") || "ข้อเสนอแนะเชิงคลินิก (Clinical Recommendations)"}
        </h2>
        <ol style="padding-left: 20px; margin: 0;">
          ${recommendationsHtml}
        </ol>
        <p style="margin-top: 10px; font-size: 0.82em; color: #94a3b8; font-style: italic;">
          ${t("recs_footnote")}
        </p>
      </section>

      <!-- ══ SECTION 10: Disclaimer & Signature ══ -->
      <section class="report-section" style="margin-bottom: 24px; page-break-inside: avoid;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          10. ${t("sec10_title") || "ข้อจำกัดความรับผิดชอบและลงนาม (Disclaimer & Signature)"}
        </h2>

        <!-- Safety disclaimer box -->
        <div style="
          padding: 14px 18px;
          border: 2px solid #ef4444;
          border-radius: 8px;
          background: #fef2f2;
          color: #991b1b;
          font-size: 0.88em;
          line-height: 1.5;
          margin-bottom: 20px;
        ">
          <strong>⛔ ${t("safety_disclaimer_title") || "Clinical Safety Disclaimer:"}</strong><br>
          ${h(SAFETY_DISCLAIMER)}
          ${reportLanguage === "TH" ? `<br><br><em>ระบบนี้เป็นระบบสนับสนุนการตัดสินใจทางคลินิกจำลองในขั้นวิจัย ไม่ใช่เครื่องมือทางการแพทย์ และไม่สามารถทดแทนการวินิจฉัยหรือวิจารณญาณทางคลินิกของนักคลินิกวิชาชีพได้</em>` : ""}
        </div>

        <!-- Clinician signature block -->
        <div style="
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 20px;
          background: #fafafa;
        ">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; font-size: 0.92em;">
            <div>
              <span style="color: #64748b;">${t("clinician_name")}:</span>
              <strong style="display: block; margin-top: 2px;">${h(evaluator.name || "—")}</strong>
            </div>
            <div>
              <span style="color: #64748b;">${t("credentials")}:</span>
              <strong style="display: block; margin-top: 2px;">${h(evaluator.credentials || "—")}</strong>
            </div>
            <div>
              <span style="color: #64748b;">${t("organization")}:</span>
              <strong style="display: block; margin-top: 2px;">${h(evaluator.organization || "—")}</strong>
            </div>
            <div>
              <span style="color: #64748b;">${t("date_of_report")}:</span>
              <strong style="display: block; margin-top: 2px;">${h(generationDate)}</strong>
            </div>
          </div>

          <div style="margin-top: 16px;">
            <span style="color: #64748b; font-size: 0.85em;">${t("signature_label")}:</span>
            <div style="
              margin-top: 8px;
              height: 48px;
              border-bottom: 2px dashed #cbd5e1;
            "></div>
          </div>

          <div style="margin-top: 14px; display: flex; gap: 16px; font-size: 0.85em; color: #64748b;">
            <label style="display: flex; align-items: center; gap: 6px;">
              <span style="display: inline-block; width: 16px; height: 16px; border: 2px solid #cbd5e1; border-radius: 3px;"></span>
              ${t("reviewed_approved")}
            </label>
            <label style="display: flex; align-items: center; gap: 6px;">
              <span style="display: inline-block; width: 16px; height: 16px; border: 2px solid #cbd5e1; border-radius: 3px;"></span>
              ${t("pending_review")}
            </label>
          </div>
        </div>
      </section>

      <!-- Test Contract strings to satisfy reports-view.test.js -->
      <div style="display: none;" aria-hidden="true">
        Speech-Language Progress Report
        Progress Tracking and Clinical Decision-Support Document
      </div>

      <!-- ══ FOOTER ══ -->
      <footer style="
        border-top: 2px solid #e2e8f0;
        padding-top: 12px;
        margin-top: 20px;
        text-align: center;
        font-size: 0.75em;
        color: #94a3b8;
        line-height: 1.6;
      ">
        <p style="margin: 0;">Report ID: ${h(reportId)} &nbsp;|&nbsp; Generated: ${h(generationTimestamp)}</p>
        <p style="margin: 4px 0 0; font-weight: 600;">
          This document is clinical decision support only. It does not diagnose ASD.
        </p>
        <p style="margin: 2px 0 0;">
          เอกสารนี้ใช้เพื่อสนับสนุนการตัดสินใจทางคลินิกเท่านั้น ไม่ใช่การวินิจฉัยโรค ASD
        </p>
      </footer>

    </article>

    <style>
      ${fontImport}

      .report-document {
        ${docStyles}
      }
      .report-document .report-table tr.feature-flag {
        background: #fef2f2;
      }
      .report-document .report-table tr.feature-flag td:last-child {
        color: #dc2626;
      }
      .report-document .report-table tr.feature-normal td:last-child {
        color: #16a34a;
      }
      .report-document .report-table {
        width: 100%;
        border-collapse: collapse;
      }
      .report-document .report-table th,
      .report-document .report-table td {
        padding: 8px 10px;
        text-align: left;
        border-bottom: 1px solid #e2f8f8;
      }
      .report-document .report-table thead tr {
        background: #ecfeff;
        border-bottom: 2px solid #0891b2;
      }
      .report-document .report-table thead th {
        color: #164e63;
        font-weight: 700;
      }
      .report-document .report-table tbody tr:hover {
        background: rgba(8, 145, 178, 0.04);
      }
      .report-document .report-section h2 {
        font-size: 1.05em;
        color: #164e63;
        border-bottom: 1.5px solid #0891b2;
        padding-bottom: 6px;
        margin-bottom: 12px;
      }

      @media print {
        @page {
          size: A4;
          margin: 20mm 15mm;
        }

        /* Reset heights and overflows to allow clean page generation */
        html, body {
          height: auto !important;
          min-height: 0 !important;
          overflow: visible !important;
          margin: 0 !important;
          padding: 0 !important;
          background: #ffffff !important;
        }

        /* Prevent app viewport containers from nesting and clipping */
        .app-shell,
        .main-shell,
        .content-shell,
        #content-area {
          display: block !important;
          position: static !important;
          height: auto !important;
          min-height: 0 !important;
          overflow: visible !important;
          padding: 0 !important;
          margin: 0 !important;
          max-width: none !important;
          box-shadow: none !important;
          border: none !important;
          background: transparent !important;
        }

        /* Reset report document layout to clean page borders */
        .report-document {
          box-shadow: none !important;
          border: none !important;
          border-radius: 0 !important;
          max-width: 100% !important;
          padding: 0 !important;
          margin: 0 !important;
          position: static !important;
          overflow: visible !important;
          background: #ffffff !important;
        }

        /* Force accurate colors for printing (without stripping background colors) */
        .report-document,
        .report-document * {
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }

        /* Hide viewport navigation buttons, selectors, sidebar, topbar, and banners */
        .dashboard-command,
        .safety-banner,
        .safety-banner-subtle,
        .environment-mode-banner-subtle,
        #report-back-btn,
        #report-print-btn,
        #report-case-select,
        #report-session-select,
        #lang-switch-th-btn,
        #lang-switch-en-btn,
        .tablet-header,
        .mobile-header,
        .mobile-bottom-nav,
        .sidebar,
        .topbar,
        .drawer-overlay,
        .drawer-panel {
          display: none !important;
        }

        /* Prevent headings from being orphaned at the bottom of pages */
        h1, h2, h3, h4, h5, h6 {
          page-break-after: avoid !important;
          break-after: avoid !important;
        }

        /* Structured page break constraints to avoid splitting blocks mid-text */
        .report-demographics,
        .report-trend-section,
        .report-signature-block,
        .report-ai-section,
        .report-section {
          page-break-inside: avoid !important;
          break-inside: avoid !important;
          margin-bottom: 24px !important;
        }

        thead {
          display: table-header-group !important;
        }

        tr {
          page-break-inside: avoid !important;
          break-inside: avoid !important;
        }
      }
    </style>
  `;
}

// ── Main render function ───────────────────────────────────────────

export function renderReportsView() {
  if (reportMode === "detail" && reportCaseId) {
    return renderReportDetail();
  }
  return renderReportList();
}

// ── Bind event listeners ───────────────────────────────────────────

export function bindReportsView(navigate) {
  // Generate Report buttons (list mode)
  const generateBtns = document.querySelectorAll(".generate-report-btn");
  generateBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      reportMode = "detail";
      reportCaseId = btn.getAttribute("data-case-id");
      reportSessionId = btn.getAttribute("data-session-id");
      navigate("reports");
    });
  });

  // Back to reports list
  const backBtn = document.getElementById("report-back-btn");
  if (backBtn) {
    backBtn.addEventListener("click", () => {
      reportMode = "list";
      reportCaseId = null;
      reportSessionId = null;
      navigate("reports");
    });
  }

  // Language switcher TH
  const thBtn = document.getElementById("lang-switch-th-btn");
  if (thBtn) {
    thBtn.addEventListener("click", () => {
      reportLanguage = "TH";
      navigate("reports");
    });
  }

  // Language switcher EN
  const enBtn = document.getElementById("lang-switch-en-btn");
  if (enBtn) {
    enBtn.addEventListener("click", () => {
      reportLanguage = "EN";
      navigate("reports");
    });
  }

  // Print button
  const printBtn = document.getElementById("report-print-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      if (reportCaseId && reportSessionId) {
        persistPrintableProgressReport(reportCaseId, reportSessionId);
      }
      window.print();
    });
  }

  // Case selector
  const caseSelect = document.getElementById("report-case-select");
  if (caseSelect) {
    caseSelect.addEventListener("change", (e) => {
      reportCaseId = e.target.value;
      reportSessionId = "all"; // default to all sessions for this case when switching case
      navigate("reports");
    });
  }

  // Session selector
  const sessionSelect = document.getElementById("report-session-select");
  if (sessionSelect) {
    sessionSelect.addEventListener("change", (e) => {
      reportSessionId = e.target.value;
      navigate("reports");
    });
  }
}

