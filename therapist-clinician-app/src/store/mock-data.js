import {
  createUser,
  createChildCase,
  createSession,
  createAudioFile,
  createTranscript,
  createAIReport
} from "@shared/models";
import {
  createPersistenceAdapter,
  snapshotFromState,
  stateFromSnapshot
} from "../persistence/repository.js";
import { detectClinicalReviewFlags } from "../services/transcript-workflow-service.js";

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
    anonymized_child_code: "CHI-ภูมิ",
    display_label: "น้องภูมิ",
    age_months: 48,
    sex: "male",
    primary_concerns: "พูดทวนคำถาม (Echolalia) และสับสนการใช้สรรพนาม (Pronoun Reversal)",
    external_clinical_status: "under_evaluation",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "High",
    latest_score: 0.78,
    score_trend: [0.65, 0.72, 0.78],
    starred: true,
    notes: "มีพฤติกรรมพูดเลียนเสียงทันทีหลังฟังจบ แสดงความต้องการโดยการสลับคำว่า 'หนู' กับ 'คุณครู' (เช่น หนูอยากเล่นรถ แต่ใช้คำว่า ครูอยากเล่นรถ)",
    created_at: "2026-05-02T09:00:00Z",
    updated_at: "2026-05-20T13:20:00Z"
  }),
  createChildCase({
    case_id: "CASE-002",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-มีนา",
    display_label: "น้องมีนา",
    age_months: 52,
    sex: "female",
    primary_concerns: "พัฒนาการปกติ (Typical Development) - ติดตามพัฒนาการทั่วไป",
    external_clinical_status: "not_provided",
    consent_status: "pending",
    anonymization_status: "anonymized",
    support_level: "Low",
    latest_score: 0.15,
    score_trend: [0.18, 0.15],
    starred: true,
    notes: "พัฒนาการภาษาและสังคมสมวัย มีทักษะการเล่นสมมติและการผลัดกันสนทนาได้ดี",
    created_at: "2026-05-03T09:00:00Z",
    updated_at: "2026-05-21T10:00:00Z"
  }),
  createChildCase({
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    anonymized_child_code: "CHI-คอปเตอร์",
    display_label: "น้องคอปเตอร์",
    age_months: 60,
    sex: "male",
    primary_concerns: "ออกเสียงไม่ชัดเจนอย่างมีนัยสำคัญ (High Unintelligible Speech Ratio)",
    external_clinical_status: "external_non_asd_recorded",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "Medium",
    latest_score: 0.57,
    score_trend: [0.52, 0.54, 0.57],
    starred: false,
    notes: "มีสัดส่วนคำพูดที่ผู้ฟังไม่เข้าใจ (xxx) ค่อนข้างสูงในการคุยโต้ตอบทั่วไป",
    created_at: "2026-05-04T09:00:00Z",
    updated_at: "2026-05-22T14:00:00Z"
  }),
  createChildCase({
    case_id: "CASE-004",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-เอ็ม",
    display_label: "น้องเอ็ม",
    age_months: 42,
    sex: "male",
    primary_concerns: "ล่าช้าในการสื่อสารสังคม สบตาน้อย และไม่เล่นร่วมกับผู้อื่น",
    external_clinical_status: "under_evaluation",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "High",
    latest_score: 0.85,
    score_trend: [0.79, 0.82, 0.85],
    starred: false,
    notes: "หลีกเลี่ยงการสบตา ไม่ตอบสนองต่อเสียงเรียกชื่อตนเองเกือบทั้งหมด ชอบเล่นล้อรถหมุนๆ",
    created_at: "2026-05-05T09:00:00Z",
    updated_at: "2026-05-23T11:00:00Z"
  }),
  createChildCase({
    case_id: "CASE-005",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-ปันปัน",
    display_label: "น้องปันปัน",
    age_months: 46,
    sex: "female",
    primary_concerns: "ความล่าช้าในการสื่อความหมายทางภาษา (Expressive Language Delay)",
    external_clinical_status: "under_evaluation",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "Medium",
    latest_score: 0.48,
    score_trend: [0.42, 0.45, 0.48],
    starred: true,
    notes: "เข้าใจคำสั่งได้ดีแต่พูดตอบกลับเป็นประโยคยาวๆ ไม่ค่อยได้ มักชี้บอกความต้องการหรือพูดคำเดี่ยว",
    created_at: "2026-05-06T09:00:00Z",
    updated_at: "2026-05-24T12:00:00Z"
  }),
  createChildCase({
    case_id: "CASE-006",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-วิน",
    display_label: "น้องวิน",
    age_months: 55,
    sex: "male",
    primary_concerns: "ปัญหาการออกเสียงพยัญชนะไทย (Articulation Issues - เช่น ร, ล)",
    external_clinical_status: "not_provided",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "Low",
    latest_score: 0.28,
    score_trend: [0.32, 0.28],
    starred: false,
    notes: "ออกเสียงควบกล้ำและสระบางเสียงเพี้ยนไป ไม่พบความล่าช้าด้านการสื่อสารทางสังคม",
    created_at: "2026-05-07T09:00:00Z",
    updated_at: "2026-05-25T15:00:00Z"
  }),
  createChildCase({
    case_id: "CASE-007",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-ลินดา",
    display_label: "น้องลินดา",
    age_months: 50,
    sex: "female",
    primary_concerns: "ความผิดปกติของรูปแบบการผลัดกันพูด (Atypical Turn-taking & Intonation)",
    external_clinical_status: "under_evaluation",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "Medium",
    latest_score: 0.52,
    score_trend: [0.48, 0.52],
    starred: false,
    notes: "มักแย่งจังหวะคู่สนทนาและไม่รอฟังคู่สนทนาพูดจบ ใช้น้ำเสียงราบเรียบระดับเดียวในการแสดงออก",
    created_at: "2026-05-08T09:00:00Z",
    updated_at: "2026-05-26T14:30:00Z"
  }),
  createChildCase({
    case_id: "CASE-008",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-ไบร์ท",
    display_label: "น้องไบร์ท",
    age_months: 62,
    sex: "male",
    primary_concerns: "ติดตามพัฒนาการด้านภาษาทั่วไป (Typical Progress Tracking)",
    external_clinical_status: "not_provided",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "Low",
    latest_score: 0.18,
    score_trend: [0.22, 0.18],
    starred: false,
    notes: "พัฒนาการเรียนรู้และภาษาตามวัย สามารถสนทนาโต้ตอบชัดเจนและตั้งใจฟังดีมาก",
    created_at: "2026-05-09T09:00:00Z",
    updated_at: "2026-05-27T09:30:00Z"
  }),
  createChildCase({
    case_id: "CASE-009",
    owner_user_id: "user_therapist_001",
    anonymized_child_code: "CHI-แก้ม",
    display_label: "น้องแก้ม",
    age_months: 44,
    sex: "female",
    primary_concerns: "คำคลังศัพท์น้อยมาก ร่วมกับพูดทวนแบบดีเลย์ (Delayed Echolalia)",
    external_clinical_status: "under_evaluation",
    consent_status: "granted",
    anonymization_status: "anonymized",
    support_level: "High",
    latest_score: 0.72,
    score_trend: [0.68, 0.70, 0.72],
    starred: true,
    notes: "ชอบนำวลีหรือเนื้อหาจากการ์ตูนมาพูดซ้ำบ่อยๆ โดยไม่สอดคล้องกับบริบทปัจจุบัน มีคำคลังศัพท์น้อยกว่า 30 คำ",
    created_at: "2026-05-10T09:00:00Z",
    updated_at: "2026-05-28T16:00:00Z"
  })
];

