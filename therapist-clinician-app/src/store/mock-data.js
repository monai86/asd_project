import {
  createUser,
  createChildCase,
  createSession,
  createAudioFile,
  createTranscript,
  createAIReport
} from "@shared/models";

export const mockUsers = [
  createUser({
    user_id: "user_therapist_001",
    name: "Jane Smith",
    credentials: "M.S., CCC-SLP",
    email: "therapist@example.test",
    role: "therapist",
    organization: "Mock Speech Clinic"
  }),
  createUser({
    user_id: "user_clinician_001",
    name: "Ben Clinician",
    credentials: "Clinical Reviewer",
    email: "clinician@example.test",
    role: "clinician",
    organization: "Mock Speech Clinic"
  }),
  createUser({
    user_id: "user_admin_001",
    name: "Research Admin",
    credentials: "Prototype Admin",
    email: "admin@example.test",
    role: "admin",
    organization: "Prototype Admin"
  })
];

export const mockCases = [
  createChildCase({
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
    updated_at: "2026-05-05T13:20:00Z"
  }),
  createChildCase({
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
    updated_at: "2026-05-06T10:00:00Z"
  }),
  createChildCase({
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
    updated_at: "2026-05-07T14:00:00Z"
  })
];

export const mockSessions = [
  createSession({
    session_id: "SESSION-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-20",
    session_type: "free_play",
    audio_file_id: "AUDIO-001",
    transcript_id: "TRANSCRIPT-001",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "awaiting_review",
    report_status: "pending",
    notes: "Child used more spontaneous phrases today and responded better to WH-questions."
  }),
  createSession({
    session_id: "SESSION-002",
    case_id: "CASE-002",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-21",
    session_type: "therapy_session",
    audio_file_id: null,
    transcript_id: null,
    processing_status: "not_started",
    feature_extraction_status: "not_started",
    ai_analysis_status: "not_started",
    therapist_review_status: "not_started",
    report_status: "not_started",
    notes: "Seeded session without uploaded media."
  }),
  createSession({
    session_id: "SESSION-003",
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    session_date: "2026-05-22",
    session_type: "structured_assessment",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-003",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "needs_correction",
    report_status: "pending",
    notes: "Mock transcript needs speaker-label correction."
  })
];

export const mockAudioFiles = [
  createAudioFile({
    audio_file_id: "AUDIO-001",
    original_filename: "session_sample.wav",
    stored_filename: "CASE-001_SESSION-001_AUDIO-001.wav",
    file_type: "wav",
    file_size: 18400000,
    upload_time: "2026-05-20T09:15:00Z",
    owner_user_id: "user_therapist_001",
    case_id: "CASE-001",
    session_id: "SESSION-001",
    processing_status: "completed"
  })
];

export const mockTranscriptLines = {
  "SESSION-001": [
    { speaker: "CHI", text: "want car .", confidence: 0.89 },
    { speaker: "MOT", text: "which car do you want ?", confidence: 0.93 },
    { speaker: "CHI", text: "red car .", confidence: 0.86 },
    { speaker: "CHI", text: "0 .", confidence: 0.74 }
  ],
  "SESSION-003": [
    { speaker: "MOT", text: "tell me what happened .", confidence: 0.91 },
    { speaker: "CHI", text: "xxx then go home .", confidence: 0.51 },
    { speaker: "INV", text: "try again slowly .", confidence: 0.88 }
  ]
};

export const mockTranscriptRecords = {
  "SESSION-001": createTranscript({
    transcript_id: "TRANSCRIPT-001",
    session_id: "SESSION-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    original_filename: "session_001.cha",
    transcript_text: `@Begin
@Languages:	eng
@Participants:	CHI Child Target_Child, MOT Mother Mother
@ID:	eng|Mock|CHI|4;08.00|male|||Target_Child|||
@ID:	eng|Mock|MOT|||||Mother|||
*CHI:	want car .
*MOT:	which car do you want ?
*CHI:	red car .
@End`,
    review_status: "awaiting_review",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-003": createTranscript({
    transcript_id: "TRANSCRIPT-003",
    session_id: "SESSION-003",
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    original_filename: "session_003.cha",
    transcript_text: `@Begin
@Languages:	eng
@Participants:	CHI Child Target_Child, MOT Mother Mother
@ID:	eng|Mock|CHI|4;06.00||||Target_Child|||
@ID:	eng|Mock|MOT|||||Mother|||
*MOT:	tell me what happened .
*CHI:	xxx then go home .
@End`,
    review_status: "needs_correction",
    qa_status: "needs_review",
    qa_score: 92,
    qa_issues: [
      {
        code: "LOW_CONFIDENCE_SEGMENT",
        severity: "warning",
        message: "Mock transcript contains low-confidence child text."
      }
    ],
    reviewer_notes: "Speaker-label correction needed before feature interpretation."
  })
};

