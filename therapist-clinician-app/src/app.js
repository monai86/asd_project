const MOCK_MODE = true;
const MAX_FILE_SIZE_MB = 250;
const ALLOWED_FILE_TYPES = ["wav", "mp3", "m4a", "mp4", "mov"];
const ALLOWED_TRANSCRIPT_FILE_TYPES = ["cha"];
const SAFETY_DISCLAIMER =
  "This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.";

const users = [
  {
    user_id: "user_therapist_001",
    name: "Jane Smith",
    credentials: "M.S., CCC-SLP",
    email: "therapist@example.test",
    password: "demo-password",
    role: "therapist",
    organization: "Mock Speech Clinic",
    created_at: "2026-05-01T09:00:00Z",
    last_login: null,
  },
  {
    user_id: "user_clinician_001",
    name: "Ben Clinician",
    credentials: "Clinical Reviewer",
    email: "clinician@example.test",
    password: "demo-password",
    role: "clinician",
    organization: "Mock Speech Clinic",
    created_at: "2026-05-01T09:00:00Z",
    last_login: null,
  },
  {
    user_id: "user_admin_001",
    name: "Research Admin",
    credentials: "Prototype Admin",
    email: "admin@example.test",
    password: "demo-password",
    role: "admin",
    organization: "Prototype Admin",
    created_at: "2026-05-01T09:00:00Z",
    last_login: null,
  },
];

let cases = [
  {
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-A01",
    display_label: "Case A",
    age_months: 56,
    sex: "male",
    primary_concerns: "Delayed expressive language, limited eye contact, repetitive phrases.",
    external_clinical_status: "under_evaluation",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "Moderate",
    latest_score: 0.68,
    score_trend: [0.58, 0.44, 0.55, 0.52, 0.60, 0.68],
    starred: true,
    notes: "Mock case. No real child identifiers.",
    created_at: "2026-05-02T09:00:00Z",
    updated_at: "2026-05-05T13:20:00Z",
  },
  {
    case_id: "CASE-002",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-A02",
    display_label: "Case B",
    age_months: 60,
    sex: "not_specified",
    primary_concerns: "Transcript review pending after a therapy session.",
    external_clinical_status: "not_provided",
    consent_status: "pending",
    anonymization_status: "anonymized",
    support_level: "Low",
    latest_score: 0.41,
    score_trend: [0.46, 0.43, 0.39, 0.41],
    starred: false,
    notes: "Mock case. Consent reminder needed before real upload.",
    created_at: "2026-05-03T09:00:00Z",
    updated_at: "2026-05-06T10:00:00Z",
  },
  {
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    anonymized_child_code: "CHI-B01",
    display_label: "Case C",
    age_months: 54,
    sex: "not_specified",
    primary_concerns: "Monitoring language sample quality over repeated sessions.",
    external_clinical_status: "external_non_asd_recorded",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "Needs review",
    latest_score: 0.57,
    score_trend: [0.52, 0.54, 0.57],
    starred: false,
    notes: "Mock case for clinician role visibility.",
    created_at: "2026-05-04T09:00:00Z",
    updated_at: "2026-05-07T14:00:00Z",
  },
];

let sessions = [
  {
    session_id: "SESSION-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-20",
    session_type: "free_play",
    audio_file_id: "AUDIO-001",
    transcript_id: "TRANSCRIPT-001",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "awaiting_review",
    report_status: "pending",
    notes: "Child used more spontaneous phrases today and responded better to WH-questions.",
  },
  {
    session_id: "SESSION-002",
    case_id: "CASE-002",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-21",
    session_type: "therapy_session",
    audio_file_id: null,
    transcript_id: null,
    feature_extraction_status: "not_started",
    ai_analysis_status: "not_started",
    therapist_review_status: "not_started",
    report_status: "not_started",
    notes: "Seeded session without uploaded media.",
  },
  {
    session_id: "SESSION-003",
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    session_date: "2026-05-22",
    session_type: "structured_assessment",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-003",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "needs_correction",
    report_status: "pending",
    notes: "Mock transcript needs speaker-label correction.",
  },
];

let audioFiles = [
  {
    audio_file_id: "AUDIO-001",
    original_filename: "session_sample.wav",
    stored_filename: "CASE-001_SESSION-001_AUDIO-001.wav",
    file_type: "wav",
    file_size: 18400000,
    upload_time: "2026-05-20T09:15:00Z",
    owner_user_id: "user_therapist_001",
    case_id: "CASE-001",
    session_id: "SESSION-001",
    processing_status: "completed",
  },
];

let transcriptLines = {
  "SESSION-001": [
    { speaker: "CHI", text: "want car .", confidence: 0.89 },
    { speaker: "MOT", text: "which car do you want ?", confidence: 0.93 },
    { speaker: "CHI", text: "red car .", confidence: 0.86 },
    { speaker: "CHI", text: "0 .", confidence: 0.74 },
  ],
  "SESSION-003": [
    { speaker: "MOT", text: "tell me what happened .", confidence: 0.91 },
    { speaker: "CHI", text: "xxx then go home .", confidence: 0.51 },
    { speaker: "INV", text: "try again slowly .", confidence: 0.88 },
  ],
};

let transcriptRecords = {
  "SESSION-001": {
    transcript_id: "TRANSCRIPT-001",
    session_id: "SESSION-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    original_filename: "session_001.cha",
    transcript_text: `@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Mock|CHI|4;08.00|male|||Target_Child|||
@ID:\teng|Mock|MOT|||||Mother|||
*CHI:\twant car .
*MOT:\twhich car do you want ?
*CHI:\tred car .
@End`,
    review_status: "awaiting_review",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: [],
    reviewer_notes: "",
  },
  "SESSION-003": {
    transcript_id: "TRANSCRIPT-003",
    session_id: "SESSION-003",
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    original_filename: "session_003.cha",
    transcript_text: `@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Mock|CHI|4;06.00||||Target_Child|||
@ID:\teng|Mock|MOT|||||Mother|||
*MOT:\ttell me what happened .
*CHI:\txxx then go home .
@End`,
    review_status: "needs_correction",
    qa_status: "needs_review",
    qa_score: 92,
    qa_issues: [{ code: "LOW_CONFIDENCE_SEGMENT", severity: "warning", message: "Mock transcript contains low-confidence child text." }],
    reviewer_notes: "Speaker-label correction needed before feature interpretation.",
  },
};

let goals = [
  { goal_id: "GOAL-001", case_id: "CASE-001", text: "Increase spontaneous two-word utterances during play.", status: "active" },
  { goal_id: "GOAL-004", case_id: "CASE-001", text: "Improve response to open WH-questions.", status: "active" },
  { goal_id: "GOAL-005", case_id: "CASE-001", text: "Extend reciprocal turn-taking in play routines.", status: "active" },
  { goal_id: "GOAL-002", case_id: "CASE-002", text: "Improve transcript-ready session sampling consistency.", status: "active" },
  { goal_id: "GOAL-003", case_id: "CASE-003", text: "Monitor intelligibility and speaker-label quality.", status: "active" },
];

let notes = [
  { note_id: "NOTE-001", case_id: "CASE-001", text: "Parent reports more requesting at home; verify in next session.", created_at: "2026-05-06T11:20:00Z" },
  { note_id: "NOTE-002", case_id: "CASE-003", text: "Correct low-confidence child line before interpreting features.", created_at: "2026-05-07T15:45:00Z" },
];

let generatedReports = [
  {
    report_id: "REPORT-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    title: "Progress Report: CHI-A01",
    export_status: "completed",
    created_at: "2026-05-20T10:20:00Z",
  },
];

const featureRows = [
  { domain: "Social Communication", feature: "Turn-taking", result: "0.62 / 1.00", change: "+ 0.12", direction: "up", icon: "sc" },
  { domain: "Language", feature: "Mean Length of Utterance", result: "3.25 words", change: "+ 0.45", direction: "up", icon: "la" },
  { domain: "Language", feature: "Vocabulary Diversity", result: "0.38", change: "+ 0.05", direction: "up", icon: "la" },
  { domain: "Repetitive Patterns", feature: "Repetitive Phrases", result: "High", change: "- 0.08", direction: "down", icon: "rp" },
  { domain: "ASD-specific Markers", feature: "Pronoun Reversal", result: "Occasional", change: "+ 0.10", direction: "down", icon: "am" },
];

const factorGroups = {
  increasing: [
    ["Repetitive phrase frequency", "+0.23"],
    ["Limited reciprocal response", "+0.18"],
    ["Restricted interests", "+0.12"],
  ],
  reducing: [
    ["Improved turn-taking", "-0.15"],
    ["More varied vocabulary", "-0.10"],
    ["Better eye contact", "-0.08"],
  ],
};

const featureSchema = [
  ["age_months", "Age in months", "Demographics"],
  ["total_utterances", "Child utterances", "Productivity"],
  ["mlu", "MLU in morphemes", "Complexity"],
  ["mluw", "MLU in words", "Complexity"],
  ["ttr", "Type-token ratio", "Lexical diversity"],
  ["total_words", "Total child words", "Productivity"],
  ["unintelligible_count", "Unintelligible utterances", "ASD-relevant markers"],
  ["unintelligible_ratio", "Unintelligible ratio", "ASD-relevant markers"],
  ["zero_vocalization_count", "Zero vocalizations", "ASD-relevant markers"],
  ["nonverbal_vocalization_count", "Non-verbal vocalizations", "ASD-relevant markers"],
  ["question_ratio", "Question ratio", "Pragmatic"],
  ["echolalia_count", "Echolalia count", "ASD-relevant markers"],
  ["echolalia_ratio", "Echolalia ratio", "ASD-relevant markers"],
  ["pronoun_reversal_count", "Pronoun reversal count", "ASD-relevant markers"],
];

let extractedFeatureOutputs = {
  "SESSION-001": {
    feature_id: "FEATURE-001",
    feature_schema_version: "14-feature-schema",
    features: {
      age_months: 56,
      total_utterances: 3,
      mlu: 2.33,
      mluw: 2.33,
      ttr: 0.86,
      total_words: 7,
      unintelligible_count: 0,
      unintelligible_ratio: 0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0,
      echolalia_count: 1,
      echolalia_ratio: 0.33,
      pronoun_reversal_count: 0,
    },
  },
};