export const mockSessions = [
  createSession({
    session_id: "SESSION-001-A",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    session_date: "2026-04-01",
    session_type: "free_play",
    audio_file_id: "AUDIO-001-A",
    transcript_id: "TRANSCRIPT-001-A",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "reviewed",
    report_status: "completed",
    notes: "Initial session. Child showed limited vocabulary, repeating 'car' many times when prompted. Very low spontaneous phrases."
  }),
  createSession({
    session_id: "SESSION-001-B",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-01",
    session_type: "free_play",
    audio_file_id: "AUDIO-001-B",
    transcript_id: "TRANSCRIPT-001-B",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "reviewed",
    report_status: "completed",
    notes: "Second session. Added some new toys (blocks). MLU improved slightly. Repetitive phrases (echolalia) decreased."
  }),
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
    notes: "Latest session. Child used more spontaneous phrases today and responded better to WH-questions."
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
  }),
  createSession({
    session_id: "SESSION-004",
    case_id: "CASE-004",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-23",
    session_type: "free_play",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-004",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "awaiting_review",
    report_status: "pending",
    notes: "High concern case. Significant lack of verbal responsiveness."
  }),
  createSession({
    session_id: "SESSION-005",
    case_id: "CASE-005",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-24",
    session_type: "therapy_session",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-005",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "reviewed",
    report_status: "completed",
    notes: "Shows expressive delay. Mostly single words or gestures."
  }),
  createSession({
    session_id: "SESSION-006",
    case_id: "CASE-006",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-25",
    session_type: "structured_assessment",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-006",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "reviewed",
    report_status: "completed",
    notes: "Substituted articulation issues observed (e.g. 'lay' for 'play')."
  }),
  createSession({
    session_id: "SESSION-007",
    case_id: "CASE-007",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-26",
    session_type: "free_play",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-007",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "reviewed",
    report_status: "completed",
    notes: "Atypical turn taking. Interrupted therapist constantly."
  }),
  createSession({
    session_id: "SESSION-008",
    case_id: "CASE-008",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-27",
    session_type: "free_play",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-008",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "reviewed",
    report_status: "completed",
    notes: "Typical development, normal speech flow."
  }),
  createSession({
    session_id: "SESSION-009",
    case_id: "CASE-009",
    owner_user_id: "user_therapist_001",
    session_date: "2026-05-28",
    session_type: "therapy_session",
    audio_file_id: null,
    transcript_id: "TRANSCRIPT-009",
    processing_status: "transcript_ready",
    feature_extraction_status: "completed",
    ai_analysis_status: "completed",
    therapist_review_status: "reviewed",
    report_status: "completed",
    notes: "Delayed echolalia observed. Repeated movie quotes."
  })
];