export const mockGoals = [
  { goal_id: "GOAL-001", case_id: "CASE-001", text: "Increase spontaneous two-word utterances during play.", status: "active" },
  { goal_id: "GOAL-004", case_id: "CASE-001", text: "Improve response to open WH-questions.", status: "active" },
  { goal_id: "GOAL-005", case_id: "CASE-001", text: "Extend reciprocal turn-taking in play routines.", status: "active" },
  { goal_id: "GOAL-002", case_id: "CASE-002", text: "Improve transcript-ready session sampling consistency.", status: "active" },
  { goal_id: "GOAL-003", case_id: "CASE-003", text: "Monitor intelligibility and speaker-label quality.", status: "active" }
];

export const mockNotes = [
  { note_id: "NOTE-001", case_id: "CASE-001", text: "Parent reports more requesting at home; verify in next session.", created_at: "2026-05-06T11:20:00Z" },
  { note_id: "NOTE-002", case_id: "CASE-003", text: "Correct low-confidence child line before interpreting features.", created_at: "2026-05-07T15:45:00Z" }
];

export const mockGeneratedReports = [
  createAIReport({
    report_id: "REPORT-001",
    case_id: "CASE-001",
    session_id: "SESSION-001",
    owner_user_id: "user_therapist_001",
    title: "Progress Report: CHI-A01",
    export_status: "completed",
    created_at: "2026-05-20T10:20:00Z"
  })
];

export const mockFeatureRows = [
  { domain: "Social Communication", feature: "Turn-taking", result: "0.62 / 1.00", change: "+ 0.12", direction: "up", icon: "sc" },
  { domain: "Language", feature: "Mean Length of Utterance", result: "3.25 words", change: "+ 0.45", direction: "up", icon: "la" },
  { domain: "Language", feature: "Vocabulary Diversity", result: "0.38", change: "+ 0.05", direction: "up", icon: "la" },
  { domain: "Repetitive Patterns", feature: "Repetitive Phrases", result: "High", change: "- 0.08", direction: "down", icon: "rp" },
  { domain: "ASD-specific Markers", feature: "Pronoun Reversal", result: "Occasional", change: "+ 0.10", direction: "down", icon: "am" }
];

export const mockFactorGroups = {
  increasing: [
    ["Repetitive phrase frequency", "+0.23"],
    ["Limited reciprocal response", "+0.18"],
    ["Restricted interests", "+0.12"]
  ],
  reducing: [
    ["Improved turn-taking", "-0.15"],
    ["More varied vocabulary", "-0.10"],
    ["Better eye contact", "-0.08"]
  ]
};

export const featureSchema = [
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
  ["pronoun_reversal_count", "Pronoun reversal count", "ASD-relevant markers"]
];

export const mockExtractedFeatureOutputs = {
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
      pronoun_reversal_count: 0
    }
  }
};

export const mockAiDecisionOutputs = {
  "SESSION-001": {
    output_id: "AI-OUTPUT-001",
    concern_level: "moderate_concern",
    screening_support_score: 0.68,
    top_contributing_features: ["echolalia_ratio", "mlu", "ttr"],
    evidence_items: [
      "Repetition markers should be reviewed in the transcript context.",
      "Short utterance length can reflect language sample limits.",
      "Lexical diversity should be compared across similar sessions."
    ],
    explanation: "Decision-support only. Review transcript QA, session context, and therapist notes before interpreting this output."
  }
};

export function seedStore(storeInstance) {
  storeInstance.setState({
    currentUser: null,
    activeView: "dashboard",
    selectedCaseId: "CASE-001",
    selectedSessionId: "SESSION-001",
    cases: mockCases,
    sessions: mockSessions,
    audioFiles: mockAudioFiles,
    transcripts: mockTranscriptRecords,
    transcriptLines: mockTranscriptLines,
    goals: mockGoals,
    notes: mockNotes,
    generatedReports: mockGeneratedReports,
    aiDecisionOutputs: mockAiDecisionOutputs,
    extractedFeatureOutputs: mockExtractedFeatureOutputs,
    auditLogs: []
  });
}