let aiDecisionOutputs = {
  "SESSION-001": {
    output_id: "AI-OUTPUT-001",
    concern_level: "moderate_concern",
    screening_support_score: 0.68,
    top_contributing_features: ["echolalia_ratio", "mlu", "ttr"],
    evidence_items: [
      "Repetition markers should be reviewed in the transcript context.",
      "Short utterance length can reflect language sample limits.",
      "Lexical diversity should be compared across similar sessions.",
    ],
    explanation: "Decision-support only. Review transcript QA, session context, and therapist notes before interpreting this output.",
  },
};

let auditLogs = [];
let currentUser = null;
let activeView = "dashboard";
let selectedCaseId = "CASE-001";
let selectedSessionId = "SESSION-001";
let lastGeneratedReportMarkdown = "";

function nowIso() {
  return new Date().toISOString();
}

function addAudit(event_type, target_type, target_id, message) {
  auditLogs.unshift({
    audit_id: `AUDIT-${String(auditLogs.length + 1).padStart(4, "0")}`,
    event_type,
    actor_user_id: currentUser ? currentUser.user_id : "anonymous",
    target_type,
    target_id,
    message,
    created_at: nowIso(),
  });
}

function canSeeOwner(ownerUserId) {
  return currentUser && (currentUser.role === "admin" || currentUser.user_id === ownerUserId);
}

function visibleCases() {
  return cases.filter((item) => canSeeOwner(item.owner_user_id));
}

function visibleSessions() {
  const visibleCaseIds = new Set(visibleCases().map((item) => item.case_id));
  return sessions.filter((item) => visibleCaseIds.has(item.case_id) && canSeeOwner(item.owner_user_id));
}

function visibleAudioFiles() {
  return audioFiles.filter((item) => canSeeOwner(item.owner_user_id));
}

function selectedCase() {
  return visibleCases().find((item) => item.case_id === selectedCaseId) || visibleCases()[0] || null;
}

function selectedSession() {
  return visibleSessions().find((item) => item.session_id === selectedSessionId) || visibleSessions()[0] || null;
}

function caseSessions(caseId) {
  return visibleSessions().filter((item) => item.case_id === caseId);
}

function caseAudioFiles(caseId) {
  return visibleAudioFiles().filter((item) => item.case_id === caseId);
}

function caseGeneratedReports(caseId) {
  return generatedReports.filter((item) => item.case_id === caseId && canSeeOwner(item.owner_user_id));
}

function caseGoals(caseId) {
  return goals.filter((goal) => goal.case_id === caseId);
}

function progressSessions(caseId) {
  return caseSessions(caseId).slice().sort((a, b) => a.session_date.localeCompare(b.session_date));
}

function scoreTimeline(caseItem) {
  const rows = progressSessions(caseItem.case_id);
  return rows.map((session, index) => {
    const aiOutput = aiDecisionOutputs[session.session_id];
    return {
      label: session.session_id.replace("SESSION-", "S"),
      date: session.session_date,
      score: aiOutput?.screening_support_score ?? caseItem.score_trend[index] ?? caseItem.latest_score,
      review: session.therapist_review_status,
    };
  });
}

function featureRowsForCase(caseId) {
  return progressSessions(caseId)
    .map((session) => ({ session, output: extractedFeatureOutputs[session.session_id] }))
    .filter((row) => row.output);
}

function featureTrendRows(caseItem) {
  const rows = featureRowsForCase(caseItem.case_id);
  const preferred = ["total_utterances", "total_words", "mlu", "ttr", "unintelligible_ratio", "echolalia_ratio"];
  return preferred.map((metric) => {
    const values = rows.map((row) => row.output.features[metric]).filter((value) => Number.isFinite(value));
    const first = values[0] ?? null;
    const latest = values.at(-1) ?? null;
    const delta = first === null || latest === null ? null : Number((latest - first).toFixed(3));
    const lowerIsBetter = ["unintelligible_ratio", "echolalia_ratio"].includes(metric);
    const improved = delta === null ? null : lowerIsBetter ? delta < 0 : delta > 0;
    return { metric, first, latest, delta, improved };
  });
}

function goalProgress(caseItem) {
  const rows = caseGoals(caseItem.case_id);
  return {
    total: rows.length,
    active: rows.filter((goal) => goal.status === "active").length,
    paused: rows.filter((goal) => goal.status === "paused").length,
    completed: rows.filter((goal) => goal.status === "completed").length,
    rows,
  };
}

function normalizeRadarMetric(metric, value) {
  const ranges = {
    total_utterances: 8,
    total_words: 32,
    mlu: 6,
    ttr: 1,
    unintelligible_ratio: 1,
    echolalia_ratio: 1,
  };
  return Math.max(0.08, Math.min(1, Number(value || 0) / ranges[metric]));
}

