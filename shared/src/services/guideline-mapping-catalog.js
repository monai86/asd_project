export const SAFETY_PLACEHOLDER = "Reference Pending Verification";

export const GUIDELINE_SOURCE_TYPES = {
  VERIFIED_OPEN_ACCESS: "verified_open_access",
  TODO_VERIFY_SOURCE: "todo_verify_source"
};

export const THAI_VALIDATION_STATUSES = {
  VALIDATED: "validated",
  PARTIALLY_APPLICABLE: "partially_applicable",
  NOT_VALIDATED: "not_validated",
  PENDING: "pending"
};

export const GUIDELINE_SOURCES = {
  lsa: {
    id: "LSA-METHODOLOGY",
    title: "Language Sample Analysis Methodology Reference",
    source_type: GUIDELINE_SOURCE_TYPES.VERIFIED_OPEN_ACCESS,
    source_url: "https://www.asha.org/practice-portal/clinical-topics/spoken-language-disorders/",
    is_open_access: true,
    evidence_level: "Tier2",
    limitations: "Used for broad language sample analysis construct linkage only; no project-verified Thai norm or cutoff is provided."
  },
  ashaSpokenLanguage: {
    id: "ASHA-SPOKEN-LANGUAGE",
    title: "ASHA Spoken Language Disorders",
    source_type: GUIDELINE_SOURCE_TYPES.VERIFIED_OPEN_ACCESS,
    source_url: "https://www.asha.org/practice-portal/clinical-topics/spoken-language-disorders/",
    is_open_access: true,
    evidence_level: "Tier1",
    limitations: "Used for broad construct linkage; this project does not derive diagnostic thresholds from this source."
  },
  ashaAutism: {
    id: "ASHA-AUTISM",
    title: "ASHA Autism and Autism Spectrum Disorder",
    source_type: GUIDELINE_SOURCE_TYPES.VERIFIED_OPEN_ACCESS,
    source_url: "https://www.asha.org/practice-portal/clinical-topics/autism/",
    is_open_access: true,
    evidence_level: "Tier1",
    limitations: "Used to contextualize social-communication review cues; not used as an automated ASD interpretation."
  },
  ashaSocialCommunication: {
    id: "ASHA-SOCIAL-COMMUNICATION",
    title: "ASHA Social Communication Disorder",
    source_type: GUIDELINE_SOURCE_TYPES.VERIFIED_OPEN_ACCESS,
    source_url: "https://www.asha.org/practice-portal/clinical-topics/social-communication-disorder/",
    is_open_access: true,
    evidence_level: "Tier1",
    limitations: "Used for social-pragmatic construct linkage; no severity label or cutoff is inferred."
  },
  niceAutism: {
    id: "NICE-CG128",
    title: "NICE CG128 Autism spectrum disorder in under 19s",
    source_type: GUIDELINE_SOURCE_TYPES.VERIFIED_OPEN_ACCESS,
    source_url: "https://www.nice.org.uk/guidance/cg128",
    is_open_access: true,
    evidence_level: "Tier1",
    limitations: "Used for high-level review context only; this prototype does not implement NICE diagnostic pathways."
  },
  thaiDspm: {
    id: "THAI-DSPM",
    title: "Thai DSPM developmental surveillance reference",
    source_type: GUIDELINE_SOURCE_TYPES.TODO_VERIFY_SOURCE,
    source_url: SAFETY_PLACEHOLDER,
    is_open_access: false,
    evidence_level: "Tier1",
    limitations: "TODO: verify source before using this as a Thai developmental reference in reports."
  }
};