export const mockAudioFiles = [
  {
    ...createAudioFile({
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
    }),
    storage_mode: "metadata_only"
  }
];

export const mockTranscriptLines = {
  "SESSION-001-A": [
    { speaker: "CHI", text: "car .", confidence: 0.82, timing: { start_time: 1.5, end_time: 2.2 } },
    { speaker: "MOT", text: "what ?", confidence: 0.90, timing: { start_time: 2.5, end_time: 3.0 } },
    { speaker: "CHI", text: "car .", confidence: 0.88, timing: { start_time: 3.2, end_time: 3.8 } },
    { speaker: "CHI", text: "car .", confidence: 0.85, timing: { start_time: 4.2, end_time: 4.8 } },
    { speaker: "MOT", text: "yes , car .", confidence: 0.95, timing: { start_time: 5.0, end_time: 5.8 } },
    { speaker: "CHI", text: "car .", confidence: 0.86, timing: { start_time: 6.0, end_time: 6.6 } }
  ],
  "SESSION-001-B": [
    { speaker: "CHI", text: "red car .", confidence: 0.85, timing: { start_time: 1.0, end_time: 2.1 } },
    { speaker: "MOT", text: "where is it ?", confidence: 0.92, timing: { start_time: 2.5, end_time: 3.8 } },
    { speaker: "CHI", text: "red car .", confidence: 0.88, timing: { start_time: 4.0, end_time: 5.2 } },
    { speaker: "CHI", text: "go block .", confidence: 0.76, timing: { start_time: 5.5, end_time: 6.8 } },
    { speaker: "MOT", text: "play blocks ?", confidence: 0.94, timing: { start_time: 7.0, end_time: 8.2 } },
    { speaker: "CHI", text: "block .", confidence: 0.84, timing: { start_time: 8.5, end_time: 9.3 } }
  ],
  "SESSION-001": [
    { speaker: "CHI", text: "want car .", confidence: 0.89, timing: { start_time: 1.2, end_time: 2.5 } },
    { speaker: "MOT", text: "which car do you want ?", confidence: 0.93, timing: { start_time: 2.8, end_time: 4.2 } },
    { speaker: "CHI", text: "red car .", confidence: 0.86, timing: { start_time: 4.5, end_time: 5.6 } },
    { speaker: "CHI", text: "play blocks now .", confidence: 0.82, timing: { start_time: 6.0, end_time: 7.5 } },
    { speaker: "MOT", text: "okay let's play blocks .", confidence: 0.95, timing: { start_time: 7.8, end_time: 9.2 } },
    { speaker: "CHI", text: "build tower .", confidence: 0.79, timing: { start_time: 9.5, end_time: 10.8 } },
    { speaker: "CHI", text: "0 .", confidence: 0.74, timing: { start_time: 11.2, end_time: 12.0 } }
  ],
  "SESSION-003": [
    { speaker: "MOT", text: "tell me what happened .", confidence: 0.91, timing: { start_time: 1.0, end_time: 3.5 } },
    { speaker: "CHI", text: "xxx then go home .", confidence: 0.51, timing: { start_time: 4.2, end_time: 6.0 } },
    { speaker: "INV", text: "try again slowly .", confidence: 0.88, timing: { start_time: 6.5, end_time: 8.2 } }
  ],
  "SESSION-004": [
    { speaker: "INV", text: "hello Em .", confidence: 0.92, timing: { start_time: 1.0, end_time: 2.0 } },
    { speaker: "CHI", text: "0 .", confidence: 0.80, timing: { start_time: 2.5, end_time: 3.5 } },
    { speaker: "MOT", text: "look at therapist please .", confidence: 0.90, timing: { start_time: 4.0, end_time: 6.0 } },
    { speaker: "CHI", text: "xxx .", confidence: 0.45, timing: { start_time: 6.5, end_time: 8.0 } },
    { speaker: "CHI", text: "0 .", confidence: 0.85, timing: { start_time: 8.5, end_time: 9.5 } }
  ],
  "SESSION-005": [
    { speaker: "INV", text: "what is this ?", confidence: 0.95, timing: { start_time: 1.0, end_time: 2.0 } },
    { speaker: "CHI", text: "candy .", confidence: 0.92, timing: { start_time: 2.5, end_time: 3.2 } },
    { speaker: "INV", text: "do you want it ?", confidence: 0.93, timing: { start_time: 3.8, end_time: 4.8 } },
    { speaker: "CHI", text: "want candy .", confidence: 0.88, timing: { start_time: 5.2, end_time: 6.5 } }
  ],
  "SESSION-006": [
    { speaker: "INV", text: "let's play a game .", confidence: 0.96, timing: { start_time: 1.0, end_time: 2.5 } },
    { speaker: "CHI", text: "I want to lay with the red car .", confidence: 0.84, timing: { start_time: 3.0, end_time: 5.2 } }
  ],
  "SESSION-007": [
    { speaker: "INV", text: "what did you do—", confidence: 0.90, timing: { start_time: 1.0, end_time: 1.8 } },
    { speaker: "CHI", text: "go to school play with toys and eat ice cream .", confidence: 0.88, timing: { start_time: 1.5, end_time: 4.5 } }
  ],
  "SESSION-008": [
    { speaker: "INV", text: "wow you drew a big tree .", confidence: 0.95, timing: { start_time: 1.0, end_time: 3.0 } },
    { speaker: "CHI", text: "yes I can draw a big tree now .", confidence: 0.91, timing: { start_time: 3.5, end_time: 6.0 } }
  ],
  "SESSION-009": [
    { speaker: "INV", text: "what color is this ?", confidence: 0.94, timing: { start_time: 1.0, end_time: 2.2 } },
    { speaker: "CHI", text: "let's go green grass .", confidence: 0.86, timing: { start_time: 2.8, end_time: 4.5 } }
  ]
};