function radarPoints(entries, key, radius, cx, cy) {
  return entries.map((entry, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / entries.length;
    const value = normalizeRadarMetric(entry.metric, entry[key]);
    const x = cx + Math.cos(angle) * radius * value;
    const y = cy + Math.sin(angle) * radius * value;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function radarEntries(caseItem) {
  const rows = featureRowsForCase(caseItem.case_id);
  if (!rows.length) {
    return featureTrendRows(caseItem).map((row) => ({
      metric: row.metric,
      first: 0,
      latest: 0,
    }));
  }
  const first = rows[0].output.features;
  const latest = rows.at(-1).output.features;
  return ["total_utterances", "total_words", "mlu", "ttr", "unintelligible_ratio", "echolalia_ratio"].map((metric) => ({
    metric,
    first: first[metric] ?? 0,
    latest: latest[metric] ?? 0,
  }));
}

function sessionAudioFiles(sessionId) {
  return visibleAudioFiles().filter((item) => item.session_id === sessionId);
}

function sessionTranscript(sessionId) {
  const transcript = transcriptRecords[sessionId];
  return transcript && canSeeOwner(transcript.owner_user_id) ? transcript : null;
}

function labelize(value) {
  return String(value || "").replaceAll("_", " ");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes)) return "0 MB";
  const mb = bytes / 1024 / 1024;
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function buildStoredFilename(caseId, sessionId, audioFileId, ext) {
  return `${caseId}_${sessionId}_${audioFileId}.${ext}`;
}

function reviewChatText(text) {
  const issues = [];
  const checks = [
    ["MISSING_BEGIN", !text.includes("@Begin"), "Missing @Begin header."],
    ["MISSING_END", !text.includes("@End"), "Missing @End footer."],
    ["MISSING_PARTICIPANTS", !text.includes("@Participants"), "Missing @Participants header."],
    ["MISSING_ID", !text.includes("@ID"), "Missing @ID participant metadata."],
    ["MISSING_CHI_TIER", !/^\*CHI:/m.test(text), "No child speaker tier (*CHI:) was found."],
  ];
  checks.forEach(([code, failed, message]) => {
    if (failed) issues.push({ code, severity: "error", message });
  });
  if (/^\*[A-Z]{1,2}:/m.test(text)) {
    issues.push({ code: "MALFORMED_SPEAKER_TIER", severity: "warning", message: "Some speaker tiers may not use three-letter CHAT speaker codes." });
  }
  const score = Math.max(0, 100 - issues.reduce((total, issue) => total + (issue.severity === "error" ? 20 : 8), 0));
  const hasError = issues.some((issue) => issue.severity === "error");
  return {
    qa_status: hasError ? "fail" : issues.length ? "needs_review" : "pass",
    qa_score: score,
    qa_issues: issues,
  };
}

function mockChatForSession(session, caseItem) {
  const ageYears = Math.floor((caseItem?.age_months || 48) / 12);
  const ageMonths = String((caseItem?.age_months || 48) % 12).padStart(2, "0");
  const sex = caseItem?.sex === "male" || caseItem?.sex === "female" ? caseItem.sex : "";
  return `@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Mock|CHI|${ageYears};${ageMonths}.00|${sex}|||Target_Child|||
@ID:\teng|Mock|MOT|||||Mother|||
*CHI:\twant car .
*MOT:\twhich car do you want ?
*CHI:\tred car .
@End`;
}

function extractMockFeaturesForSession(session) {
  const transcript = sessionTranscript(session.session_id);
  const caseItem = cases.find((item) => item.case_id === session.case_id);
  const childLines = (transcript?.transcript_text || "")
    .split("\n")
    .filter((line) => line.startsWith("*CHI:"))
    .map((line) => line.split(":", 2)[1]?.trim() || "");
  const words = childLines.flatMap((line) => line.split(/\s+/).map((word) => word.replace(/[.,?!]/g, "").toLowerCase()).filter(Boolean));
  const totalUtterances = Math.max(childLines.length, 1);
  const totalWords = words.length;
  const unintelligible = childLines.filter((line) => /\bxxx\b|\byyy\b/.test(line)).length;
  const zero = childLines.filter((line) => line.trim() === "0 ." || line.trim() === "0.").length;
  const echolalia = childLines.filter((line) => line.includes("[/]")).length || (childLines.length > 2 ? 1 : 0);
  const features = {
    age_months: caseItem?.age_months || 48,
    total_utterances: totalUtterances,
    mlu: Number((totalWords / totalUtterances).toFixed(3)),
    mluw: Number((totalWords / totalUtterances).toFixed(3)),
    ttr: Number((new Set(words).size / Math.max(totalWords, 1)).toFixed(3)),
    total_words: totalWords,
    unintelligible_count: unintelligible,
    unintelligible_ratio: Number((unintelligible / totalUtterances).toFixed(3)),
    zero_vocalization_count: zero,
    nonverbal_vocalization_count: childLines.filter((line) => line.includes("&=")).length,
    question_ratio: Number((childLines.filter((line) => line.includes("?")).length / totalUtterances).toFixed(3)),
    echolalia_count: echolalia,
    echolalia_ratio: Number((echolalia / totalUtterances).toFixed(3)),
    pronoun_reversal_count: childLines.filter((line) => /\bi\b.*\byou\b|\byou\b.*\bi\b/i.test(line)).length,
  };
  return Object.fromEntries(featureSchema.map(([key]) => [key, features[key]]));
}

function generateDecisionSupport(features) {
  const markerLoad = features.unintelligible_ratio * 0.22 + Math.min(features.echolalia_ratio, 1) * 0.2 + Math.min(features.zero_vocalization_count, 4) * 0.035;
  const languageSupport = Math.max(0, 0.22 - Math.min(features.mlu, 5) * 0.025);
  const score = Math.min(0.9, Math.max(0.12, 0.38 + markerLoad + languageSupport));
  const contributions = [
    ["unintelligible_ratio", features.unintelligible_ratio],
    ["echolalia_ratio", features.echolalia_ratio],
    ["zero_vocalization_count", features.zero_vocalization_count / 4],
    ["mlu", Math.max(0, 3.5 - features.mlu) / 3.5],
    ["ttr", Math.max(0, 0.55 - features.ttr)],
  ].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([key]) => key);
  return {
    output_id: `AI-OUTPUT-${String(Object.keys(aiDecisionOutputs).length + 1).padStart(3, "0")}`,
    concern_level: score >= 0.67 ? "moderate_concern" : score >= 0.4 ? "watchful_review" : "low_concern",
    screening_support_score: Number(score.toFixed(2)),
    top_contributing_features: contributions,
    evidence_items: contributions.map((feature) => `${feature} should be interpreted with transcript QA and session context.`),
    explanation: "Decision-support only. This is not a diagnosis and must be interpreted with qualified clinical judgment.",
  };
}

function statusClass(status) {
  if (["completed", "reviewed", "granted", "anonymized", "active"].includes(status)) return "status-good";
  if (["pending", "awaiting_review", "needs_correction", "processing", "not_started"].includes(status)) return "status-warn";
  if (["failed", "declined"].includes(status)) return "status-bad";
  return "status-muted";
}

function render() {
  const root = document.getElementById("app");
  if (!currentUser) {
    root.innerHTML = renderLogin();
    bindLogin();
    return;
  }
  root.innerHTML = `
    <div class="app-shell">
      ${renderSidebar()}
      <main class="main-shell">
        ${renderTopbar()}
        <div class="content-shell">${renderView()}</div>
      </main>
    </div>
  `;
  bindApp();
}

function renderLogin() {
  return `
    <main class="login-layout">
      <section class="login-panel">
        <div class="product-mark">ap</div>
        <p class="eyebrow">MOCK_MODE=${MOCK_MODE}</p>
        <h1>Speech Therapist Prototype</h1>
        <p class="lead">A focused workspace for therapists and clinicians to manage anonymized child cases, review speech sessions, and track progress with decision-support outputs.</p>
        <div class="safety-banner">${SAFETY_DISCLAIMER}</div>
        <form id="login-form" class="form-grid">
          <label>Email <input name="email" type="email" value="therapist@example.test" autocomplete="username" /></label>
          <label>Password <input name="password" type="password" value="demo-password" autocomplete="current-password" /></label>
          <button class="primary-action" type="submit">Log in</button>
        </form>
        <p id="login-error" class="form-error" hidden>Mock login failed. Use one of the sample accounts.</p>
      </section>
      <aside class="credential-panel">
        <h2>Sample Accounts</h2>
        ${users.map((user) => `
          <button class="credential-row" data-email="${user.email}">
            <span>${user.role}</span>
            <strong>${user.email}</strong>
            <small>demo-password</small>
          </button>
        `).join("")}
      </aside>
    </main>
  `;
}

function renderSidebar() {
  const items = [
    ["dashboard", "Dashboard", "⌂"],
    ["cases", "Children", "◌"],
    ["session", "Sessions", "+"],
    ["transcript", "Assessments", "□"],
    ["progress", "Progress Tracking", "↗"],
    ["reports", "Reports", "▤"],
    ["library", "Resource Library", "◇"],
    ["settings", "Settings", "⚙"],
  ];
  if (currentUser.role === "admin") items.push(["audit", "Audit Logs", "◎"]);
  return `
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon">ap</div>
        <div>
          <strong>asd-Project</strong>
          <small>Therapist Prototype</small>
        </div>
      </div>
      <nav>
        ${items.map(([view, label, icon]) => `
          <button class="nav-item ${activeView === view ? "active" : ""}" data-view="${view}">
            <span>${icon}</span><b>${label}</b>
          </button>
        `).join("")}
      </nav>
      <div class="sidebar-profile">
        <div class="avatar clinician">${initials(currentUser.name)}</div>
        <div>
          <strong>${currentUser.role === "admin" ? "Admin" : "Therapist"}</strong>
          <span>${currentUser.name}, ${currentUser.credentials}</span>
        </div>
        <button class="icon-button" id="logout-button" aria-label="Log out">↪</button>
      </div>
      <div class="schedule-card">
        <strong>Today's Schedule</strong>
        ${visibleSessions().slice(0, 3).map((session, index) => {
          const caseItem = cases.find((item) => item.case_id === session.case_id);
          return `<button class="schedule-row" data-select-session="${session.session_id}" data-view="transcript"><span>${["10:00", "11:30", "13:30"][index] || "15:00"}</span>${caseItem?.display_label || session.case_id} (${session.session_id.replace("SESSION-00", "Session ")})</button>`;
        }).join("") || `<p class="empty-state">No visible sessions.</p>`}
      </div>
    </aside>
  `;
}

function renderTopbar() {
  return `
    <header class="topbar">
      <div>
        <p class="welcome">Waving hello, ${currentUser.name.split(" ")[0]}.</p>
        <h2>${viewTitle()}</h2>
      </div>
      <div class="topbar-actions">
        <button class="icon-button" aria-label="Search">⌕</button>
        <button class="icon-button notification" aria-label="Notifications">♢<span>3</span></button>
        <button class="icon-button" aria-label="Help">?</button>
      </div>
    </header>
  `;
}

function viewTitle() {
  return {
    dashboard: "Therapist Dashboard",
    cases: "Children",
    session: "Sessions",
    transcript: "Assessments",
    progress: "Progress Tracking",
    reports: "Reports",
    library: "Resource Library",
    settings: "Settings",
    audit: "Audit Logs",
  }[activeView];
}

function renderView() {
  if (activeView === "cases") return renderCases();
  if (activeView === "session") return renderNewSession();
  if (activeView === "transcript") return renderTranscriptReview();
  if (activeView === "progress") return renderProgressReports();
  if (activeView === "reports") return renderProgressReports();
  if (activeView === "library") return renderResourceLibrary();
  if (activeView === "settings") return renderSettings();
  if (activeView === "audit") return renderAuditLogs();
  return renderDashboard();
}

function renderDashboard() {
  const caseItem = selectedCase();
  const ownedCases = visibleCases();
  const ownedSessions = visibleSessions();
  const transcriptQueue = ownedSessions.filter((item) => item.therapist_review_status === "awaiting_review" || item.therapist_review_status === "needs_correction");
  const reportQueue = ownedSessions.filter((item) => item.report_status === "pending");
  if (!caseItem) return `<p class="empty-state">No visible anonymized cases.</p>`;
  return `
    <section class="dashboard-command">
      <div>
        <p>Overview of your caseload and recent activities</p>
      </div>
      <div class="action-row">
        <select id="case-filter" aria-label="Select child case">
          ${ownedCases.map((item) => `<option value="${item.case_id}" ${item.case_id === caseItem.case_id ? "selected" : ""}>${item.display_label || item.case_id}</option>`).join("")}
        </select>
        <button class="primary-action" data-view="session">+ New Session</button>
      </div>
    </section>
    <section class="dashboard-grid">
      ${renderFocusCaseCard(caseItem)}
      ${renderScoreCard(caseItem)}
      ${renderScoreTrendCard(caseItem)}
      ${renderFeatureSummary()}
      ${renderFactorsAndSession(caseItem)}
    </section>
    <section class="metric-strip">
      ${metric("Active cases", ownedCases.length, "visible to this user")}
      ${metric("Transcript review", transcriptQueue.length, "awaiting review", "warn")}
      ${metric("Reports pending", reportQueue.length, "ready after review", "accent")}
      ${metric("Uploaded files", visibleAudioFiles().length, "metadata only")}
    </section>
    ${renderDashboardQuickActions()}
    ${renderDashboardQueues(ownedCases, ownedSessions, transcriptQueue)}
    ${renderClinicalReminder()}
  `;
}

function renderDashboardQuickActions() {
  return `
    <section class="panel quick-actions-panel">
      <div class="panel-title">
        <h3>Quick Actions</h3>
        <span>mock workflow shortcuts</span>
      </div>
      <div class="quick-action-grid">
        <button class="secondary-action" data-view="cases">Create case</button>
        <button class="secondary-action" data-view="session">Add session</button>
        <button class="secondary-action" data-view="session">Upload audio metadata</button>
        <button class="primary-action" data-view="reports">Generate report</button>
      </div>
    </section>
  `;
}

function renderDashboardQueues(ownedCases, ownedSessions, transcriptQueue) {
  const recentCases = ownedCases.slice().sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 3);
  const recentSessions = ownedSessions.slice().sort((a, b) => b.session_date.localeCompare(a.session_date)).slice(0, 3);
  return `
    <section class="three-column dashboard-lists">
      <article class="panel">
        <div class="panel-title"><h3>Recent Cases</h3><span>${recentCases.length}</span></div>
        ${recentCases.map((item) => `<button class="compact-row" data-view="cases" data-select-case="${item.case_id}"><strong>${item.display_label || item.case_id}</strong><span>${item.anonymized_child_code} · ${labelize(item.consent_status)}</span></button>`).join("") || `<p class="empty-state">No recent cases.</p>`}
      </article>
      <article class="panel">
        <div class="panel-title"><h3>Recent Sessions</h3><span>${recentSessions.length}</span></div>
        ${recentSessions.map((item) => `<button class="compact-row" data-view="transcript" data-select-session="${item.session_id}"><strong>${item.session_id}</strong><span>${item.session_date} · ${labelize(item.session_type)}</span></button>`).join("") || `<p class="empty-state">No recent sessions.</p>`}
      </article>
      <article class="panel">
        <div class="panel-title"><h3>High Review-Priority Cases</h3><span>${transcriptQueue.length}</span></div>
        ${transcriptQueue.map((session) => {
          const caseItem = cases.find((item) => item.case_id === session.case_id);
          return `<button class="compact-row" data-view="transcript" data-select-session="${session.session_id}"><strong>${caseItem?.display_label || session.case_id}</strong><span>${session.session_id} · ${labelize(session.therapist_review_status)}</span></button>`;
        }).join("") || `<p class="empty-state">No high review-priority cases.</p>`}
      </article>
    </section>
  `;
}