export const FEATURE_GUIDELINE_MAPPINGS = {
  mlu: {
    label_th: "ความยาวเฉลี่ยของถ้อยคำ",
    label_en: "Mean Length of Utterance",
    calculation_th: SAFETY_PLACEHOLDER,
    calculation_en: SAFETY_PLACEHOLDER,
    clinical_construct: "expressive_language_complexity",
    clinical_relevance_th: "ตัวชี้วัดเชิงพรรณนาของความซับซ้อนทางภาษาในการวิเคราะห์ตัวอย่างภาษา",
    clinical_relevance_en: "A descriptive language sample measure of expressive language complexity.",
    source_key: "lsa",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "ยังไม่มีค่า normative ที่ตรวจสอบแล้วสำหรับใช้ตีความ MLU/MLU-w ของเด็กไทยในระบบนี้",
    interpretation_note: "No project-verified threshold or norm is available; interpret as a descriptive value only.",
    limitations: "Do not label the value as normal, abnormal, delayed, elevated, or clinically significant.",
    used_in_report: true,
    status: "pending"
  },
  mluw: {
    label_th: "ความยาวเฉลี่ยของถ้อยคำแบบนับคำ (MLU-w)",
    label_en: "Mean Length of Utterance by Words (MLU-w)",
    calculation_th: "จำนวนคำทั้งหมดของเด็ก ÷ จำนวน utterance ของเด็ก",
    calculation_en: "Total child word tokens divided by total child utterances.",
    clinical_construct: "expressive_language_complexity",
    clinical_relevance_th: "ค่าพรรณนาความยาวถ้อยคำสำหรับภาษาไทยเมื่อมีการตัดคำแล้ว",
    clinical_relevance_en: "A descriptive utterance-length measure for Thai language sample review.",
    source_key: "lsa",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "คำนวณได้ แต่การเทียบเกณฑ์เด็กไทยยังรอการตรวจสอบแหล่งอ้างอิง",
    interpretation_note: "No project-verified Thai threshold or norm is available.",
    limitations: "Use for descriptive language sample review only.",
    used_in_report: true,
    status: "pending"
  },
  ttr: {
    label_th: "อัตราส่วนความหลากหลายของคำศัพท์",
    label_en: "Type-Token Ratio",
    calculation_th: "จำนวนคำที่ไม่ซ้ำ ÷ จำนวนคำทั้งหมด",
    calculation_en: "Unique word types divided by total word tokens.",
    clinical_construct: "lexical_diversity",
    clinical_relevance_th: "ค่าพรรณนาความหลากหลายของคำศัพท์ และไวต่อความยาวตัวอย่างภาษา",
    clinical_relevance_en: "A descriptive lexical diversity measure that is sensitive to sample length.",
    source_key: "lsa",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "ไม่มี threshold หรือ Thai norm ที่ตรวจสอบแล้วในระบบนี้",
    interpretation_note: "No project-verified threshold or norm is available.",
    limitations: "Interpret only with sample length and transcript quality context.",
    used_in_report: true,
    status: "pending"
  },
  total_utterances: {
    label_th: "จำนวน utterance ทั้งหมด",
    label_en: "Total Utterances",
    calculation_th: "จำนวน utterance ของเด็กใน transcript ที่ใช้วิเคราะห์",
    calculation_en: "Count of child utterances in the analyzed transcript.",
    clinical_construct: "language_sample_productivity",
    clinical_relevance_th: "ค่าพื้นฐานสำหรับดูปริมาณตัวอย่างภาษาและความน่าเชื่อถือของ metric อื่น",
    clinical_relevance_en: "A basic language sample productivity value that contextualizes other metrics.",
    source_key: "lsa",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "ใช้เป็นบริบทปริมาณข้อมูล ไม่ใช่เกณฑ์วินิจฉัย",
    interpretation_note: "Use as sample-size context only.",
    limitations: "Does not establish clinical severity.",
    used_in_report: true,
    status: "descriptive"
  },
  total_words: {
    label_th: "จำนวนคำทั้งหมด",
    label_en: "Total Words",
    calculation_th: "จำนวนคำของเด็กใน transcript ที่ใช้วิเคราะห์",
    calculation_en: "Count of child word tokens in the analyzed transcript.",
    clinical_construct: "language_sample_productivity",
    clinical_relevance_th: "ค่าพื้นฐานสำหรับดูปริมาณคำพูดในตัวอย่างภาษา",
    clinical_relevance_en: "A basic productivity measure for the amount of child speech in the sample.",
    source_key: "lsa",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "ต้องตีความร่วมกับบริบท session และคุณภาพ transcript",
    interpretation_note: "Use as descriptive sample context only.",
    limitations: "Does not establish expressive ability by itself.",
    used_in_report: true,
    status: "descriptive"
  },
  unintelligible_count: {
    label_th: "จำนวนถ้อยคำที่ฟังไม่เข้าใจ",
    label_en: "Unintelligible Utterance Count",
    calculation_th: "จำนวน utterance ที่ถูกระบุว่าฟังไม่เข้าใจ",
    calculation_en: "Count of utterances marked as unintelligible.",
    clinical_construct: "speech_intelligibility_and_sample_quality",
    clinical_relevance_th: "ช่วยให้ clinician ตรวจคุณภาพความชัดเจนของการสื่อสารและคุณภาพตัวอย่างภาษา",
    clinical_relevance_en: "Supports review of speech intelligibility and sample quality.",
    source_key: "ashaSpokenLanguage",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "DSPM อาจให้บริบทพัฒนาการไทย แต่ threshold ของ count นี้ยังรอการตรวจสอบ",
    interpretation_note: "Review as a transcript quality and intelligibility cue.",
    limitations: "Do not infer severity without clinician review.",
    used_in_report: true,
    status: "pending"
  },
  unintelligible_ratio: {
    label_th: "อัตราส่วนถ้อยคำที่ฟังไม่เข้าใจ",
    label_en: "Unintelligible Utterance Ratio",
    calculation_th: "จำนวน utterance ที่ฟังไม่เข้าใจ ÷ จำนวน utterance ทั้งหมด",
    calculation_en: "Unintelligible utterances divided by total utterances.",
    clinical_construct: "speech_intelligibility_and_sample_quality",
    clinical_relevance_th: "ช่วยให้ clinician ตรวจคุณภาพความชัดเจนของการสื่อสารและคุณภาพตัวอย่างภาษา",
    clinical_relevance_en: "Supports review of speech intelligibility and sample quality.",
    source_key: "ashaSpokenLanguage",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "DSPM อาจให้บริบทพัฒนาการไทย แต่ threshold ของ ratio นี้ยังรอการตรวจสอบ",
    interpretation_note: "No project-verified ratio threshold is available.",
    limitations: "Use as a review cue, not as a clinical cutoff.",
    used_in_report: true,
    status: "pending"
  },
  echolalia_count: {
    label_th: "จำนวนการพูดทวน",
    label_en: "Echolalia Count",
    calculation_th: "จำนวน utterance ที่เป็น echolalia ตามการ coding/review",
    calculation_en: "Count of utterances coded or reviewed as echolalic.",
    clinical_construct: "social_communication_review",
    clinical_relevance_th: "พฤติกรรมการพูดทวนอาจเกี่ยวข้องกับการสื่อสารทางสังคม แต่ต้องดูหน้าที่และบริบทของถ้อยคำ",
    clinical_relevance_en: "Echolalia may be relevant to social communication review, but function and context must be reviewed.",
    source_key: "ashaAutism",
    thai_validation_status: THAI_VALIDATION_STATUSES.PARTIALLY_APPLICABLE,
    thai_note: "สังเกตได้ข้ามภาษาในบางบริบท แต่ไม่มี threshold ที่ validate กับเด็กไทย",
    interpretation_note: "Review function and context; do not interpret count alone.",
    limitations: "Not a diagnostic marker by itself.",
    used_in_report: true,
    status: "pending"
  },
  echolalia_ratio: {
    label_th: "อัตราส่วนการพูดทวน",
    label_en: "Echolalia Ratio",
    calculation_th: "จำนวน utterance ที่เป็น echolalia ÷ จำนวน utterance ทั้งหมด",
    calculation_en: "Echolalic utterances divided by total utterances.",
    clinical_construct: "social_communication_review",
    clinical_relevance_th: "พฤติกรรมการพูดทวนอาจเกี่ยวข้องกับการสื่อสารทางสังคม แต่ต้องดูหน้าที่และบริบทของถ้อยคำ",
    clinical_relevance_en: "Echolalia may be relevant to social communication review, but function and context must be reviewed.",
    source_key: "ashaAutism",
    thai_validation_status: THAI_VALIDATION_STATUSES.PARTIALLY_APPLICABLE,
    thai_note: "สังเกตได้ข้ามภาษาในบางบริบท แต่ไม่มี threshold ที่ validate กับเด็กไทย",
    interpretation_note: "No project-verified ratio threshold is available.",
    limitations: "Review as a cue, not as a diagnostic result.",
    used_in_report: true,
    status: "pending"
  },
  pronoun_reversal_count: {
    label_th: "จำนวนการใช้สรรพนามสลับบทบาท",
    label_en: "Pronoun Reversal Count",
    calculation_th: "นับเหตุการณ์ที่ clinician ระบุว่าใช้สรรพนามผิดบทบาท",
    calculation_en: "Count of clinician-identified pronoun role reversals.",
    clinical_construct: "language_specific_social_communication_review",
    clinical_relevance_th: "เป็นข้อมูลเชิงพรรณนาที่ต้องใช้ความรู้ภาษาไทยและบริบทการสนทนา",
    clinical_relevance_en: "A descriptive observation requiring language-specific clinical review.",
    source_key: "ashaAutism",
    thai_validation_status: THAI_VALIDATION_STATUSES.NOT_VALIDATED,
    thai_note: "ระบบสรรพนามภาษาไทยต่างจากภาษาอังกฤษ จึงห้ามตีความจาก English marker โดยตรง",
    interpretation_note: "Requires clinician review; English-derived assumptions do not transfer directly to Thai.",
    limitations: "Do not use as a standalone ASD marker.",
    used_in_report: true,
    status: "pending"
  },
  zero_vocalization_count: {
    label_th: "จำนวน turn ที่ไม่มีการตอบสนองด้วยเสียง",
    label_en: "Zero Vocalization Turns",
    calculation_th: "จำนวน turn ของคู่สนทนาที่ไม่มีการตอบสนองด้วยเสียงจากเด็ก",
    calculation_en: "Number of partner turns with no child vocal response.",
    clinical_construct: "communication_engagement",
    clinical_relevance_th: "ช่วยทบทวนการมีส่วนร่วมในการสื่อสาร แต่ต้องดูโครงสร้างกิจกรรม ความเหนื่อย และบริบท",
    clinical_relevance_en: "Supports review of communication engagement with session context.",
    source_key: "ashaAutism",
    thai_validation_status: THAI_VALIDATION_STATUSES.PARTIALLY_APPLICABLE,
    thai_note: "ใช้เป็นข้อมูลทบทวนบริบท ไม่ใช่ threshold เชิงวินิจฉัย",
    interpretation_note: "Review with activity structure, fatigue, and partner behavior.",
    limitations: "No project-verified cutoff is available.",
    used_in_report: true,
    status: "pending"
  },
  nonverbal_vocalization_count: {
    label_th: "จำนวนเสียงหรือการสื่อสารที่ไม่ใช่คำพูด",
    label_en: "Nonverbal Vocalization Count",
    calculation_th: "นับเสียงหรือการสื่อสารที่ไม่ใช่คำพูดตามการ coding ของ transcript",
    calculation_en: "Count of non-word vocalizations or coded nonverbal communicative acts.",
    clinical_construct: "communication_mode",
    clinical_relevance_th: "ช่วยติดตามรูปแบบการสื่อสารในตัวอย่างภาษา",
    clinical_relevance_en: "Supports descriptive review of communication mode in the language sample.",
    source_key: "ashaAutism",
    thai_validation_status: THAI_VALIDATION_STATUSES.PARTIALLY_APPLICABLE,
    thai_note: "เป็นค่าพรรณนา ต้องดูบริบทและสัดส่วนเทียบกับการสื่อสารรูปแบบอื่น",
    interpretation_note: "Use descriptively with context.",
    limitations: "Does not establish clinical significance by itself.",
    used_in_report: true,
    status: "descriptive"
  },
  question_ratio: {
    label_th: "อัตราส่วนการถามคำถาม",
    label_en: "Question Ratio",
    calculation_th: "จำนวน utterance ที่เป็นคำถาม ÷ จำนวน utterance ทั้งหมด",
    calculation_en: "Question utterances divided by total utterances.",
    clinical_construct: "pragmatic_language_use",
    clinical_relevance_th: "ค่าพรรณนาการใช้ภาษาเชิงปฏิสัมพันธ์ในตัวอย่างภาษา",
    clinical_relevance_en: "A descriptive pragmatic language sample measure.",
    source_key: "ashaSocialCommunication",
    thai_validation_status: THAI_VALIDATION_STATUSES.PENDING,
    thai_note: "ไม่มี threshold ที่ตรวจสอบแล้วสำหรับการตีความในเด็กไทย",
    interpretation_note: "No project-verified threshold is available.",
    limitations: "Use as a pragmatic review cue only.",
    used_in_report: true,
    status: "pending"
  },
  turn_taking_count: {
    label_th: "จำนวนการผลัดกันสนทนา",
    label_en: "Turn-Taking Count",
    calculation_th: "จำนวนการแลกเปลี่ยนบทสนทนาระหว่างเด็กและคู่สนทนา",
    calculation_en: "Count of conversational exchanges between child and partner.",
    clinical_construct: "conversational_reciprocity",
    clinical_relevance_th: "ค่าพรรณนาการมีส่วนร่วมและ reciprocity ในตัวอย่างภาษา",
    clinical_relevance_en: "A descriptive measure related to conversational reciprocity.",
    source_key: "ashaSocialCommunication",
    thai_validation_status: THAI_VALIDATION_STATUSES.PARTIALLY_APPLICABLE,
    thai_note: "ควรใช้ติดตามแนวโน้มและบริบท ไม่ใช้เป็น cutoff",
    interpretation_note: "Use for trend and context review only.",
    limitations: "No project-verified cutoff is available.",
    used_in_report: true,
    status: "descriptive"
  },
  restricted_interest_words: {
    label_th: "คำที่เกี่ยวข้องกับความสนใจเฉพาะ",
    label_en: "Restricted Interest Vocabulary",
    calculation_th: "นับคำที่ถูกจัดเป็นหัวข้อความสนใจเฉพาะตามบริบท transcript",
    calculation_en: "Count of words coded as restricted-interest vocabulary in transcript context.",
    clinical_construct: "restricted_interest_context",
    clinical_relevance_th: "เป็นข้อมูลบริบทสำหรับการทบทวน social communication และพฤติกรรมซ้ำ/สนใจจำกัด",
    clinical_relevance_en: "Context for reviewing social communication and restricted-interest patterns.",
    source_key: "niceAutism",
    thai_validation_status: THAI_VALIDATION_STATUSES.NOT_VALIDATED,
    thai_note: "การนับคำอย่างเดียวไม่เพียงพอ ต้องดูบริบท ความถี่ และผลกระทบข้าม setting",
    interpretation_note: "Review transcript context and cross-setting information.",
    limitations: "Word count alone is not sufficient for clinical interpretation.",
    used_in_report: true,
    status: "pending"
  }
};

export function getGuidelineSource(sourceKey) {
  return GUIDELINE_SOURCES[sourceKey] || null;
}

export function getReportableFeatureMappings() {
  return Object.fromEntries(
    Object.entries(FEATURE_GUIDELINE_MAPPINGS).filter(([, mapping]) => mapping.used_in_report)
  );
}