export const mockTranscriptRecords = {
  "SESSION-001-A": createTranscript({
    transcript_id: "TRANSCRIPT-001-A",
    session_id: "SESSION-001-A",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    original_filename: "session_001_a.cha",
    transcript_text: `@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child, MOT Mother Mother\n@ID:\teng|Mock|CHI|4;06.00|male|||Target_Child|||\n@ID:\teng|Mock|MOT|||||Mother|||\n*CHI:\tcar .\n*MOT:\twhat ?\n*CHI:\tcar .\n*CHI:\tcar .\n*MOT:\tyes , car .\n*CHI:\tcar .\n@End`,
    review_status: "reviewed",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-001-B": createTranscript({
    transcript_id: "TRANSCRIPT-001-B",
    session_id: "SESSION-001-B",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    original_filename: "session_001_b.cha",
    transcript_text: `@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child, MOT Mother Mother\n@ID:\teng|Mock|CHI|4;07.00|male|||Target_Child|||\n@ID:\teng|Mock|MOT|||||Mother|||\n*CHI:\tred car .\n*MOT:\twhere is it ?\n*CHI:\tred car .\n*CHI:\tgo block .\n*MOT:\tplay blocks ?\n*CHI:\tblock .\n@End`,
    review_status: "reviewed",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-001": createTranscript({
    transcript_id: "TRANSCRIPT-001",
    session_id: "SESSION-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    original_filename: "session_001.cha",
    transcript_text: `@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child, MOT Mother Mother\n@ID:\teng|Mock|CHI|4;08.00|male|||Target_Child|||\n@ID:\teng|Mock|MOT|||||Mother|||\n*CHI:\twant car .\n*MOT:\twhich car do you want ?\n*CHI:\tred car .\n*CHI:\tplay blocks now .\n*MOT:\tokay let's play blocks .\n*CHI:\tbuild tower .\n@End`,
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
    transcript_text: `@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child, MOT Mother Mother\n@ID:\teng|Mock|CHI|4;06.00||||Target_Child|||\n@ID:\teng|Mock|MOT|||||Mother|||\n*MOT:\ttell me what happened .\n*CHI:\txxx then go home .\n@End`,
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
  }),
  "SESSION-004": createTranscript({
    transcript_id: "TRANSCRIPT-004",
    session_id: "SESSION-004",
    case_id: "CASE-004",
    owner_user_id: "user_therapist_001",
    original_filename: "session_004.cha",
    transcript_text: `@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child, INV Investigator, MOT Mother\n@ID:\teng|Mock|CHI|3;06.00|male|||Target_Child|||\n@ID:\teng|Mock|INV|||||Investigator|||\n*INV:\thello Em .\n*CHI:\t0 .\n*MOT:\tlook at therapist please .\n*CHI:\txxx .\n*CHI:\t0 .\n@End`,
    review_status: "awaiting_review",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-005": createTranscript({
    transcript_id: "TRANSCRIPT-005",
    session_id: "SESSION-005",
    case_id: "CASE-005",
    owner_user_id: "user_therapist_001",
    original_filename: "session_005.cha",
    transcript_text: `@Begin\n@Languages:\teng\n*INV:\twhat is this ?\n*CHI:\tcandy .\n*INV:\tdo you want it ?\n*CHI:\twant candy .\n@End`,
    review_status: "reviewed",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-006": createTranscript({
    transcript_id: "TRANSCRIPT-006",
    session_id: "SESSION-006",
    case_id: "CASE-006",
    owner_user_id: "user_therapist_001",
    original_filename: "session_006.cha",
    transcript_text: `@Begin\n@Languages:\teng\n*INV:\tlet's play a game .\n*CHI:\tI want to lay with the red car .\n@End`,
    review_status: "reviewed",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-007": createTranscript({
    transcript_id: "TRANSCRIPT-007",
    session_id: "SESSION-007",
    case_id: "CASE-007",
    owner_user_id: "user_therapist_001",
    original_filename: "session_007.cha",
    transcript_text: `@Begin\n@Languages:\teng\n*INV:\twhat did you do—\n*CHI:\tgo to school play with toys and eat ice cream .\n@End`,
    review_status: "reviewed",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-008": createTranscript({
    transcript_id: "TRANSCRIPT-008",
    session_id: "SESSION-008",
    case_id: "CASE-008",
    owner_user_id: "user_therapist_001",
    original_filename: "session_008.cha",
    transcript_text: `@Begin\n@Languages:\teng\n*INV:\twow you drew a big tree .\n*CHI:\tyes I can draw a big tree now .\n@End`,
    review_status: "reviewed",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  }),
  "SESSION-009": createTranscript({
    transcript_id: "TRANSCRIPT-009",
    session_id: "SESSION-009",
    case_id: "CASE-009",
    owner_user_id: "user_therapist_001",
    original_filename: "session_009.cha",
    transcript_text: `@Begin\n@Languages:\teng\n*INV:\twhat color is this ?\n*CHI:\tlet's go green grass .\n@End`,
    review_status: "reviewed",
    qa_status: "pass",
    qa_score: 100,
    qa_issues: []
  })
};