function renderFocusCaseCard(caseItem) {
  const sessionsForCase = caseSessions(caseItem.case_id);
  const goalsForCase = goals.filter((goal) => goal.case_id === caseItem.case_id);
  return `
    <article class="panel case-hero">
      <div class="case-top">
        <div class="avatar child">${caseItem.display_label?.split(" ")[1] || "A"}</div>
        <div>
          <h3>${caseItem.display_label || caseItem.case_id} <span class="star">${caseItem.starred ? "★" : ""}</span></h3>
          <small>ID: ${caseItem.anonymized_child_code}</small>
          <div class="tag-row">
            <span class="mini-tag">${labelize(caseItem.sex)}</span>
            <span class="mini-tag">${Math.floor(caseItem.age_months / 12)}y ${caseItem.age_months % 12}m</span>
          </div>
        </div>
        <span class="status-pill ${statusClass(caseItem.consent_status)}">${labelize(caseItem.consent_status)}</span>
      </div>
      <h4>Primary Concerns</h4>
      <p class="clinical-note">${escapeHtml(caseItem.primary_concerns)}</p>
      <div class="support-box">
        <span>Current Support Level</span>
        <strong><i></i>${escapeHtml(caseItem.support_level)}</strong>
      </div>
      <div class="case-stats">
        <div><strong>${sessionsForCase.length}</strong><span>Sessions</span></div>
        <div><strong>${transcriptLines[sessionsForCase[0]?.session_id]?.length || 3}</strong><span>Assessments</span></div>
        <div><strong>${goalsForCase.length}</strong><span>Goals</span></div>
      </div>
      <button class="ghost-action" data-view="cases" data-select-case="${caseItem.case_id}">View Full Profile</button>
    </article>
  `;
}

function renderScoreCard(caseItem) {
  return `
    <article class="panel score-card">
      <div class="panel-title">
        <h3>Latest Screening Support Score</h3>
        <span title="Decision support only">ⓘ</span>
      </div>
      <div class="gauge" style="--score:${caseItem.latest_score}">
        <div class="gauge-core">
          <strong>${caseItem.latest_score.toFixed(2)}</strong>
          <span>${caseItem.support_level} Concern</span>
        </div>
      </div>
      <p class="score-range">Score Range: 0 (Low) - 1 (High)</p>
      <div class="clinical-callout">This is a screening support score, not a diagnosis. Always interpret with clinical judgment.</div>
    </article>
  `;
}

function renderScoreTrendCard(caseItem) {
  return `
    <article class="panel trend-panel">
      <div class="panel-title">
        <h3>Score Trend Over Sessions</h3>
        <span title="Mock seeded trend">ⓘ</span>
      </div>
      ${renderLineChart(caseItem.score_trend)}
      <div class="improvement-box"><strong>↗ + 0.18 improvement</strong><span>Compared to first session</span></div>
    </article>
  `;
}

function renderLineChart(points) {
  const width = 560;
  const height = 190;
  const pad = 26;
  const coords = points.map((value, index) => {
    const x = pad + (index * (width - pad * 2)) / Math.max(points.length - 1, 1);
    const y = height - pad - value * (height - pad * 2);
    return [x, y];
  });
  const path = coords.map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  return `
    <svg class="line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Score trend over sessions">
      <g class="grid-lines">
        <line x1="${pad}" y1="30" x2="${width - pad}" y2="30"></line>
        <line x1="${pad}" y1="75" x2="${width - pad}" y2="75"></line>
        <line x1="${pad}" y1="120" x2="${width - pad}" y2="120"></line>
        <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}"></line>
      </g>
      <path class="chart-path" d="${path}"></path>
      ${coords.map(([x, y], index) => `<circle class="chart-dot" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5"></circle><text x="${x.toFixed(1)}" y="${height - 4}">Session ${index + 1}</text>`).join("")}
      <foreignObject x="${width - 78}" y="${coords.at(-1)[1] - 38}" width="56" height="32"><div class="score-bubble">${points.at(-1).toFixed(2)}</div></foreignObject>
    </svg>
  `;
}

function renderFeatureSummary() {
  return `
    <article class="panel feature-panel">
      <div class="panel-title">
        <h3>Feature Summary (Latest Session)</h3>
        <span title="Reviewed features only">ⓘ</span>
      </div>
      <div class="feature-table">
        <div class="feature-head"><span>Domain</span><span>Feature</span><span>Result</span><span>Compared to Last Session</span></div>
        ${featureRows.map((row, index) => `
          <div class="feature-row">
            <span class="feature-domain"><i class="${row.icon}"></i>${row.domain}</span>
            <span>${row.feature}</span>
            <span>${row.result}<b style="--bar:${52 + index * 8}%"></b></span>
            <span class="${row.direction === "up" ? "positive" : "negative"}">${row.direction === "up" ? "↑" : "↓"} ${row.change}</span>
          </div>
        `).join("")}
      </div>
      <button class="ghost-action" data-view="progress">View All Features</button>
    </article>
  `;
}

function renderFactorsAndSession(caseItem) {
  const latestSession = caseSessions(caseItem.case_id)[0] || selectedSession();
  const goalCount = goals.filter((goal) => goal.case_id === caseItem.case_id).length;
  return `
    <div class="right-stack">
      <article class="panel factors-panel">
        <div class="panel-title"><h3>Top Contributing Factors</h3><span>ⓘ</span></div>
        <div class="factor-columns">
          <div class="factor-list increasing">
            <strong>Increasing Concern</strong>
            ${factorGroups.increasing.map(([label, value]) => `<p>${label}<span>${value}</span></p>`).join("")}
          </div>
          <div class="factor-list reducing">
            <strong>Reducing Concern</strong>
            ${factorGroups.reducing.map(([label, value]) => `<p>${label}<span>${value}</span></p>`).join("")}
          </div>
        </div>
      </article>
      <article class="panel session-card">
        <div class="panel-title">
          <h3>Latest Session</h3>
          <button class="small-action" data-view="transcript" data-select-session="${latestSession?.session_id || ""}">View Session</button>
        </div>
        <small>${latestSession?.session_date || "No session"} (${latestSession?.session_id || "none"})</small>
        <div class="session-grid">
          <div><span>Input Type</span><p>Transcript (25 min)<br>Observation<br>Therapist Notes</p></div>
          <div><span>Therapist Note</span><p>${escapeHtml(latestSession?.notes || "No notes yet.")}</p></div>
          <div><span>Therapy Goals</span><strong>${Math.min(goalCount, 3)}/${Math.max(goalCount, 3)}</strong><p>Goals<br><b>On Track</b></p></div>
        </div>
      </article>
    </div>
  `;
}

function metric(label, value, detail, tone = "") {
  return `
    <article class="metric-card ${tone}">
      <span>${label}</span>
      <strong>${value}</strong>
      <small>${detail}</small>
    </article>
  `;
}

function renderClinicalReminder() {
  return `
    <section class="clinical-reminder">
      <div class="shield">✓</div>
      <div>
        <h3>Clinical Reminder</h3>
        <p>${SAFETY_DISCLAIMER} Consider the entire clinical picture before acting on any output.</p>
      </div>
      <div class="reminder-visual" aria-hidden="true"><span></span><i></i><b></b></div>
    </section>
  `;
}

function renderCaseRow(item) {
  return `
    <button class="row-button" data-select-case="${item.case_id}" data-view="cases">
      <div>
        <strong>${item.display_label || item.case_id} · ${item.anonymized_child_code}</strong>
        <small>${item.age_months} months · ${escapeHtml(item.primary_concerns)}</small>
      </div>
      <span class="status-pill ${statusClass(item.consent_status)}">${labelize(item.consent_status)}</span>
    </button>
  `;
}

function renderSessionRow(item) {
  const caseItem = cases.find((caseRow) => caseRow.case_id === item.case_id);
  return `
    <button class="row-button" data-select-session="${item.session_id}" data-view="transcript">
      <div>
        <strong>${item.session_id} · ${caseItem ? caseItem.anonymized_child_code : item.case_id}</strong>
        <small>${item.session_date} · ${labelize(item.session_type)} · ${escapeHtml(item.notes)}</small>
        ${caseItem ? `<span class="inline-status">${labelize(caseItem.consent_status)} · ${labelize(caseItem.anonymization_status)}</span>` : ""}
      </div>
      <span class="status-pill ${statusClass(item.therapist_review_status)}">${labelize(item.therapist_review_status)}</span>
    </button>
  `;
}

function renderCases() {
  const ownedCases = visibleCases();
  const caseItem = selectedCase();
  return `
    <section class="two-column wide-left">
      <div class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Case ownership</p>
            <h3>Visible anonymized children</h3>
          </div>
          <span class="role-pill">${ownedCases.length} case(s)</span>
        </div>
        ${ownedCases.map(renderCaseRow).join("")}
      </div>
      <form class="panel form-grid" id="case-form">
        <p class="eyebrow">Create case</p>
        <h3>New anonymized child case</h3>
        <label>Anonymized code <input name="anonymized_child_code" placeholder="CHI-A03" required /></label>
        <label>Age months <input name="age_months" type="number" min="0" max="216" value="48" required /></label>
        <label>Sex
          <select name="sex">
            <option value="not_specified">not specified</option>
            <option value="female">female</option>
            <option value="male">male</option>
            <option value="other">other</option>
          </select>
        </label>
        <label>External clinical status
          <select name="external_clinical_status">
            <option value="not_provided">not provided</option>
            <option value="under_evaluation">under evaluation</option>
            <option value="external_asd_recorded">external ASD recorded</option>
            <option value="external_non_asd_recorded">external non-ASD recorded</option>
          </select>
        </label>
        <label>Consent status
          <select name="consent_status">
            <option value="not_recorded">not recorded</option>
            <option value="pending">pending</option>
            <option value="granted">granted</option>
            <option value="declined">declined</option>
          </select>
        </label>
        <label>Anonymization status
          <select name="anonymization_status">
            <option value="anonymized">anonymized</option>
            <option value="pending">pending</option>
            <option value="needs_review">needs review</option>
          </select>
        </label>
        <label class="full-span">Primary concerns <textarea name="primary_concerns" placeholder="No real names or identifiers." required></textarea></label>
        <button class="primary-action full-span" type="submit">Create case</button>
      </form>
    </section>
    ${caseItem ? renderCaseDetail(caseItem) : ""}
  `;
}

function renderCaseDetail(item) {
  const sessionsForCase = caseSessions(item.case_id);
  const goalsForCase = goals.filter((goal) => goal.case_id === item.case_id);
  const notesForCase = notes.filter((note) => note.case_id === item.case_id);
  const filesForCase = caseAudioFiles(item.case_id);
  const reportsForCase = caseGeneratedReports(item.case_id);
  return `
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Child profile</p>
          <h3>${item.display_label || item.case_id} · ${item.anonymized_child_code}</h3>
        </div>
        <div class="status-stack">
          <span class="status-pill ${statusClass(item.consent_status)}">${labelize(item.consent_status)}</span>
          <span class="status-pill ${statusClass(item.anonymization_status)}">${labelize(item.anonymization_status)}</span>
        </div>
      </div>
      <div class="detail-grid">
        <div><span>Age</span><strong>${item.age_months} months</strong></div>
        <div><span>Sex</span><strong>${labelize(item.sex)}</strong></div>
        <div><span>External clinical status</span><strong>${labelize(item.external_clinical_status)}</strong></div>
        <div><span>Owner</span><strong>${item.owner_user_id}</strong></div>
      </div>
      <p class="clinical-note">${escapeHtml(item.primary_concerns)}</p>
      <div class="three-column">
        <div>
          <h4>Session timeline</h4>
          ${sessionsForCase.map((session) => `<p class="timeline-item">${session.session_date} · ${labelize(session.session_type)} · ${labelize(session.therapist_review_status)}</p>`).join("") || `<p class="empty-state">No sessions yet.</p>`}
        </div>
        <div>
          <h4>Therapy goals</h4>
          ${goalsForCase.map((goal) => `<p class="timeline-item">${escapeHtml(goal.text)}</p>`).join("") || `<p class="empty-state">No goals yet.</p>`}
        </div>
        <div>
          <h4>Therapist notes</h4>
          ${notesForCase.map((note) => `<p class="timeline-item">${escapeHtml(note.text)}</p>`).join("") || `<p class="empty-state">No notes yet.</p>`}
        </div>
      </div>
    </section>
    ${renderAudioMetadataPanel("Uploaded File Metadata", filesForCase)}
    ${renderCaseWorkflowOverview(item, sessionsForCase, reportsForCase)}
    <section class="two-column wide-left">
      <form class="panel form-grid" id="case-edit-form">
        <p class="eyebrow">Edit profile</p>
        <h3>Update case context</h3>
        <input name="case_id" type="hidden" value="${item.case_id}" />
        <label>Age months <input name="age_months" type="number" min="0" max="216" value="${item.age_months}" required /></label>
        <label>Sex
          <select name="sex">
            ${["not_specified", "female", "male", "other"].map((value) => `<option value="${value}" ${value === item.sex ? "selected" : ""}>${labelize(value)}</option>`).join("")}
          </select>
        </label>
        <label>External clinical status
          <select name="external_clinical_status">
            ${["not_provided", "under_evaluation", "external_asd_recorded", "external_non_asd_recorded"].map((value) => `<option value="${value}" ${value === item.external_clinical_status ? "selected" : ""}>${labelize(value)}</option>`).join("")}
          </select>
        </label>
        <label>Consent status
          <select name="consent_status">
            ${["not_recorded", "pending", "granted", "declined"].map((value) => `<option value="${value}" ${value === item.consent_status ? "selected" : ""}>${labelize(value)}</option>`).join("")}
          </select>
        </label>
        <label>Anonymization status
          <select name="anonymization_status">
            ${["anonymized", "pending", "needs_review"].map((value) => `<option value="${value}" ${value === item.anonymization_status ? "selected" : ""}>${labelize(value)}</option>`).join("")}
          </select>
        </label>
        <label class="full-span">Primary concerns <textarea name="primary_concerns" required>${escapeHtml(item.primary_concerns)}</textarea></label>
        <label class="full-span">Case notes <textarea name="notes">${escapeHtml(item.notes)}</textarea></label>
        <button class="primary-action full-span" type="submit">Save case updates</button>
      </form>
      <form class="panel form-grid" id="note-form">
        <p class="eyebrow">Therapist notes</p>
        <h3>Add clinical note</h3>
        <input name="case_id" type="hidden" value="${item.case_id}" />
        <label class="full-span">Link to session
          <select name="session_id">
            <option value="">Case-level note</option>
            ${sessionsForCase.map((session) => `<option value="${session.session_id}">${session.session_date} · ${session.session_id}</option>`).join("")}
          </select>
        </label>
        <label class="full-span">Note text <textarea name="note_text" placeholder="Clinical context only. Do not enter real child identifiers." required></textarea></label>
        <button class="secondary-action full-span" type="submit">Add therapist note</button>
      </form>
    </section>
  `;
}

function renderCaseWorkflowOverview(item, sessionsForCase, reportsForCase) {
  const aiHistory = sessionsForCase
    .map((session) => ({ session, output: aiDecisionOutputs[session.session_id] }))
    .filter((row) => row.output);
  return `
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Phase 7 acceptance view</p>
          <h3>Case workflow status</h3>
        </div>
        <button class="small-action" data-view="reports" data-select-case="${item.case_id}">Generate report</button>
      </div>
      <div class="case-workflow-grid">
        <div>
          <h4>Feature Trends</h4>
          ${featureTrendRows(item).map((row) => `<p class="timeline-item">${row.metric}: ${row.first ?? "n/a"} to ${row.latest ?? "n/a"} (${row.delta ?? "n/a"})</p>`).join("")}
        </div>
        <div>
          <h4>AI Screening Support History</h4>
          ${aiHistory.map(({ session, output }) => `<p class="timeline-item">${session.session_date} · ${output.screening_support_score.toFixed(2)} · ${labelize(output.concern_level)}</p>`).join("") || `<p class="empty-state">No AI support output yet.</p>`}
        </div>
        <div>
          <h4>Transcript Review Status</h4>
          ${sessionsForCase.map((session) => `<p class="timeline-item">${session.session_id}: ${labelize(session.therapist_review_status)}</p>`).join("") || `<p class="empty-state">No sessions yet.</p>`}
        </div>
        <div>
          <h4>Generated Reports</h4>
          ${reportsForCase.map((report) => `<p class="timeline-item">${escapeHtml(report.title)} · ${labelize(report.export_status)}</p>`).join("") || `<p class="empty-state">No generated reports yet.</p>`}
        </div>
      </div>
    </section>
  `;
}

function renderNewSession() {
  const caseOptions = visibleCases().map((item) => `<option value="${item.case_id}">${item.display_label || item.case_id} · ${item.anonymized_child_code}</option>`).join("");
  return `
    <section class="two-column">
      <form class="panel form-grid" id="session-form">
        <p class="eyebrow">Metadata-only mock upload</p>
        <h3>New session</h3>
        <div class="safety-banner full-span">Phase 3 stores audio/video metadata only. No file bytes are persisted, no browser preview is created, and the real audio pipeline is not run.</div>
        <label>Child case <select name="case_id">${caseOptions}</select></label>
        <label>Session date <input name="session_date" type="date" value="2026-05-27" /></label>
        <label>Session type
          <select name="session_type">
            <option value="free_play">free play</option>
            <option value="parent_child_interaction">parent-child interaction</option>
            <option value="structured_assessment">structured assessment</option>
            <option value="therapy_session">therapy session</option>
          </select>
        </label>
        <label>Audio/video file metadata <input name="media_file" type="file" accept=".wav,.mp3,.m4a,.mp4,.mov" /></label>
        <label class="full-span">Session context <textarea name="notes" placeholder="Context only. Do not enter real child identifiers."></textarea></label>
        <button class="primary-action full-span" type="submit">Create mock session</button>
        <p id="file-error" class="form-error full-span" hidden></p>
      </form>
      <div class="panel">
        <p class="eyebrow">Mock processing status</p>
        <h3>Ready for real pipeline later</h3>
        <ol class="pipeline-list">
          <li>Validate file type and size</li>
          <li>Create secure metadata record by owner/case/session</li>
          <li>Keep mock processing status: pending, processing, completed, or failed</li>
          <li>Run ASR transcription only in a later phase</li>
          <li>Run diarization and CHAT formatting</li>
          <li>Transcript QA and therapist review</li>
          <li>Feature extraction and AI support output</li>
          <li>Therapist-approved report generation</li>
        </ol>
        <div class="safety-banner">Allowed files: ${ALLOWED_FILE_TYPES.join(", ")} · max ${MAX_FILE_SIZE_MB} MB. Phase 3 records metadata only.</div>
      </div>
    </section>
  `;
}

function renderTranscriptReview() {
  const session = selectedSession();
  if (!session) return `<p class="empty-state">No visible session selected.</p>`;
  const lines = transcriptLines[session.session_id] || [];
  const caseItem = cases.find((item) => item.case_id === session.case_id);
  const filesForSession = sessionAudioFiles(session.session_id);
  const transcript = sessionTranscript(session.session_id);
  const sessionNotes = notes.filter((note) => note.session_id === session.session_id || note.case_id === session.case_id);
  return `
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">CHAT transcript workflow</p>
          <h3>${session.session_id} transcript</h3>
        </div>
        <span class="status-pill ${statusClass(session.therapist_review_status)}">${labelize(session.therapist_review_status)}</span>
      </div>
      ${caseItem ? `
        <h4>Session metadata</h4>
        <div class="detail-grid compact">
          <div><span>Child case</span><strong>${caseItem.display_label || caseItem.case_id}</strong></div>
          <div><span>Consent</span><strong>${labelize(caseItem.consent_status)}</strong></div>
          <div><span>Anonymization</span><strong>${labelize(caseItem.anonymization_status)}</strong></div>
          <div><span>Session date</span><strong>${session.session_date}</strong></div>
          <div><span>Session type</span><strong>${labelize(session.session_type)}</strong></div>
          <div><span>Feature status</span><strong>${labelize(session.feature_extraction_status)}</strong></div>
          <div><span>AI status</span><strong>${labelize(session.ai_analysis_status)}</strong></div>
          <div><span>Report status</span><strong>${labelize(session.report_status)}</strong></div>
        </div>
      ` : ""}
      <div class="safety-banner">ASR-generated transcripts may contain errors and must be reviewed before clinical interpretation.</div>
      <div class="clinical-callout">Audio/video player deferred: Phase 7 still uses metadata-only mock upload records, so no playable file bytes or browser preview are available.</div>
      ${renderAudioMetadataInline(filesForSession)}
      <div class="transcript-actions">
        <label>Upload/select .cha transcript <input id="transcript-file" type="file" accept=".cha" /></label>
        <button class="secondary-action" id="generate-mock-chat" ${filesForSession.length ? "" : "disabled"}>Generate mock CHAT from audio metadata</button>
        <p id="transcript-error" class="form-error" hidden></p>
      </div>
      <div class="clinical-note">Real audio-to-CHAT execution is deferred until file storage exists. Phase 4 can upload/select .cha text or generate mock CHAT for review.</div>
      ${renderTranscriptQa(transcript)}
      ${renderDecisionSupportPanel(session)}
      <div class="transcript-workspace">
        <label>CHAT transcript viewer and correction UI
          <textarea id="chat-transcript-text" spellcheck="false" placeholder="@Begin">${escapeHtml(transcript?.transcript_text || "")}</textarea>
        </label>
        <label>Interpretation notes
          <textarea id="transcript-reviewer-notes" placeholder="Review notes before clinical interpretation.">${escapeHtml(transcript?.reviewer_notes || "")}</textarea>
        </label>
      </div>
      <div class="transcript-table">
        <h4>Line correction workspace</h4>
        ${lines.map((line, index) => `
          <div class="transcript-row">
            <select data-line-speaker="${index}">
              ${["CHI", "MOT", "INV"].map((speaker) => `<option ${speaker === line.speaker ? "selected" : ""}>${speaker}</option>`).join("")}
            </select>
            <input data-line-text="${index}" value="${escapeHtml(line.text)}" />
            <span>${Math.round(line.confidence * 100)}%</span>
          </div>
        `).join("") || `<p class="empty-state">No transcript generated yet.</p>`}
      </div>
      <div class="action-row">
        <button class="secondary-action" id="save-transcript">Save corrections</button>
        <button class="primary-action" id="mark-reviewed">Mark transcript reviewed</button>
        <button class="ghost-action" id="rerun-features">Re-run feature extraction</button>
        <button class="ghost-action" data-view="reports" data-select-case="${session.case_id}">Report generation button</button>
      </div>
      <div class="qa-panel">
        <div class="panel-title"><h3>Therapist Notes</h3><span>${sessionNotes.length}</span></div>
        ${sessionNotes.map((note) => `<p class="timeline-item">${escapeHtml(note.text)}</p>`).join("") || `<p class="empty-state">No therapist notes linked to this session or case.</p>`}
      </div>
    </section>
  `;
}

function renderTranscriptQa(transcript) {
  if (!transcript) {
    return `<div class="qa-panel"><strong>Transcript QA Results</strong><p class="empty-state">No CHAT transcript selected for this session yet.</p></div>`;
  }
  return `
    <div class="qa-panel">
      <div class="panel-title">
        <h3>Transcript QA Results</h3>
        <span class="status-pill ${transcript.qa_status === "fail" ? "status-bad" : transcript.qa_status === "pass" ? "status-good" : "status-warn"}">${labelize(transcript.qa_status)}</span>
      </div>
      <div class="detail-grid compact">
        <div><span>Transcript</span><strong>${transcript.transcript_id}</strong></div>
        <div><span>Original file</span><strong>${escapeHtml(transcript.original_filename || "mock generated")}</strong></div>
        <div><span>QA score</span><strong>${transcript.qa_score ?? "not run"}</strong></div>
        <div><span>Review</span><strong>${labelize(transcript.review_status)}</strong></div>
      </div>
      ${transcript.qa_issues.length ? transcript.qa_issues.map((issue) => `<p class="timeline-item">${issue.severity}: ${issue.code} · ${escapeHtml(issue.message)}</p>`).join("") : `<p class="clinical-note">No blocking QA issues found in the mock reviewer.</p>`}
    </div>
  `;
}

function renderDecisionSupportPanel(session) {
  const featureOutput = extractedFeatureOutputs[session.session_id];
  const aiOutput = aiDecisionOutputs[session.session_id];
  return `
    <div class="decision-panel">
      <div class="panel-title">
        <h3>AI Decision-Support Output</h3>
        <span title="Support output only">ⓘ</span>
      </div>
      <div class="clinical-callout">This panel shows screening support, not a diagnosis. Review transcript QA and therapist notes before interpretation.</div>
      ${featureOutput ? renderFeatureSchemaOutput(featureOutput) : `<p class="empty-state">No extracted 14-feature schema output yet. Mark the transcript reviewed, then re-run feature extraction.</p>`}
      ${aiOutput ? renderAiSupportOutput(aiOutput) : `<p class="empty-state">No AI decision-support output generated yet.</p>`}
    </div>
  `;
}

function renderFeatureSchemaOutput(featureOutput) {
  return `
    <div class="feature-schema-panel">
      <div class="panel-title">
        <h4>14-feature schema summary</h4>
        <span>${featureOutput.feature_schema_version}</span>
      </div>
      <div class="feature-mini-grid">
        ${featureSchema.map(([key, title, group]) => `
          <div>
            <span>${group}</span>
            <strong>${title}</strong>
            <b>${featureOutput.features[key]}</b>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function renderAiSupportOutput(aiOutput) {
  return `
    <div class="ai-output-grid">
      <div>
        <span>Screening Support Score</span>
        <strong>${aiOutput.screening_support_score.toFixed(2)}</strong>
        <p>${labelize(aiOutput.concern_level)}</p>
      </div>
      <div>
        <span>Top contributing features</span>
        ${aiOutput.top_contributing_features.map((feature) => `<p class="timeline-item">${feature}</p>`).join("")}
      </div>
      <div>
        <span>Evidence Review Panel</span>
        ${aiOutput.evidence_items.map((item) => `<p class="timeline-item">${escapeHtml(item)}</p>`).join("")}
      </div>
    </div>
    <p class="clinical-note">${escapeHtml(aiOutput.explanation)}</p>
  `;
}

function renderAudioMetadataPanel(title, files) {
  return `
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Metadata-only mock upload</p>
          <h3>${title}</h3>
        </div>
        <span class="role-pill">${files.length} file(s)</span>
      </div>
      ${renderAudioMetadataRows(files)}
    </section>
  `;
}

function renderAudioMetadataInline(files) {
  return `
    <div class="metadata-inline">
      <strong>Uploaded File Metadata</strong>
      ${renderAudioMetadataRows(files)}
    </div>
  `;
}

function renderAudioMetadataRows(files) {
  if (!files.length) {
    return `<p class="empty-state">No file metadata linked to this item. Phase 3 does not store real audio/video files.</p>`;
  }
  return `
    <div class="file-table">
      <div class="file-row file-head"><span>Original filename</span><span>Stored filename</span><span>Type</span><span>Size</span><span>Status</span></div>
      ${files.map((file) => `
        <div class="file-row">
          <span>${escapeHtml(file.original_filename)}</span>
          <span>${escapeHtml(file.stored_filename)}</span>
          <span>${escapeHtml(file.file_type)}</span>
          <span>${formatFileSize(file.file_size)}</span>
          <span class="status-pill ${statusClass(file.processing_status)}">${labelize(file.processing_status)}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function renderProgressReports() {
  const caseItem = selectedCase();
  if (!caseItem) return `<p class="empty-state">No visible case selected.</p>`;
  const timeline = scoreTimeline(caseItem);
  return `
    <section class="dashboard-command">
      <div>
        <p>Progress is descriptive decision support only. Use comparable sessions and therapist-reviewed transcripts.</p>
      </div>
      <select id="case-filter" aria-label="Select child case">
        ${visibleCases().map((item) => `<option value="${item.case_id}" ${item.case_id === caseItem.case_id ? "selected" : ""}>${item.display_label || item.case_id}</option>`).join("")}
      </select>
    </section>
    <section class="progress-grid">
      ${renderScoreTimelinePanel(caseItem, timeline)}
      ${renderGoalProgressPanel(caseItem)}
      ${renderFeatureTrendPanel(caseItem)}
      ${renderBeforeAfterRadar(caseItem)}
      ${renderReportBuilder(caseItem)}
    </section>
  `;
}

function renderScoreTimelinePanel(caseItem, timeline) {
  const points = timeline.map((row) => row.score);
  return `
    <article class="panel progress-card span-two">
      <div class="panel-title">
        <h3>Score Timeline</h3>
        <span>${caseItem.anonymized_child_code}</span>
      </div>
      ${renderLineChart(points.length ? points : [caseItem.latest_score])}
      <div class="timeline-grid">
        ${timeline.map((row) => `
          <div>
            <span>${row.label}</span>
            <strong>${row.score.toFixed(2)}</strong>
            <small>${row.date} · ${labelize(row.review)}</small>
          </div>
        `).join("") || `<p class="empty-state">No visible sessions for score timeline.</p>`}
      </div>
    </article>
  `;
}

function renderGoalProgressPanel(caseItem) {
  const progress = goalProgress(caseItem);
  const completion = progress.total ? Math.round((progress.completed / progress.total) * 100) : 0;
  return `
    <article class="panel progress-card">
      <div class="panel-title">
        <h3>Therapy Goal Progress</h3>
        <span>${completion}%</span>
      </div>
      <div class="goal-ring" style="--goal:${completion}%">
        <strong>${progress.completed}/${progress.total || 0}</strong>
        <span>completed</span>
      </div>
      <div class="goal-stats">
        <span>Active <b>${progress.active}</b></span>
        <span>Paused <b>${progress.paused}</b></span>
        <span>Completed <b>${progress.completed}</b></span>
      </div>
      ${progress.rows.map((goal) => `<p class="timeline-item">${escapeHtml(goal.text)} <span class="status-pill ${statusClass(goal.status)}">${labelize(goal.status)}</span></p>`).join("") || `<p class="empty-state">No therapy goals yet.</p>`}
    </article>
  `;
}

function renderFeatureTrendPanel(caseItem) {
  const rows = featureTrendRows(caseItem);
  return `
    <article class="panel progress-card span-two">
      <div class="panel-title">
        <h3>Feature Trends Over Sessions</h3>
        <span>14-feature schema subset</span>
      </div>
      <div class="trend-table">
        <div class="trend-row trend-head"><span>Feature</span><span>First</span><span>Latest</span><span>Delta</span><span>Direction</span></div>
        ${rows.map((row) => `
          <div class="trend-row">
            <span>${row.metric}</span>
            <span>${row.first ?? "n/a"}</span>
            <span>${row.latest ?? "n/a"}</span>
            <span>${row.delta ?? "n/a"}</span>
            <span class="${row.improved ? "positive" : row.improved === false ? "negative" : ""}">${row.improved === null ? "needs more data" : row.improved ? "positive" : "mixed"}</span>
          </div>
        `).join("")}
      </div>
      <p class="clinical-note">Feature trends describe change only. They do not prove clinical improvement without therapist review and matched session context.</p>
    </article>
  `;
}

function renderBeforeAfterRadar(caseItem) {
  const entries = radarEntries(caseItem);
  const cx = 150;
  const cy = 150;
  const radius = 106;
  const axes = entries.map((entry, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / entries.length;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    const labelX = cx + Math.cos(angle) * (radius + 24);
    const labelY = cy + Math.sin(angle) * (radius + 24);
    return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"></line><text x="${labelX.toFixed(1)}" y="${labelY.toFixed(1)}">${entry.metric.replace("_ratio", "").replace("total_", "")}</text>`;
  }).join("");
  return `
    <article class="panel progress-card radar-card">
      <div class="panel-title">
        <h3>Before/After Radar</h3>
        <span>first vs latest</span>
      </div>
      <svg class="radar-chart" viewBox="0 0 300 300" role="img" aria-label="Before and after radar chart">
        <polygon class="radar-grid-shape" points="150,44 242,97 242,203 150,256 58,203 58,97"></polygon>
        <g class="radar-axis">${axes}</g>
        <polygon class="radar-first" points="${radarPoints(entries, "first", radius, cx, cy)}"></polygon>
        <polygon class="radar-latest" points="${radarPoints(entries, "latest", radius, cx, cy)}"></polygon>
      </svg>
      <div class="radar-legend"><span><i class="first"></i>First reviewed session</span><span><i class="latest"></i>Latest reviewed session</span></div>
    </article>
  `;
}

function renderReportBuilder(caseItem) {
  return `
    <article class="panel progress-card report-builder span-three">
      <div class="panel-title">
        <div>
          <p class="eyebrow">Report generation</p>
          <h3>Printable / Exportable Progress Report</h3>
        </div>
        <button class="primary-action" id="generate-report">Generate progress report</button>
      </div>
      <p class="clinical-note">Reports include score timeline, feature trends, therapy goal progress, transcript review status, and the persistent decision-support disclaimer.</p>
      <div id="report-output" class="report-output" hidden></div>
    </article>
  `;
}

function buildProgressReportMarkdown(caseItem) {
  const progress = goalProgress(caseItem);
  const timeline = scoreTimeline(caseItem);
  const trends = featureTrendRows(caseItem);
  const sessionsForCase = progressSessions(caseItem.case_id);
  const transcriptStatuses = sessionsForCase.map((session) => `- ${session.session_id}: ${labelize(session.therapist_review_status)}`).join("\n") || "- No sessions yet";
  const trendRows = trends.map((row) => `| ${row.metric} | ${row.first ?? "n/a"} | ${row.latest ?? "n/a"} | ${row.delta ?? "n/a"} | ${row.improved === null ? "needs more data" : row.improved ? "positive direction" : "mixed"} |`).join("\n");
  return `# Progress Report: ${caseItem.anonymized_child_code}

${SAFETY_DISCLAIMER}

## Case Overview
- Case ID: ${caseItem.case_id}
- External clinical status: ${labelize(caseItem.external_clinical_status)}
- Consent: ${labelize(caseItem.consent_status)}
- Anonymization: ${labelize(caseItem.anonymization_status)}
- Sessions summarized: ${sessionsForCase.length}
- Therapy goals: ${progress.completed}/${progress.total} completed, ${progress.active} active, ${progress.paused} paused

## Screening Support Timeline
${timeline.map((row) => `- ${row.date} / ${row.label}: ${row.score.toFixed(2)} (${labelize(row.review)})`).join("\n") || "- No score timeline yet"}

## Feature Trends
| Feature | First | Latest | Delta | Descriptive trend |
|---|---:|---:|---:|---|
${trendRows}

## Transcript Review Status
${transcriptStatuses}

## Therapist Notes
${notes.filter((note) => note.case_id === caseItem.case_id).map((note) => `- ${note.created_at}: ${note.text}`).join("\n") || "- No therapist notes yet"}

## Safe Use Boundary
This report is for progress tracking and clinical decision support only. It must be reviewed with session context and qualified professional judgment before it is shared or acted upon.`;
}

function renderResourceLibrary() {
  return `
    <section class="panel">
      <p class="eyebrow">Clinical support materials</p>
      <h3>Resource Library</h3>
      <div class="three-column">
        <p class="timeline-item">Transcript QA checklist</p>
        <p class="timeline-item">Session sampling guide</p>
        <p class="timeline-item">Safety wording for caregiver conversations</p>
      </div>
    </section>
  `;
}

function renderSettings() {
  return `
    <section class="panel">
      <p class="eyebrow">Prototype settings</p>
      <h3>Mock mode controls</h3>
      <div class="detail-grid">
        <div><span>Mode</span><strong>MOCK_MODE=${MOCK_MODE}</strong></div>
        <div><span>Real storage</span><strong>Disabled</strong></div>
        <div><span>Role</span><strong>${currentUser.role}</strong></div>
        <div><span>Audit visibility</span><strong>${currentUser.role === "admin" ? "Admin" : "Restricted"}</strong></div>
      </div>
    </section>
  `;
}

function renderAuditLogs() {
  if (currentUser.role !== "admin") {
    return `<p class="empty-state">Audit logs are admin-only.</p>`;
  }
  return `
    <section class="panel">
      <p class="eyebrow">Admin only</p>
      <h3>Audit logs</h3>
      ${auditLogs.length ? auditLogs.map((log) => `
        <div class="audit-row">
          <strong>${log.event_type}</strong>
          <span>${log.actor_user_id} · ${log.target_type}:${log.target_id}</span>
          <small>${log.created_at}</small>
          <p>${escapeHtml(log.message)}</p>
        </div>
      `).join("") : `<p class="empty-state">No audit events yet.</p>`}
    </section>
  `;
}

function initials(name) {
  return name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function bindLogin() {
  document.querySelectorAll(".credential-row").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelector("[name=email]").value = button.dataset.email;
      document.querySelector("[name=password]").value = "demo-password";
    });
  });
  document.getElementById("login-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email")).trim().toLowerCase();
    const password = String(data.get("password"));
    const user = users.find((item) => item.email === email && item.password === password);
    if (!user) {
      document.getElementById("login-error").hidden = false;
      return;
    }
    user.last_login = nowIso();
    currentUser = user;
    selectedCaseId = visibleCases()[0]?.case_id || selectedCaseId;
    selectedSessionId = visibleSessions()[0]?.session_id || selectedSessionId;
    addAudit("login", "user", user.user_id, `Mock login for ${user.email}`);
    render();
  });
}