export const mockGoals = [
  { goal_id: "GOAL-001", case_id: "CASE-001", owner_user_id: "user_therapist_001", text: "Increase Mean Length of Utterance (MLU >= 3.0 words).", goal_text: "Increase Mean Length of Utterance (MLU >= 3.0 words).", status: "active", metric: "mlu", target_value: 3.0, current_value: 2.33, created_at: "2026-05-02T09:30:00Z", updated_at: "2026-05-20T10:00:00Z" },
  { goal_id: "GOAL-004", case_id: "CASE-001", owner_user_id: "user_therapist_001", text: "Improve vocabulary diversity (TTR >= 0.50).", goal_text: "Improve vocabulary diversity (TTR >= 0.50).", status: "active", metric: "ttr", target_value: 0.50, current_value: 0.86, created_at: "2026-05-02T09:40:00Z", updated_at: "2026-05-20T10:00:00Z" },
  { goal_id: "GOAL-005", case_id: "CASE-001", owner_user_id: "user_therapist_001", text: "Reduce Echolalia Ratio (Echolalia <= 0.20).", goal_text: "Reduce Echolalia Ratio (Echolalia <= 0.20).", status: "active", metric: "echolalia_ratio", target_value: 0.20, current_value: 0.33, created_at: "2026-05-02T09:50:00Z", updated_at: "2026-05-20T10:00:00Z" },
  { goal_id: "GOAL-002", case_id: "CASE-002", owner_user_id: "user_therapist_001", text: "Improve transcript-ready session sampling consistency.", goal_text: "Improve transcript-ready session sampling consistency.", status: "active", metric: "none", target_value: 0, current_value: 0, created_at: "2026-05-03T09:30:00Z", updated_at: "2026-05-03T09:30:00Z" },
  { goal_id: "GOAL-003", case_id: "CASE-003", owner_user_id: "user_clinician_001", text: "Monitor intelligibility and speaker-label quality.", goal_text: "Monitor intelligibility and speaker-label quality.", status: "active", metric: "none", target_value: 0, current_value: 0, created_at: "2026-05-04T09:30:00Z", updated_at: "2026-05-04T09:30:00Z" }
];

export const mockNotes = [
  { note_id: "NOTE-001", case_id: "CASE-001", session_id: null, owner_user_id: "user_therapist_001", text: "Parent reports more requesting at home; verify in next session.", note_text: "Parent reports more requesting at home; verify in next session.", created_at: "2026-05-06T11:20:00Z", updated_at: "2026-05-06T11:20:00Z" },
  { note_id: "NOTE-002", case_id: "CASE-003", session_id: "SESSION-003", owner_user_id: "user_clinician_001", text: "Correct low-confidence child line before interpreting features.", note_text: "Correct low-confidence child line before interpreting features.", created_at: "2026-05-07T15:45:00Z", updated_at: "2026-05-07T15:45:00Z" }
];