function bindApp() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      activeView = button.dataset.view;
      if (button.dataset.selectCase) selectedCaseId = button.dataset.selectCase;
      if (button.dataset.selectSession) selectedSessionId = button.dataset.selectSession;
      render();
    });
  });
  document.getElementById("case-filter")?.addEventListener("change", (event) => {
    selectedCaseId = event.currentTarget.value;
    const firstSession = caseSessions(selectedCaseId)[0];
    if (firstSession) selectedSessionId = firstSession.session_id;
    render();
  });
  document.getElementById("logout-button")?.addEventListener("click", () => {
    addAudit("logout", "user", currentUser.user_id, `Mock logout for ${currentUser.email}`);
    currentUser = null;
    activeView = "dashboard";
    render();
  });
  document.getElementById("case-form")?.addEventListener("submit", handleCaseCreate);
  document.getElementById("case-edit-form")?.addEventListener("submit", handleCaseUpdate);
  document.getElementById("note-form")?.addEventListener("submit", handleNoteCreate);
  document.getElementById("session-form")?.addEventListener("submit", handleSessionCreate);
  document.getElementById("save-transcript")?.addEventListener("click", handleTranscriptSave);
  document.getElementById("mark-reviewed")?.addEventListener("click", handleTranscriptReviewed);
  document.getElementById("rerun-features")?.addEventListener("click", handleRerunFeatures);
  document.getElementById("transcript-file")?.addEventListener("change", handleTranscriptUpload);
  document.getElementById("generate-mock-chat")?.addEventListener("click", handleGenerateMockChat);
  document.getElementById("generate-report")?.addEventListener("click", handleGenerateReport);
  document.getElementById("download-report")?.addEventListener("click", handleDownloadReport);
  document.getElementById("print-report")?.addEventListener("click", handlePrintReport);
}

function handleCaseCreate(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const newCase = {
    case_id: `CASE-${String(cases.length + 1).padStart(3, "0")}`,
    owner_user_id: currentUser.user_id,
    anonymized_child_code: String(data.get("anonymized_child_code")).trim(),
    display_label: `Case ${String.fromCharCode(65 + cases.length)}`,
    age_months: Number(data.get("age_months")),
    sex: String(data.get("sex")),
    primary_concerns: String(data.get("primary_concerns")).trim(),
    external_clinical_status: String(data.get("external_clinical_status")),
    consent_status: String(data.get("consent_status")),
    anonymization_status: String(data.get("anonymization_status")),
    support_level: "Needs review",
    latest_score: 0.5,
    score_trend: [0.5],
    starred: false,
    notes: "Created in standalone therapist app mock mode.",
    created_at: nowIso(),
    updated_at: nowIso(),
  };
  cases.unshift(newCase);
  selectedCaseId = newCase.case_id;
  addAudit("case_created", "child_case", newCase.case_id, `Created anonymized case ${newCase.case_id}`);
  render();
}

function handleSessionCreate(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const file = event.currentTarget.elements.media_file.files[0];
  const errorEl = document.getElementById("file-error");
  if (file) {
    const ext = file.name.split(".").pop().toLowerCase();
    const sizeMb = file.size / 1024 / 1024;
    if (!ALLOWED_FILE_TYPES.includes(ext)) {
      errorEl.textContent = `Unsupported file type .${ext}. Allowed: ${ALLOWED_FILE_TYPES.join(", ")}.`;
      errorEl.hidden = false;
      return;
    }
    if (sizeMb > MAX_FILE_SIZE_MB) {
      errorEl.textContent = `File is ${sizeMb.toFixed(1)} MB. Maximum is ${MAX_FILE_SIZE_MB} MB.`;
      errorEl.hidden = false;
      return;
    }
  }
  const caseId = String(data.get("case_id"));
  const caseItem = cases.find((item) => item.case_id === caseId);
  const sessionId = `SESSION-${String(sessions.length + 1).padStart(3, "0")}`;
  const audioFileId = file ? `AUDIO-${String(audioFiles.length + 1).padStart(3, "0")}` : null;
  sessions.unshift({
    session_id: sessionId,
    case_id: caseId,
    owner_user_id: caseItem.owner_user_id,
    session_date: String(data.get("session_date")),
    session_type: String(data.get("session_type")),
    audio_file_id: audioFileId,
    transcript_id: null,
    feature_extraction_status: file ? "pending" : "not_started",
    ai_analysis_status: "not_started",
    therapist_review_status: "not_started",
    report_status: "not_started",
    notes: String(data.get("notes")).trim(),
  });
  if (file) {
    const ext = file.name.split(".").pop().toLowerCase();
    audioFiles.unshift({
      audio_file_id: audioFileId,
      original_filename: file.name,
      stored_filename: buildStoredFilename(caseId, sessionId, audioFileId, ext),
      file_type: ext,
      file_size: file.size,
      upload_time: nowIso(),
      owner_user_id: caseItem.owner_user_id,
      case_id: caseId,
      session_id: sessionId,
      processing_status: "pending",
    });
    addAudit("file_uploaded", "audio_file", audioFileId, `Created metadata-only mock upload record for ${file.name}`);
  }
  selectedSessionId = sessionId;
  activeView = "transcript";
  addAudit("session_created", "session", sessionId, `Created mock session ${sessionId}`);
  render();
}