export const mockGeneratedReports = [
  createAIReport({
    report_id: "REPORT-001",
    case_id: "CASE-001",
    session_id: "SESSION-001",
    owner_user_id: "user_therapist_001",
    title: "Progress Report: CHI-ภูมิ",
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
  "SESSION-001-A": {
    feature_id: "FEATURE-001-A",
    session_id: "SESSION-001-A",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-04-01T10:00:00Z",
    features: {
      age_months: 46,
      total_utterances: 4,
      mlu: 1.00,
      mluw: 1.00,
      ttr: 0.25,
      total_words: 4,
      unintelligible_count: 0,
      unintelligible_ratio: 0.0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0,
      echolalia_count: 3,
      echolalia_ratio: 0.75,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-001-B": {
    feature_id: "FEATURE-001-B",
    session_id: "SESSION-001-B",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-01T10:00:00Z",
    features: {
      age_months: 47,
      total_utterances: 4,
      mlu: 1.50,
      mluw: 1.50,
      ttr: 0.50,
      total_words: 6,
      unintelligible_count: 0,
      unintelligible_ratio: 0.0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0,
      echolalia_count: 2,
      echolalia_ratio: 0.50,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-001": {
    feature_id: "FEATURE-001",
    session_id: "SESSION-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-20T10:00:00Z",
    features: {
      age_months: 48,
      total_utterances: 5,
      mlu: 2.33,
      mluw: 2.33,
      ttr: 0.86,
      total_words: 8,
      unintelligible_count: 0,
      unintelligible_ratio: 0.0,
      zero_vocalization_count: 1,
      nonverbal_vocalization_count: 0,
      question_ratio: 0.15,
      echolalia_count: 1,
      echolalia_ratio: 0.20,
      pronoun_reversal_count: 1
    }
  },
  "SESSION-003": {
    feature_id: "FEATURE-003",
    session_id: "SESSION-003",
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-22T10:00:00Z",
    features: {
      age_months: 60,
      total_utterances: 2,
      mlu: 3.5,
      mluw: 3.5,
      ttr: 0.70,
      total_words: 7,
      unintelligible_count: 1,
      unintelligible_ratio: 0.50,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0,
      echolalia_count: 0,
      echolalia_ratio: 0,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-004": {
    feature_id: "FEATURE-004",
    session_id: "SESSION-004",
    case_id: "CASE-004",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-23T10:00:00Z",
    features: {
      age_months: 42,
      total_utterances: 4,
      mlu: 0.5,
      mluw: 0.5,
      ttr: 0.10,
      total_words: 2,
      unintelligible_count: 1,
      unintelligible_ratio: 0.25,
      zero_vocalization_count: 2,
      nonverbal_vocalization_count: 1,
      question_ratio: 0,
      echolalia_count: 0,
      echolalia_ratio: 0,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-005": {
    feature_id: "FEATURE-005",
    session_id: "SESSION-005",
    case_id: "CASE-005",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-24T10:00:00Z",
    features: {
      age_months: 46,
      total_utterances: 2,
      mlu: 1.5,
      mluw: 1.5,
      ttr: 0.66,
      total_words: 3,
      unintelligible_count: 0,
      unintelligible_ratio: 0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0,
      echolalia_count: 0,
      echolalia_ratio: 0,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-006": {
    feature_id: "FEATURE-006",
    session_id: "SESSION-006",
    case_id: "CASE-006",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-25T10:00:00Z",
    features: {
      age_months: 55,
      total_utterances: 1,
      mlu: 8.0,
      mluw: 8.0,
      ttr: 0.90,
      total_words: 8,
      unintelligible_count: 0,
      unintelligible_ratio: 0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0,
      echolalia_count: 0,
      echolalia_ratio: 0,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-007": {
    feature_id: "FEATURE-007",
    session_id: "SESSION-007",
    case_id: "CASE-007",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-26T10:00:00Z",
    features: {
      age_months: 50,
      total_utterances: 1,
      mlu: 10.0,
      mluw: 10.0,
      ttr: 0.85,
      total_words: 10,
      unintelligible_count: 0,
      unintelligible_ratio: 0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0.1,
      echolalia_count: 0,
      echolalia_ratio: 0,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-008": {
    feature_id: "FEATURE-008",
    session_id: "SESSION-008",
    case_id: "CASE-008",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-27T10:00:00Z",
    features: {
      age_months: 62,
      total_utterances: 1,
      mlu: 9.0,
      mluw: 9.0,
      ttr: 0.88,
      total_words: 9,
      unintelligible_count: 0,
      unintelligible_ratio: 0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0.0,
      echolalia_count: 0,
      echolalia_ratio: 0,
      pronoun_reversal_count: 0
    }
  },
  "SESSION-009": {
    feature_id: "FEATURE-009",
    session_id: "SESSION-009",
    case_id: "CASE-009",
    owner_user_id: "user_therapist_001",
    feature_schema_version: "14-feature-schema",
    extraction_status: "completed",
    created_at: "2026-05-28T10:00:00Z",
    features: {
      age_months: 44,
      total_utterances: 1,
      mlu: 5.0,
      mluw: 5.0,
      ttr: 0.75,
      total_words: 5,
      unintelligible_count: 0,
      unintelligible_ratio: 0,
      zero_vocalization_count: 0,
      nonverbal_vocalization_count: 0,
      question_ratio: 0.0,
      echolalia_count: 1,
      echolalia_ratio: 1.0,
      pronoun_reversal_count: 0
    }
  }
};

export const mockAiDecisionOutputs = {
  "SESSION-001-A": {
    output_id: "AI-OUTPUT-001-A",
    session_id: "SESSION-001-A",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    concern_level: "moderate_concern",
    screening_support_score: 0.78,
    top_contributing_features: ["echolalia_ratio", "mlu"],
    evidence_items: ["High echolalia ratio (0.75)", "Extremely low MLU (1.00)"],
    explanation: "Initial screening indicates high repetition rates and low speech length.",
    therapist_review_status: "reviewed",
    created_at: "2026-04-01T10:05:00Z"
  },
  "SESSION-001-B": {
    output_id: "AI-OUTPUT-001-B",
    session_id: "SESSION-001-B",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    concern_level: "moderate_concern",
    screening_support_score: 0.58,
    top_contributing_features: ["echolalia_ratio", "mlu"],
    evidence_items: ["Moderate echolalia ratio (0.50)", "Improved MLU (1.50)"],
    explanation: "Echolalia decreased and sentence length improved compared to session A.",
    therapist_review_status: "reviewed",
    created_at: "2026-05-01T10:05:00Z"
  },
  "SESSION-001": {
    output_id: "AI-OUTPUT-001",
    session_id: "SESSION-001",
    case_id: "CASE-001",
    owner_user_id: "user_therapist_001",
    concern_level: "watchful_review",
    screening_support_score: 0.40,
    top_contributing_features: ["echolalia_ratio", "mlu", "ttr"],
    evidence_items: [
      "Repetition markers should be reviewed in the transcript context.",
      "Short utterance length can reflect language sample limits.",
      "Lexical diversity should be compared across similar sessions."
    ],
    explanation: "Decision-support only. Review transcript QA, session context, and therapist notes before interpreting this output. This system does not diagnose ASD.",
    therapist_review_status: "awaiting_review",
    created_at: "2026-05-20T10:05:00Z"
  },
  "SESSION-003": {
    output_id: "AI-OUTPUT-003",
    session_id: "SESSION-003",
    case_id: "CASE-003",
    owner_user_id: "user_clinician_001",
    concern_level: "watchful_review",
    screening_support_score: 0.57,
    top_contributing_features: ["unintelligible_ratio", "mlu"],
    evidence_items: ["High unintelligible ratio (0.50)", "Normal MLU (3.50)"],
    explanation: "Significant ratio of unintelligible segments. Needs human speaker validation.",
    therapist_review_status: "needs_correction",
    created_at: "2026-05-22T10:05:00Z"
  },
  "SESSION-004": {
    output_id: "AI-OUTPUT-004",
    session_id: "SESSION-004",
    case_id: "CASE-004",
    owner_user_id: "user_therapist_001",
    concern_level: "moderate_concern",
    screening_support_score: 0.85,
    top_contributing_features: ["zero_vocalization_count", "mlu"],
    evidence_items: ["Very high zero-vocalization rate", "Extremely low MLU (0.50)"],
    explanation: "High screening score driven by lack of active verbal engagement. Requires clinical interpretation.",
    therapist_review_status: "awaiting_review",
    created_at: "2026-05-23T10:05:00Z"
  },
  "SESSION-005": {
    output_id: "AI-OUTPUT-005",
    session_id: "SESSION-005",
    case_id: "CASE-005",
    owner_user_id: "user_therapist_001",
    concern_level: "watchful_review",
    screening_support_score: 0.48,
    top_contributing_features: ["mlu", "ttr"],
    evidence_items: ["Low MLU (1.50)", "Adequate TTR"],
    explanation: "Expressive delay markers noted. Spontaneous sentences are short.",
    therapist_review_status: "reviewed",
    created_at: "2026-05-24T10:05:00Z"
  },
  "SESSION-006": {
    output_id: "AI-OUTPUT-006",
    session_id: "SESSION-006",
    case_id: "CASE-006",
    owner_user_id: "user_therapist_001",
    concern_level: "no_concern",
    screening_support_score: 0.28,
    top_contributing_features: ["mlu"],
    evidence_items: ["Normal MLU (8.00)"],
    explanation: "Typical sentence structures. Articulation errors ( ร/ล ) do not trigger developmental screening flags.",
    therapist_review_status: "reviewed",
    created_at: "2026-05-25T10:05:00Z"
  },
  "SESSION-007": {
    output_id: "AI-OUTPUT-007",
    session_id: "SESSION-007",
    case_id: "CASE-007",
    owner_user_id: "user_therapist_001",
    concern_level: "watchful_review",
    screening_support_score: 0.52,
    top_contributing_features: ["question_ratio"],
    evidence_items: ["Atypical pragmatics observed in turn-taking"],
    explanation: "Longer utterances present but conversational turn-taking boundaries appear atypical.",
    therapist_review_status: "reviewed",
    created_at: "2026-05-26T10:05:00Z"
  },
  "SESSION-008": {
    output_id: "AI-OUTPUT-008",
    session_id: "SESSION-008",
    case_id: "CASE-008",
    owner_user_id: "user_therapist_001",
    concern_level: "no_concern",
    screening_support_score: 0.18,
    top_contributing_features: ["mlu"],
    evidence_items: ["Excellent MLU (9.0)"],
    explanation: "No atypical markers detected. Conversational flow is typical.",
    therapist_review_status: "reviewed",
    created_at: "2026-05-27T10:05:00Z"
  },
  "SESSION-009": {
    output_id: "AI-OUTPUT-009",
    session_id: "SESSION-009",
    case_id: "CASE-009",
    owner_user_id: "user_therapist_001",
    concern_level: "moderate_concern",
    screening_support_score: 0.72,
    top_contributing_features: ["echolalia_ratio"],
    evidence_items: ["Significant delayed echolalia instances"],
    explanation: "Delayed echolalia (repeating cartoons phrases out of context) noted. Requires clinical judgment.",
    therapist_review_status: "reviewed",
    created_at: "2026-05-28T10:05:00Z"
  }
};

export const mockClinicalSignoffs = [];

export const mockNorms = {
  "36-47": { mlu: { mean: 3.0, sd: 0.5 }, ttr: { mean: 0.45, sd: 0.05 } },
  "48-59": { mlu: { mean: 3.8, sd: 0.5 }, ttr: { mean: 0.48, sd: 0.05 } },
  "60-72": { mlu: { mean: 4.5, sd: 0.5 }, ttr: { mean: 0.52, sd: 0.05 } }
};

export const mockSessionVocabs = {
  "SESSION-001-A": [
    { word: "car", count: 4, type: "noun", isNew: true }
  ],
  "SESSION-001-B": [
    { word: "red", count: 2, type: "adjective", isNew: true },
    { word: "car", count: 2, type: "noun", isNew: false },
    { word: "block", count: 2, type: "noun", isNew: true },
    { word: "go", count: 1, type: "verb", isNew: true }
  ],
  "SESSION-001": [
    { word: "want", count: 1, type: "verb", isNew: true },
    { word: "car", count: 2, type: "noun", isNew: false },
    { word: "red", count: 1, type: "adjective", isNew: false },
    { word: "play", count: 1, type: "verb", isNew: true },
    { word: "block", count: 1, type: "noun", isNew: false },
    { word: "now", count: 1, type: "adverb", isNew: true },
    { word: "build", count: 1, type: "verb", isNew: true },
    { word: "tower", count: 1, type: "noun", isNew: true }
  ],
  "SESSION-004": [
    { word: "0", count: 2, type: "nonverbal", isNew: true }
  ],
  "SESSION-005": [
    { word: "candy", count: 2, type: "noun", isNew: true },
    { word: "want", count: 1, type: "verb", isNew: true }
  ]
};

export function seedStore(storeInstance) {
  // Pre-seed line numbers and clinical flags for mock data to resolve line undefined issues
  for (const sessionId in mockTranscriptLines) {
    const lines = mockTranscriptLines[sessionId];
    lines.forEach((line, idx) => {
      line.line_number = idx + 1;
      line.confidence = line.confidence ?? 1.0;
      line.review_status = line.review_status ?? "needs_review";
      line.reviewed = line.reviewed ?? false;
      line.interpretation_note = line.interpretation_note ?? "";
      
      const previousLine = idx > 0 ? lines[idx - 1] : null;
      line.clinical_flags = detectClinicalReviewFlags(line, previousLine);
    });
  }

  const seedState = {
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
    clinicalSignoffs: mockClinicalSignoffs,
    aiDecisionOutputs: mockAiDecisionOutputs,
    extractedFeatureOutputs: mockExtractedFeatureOutputs,
    developmentalNorms: mockNorms,
    audioUrls: {},
    sessionVocabs: mockSessionVocabs,
    auditLogs: [],
    users: mockUsers
  };
  const adapter = createPersistenceAdapter();
  const snapshot = adapter.hydrate(snapshotFromState(seedState));
  storeInstance.configurePersistence(adapter);
  storeInstance.setState(
    {
      ...seedState,
      ...stateFromSnapshot(snapshot),
      currentUser: null,
      dataMode: adapter.mode,
      persistenceStatus: adapter.status
    },
    { persist: false }
  );
}