function handleCaseUpdate(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const caseId = String(data.get("case_id"));
  const caseItem = cases.find((item) => item.case_id === caseId && canSeeOwner(item.owner_user_id));
  if (!caseItem) return;
  caseItem.age_months = Number(data.get("age_months"));
  caseItem.sex = String(data.get("sex"));
  caseItem.primary_concerns = String(data.get("primary_concerns")).trim();
  caseItem.external_clinical_status = String(data.get("external_clinical_status"));
  caseItem.consent_status = String(data.get("consent_status"));
  caseItem.anonymization_status = String(data.get("anonymization_status"));
  caseItem.notes = String(data.get("notes")).trim();
  caseItem.updated_at = nowIso();
  addAudit("case_updated", "child_case", caseItem.case_id, `Updated anonymized case ${caseItem.case_id}`);
  render();
}

function handleNoteCreate(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const caseId = String(data.get("case_id"));
  const caseItem = cases.find((item) => item.case_id === caseId && canSeeOwner(item.owner_user_id));
  if (!caseItem) return;
  const text = String(data.get("note_text")).trim();
  if (!text) return;
  const sessionId = String(data.get("session_id")) || null;
  const note = {
    note_id: `NOTE-${String(notes.length + 1).padStart(3, "0")}`,
    case_id: caseId,
    session_id: sessionId,
    text,
    created_at: nowIso(),
  };
  notes.unshift(note);
  addAudit("therapist_note_created", "therapist_note", note.note_id, `Added therapist note for ${caseId}`);
  render();
}

function handleTranscriptSave() {
  const session = selectedSession();
  if (!session) return;
  const text = document.getElementById("chat-transcript-text")?.value || "";
  if (text.trim()) {
    const qa = reviewChatText(text);
    const existing = transcriptRecords[session.session_id];
    const transcriptId = existing?.transcript_id || `TRANSCRIPT-${String(Object.keys(transcriptRecords).length + 1).padStart(3, "0")}`;
    transcriptRecords[session.session_id] = {
      transcript_id: transcriptId,
      session_id: session.session_id,
      case_id: session.case_id,
      owner_user_id: session.owner_user_id,
      original_filename: existing?.original_filename || "manual_chat.cha",
      transcript_text: text,
      review_status: qa.qa_status === "fail" ? "needs_correction" : "awaiting_review",
      reviewer_notes: document.getElementById("transcript-reviewer-notes")?.value || "",
      ...qa,
    };
    session.transcript_id = transcriptId;
    session.therapist_review_status = transcriptRecords[session.session_id].review_status;
  }
  const lines = transcriptLines[session.session_id] || [];
  lines.forEach((line, index) => {
    line.speaker = document.querySelector(`[data-line-speaker="${index}"]`)?.value || line.speaker;
    line.text = document.querySelector(`[data-line-text="${index}"]`)?.value || line.text;
  });
  transcriptLines[session.session_id] = lines;
  addAudit("transcript_edited", "session", session.session_id, `Saved CHAT transcript corrections for ${session.session_id}`);
  render();
}

function handleTranscriptReviewed() {
  const session = selectedSession();
  if (!session) return;
  const transcript = transcriptRecords[session.session_id];
  if (transcript) {
    transcript.review_status = "reviewed";
    transcript.reviewer_notes = document.getElementById("transcript-reviewer-notes")?.value || transcript.reviewer_notes;
  }
  session.therapist_review_status = "reviewed";
  session.feature_extraction_status = "pending";
  addAudit("transcript_reviewed", "session", session.session_id, `Marked CHAT transcript reviewed for ${session.session_id}`);
  render();
}

function handleRerunFeatures() {
  const session = selectedSession();
  if (!session) return;
  const transcript = transcriptRecords[session.session_id];
  if (!transcript) return;
  if (transcript.review_status !== "reviewed") {
    transcript.review_status = "awaiting_review";
  }
  const features = extractMockFeaturesForSession(session);
  extractedFeatureOutputs[session.session_id] = {
    feature_id: `FEATURE-${String(Object.keys(extractedFeatureOutputs).length + 1).padStart(3, "0")}`,
    feature_schema_version: "14-feature-schema",
    features,
  };
  aiDecisionOutputs[session.session_id] = generateDecisionSupport(features);
  session.feature_extraction_status = "completed";
  session.ai_analysis_status = "completed";
  session.report_status = "pending";
  addAudit("features_extracted", "session", session.session_id, `Extracted 14-feature schema output for ${session.session_id}`);
  addAudit("ai_output_generated", "ai_screening_output", aiDecisionOutputs[session.session_id].output_id, `Generated AI decision-support output for ${session.session_id}`);
  render();
}

function handleTranscriptUpload(event) {
  const session = selectedSession();
  if (!session) return;
  const file = event.currentTarget.files[0];
  const errorEl = document.getElementById("transcript-error");
  if (!file) return;
  const ext = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED_TRANSCRIPT_FILE_TYPES.includes(ext)) {
    errorEl.textContent = `Unsupported transcript type .${ext}. Allowed: ${ALLOWED_TRANSCRIPT_FILE_TYPES.join(", ")}.`;
    errorEl.hidden = false;
    return;
  }
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    const text = String(reader.result || "");
    const qa = reviewChatText(text);
    const transcriptId = `TRANSCRIPT-${String(Object.keys(transcriptRecords).length + 1).padStart(3, "0")}`;
    transcriptRecords[session.session_id] = {
      transcript_id: transcriptId,
      session_id: session.session_id,
      case_id: session.case_id,
      owner_user_id: session.owner_user_id,
      original_filename: file.name,
      transcript_text: text,
      review_status: qa.qa_status === "fail" ? "needs_correction" : "awaiting_review",
      reviewer_notes: "",
      ...qa,
    };
    session.transcript_id = transcriptId;
    session.therapist_review_status = transcriptRecords[session.session_id].review_status;
    addAudit("transcript_uploaded", "transcript", transcriptId, `Uploaded CHAT transcript ${file.name}`);
    render();
  });
  reader.readAsText(file);
}

function handleGenerateMockChat() {
  const session = selectedSession();
  if (!session) return;
  const caseItem = cases.find((item) => item.case_id === session.case_id);
  const text = mockChatForSession(session, caseItem);
  const qa = reviewChatText(text);
  const transcriptId = `TRANSCRIPT-${String(Object.keys(transcriptRecords).length + 1).padStart(3, "0")}`;
  transcriptRecords[session.session_id] = {
    transcript_id: transcriptId,
    session_id: session.session_id,
    case_id: session.case_id,
    owner_user_id: session.owner_user_id,
    original_filename: "mock_generated_from_audio_metadata.cha",
    transcript_text: text,
    review_status: qa.qa_status === "fail" ? "needs_correction" : "awaiting_review",
    reviewer_notes: "Generated from mock audio metadata. Real audio pipeline not run.",
    ...qa,
  };
  session.transcript_id = transcriptId;
  session.therapist_review_status = transcriptRecords[session.session_id].review_status;
  addAudit("transcript_uploaded", "transcript", transcriptId, `Generated mock CHAT transcript for ${session.session_id}`);
  render();
}

function handleGenerateReport() {
  const caseItem = selectedCase();
  if (!caseItem) return;
  lastGeneratedReportMarkdown = buildProgressReportMarkdown(caseItem);
  const output = document.getElementById("report-output");
  const reportId = `REPORT-${String(generatedReports.length + 1).padStart(3, "0")}`;
  generatedReports.unshift({
    report_id: reportId,
    case_id: caseItem.case_id,
    owner_user_id: caseItem.owner_user_id,
    title: `Progress Report: ${caseItem.anonymized_child_code}`,
    export_status: "completed",
    created_at: nowIso(),
  });
  output.hidden = false;
  output.innerHTML = `
    <div class="report-actions">
      <strong>Progress report ready for ${caseItem.case_id}</strong>
      <div class="action-row">
        <button class="secondary-action" id="download-report">Download Markdown</button>
        <button class="ghost-action" id="print-report">Print / Save PDF</button>
      </div>
    </div>
    <pre>${escapeHtml(lastGeneratedReportMarkdown)}</pre>
  `;
  document.getElementById("download-report")?.addEventListener("click", handleDownloadReport);
  document.getElementById("print-report")?.addEventListener("click", handlePrintReport);
  addAudit("report_exported", "report", reportId, `Generated mock report for ${caseItem.case_id}`);
}

function handleDownloadReport() {
  if (!lastGeneratedReportMarkdown) return;
  const caseItem = selectedCase();
  const blob = new Blob([lastGeneratedReportMarkdown], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${caseItem?.case_id || "case"}_progress_report.md`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function handlePrintReport() {
  window.print();
}

render();
