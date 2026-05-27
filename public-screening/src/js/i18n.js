/**
 * i18n.js — Bilingual Internationalization Module (Thai / English)
 *
 * Provides all UI strings, language switching, and automatic DOM translation
 * for the ASD Developmental Screening Support Tool.
 *
 * IMPORTANT LANGUAGE RULES:
 *  - Never use "diagnosis", "your child has ASD", "autistic"
 *  - Always use: "screening support", "concern level", "this result suggests…",
 *    "recommend consulting a qualified professional"
 */

// ─── Storage key ────────────────--------------------------------------------
const LANG_KEY = 'asd-screening-lang';

// ─── Full bilingual string dictionary ───────────────────────────────────────
export const STRINGS = {

  /* ── Navigation ────────────────---------------------------------------- */
  nav: {
    brand: {
      en: 'Developmental Screening',
      th: 'เครื่องมือคัดกรองพัฒนาการ',
    },
    home: {
      en: 'Home',
      th: 'หน้าหลัก',
    },
    screening: {
      en: 'Screening',
      th: 'แบบคัดกรอง',
    },
    education: {
      en: 'Knowledge',
      th: 'ความรู้',
    },
    results: {
      en: 'My Results',
      th: 'ผลการคัดกรองของฉัน',
    },
    resources: {
      en: 'FAQ',
      th: 'คำถามที่พบบ่อย',
    },
    about: {
      en: 'About Us',
      th: 'เกี่ยวกับเรา',
    },
    profile: {
      en: 'Profile',
      th: 'โปรไฟล์',
    },
    settings: {
      en: 'Settings',
      th: 'การตั้งค่า',
    },
    help: {
      en: 'Help',
      th: 'ความช่วยเหลือ',
    },
    login: {
      en: 'Sign In',
      th: 'เข้าสู่ระบบ',
    },
    brandSubtitle: {
      en: 'Screening Support',
      th: 'สนับสนุนการคัดกรอง',
    },
    widgetText: {
      en: 'Early understanding leads to better support.',
      th: 'การทำความเข้าใจแต่เนิ่นๆ นำไปสู่การดูแลที่ดีขึ้น',
    },
    widgetSubtext: {
      en: "You're taking an important first step.",
      th: 'คุณกำลังเริ่มต้นก้าวแรกที่สำคัญ',
    },
    langToggle: {
      en: '🌐 TH',
      th: '🌐 EN',
    },
  },

  /* ── Landing / Hero ────────────────------------------------------------ */
  landing: {
    badge: {
      en: '🧸 Educational Tool — Not a Diagnosis',
      th: '🧸 เครื่องมือเพื่อการศึกษา ไม่ใช่การวินิจฉัย',
    },
    title: {
      en: 'Autism Screening in Children',
      th: 'คัดกรองออทิซึมในเด็ก',
    },
    subtitle: {
      en: 'Quick screening, fast understanding, get the right advice',
      th: 'คัดกรองเร็ว เข้าใจไว ได้รับคำแนะนำที่ใช่',
    },
    description: {
      en: 'This screening questionnaire helps evaluate your child\'s preliminary development as an informative guide for consulting developmental specialists.',
      th: 'แบบคัดกรองนี้ช่วยให้คุณประเมินพัฒนาการของเด็กเบื้องต้น เพื่อเป็นข้อมูลในการปรึกษาผู้เชี่ยวชาญต่อไป',
    },
    cta: {
      en: 'Start Screening',
      th: 'เริ่มทำแบบคัดกรอง',
    },
    ctaLearn: {
      en: '📚 Learn More',
      th: '📚 เรียนรู้เพิ่มเติม',
    },
    featureTitle: {
      en: 'Quick Screening',
      th: 'การคัดกรองที่รวดเร็ว',
    },
    featureDesc: {
      en: 'Answer simple questions about your child.',
      th: 'ตอบคำถามง่ายๆ เกี่ยวกับพัฒนาการของบุตรหลาน',
    },
    insightTitle: {
      en: 'Personalized Insights',
      th: 'ข้อมูลเชิงลึกเฉพาะตัว',
    },
    insightDesc: {
      en: 'See indicators and helpful explanations.',
      th: 'ทำความเข้าใจเกี่ยวกับตัวบ่งชี้และคำแนะนำเพิ่มเติม',
    },
    nextTitle: {
      en: 'Next Steps',
      th: 'ขั้นตอนถัดไป',
    },
    nextDesc: {
      en: 'Get recommendations for professional support.',
      th: 'รับคำแนะนำในการติดต่อผู้เชี่ยวชาญเพิ่มเติม',
    },
    whatTitle: {
      en: 'What This Tool Does',
      th: 'เครื่องมือนี้ทำอะไร',
    },
    what1Title: {
      en: 'Simple Questionnaire',
      th: 'แบบสอบถามง่ายๆ',
    },
    what1Desc: {
      en: 'Answer simple questions about your child\'s language, communication, and behaviors. Takes 5-10 minutes.',
      th: 'ตอบคำถามเกี่ยวกับพัฒนาการด้านภาษา การสื่อสาร และพฤติกรรมของบุตรหลาน ใช้เวลาเพียง 5-10 นาที',
    },
    what2Title: {
      en: 'Concern Level',
      th: 'ระดับความกังวล',
    },
    what2Desc: {
      en: 'Results show preliminary concern levels (low / moderate / high) with clear explanations.',
      th: 'ผลลัพธ์แสดงระดับความกังวลเบื้องต้น (ต่ำ / ปานกลาง / สูง) พร้อมคำอธิบายที่เข้าใจง่าย',
    },
    what3Title: {
      en: 'Recommended Next Steps',
      th: 'คำแนะนำขั้นตอนถัดไป',
    },
    what3Desc: {
      en: 'Get recommendations on next steps, including when to consult developmental specialists.',
      th: 'รับคำแนะนำเกี่ยวกับขั้นตอนถัดไป รวมถึงเมื่อใดควรปรึกษาผู้เชี่ยวชาญด้านพัฒนาการ',
    },
    whatNotTitle: {
      en: '⚠️ What This Tool Does NOT Do',
      th: '⚠️ สิ่งที่เครื่องมือนี้ไม่ได้ทำ',
    },
    whatNot1: {
      en: '❌ This tool is <strong>NOT a diagnosis</strong> of Autism Spectrum Disorder (ASD) or any condition.',
      th: '❌ เครื่องมือนี้ <strong>ไม่ใช่การวินิจฉัย</strong> ออทิสติกสเปกตรัม (ASD) หรือความผิดปกติใดๆ',
    },
    whatNot2: {
      en: '❌ It cannot <strong>replace professional assessment</strong> by medical doctors or speech therapists.',
      th: '❌ ไม่สามารถ <strong>ทดแทนการประเมินโดยผู้เชี่ยวชาญ</strong> ทางการแพทย์หรือนักบำบัดการพูดได้',
    },
    whatNot3: {
      en: '❌ Results <strong>do not state your child has ASD</strong> — it is only a preliminary concern indicator.',
      th: '❌ ผลลัพธ์ <strong>ไม่ได้บ่งชี้ว่าบุตรหลานของคุณมี ASD</strong> — เป็นเพียงตัวบ่งชี้ความกังวลเบื้องต้น',
    },
    whatNot4: {
      en: '❌ There is no <strong>data storage or transmission</strong> — everything is processed purely in your browser.',
      th: '❌ ไม่มีการ <strong>เก็บหรือส่งข้อมูล</strong> ใดๆ ของคุณ — ทุกอย่างประมวลผลในเบราว์เซอร์เท่านั้น',
    },
    howTitle: {
      en: 'How It Works',
      th: 'ขั้นตอนการใช้งาน',
    },
    step1Title: {
      en: 'Complete Questionnaire',
      th: 'ตอบแบบสอบถาม',
    },
    step1Desc: {
      en: 'Answer simple questions about your child\'s development.',
      th: 'ตอบคำถามง่ายๆ เกี่ยวกับพัฒนาการของบุตรหลาน',
    },
    step2Title: {
      en: 'View Results',
      th: 'ดูผลลัพธ์',
    },
    step2Desc: {
      en: 'Receive concern level with explanations.',
      th: 'รับผลระดับความกังวลพร้อมคำอธิบาย',
    },
    step3Title: {
      en: 'Consult Specialist',
      th: 'ปรึกษาผู้เชี่ยวชาญ',
    },
    step3Desc: {
      en: 'Take the summary report to discuss with doctors or therapists.',
      th: 'นำผลสรุปไปพูดคุยกับแพทย์หรือนักบำบัด',
    },
    disclaimerTitle: {
      en: '📌 Disclaimer',
      th: '📌 ข้อจำกัดความรับผิดชอบ',
    },
    disclaimerText: {
      en: 'This tool is developed for educational and screening support purposes only. It cannot replace clinical evaluation by a child development specialist, speech-language pathologist, or medical doctor. If you have concerns about your child\'s development, please consult a qualified professional.',
      th: 'เครื่องมือนี้พัฒนาขึ้นเพื่อวัตถุประสงค์ทางการศึกษาและสนับสนุนการคัดกรองเบื้องต้นเท่านั้น ไม่สามารถใช้ทดแทนการประเมินทางคลินิกโดยผู้เชี่ยวชาญด้านพัฒนาการเด็ก นักแก้ไขการพูดและภาษา หรือแพทย์ได้ หากคุณมีความกังวลเกี่ยวกับพัฒนาการของบุตรหลาน กรุณาปรึกษาผู้เชี่ยวชาญที่มีคุณวุฒิ',
    },
    disclaimerCta: {
      en: 'I understand — Start Screening',
      th: 'ฉันเข้าใจแล้ว — เริ่มการคัดกรอง',
    },
  },

  /* ── Screening Form ──────────────────────────────────────────────────── */
  screening: {
    title: {
      en: 'Developmental Screening Questionnaire',
      th: 'แบบสอบถามคัดกรองพัฒนาการ',
    },
    subtitle: {
      en: 'Answer simple questions about your child\'s development. Takes about 5-10 minutes.',
      th: 'ตอบคำถามง่ายๆ เกี่ยวกับพัฒนาการของบุตรหลาน ใช้เวลาประมาณ 5-10 นาที',
    },
    disclaimer: {
      en: 'This tool is for preliminary screening support only. It is not a medical diagnosis. Please consult a qualified professional for an appropriate assessment.',
      th: 'เครื่องมือนี้เป็นการคัดกรองเบื้องต้นเพื่อการศึกษาเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์ กรุณาปรึกษาผู้เชี่ยวชาญสำหรับการประเมินที่เหมาะสม',
    },
    step1Label: { en: 'Child Info', th: 'ข้อมูลทั่วไป' },
    step2Label: { en: 'Communication', th: 'การสื่อสาร' },
    step3Label: { en: 'Social Interaction', th: 'ปฏิสัมพันธ์ทางสังคม' },
    step4Label: { en: 'Repetitive Patterns', th: 'พฤติกรรมซ้ำๆ' },
    step5Label: { en: 'Review', th: 'ตรวจสอบข้อมูล' },
    step1Title: {
      en: '👶 Child\'s Preliminary Information',
      th: '👶 ข้อมูลเบื้องต้นของเด็ก',
    },
    step1Desc: {
      en: 'This information helps contextualize screening support for your child\'s age.',
      th: 'ข้อมูลนี้ช่วยให้ผลลัพธ์เหมาะสมกับช่วงวัยของบุตรหลาน',
    },
    ageLabel: {
      en: 'Age Range *',
      th: 'ช่วงอายุ *',
    },
    agePlaceholder: {
      en: '— Select age range —',
      th: '— กรุณาเลือกช่วงอายุ —',
    },
    age0_12: { en: 'Under 12 months', th: 'น้อยกว่า 12 เดือน' },
    age12_18: { en: '12 – 18 months', th: '12 – 18 เดือน' },
    age18_24: { en: '18 – 24 months', th: '18 – 24 เดือน' },
    age24_36: { en: '24 – 36 months (2-3 years)', th: '24 – 36 เดือน (2-3 ปี)' },
    age36_48: { en: '36 – 48 months (3-4 years)', th: '36 – 48 เดือน (3-4 ปี)' },
    age48_60: { en: '48 – 60 months (4-5 years)', th: '48 – 60 เดือน (4-5 ปี)' },
    age60: { en: 'More than 60 months (5+ years)', th: 'มากกว่า 60 เดือน (5+ ปี)' },
    sexLabel: {
      en: 'Sex (optional)',
      th: 'เพศ (ไม่บังคับ)',
    },
    sexMale: { en: 'Male', th: 'ชาย' },
    sexFemale: { en: 'Female', th: 'หญิง' },
    sexOther: { en: 'Unspecified', th: 'ไม่ระบุ' },
    step2Title: {
      en: '🗣️ Speech & Language Concerns',
      th: '🗣️ ความกังวลด้านภาษาและการพูด',
    },
    step2Desc: {
      en: 'Select the option that best matches your observations.',
      th: 'เลือกตัวเลือกที่ตรงกับสิ่งที่คุณสังเกตเห็นมากที่สุด',
    },
    step3Title: {
      en: '🤝 Social Communication Concerns',
      th: '🤝 ความกังวลด้านการสื่อสารทางสังคม',
    },
    step3Desc: {
      en: 'Questions regarding your child\'s social interaction patterns.',
      th: 'คำถามเกี่ยวกับปฏิสัมพันธ์ทางสังคมของบุตรหลาน',
    },
    step4Title: {
      en: '🔄 Repetitive Behavior Concerns',
      th: '🔄 ความกังวลด้านพฤติกรรมซ้ำ',
    },
    step4Desc: {
      en: 'Questions regarding observed repetitive behavioral patterns.',
      th: 'คำถามเกี่ยวกับรูปแบบพฤติกรรมที่สังเกตเห็น',
    },
    step5Title: {
      en: '📝 Review & Observations',
      th: '📝 ตรวจสอบข้อมูลและข้อสังเกตเพิ่มเติม',
    },
    step5Desc: {
      en: 'Review child details and add optional voice observations or notes before processing.',
      th: 'ตรวจสอบข้อมูลเบื้องต้นและเพิ่มการอัดเสียงหรือบันทึกเพิ่มเติมเพื่อประมวลผล',
    },
    notesLabel: {
      en: 'Additional Observations',
      th: 'ข้อสังเกตเพิ่มเติม',
    },
    notesPlaceholder: {
      en: 'e.g., example sentences, general concerns, school observations...',
      th: 'เช่น ตัวอย่างประโยคที่เด็กพูด สิ่งที่คุณกังวล หรือสิ่งที่ครู/ผู้ดูแลสังเกตเห็น...',
    },
    transcriptLabel: {
      en: 'Speech Transcript / Logs (optional)',
      th: 'บันทึกการพูด (ไม่บังคับ)',
    },
    transcriptPlaceholder: {
      en: 'You can type dialogue exchanges or speech samples here...',
      th: 'คุณสามารถพิมพ์ตัวอย่างบทสนทนาหรือสิ่งที่เด็กพูดได้ที่นี่...',
    },
    privacyNote: {
      en: '🔒 All data is processed locally in your browser. No data is sent or stored on any server.',
      th: '🔒 ข้อมูลทั้งหมดประมวลผลในเบราว์เซอร์ของคุณเท่านั้น ไม่มีการส่งหรือเก็บข้อมูลใดๆ บนเซิร์ฟเวอร์',
    },
    prev: { en: '← Previous', th: '← ก่อนหน้า' },
    next: { en: 'Next →', th: 'ถัดไป →' },
    submit: { en: '📊 View Screening Results', th: '📊 ดูผลการคัดกรอง' },
    ageError: { en: 'Please select an age range', th: 'กรุณาเลือกช่วงอายุ' },
    ageOptions: {
      under12: { en: 'Under 12 months', th: 'ต่ำกว่า 12 เดือน' },
      m12_18:  { en: '12–18 months',    th: '12–18 เดือน' },
      m18_24:  { en: '18–24 months',    th: '18–24 เดือน' },
      m24_36:  { en: '24–36 months',    th: '24–36 เดือน (2-3 ปี)' },
      m36_48:  { en: '36–48 months',    th: '36–48 เดือน (3-4 ปี)' },
      m48_60:  { en: '48–60 months',    th: '48–60 เดือน (4-5 ปี)' },
      over60:  { en: '60+ months',      th: '60 เดือนขึ้นไป' },
    },
    voiceDesc: {
      en: 'If you wish, you can record a short audio clip of your child speaking (30–60 seconds) to automatically generate supplementary notes.',
      th: 'หากต้องการ คุณสามารถบันทึกเสียงบุตรหลานพูด (30–60 วินาที) เพื่อเพิ่มหมายเหตุการสังเกตโดยอัตโนมัติ',
    },
    voiceRecording: {
      en: 'Recording...',
      th: 'กำลังบันทึก...',
    },
    voiceTranscriptLabel: {
      en: 'Voice Transcript Preview',
      th: 'ตัวอย่างผลการแปลงเสียงเป็นข้อความ',
    },
    voiceAnalysisLabel: {
      en: 'Language Observation Summary',
      th: 'สรุปผลการสังเกตด้านภาษา',
    },
    voiceUnsupported: {
      en: 'This browser does not support voice recording. Please use Chrome or Edge.',
      th: 'เบราว์เซอร์นี้ไม่รองรับการบันทึกเสียง กรุณาใช้ Chrome หรือ Edge',
    },
    voiceBadge: {
      en: '🎙️ Voice Observation (Optional)',
      th: '🎙️ การสังเกตด้วยเสียง (ไม่บังคับ)',
    },
    voiceBadgeEn: {
      en: 'Voice Observation (Optional)',
      th: 'Voice Observation (Optional)',
    },
    voiceStart: {
      en: '🎙️ Start Recording',
      th: '🎙️ เริ่มบันทึกเสียง',
    },
    voiceStop: {
      en: '⏹️ Stop Recording',
      th: '⏹️ หยุดบันทึก',
    },
    voiceClear: {
      en: '✕ Clear Voice Data',
      th: '✕ ล้างข้อมูลเสียง',
    }
  },

  /* ── Results ────────────────------------------------------------------- */
  results: {
    pageTitle: {
      en: 'Screening Support Results',
      th: 'ผลการคัดกรองเบื้องต้น',
    },
    overallLabel: {
      en: 'Overall Developmental Concern Level',
      th: 'ระดับความกังวลด้านพัฒนาการโดยรวม',
    },
    low: {
      en: 'Low Risk',
      th: 'ความเสี่ยงต่ำ',
    },
    moderate: {
      en: 'Moderate Risk',
      th: 'ความเสี่ยงปานกลาง',
    },
    high: {
      en: 'High Risk',
      th: 'ความเสี่ยงสูง',
    },
    lowExplanation: {
      en: 'Based on your responses, the observed communication patterns appear to be within a typical developmental range. Continued monitoring is always encouraged.',
      th: 'จากคำตอบของคุณ รูปแบบการสื่อสารที่สังเกตได้อยู่ในช่วงพัฒนาการปกติ แนะนำให้ติดตามสังเกตต่อเนื่อง',
    },
    moderateExplanation: {
      en: 'This result suggests some areas of developmental communication that may benefit from further evaluation. We recommend discussing these observations with a qualified professional.',
      th: 'ผลลัพธ์นี้บ่งชี้ว่ามีบางด้านของพัฒนาการการสื่อสารที่อาจได้ประโยชน์จากการประเมินเพิ่มเติม แนะนำให้ปรึกษาผู้เชี่ยวชาญ',
    },
    highExplanation: {
      en: 'This result suggests several areas of developmental concern that may indicate the need for professional evaluation. We strongly recommend consulting a qualified healthcare or developmental specialist.',
      th: 'ผลลัพธ์นี้บ่งชี้ว่ามีหลายด้านที่น่ากังวลด้านพัฒนาการ ซึ่งอาจบ่งบอกถึงความจำเป็นในการประเมินโดยผู้เชี่ยวชาญ แนะนำอย่างยิ่งให้ปรึกษาผู้เชี่ยวชาญด้านสุขภาพหรือพัฒนาการ',
    },
    speechCategory: {
      en: 'Communication & Language',
      th: 'การสื่อสารและภาษา',
    },
    socialCategory: {
      en: 'Social Interaction',
      th: 'ปฏิสัมพันธ์ทางสังคม',
    },
    repetitiveCategory: {
      en: 'Repetitive Patterns',
      th: 'พฤติกรรมซ้ำๆ',
    },
    playCategory: {
      en: 'Play & Imagination',
      th: 'การเล่นและจินตนาการ',
    },
    sensoryCategory: {
      en: 'Sensory Sensitivity',
      th: 'การตอบสนองประสาทสัมผัส',
    },
    communicationLow: {
      en: 'Child communicates age-appropriately.',
      th: 'เด็กมีการสื่อสารและใช้ภาษาที่เหมาะสมตามวัย',
    },
    communicationModerate: {
      en: 'Child shows minor language milestones variation.',
      th: 'เด็กมีพัฒนาการด้านภาษาที่หลากหลายหรือคลาดเคลื่อนจากเกณฑ์เล็กน้อย',
    },
    communicationHigh: {
      en: 'Child shows significant speech or word usage concerns.',
      th: 'เด็กมีความกังวลในการสื่อสารหรือการพูดที่ต้องการความดูแลอย่างใกล้ชิด',
    },
    socialLow: {
      en: 'Responsive social engagement observed.',
      th: 'มีปฏิสัมพันธ์และการตอบสนองทางสังคมตามเกณฑ์วัยปกติ',
    },
    socialModerate: {
      en: 'Occasional social response delays or play sharing variations.',
      th: 'พบบางพฤติกรรมที่เด็กอาจตอบสนองทางสังคมล่าช้าหรือการร่วมเล่นลดลงเป็นบางครั้ง',
    },
    socialHigh: {
      en: 'Child rarely engages or makes eye contact with others.',
      th: 'เด็กมักไม่สบตาหรือไม่ค่อยสนใจมีปฏิสัมพันธ์ร่วมกับผู้อื่น',
    },
    repetitiveLow: {
      en: 'No repetitive movements or echolalia noted.',
      th: 'ไม่พบพฤติกรรมเคลื่อนไหวซ้ำๆ หรือการพูดตามแบบผิดสังเกต',
    },
    repetitiveModerate: {
      en: 'Mild preference for routines or occasional repetitive behavior.',
      th: 'ยึดติดกิจวัตรเดิมๆ หรือมีพฤติกรรมซ้ำๆ บ้างเล็กน้อย',
    },
    repetitiveHigh: {
      en: 'Strong attachment to routines or repetitive vocal/motor patterns.',
      th: 'ยึดติดกิจวัตรหรือพฤติกรรมเดิมอย่างมาก หรือมีอาการโยกตัว/สะบัดมือซ้ำๆ ชัดเจน',
    },
    playLow: {
      en: 'Functional and imaginative play is typical.',
      th: 'มีทักษะการเล่นสมมติและการเล่นตามจินตนาการปกติสมวัย',
    },
    playModerate: {
      en: 'Shows preference for concrete objects over pretend play.',
      th: 'ชอบเล่นของเล่นในเชิงรูปธรรมมากกว่าการสมมติหรือมีจินตนาการบางอย่างจำกัด',
    },
    playHigh: {
      en: 'Limited pretend play or unconventional use of play items.',
      th: 'แทบไม่มีการเล่นสมมติ หรือมักเล่นของเล่นในรูปแบบไม่ปกติซ้ำๆ เช่น หมุนล้อรถอย่างเดียว',
    },
    sensoryLow: {
      en: 'Normal response to sensory stimuli.',
      th: 'มีการตอบสนองต่อแสง เสียง กลิ่น และสัมผัสปกติทั่วไป',
    },
    sensoryModerate: {
      en: 'Occasional sensitivity to loud noises or textures.',
      th: 'มีปฏิกิริยาไวต่อเสียงดังหรือเนื้อสัม่ผัสบางชนิดเป็นบางคราว',
    },
    sensoryHigh: {
      en: 'Strong distress with sound, light, or specific textures.',
      th: 'มีความไวต่อสิ่งเร้าทางประสาทสัมผัสอย่างมาก เช่น อุดหูเมื่อได้ยินเสียงทั่วไป หรือหงุดหงิดกับเสื้อผ้าสัมผัสเฉพาะ',
    },
    categoryBreakdownTitle: {
      en: 'Category Summary',
      th: 'สรุปตามหมวดหมู่',
    },
    featureBreakdownTitle: {
      en: 'Detailed Feature Breakdown',
      th: 'ผลแยกตามรายข้อ',
    },
    recommendationsTitle: {
      en: 'Recommended Next Steps',
      th: 'คำแนะนำขั้นตอนถัดไป',
    },
    talkToProfessionalTitle: {
      en: 'Consult a Professional',
      th: 'ปรึกษาผู้เชี่ยวชาญ',
    },
    talkToProfessionalDesc: {
      en: 'If you have concerns, we encourage you to discuss this summary with a developmental pediatrician, speech-language pathologist, or child psychologist. Professional assessment is key to planning developmental support.',
      th: 'หากคุณมีความกังวล แนะนำให้นำผลสรุปนี้ไปพูดคุยกับกุมารแพทย์พัฒนาการ นักแก้ไขการพูดและภาษา หรือนักจิตวิทยาเด็ก การประเมินโดยผู้เชี่ยวชาญเป็นสิ่งสำคัญในการวางแผนสนับสนุนพัฒนาการ',
    },
    downloadBtn: {
      en: 'Download Summary',
      th: 'ดาวน์โหลดสรุปผล',
    },
    startOverBtn: {
      en: 'Start Over',
      th: 'ทำแบบคัดกรองใหม่',
    },
    scoreLabel: {
      en: 'Score',
      th: 'คะแนน',
    },
    ageRangeLabel: {
      en: 'Child\'s Age Range',
      th: 'ช่วงอายุของเด็ก',
    },
    disclaimer: {
      en: 'This screening support result is NOT a medical diagnosis. It is intended to help identify areas where professional consultation may be beneficial. Please share this with a qualified healthcare professional for proper assessment.',
      th: 'ผลการคัดกรองนี้ไม่ใช่การวินิจฉัยทางการแพทย์ มีจุดประสงค์เพื่อช่วยระบุด้านที่อาจได้ประโยชน์จากการปรึกษาผู้เชี่ยวชาญ กรุณานำผลนี้ไปปรึกษาผู้เชี่ยวชาญด้านสุขภาพเพื่อการประเมินที่เหมาะสม',
    },
    voiceObsTitle: {
      en: '📝 Voice Observation Notes',
      th: '📝 หมายเหตุจากการสังเกตเสียง',
    },
    voiceObsDisclaimer: {
      en: 'This information is an additional observation note, not a clinical assessment.',
      th: 'ข้อมูลนี้เป็นบันทึกการสังเกตเพิ่มเติม ไม่ใช่ผลการประเมินทางคลินิก',
    },
    noData: {
      en: 'No screening data found. Please complete the screening first.',
      th: 'ไม่พบข้อมูลการคัดกรอง กรุณาทำแบบคัดกรองก่อน',
    },
    noDataTitle: {
      en: 'No Screening Data Found',
      th: 'ยังไม่มีข้อมูลการคัดกรอง',
    },
    noDataDesc: {
      en: 'Please complete the screening questionnaire first to view results.',
      th: 'กรุณาทำแบบคัดกรองก่อนเพื่อดูผลลัพธ์',
    },
    noDataCta: {
      en: 'Start Screening',
      th: 'เริ่มการคัดกรอง',
    },
    explanationTitle: {
      en: 'Explanation of Results',
      th: 'คำอธิบายผลลัพธ์',
    },
    learnMore: {
      en: 'Learn More',
      th: 'เรียนรู้เพิ่มเติม',
    },
  },

  /* ── Education ───────────────────────────────────────────────────────── */
  education: {
    title: {
      en: 'Learning About Child Development & Screening',
      th: 'ข้อมูลความรู้เกี่ยวกับการคัดกรองพัฒนาการ',
    },
    subtitle: {
      en: 'Information to help parents and caregivers understand child developmental screening.',
      th: 'ข้อมูลเพื่อช่วยให้ผู้ปกครองและผู้ดูแลเข้าใจการคัดกรองพัฒนาการเด็ก',
    },
    s1Title: {
      en: 'Preliminary Screening vs Diagnosis — What is the difference?',
      th: 'การคัดกรองเบื้องต้น vs การวินิจฉัย — ต่างกันอย่างไร?',
    },
    s1p1: {
      en: '<strong>Screening</strong> is a preliminary process that helps identify whether a child has patterns that may warrant further evaluation. It is like a routine wellness check that flags the need for detailed investigation.',
      th: '<strong>การคัดกรอง (Screening)</strong> เป็นกระบวนการเบื้องต้นที่ช่วยระบุว่าเด็กอาจมีลักษณะที่ควรได้รับการประเมินเพิ่มเติม เปรียบเสมือนการตรวจคัดกรองสุขภาพทั่วไป ที่ช่วยระบุความจำเป็นในการตรวจละเอียด',
    },
    s1p2: {
      en: '<strong>Diagnosis</strong> is a clinical process that must be performed by a specialist team, which includes developmental pediatricians, child psychologists, and/or speech-language pathologists, using standardized tools and systematic observation.',
      th: '<strong>การวินิจฉัย (Diagnosis)</strong> เป็นกระบวนการทางคลินิกที่ต้องดำเนินการโดยทีมผู้เชี่ยวชาญ ซึ่งรวมถึงกุมารแพทย์พัฒนาการ นักจิตวิทยาเด็ก และ/หรือ นักแก้ไขการพูดและภาษา ใช้เครื่องมือมาตรฐานและการสังเกตอย่างเป็นระบบ',
    },
    s1note: {
      en: '💡 <strong>Key Point:</strong> This tool is for screening support only and cannot replace professional diagnosis. Results simply indicate whether further professional consultation is recommended.',
      th: '💡 <strong>จุดสำคัญ:</strong> เครื่องมือนี้เป็นเพียงการคัดกรองสนับสนุน ไม่สามารถทดแทนการวินิจฉัยโดยผู้เชี่ยวชาญได้ ผลการคัดกรองเบื้องต้น บ่งชี้ว่าควรหรือไม่ควรปรึกษาผู้เชี่ยวชาญเพิ่มเติม',
    },
    s2Title: {
      en: 'Speech-Language Developmental Indicators',
      th: 'สัญญาณพัฒนาการด้านภาษาและการสื่อสาร',
    },
    s2p1: {
      en: 'Speech-language development is a key area in developmental screening support. Indicators that may warrant professional evaluation include:',
      th: 'พัฒนาการด้านภาษาและการสื่อสารเป็นหนึ่งในตัวบ่งชี้ที่สำคัญในการคัดกรองเบื้องต้นสำหรับ ASD สัญญาณที่อาจบ่งบอกถึงความจำเป็นในการประเมินเพิ่มเติม ได้แก่:',
    },
    s2i1Title: { en: '📏 Sentence Length (MLU)', th: '📏 ความยาวประโยค (MLU)' },
    s2i1Desc: {
      en: 'The number of words or morphemes per sentence being lower than age-appropriate norms may suggest grammatical delay.',
      th: 'จำนวนคำหรือหน่วยคำต่อประโยคที่ต่ำกว่าเกณฑ์อายุ อาจบ่งชี้ถึงความล่าช้าทางไวยากรณ์',
    },
    s2i2Title: { en: '📖 Word Variety (TTR)', th: '📖 ความหลากหลายของคำศัพท์ (TTR)' },
    s2i2Desc: {
      en: 'Using repetitive or limited vocabulary may suggest a restricted lexical range.',
      th: 'การใช้คำซ้ำๆ จำกัด อาจบ่งชี้ถึงข้อจำกัดด้านคลังคำศัพท์',
    },
    s2i3Title: { en: '🔄 Repeating Others (Echolalia)', th: '🔄 การพูดตามคนอื่น (Echolalia)' },
    s2i3Desc: {
      en: 'Repeating phrases or sentences spoken by others without communicative intent is an indicator that warrants observation.',
      th: 'การพูดซ้ำประโยคหรือวลีที่ผู้อื่นพูดโดยไม่เข้าใจความหมาย อาจเป็นตัวบ่งชี้ที่ควรสังเกต',
    },
    s2i4Title: { en: '🔀 Pronoun Confusion', th: '🔀 การสลับสรรพนาม' },
    s2i4Desc: {
      en: 'Mixing up or switching pronouns like "I" and "you" can be a characteristic observed in child speech.',
      th: 'การใช้ "ฉัน" และ "คุณ" สลับกัน อาจเป็นลักษณะที่พบในเด็กบางกลุ่ม',
    },
    s2i5Title: { en: '🤫 Verbal Unresponsiveness', th: '🤫 การไม่ตอบสนองด้วยเสียง' },
    s2i5Desc: {
      en: 'Instances where the child does not verbally respond when spoken to may indicate challenges in social communication.',
      th: 'ช่วงเวลาที่เด็กไม่ตอบสนองด้วยเสียงเมื่อถูกพูดด้วย อาจบ่งชี้ถึงความยากลำบากในการสื่อสาร',
    },
    s2i6Title: { en: '❓ Asking Questions', th: '❓ การถามคำถาม' },
    s2i6Desc: {
      en: 'Low rates of initiating questions may point to challenges in pragmatic language use.',
      th: 'อัตราการริเริ่มถามคำถามที่ต่ำ อาจบ่งชี้ถึงข้อจำกัดด้านทักษะเชิงปฏิบัติ (Pragmatic)',
    },
    s2warning: {
      en: '⚠️ These indicators are also found in typically developing children. Having these signs does not mean a child has ASD. Only a qualified professional can perform an appropriate assessment.',
      th: '⚠️ สัญญาณเหล่านี้พบได้ในเด็กพัฒนาการปกติเช่นกัน การมีสัญญาณเหล่านี้ไม่ได้หมายความว่าเด็กมี ASD ผู้เชี่ยวชาญเท่านั้นที่สามารถประเมินได้อย่างเหมาะสม',
    },
    s3Title: {
      en: 'Why Early Professional Consultation Matters',
      th: 'ทำไมการปรึกษาผู้เชี่ยวชาญเร็วจึงสำคัญ?',
    },
    s3p1: {
      en: 'Research consistently shows that early developmental support can make a significant difference, particularly during the first 6 years when brain plasticity is highest.',
      th: 'งานวิจัยจำนวนมากแสดงให้เห็นว่าการสนับสนุนพัฒนาการตั้งแต่เนิ่นๆ สามารถสร้างความแตกต่างอย่างมีนัยสำคัญต่อพัฒนาการของเด็ก โดยเฉพาะในช่วง 0-6 ปีแรก ซึ่งเป็นช่วงวิกฤตของการพัฒนาสมอง',
    },
    s3b1Title: { en: 'Critical Brain Window', th: 'ช่วงเวลาวิกฤตของสมอง' },
    s3b1Desc: {
      en: 'The brain develops most rapidly in the first 3 years. Intervention during this window is highly effective.',
      th: 'สมองเด็กพัฒนาอย่างรวดเร็วในช่วง 3 ปีแรก การสนับสนุนในช่วงนี้มีประสิทธิภาพสูงสุด',
    },
    s3b2Title: { en: 'Language Skill Development', th: 'การพัฒนาทักษะภาษา' },
    s3b2Desc: {
      en: 'Early speech-language support can significantly enhance a child\'s communicative competence.',
      th: 'การบำบัดด้านภาษาตั้งแต่เนิ่นๆ สามารถช่วยเพิ่มทักษะการสื่อสารได้อย่างมีนัยสำคัญ',
    },
    s3b3Title: { en: 'Social Skills', th: 'ทักษะทางสังคม' },
    s3b3Desc: {
      en: 'Early social skill support helps children build better relationships and social integration.',
      th: 'การสนับสนุนทักษะทางสังคมตั้งแต่เนิ่นๆ ช่วยให้เด็กสร้างความสัมพันธ์ที่ดีขึ้น',
    },
    s3b4Title: { en: 'Family Empowerment', th: 'ความมั่นใจของครอบครัว' },
    s3b4Desc: {
      en: 'Understanding and having a clear support plan reduces anxiety and empowers parents in caregiving.',
      th: 'การมีความรู้และแผนการสนับสนุนช่วยลดความกังวลและเพิ่มความมั่นใจของผู้ปกครอง',
    },
    s4Title: {
      en: 'How This Tool Works',
      th: 'เครื่องมือนี้ทำงานอย่างไร?',
    },
    s4p1: {
      en: 'This tool uses a questionnaire based on developmental speech-language milestones to assess concern levels across three domains:',
      th: 'เครื่องมือนี้ใช้แบบสอบถามที่ออกแบบจากงานวิจัยด้านภาษาศาสตร์คลินิก เพื่อประเมินระดับความกังวลเบื้องต้นใน 3 ด้าน:',
    },
    s4a1: { en: '🗣️ Speech & Language', th: '🗣️ ภาษาและการพูด' },
    s4a1d: {
      en: 'Sentence length, vocabulary variety, and speech clarity.',
      th: 'ความยาวประโยค ความหลากหลายคำศัพท์ ความชัดเจนในการพูด',
    },
    s4a2: { en: '🤝 Social Communication', th: '🤝 การสื่อสารทางสังคม' },
    s4a2d: {
      en: 'Eye contact, name responsiveness, and conversation initiation.',
      th: 'การสบตา การตอบชื่อ การริเริ่มบทสนทนา',
    },
    s4a3: { en: '🔄 Repetitive Behaviors', th: '🔄 พฤติกรรมซ้ำ' },
    s4a3d: {
      en: 'Echolalia, pronoun swapping, and routine adherence.',
      th: 'การพูดตาม การสลับสรรพนาม การยึดติดกิจวัตร',
    },
    s4warning: {
      en: '⚠️ <strong>Key Limitation:</strong> This tool uses a basic rule-based algorithm. It does not use machine learning or clinical models. Results are preliminary screening indicators and must not replace professional review.',
      th: '⚠️ <strong>ข้อจำกัดสำคัญ:</strong> เครื่องมือนี้ใช้อัลกอริทึมอย่างง่ายตามการตอบแบบสอบถาม ไม่ได้ใช้โมเดล AI หรือข้อมูลทางคลินิก ผลลัพธ์เป็นเพียงตัวบ่งชี้เบื้องต้นเท่านั้น และไม่สามารถทดแทนการประเมินโดยผู้เชี่ยวชาญได้',
    },
    s5Title: {
      en: 'Privacy & Data Security',
      th: 'ความเป็นส่วนตัวและข้อมูล',
    },
    s5h1: {
      en: '🛡️ Your Data is Secure',
      th: '🛡️ ข้อมูลของคุณปลอดภัย',
    },
    s5l1: {
      en: '✅ All data is processed <strong>locally in your browser</strong>.',
      th: '✅ ข้อมูลทั้งหมดประมวลผล <strong>ในเบราว์เซอร์ของคุณเท่านั้น</strong>',
    },
    s5l2: {
      en: '✅ <strong>No data is sent</strong> to any server.',
      th: '✅ <strong>ไม่มีข้อมูลถูกส่ง</strong> ไปยังเซิร์ฟเวอร์ใดๆ',
    },
    s5l3: {
      en: '✅ <strong>No data is retained</strong> after you close the tab.',
      th: '✅ <strong>ไม่มีการเก็บข้อมูล</strong> หลังจากปิดเบราว์เซอร์',
    },
    s5l4: {
      en: '✅ No <strong>login or registration</strong> required.',
      th: '✅ ไม่ต้อง <strong>ล็อกอินหรือสมัครสมาชิก</strong>',
    },
    s5l5: {
      en: '✅ No <strong>tracking cookies</strong> or analytics scripts.',
      th: '✅ <strong>ไม่มี cookies ติดตาม</strong> หรือ analytics',
    },
    s6Title: {
      en: 'Frequently Asked Questions',
      th: 'คำถามที่พบบ่อย',
    },
    faq1q: {
      en: 'Does a "High" concern level mean my child has ASD?',
      th: 'ผลระดับ "สูง" หมายความว่าลูกมี ASD ใช่ไหม?',
    },
    faq1a: {
      en: '<strong>No.</strong> A "High Concern" result simply suggests that observed patterns indicate the value of further professional assessment. Many children who flag as concern do not have ASD.',
      th: '<strong>ไม่ใช่</strong> ผลลัพธ์ "ระดับความกังวลสูง" หมายความว่าคำตอบของคุณบ่งชี้ว่าอาจมีลักษณะบางอย่างที่ควรได้รับการประเมินเพิ่มเติมโดยผู้เชี่ยวชาญ มีเด็กจำนวนมากที่มีผลคัดกรองสูงแต่ไม่ได้มี ASD',
    },
    faq2q: {
      en: 'Should I use this tool if my child is very young?',
      th: 'ลูกอายุน้อยมาก ควรใช้เครื่องมือนี้ไหม?',
    },
    faq2a: {
      en: 'This screening tool is calibrated for children 12 months and older. For infants under 12 months, developmental variance is high, and direct pediatric advice is recommended.',
      th: 'เครื่องมือนี้ออกแบบสำหรับเด็กตั้งแต่ 12 เดือนขึ้นไป สำหรับเด็กอายุน้อยกว่า 12 เดือน พัฒนาการมีความหลากหลายมาก ควรปรึกษากุมารแพทย์โดยตรง',
    },
    faq3q: {
      en: 'What type of specialist should I consult?',
      th: 'ควรปรึกษาผู้เชี่ยวชาญประเภทไหน?',
    },
    faq3a: {
      en: 'We recommend starting with a developmental pediatrician, who can refer you to a speech-language pathologist or child psychologist as appropriate.',
      th: 'แนะนำให้เริ่มจากกุมารแพทย์พัฒนาการ (Developmental Pediatrician) ซึ่งสามารถส่งต่อไปยังนักแก้ไขการพูดและภาษา (Speech-Language Pathologist) หรือนักจิตวิทยาเด็ก (Child Psychologist) ตามความเหมาะสม',
    },
    faq4q: {
      en: 'Is this tool suitable for Thai children?',
      th: 'เครื่องมือนี้ใช้ได้กับเด็กไทยไหม?',
    },
    faq4a: {
      en: 'The indicators are drawn from international clinical linguistic research. However, this screening tool has not been clinically validated specifically on a Thai cohort. It should only be used as a supportive reference.',
      th: 'คำถามในเครื่องมือนี้อ้างอิงจากงานวิจัยระหว่างประเทศ แต่ยังไม่ได้ผ่านการ ตรวจสอบความถูกต้องกับกลุ่มเด็กไทยโดยเฉพาะ ดังนั้นจึงควรใช้เป็นข้อมูล ประกอบการพูดคุยกับผู้เชี่ยวชาญเท่านั้น',
    },
    ctaTitle: {
      en: 'Ready to begin?',
      th: 'พร้อมที่จะเริ่มต้นหรือยัง?',
    },
    ctaDesc: {
      en: 'Completing the screening questionnaire takes only 5-10 minutes.',
      th: 'การทำแบบคัดกรองใช้เวลาเพียง 5-10 นาที',
    },
    ctaBtn: {
      en: '🩺 Start Screening Support',
      th: '🩺 เริ่มการคัดกรองเบื้องต้น',
    },
  },

  /* ── Footer ────────────────-------------------------------------------- */
  footer: {
    disclaimer: {
      en: 'This tool is part of an educational research project. It is not a medical device.',
      th: 'เครื่องมือนี้เป็นส่วนหนึ่งของโครงการวิจัยทางการศึกษา ไม่ใช่อุปกรณ์ทางการแพทย์',
    },
    copy: {
      en: 'Designed for child development screening support and educational purposes.',
      th: 'ออกแบบเพื่อการศึกษาและสนับสนุนการคัดกรอง',
    },
  },

  /* ── About / Safety Page ────────────────-------------------------------- */
  aboutPage: {
    title: {
      en: 'About this App & Safety Info',
      th: 'เกี่ยวกับระบบและความปลอดภัย',
    },
    subtitle: {
      en: 'Understand the capabilities, limitations, and safety commitments of asd-Project.',
      th: 'ทำความเข้าใจความสามารถ ข้อจำกัด และข้อตกลงความปลอดภัยของโครงการ asd-Project',
    },
    whatItIsTitle: {
      en: 'What the App Does',
      th: 'บทบาทหน้าที่ของเครื่องมือนี้',
    },
    whatItIsText: {
      en: 'asd-Project is an AI-assisted screening support tool designed to help parents, caregivers, and educators recognize early indicators of speech, language, and social communication development in children. By analyzing simple behavioral questionnaires and optional voice samples, it estimates a developmental concern level and provides educational next steps.',
      th: 'asd-Project เป็นเครื่องมือช่วยคัดกรองเบื้องต้นเพื่อช่วยให้ผู้ปกครอง ผู้ดูแล และอาจารย์ เข้าใจลักษณะสัญญาณบ่งชี้พัฒนาการในเด็ก ทั้งในด้านภาษา การแก้ไขคำพูด และการสื่อสารทางสังคม โดยประมวลผลผ่านแบบสอบถามและตัวเลือกบันทึกเสียงสนับสนุน เพื่อประเมินระดับความกังวลเบื้องต้นและให้ข้อแนะนำทางเลือกเพื่อการศึกษา',
    },
    whatItIsNotTitle: {
      en: 'What the App Does NOT Do',
      th: 'สิ่งที่เป็นข้อจำกัดและข้อควรระวัง',
    },
    whatItIsNotText: {
      en: 'This app is NOT a diagnostic tool. It does not provide medical diagnoses, clinical assessments, or official health reports. It does not state whether a child has Autism Spectrum Disorder (ASD). Only qualified pediatricians, child psychologists, and speech therapists can perform official developmental diagnoses.',
      th: 'เครื่องมือนี้ไม่ใช่การวินิจฉัยทางการแพทย์ ไม่ได้มีหน้าที่ประเมินทางคลินิกอย่างเป็นทางการ และไม่ระบุชี้ชัดว่าเด็กมีภาวะออทิสติกสเปกตรัม (ASD) หรือไม่ การประเมินเพื่อการวินิจฉัยต้องทำโดยแพทย์พัฒนาการเด็ก นักจิตวิทยาเด็ก หรือนักแก้ไขการพูดที่มีคุณวุฒิเท่านั้น',
    },
    humanReviewTitle: {
      en: 'Human Professional Review & Guidelines',
      th: 'ข้อกำหนดการทบทวนโดยผู้เชี่ยวชาญ',
    },
    humanReviewText: {
      en: 'We strongly recommend sharing the downloaded PDF summary report with a pediatrician, child therapist, or speech-language pathologist. Any developmental observations made by the app should be reviewed by a human professional to ensure the child receives appropriate, personalized support.',
      th: 'เราแนะนำอย่างยิ่งให้ผู้ปกครองนำรายงานสรุป (PDF) ไปเปิดเผยต่อแพทย์ พยาบาล นักจิตวิทยา หรือนักแก้ไขการพูด เพื่อรับการตรวจประเมินเพิ่มเติม การสังเกตทั้งหมดของระบบควรได้รับการยืนยันและพิจารณาโดยผู้เชี่ยวชาญที่เป็นมนุษย์เพื่อให้เด็กได้รับการสนับสนุนที่ถูกต้องเหมาะสม',
    },
    privacyTitle: {
      en: 'Privacy & Data Security',
      th: 'นโยบายความเป็นส่วนตัวและความปลอดภัยข้อมูล',
    },
    privacyText: {
      en: 'Privacy is our top priority. All responses and audio recordings are processed locally on your device within the browser (using SessionStorage). No data is transmitted to or stored on any server. Once you close this tab or clear the results, your data is permanently deleted.',
      th: 'ความเป็นส่วนตัวคือสิ่งสำคัญสูงสุดของเรา คำตอบและไฟล์เสียงบันทึกทั้งหมดจะถูกประมวลผลบนอุปกรณ์ของท่านในเบราว์เซอร์เท่านั้น (เก็บไว้ใน SessionStorage) ไม่มีการจัดเก็บหรือส่งข้อมูลออกไปยังเซิร์ฟเวอร์ภายนอก ข้อมูลจะถูกลบถาวรเมื่อท่านปิดแท็บเบราว์เซอร์หรือกดเริ่มต้นใหม่',
    },
    limitationsTitle: {
      en: 'System Limitations',
      th: 'ข้อจำกัดทางเทคนิค',
    },
    limitationsText: {
      en: '1. Language models and voice recognition APIs may vary in accuracy depending on noise, accents, and child pronunciation.<br/>2. The rules are simplified and based on international milestones, which might not fit all cultural contexts perfectly.<br/>3. The tool relies entirely on self-reported inputs from parents.',
      th: '1. การทำงานของระบบแปลงเสียงเป็นข้อความขึ้นกับสภาพแวดล้อม ความชัดเจนของสำเนียง และการออกเสียงของเด็ก<br/>2. เกณฑ์การคัดกรองอ้างอิงพัฒนาการเฉลี่ยทั่วไป อาจไม่สอดคล้องกับเด็กทุกคนอย่างสมบูรณ์แบบ<br/>3. การประเมินความกังวลวิเคราะห์ตามคำตอบที่ได้รับจากผู้ปกครองเท่านั้น',
    },
  },
  
  /* ── Profile Page ────────────────---------------------------------------- */
  profilePage: {
    title: {
      en: 'My Profile',
      th: 'ข้อมูลส่วนตัวของฉัน',
    },
    subtitle: {
      en: 'Manage your family profile and child information.',
      th: 'จัดการข้อมูลส่วนตัวของคุณและข้อมูลประวัติของเด็ก',
    },
    userSection: {
      en: 'Parent / Caregiver Details',
      th: 'ข้อมูลผู้ปกครอง / ผู้ดูแล',
    },
    nameLabel: {
      en: 'Full Name',
      th: 'ชื่อ-นามสกุล',
    },
    emailLabel: {
      en: 'Email Address',
      th: 'อีเมล',
    },
    childSection: {
      en: 'Saved Child Profiles',
      th: 'ประวัติพัฒนาการของเด็ก',
    },
    noChildText: {
      en: 'No saved child profiles yet. You can save screening results on the results page.',
      th: 'ยังไม่มีประวัติของเด็กที่บันทึกไว้ คุณสามารถบันทึกประวัติการคัดกรองได้จากหน้าผลลัพธ์',
    },
    saveBtn: {
      en: 'Save Changes',
      th: 'บันทึกข้อมูล',
    },
  },

  /* ── Settings Page ────────────────--------------------------------------- */
  settingsPage: {
    title: {
      en: 'Settings',
      th: 'การตั้งค่าระบบ',
    },
    subtitle: {
      en: 'Customize application theme, language, and data preferences.',
      th: 'ปรับแต่งธีมการแสดงผล ภาษา และความพึงพอใจการจัดการข้อมูล',
    },
    appearanceSection: {
      en: 'Appearance & Theme',
      th: 'การแสดงผลและธีม',
    },
    themeLabel: {
      en: 'Interface Theme',
      th: 'ธีมระบบ',
    },
    themeLight: {
      en: 'Light Mode',
      th: 'โหมดสว่าง',
    },
    themeDark: {
      en: 'Dark Mode',
      th: 'โหมดมืด',
    },
    langLabel: {
      en: 'Language Preference',
      th: 'การตั้งค่าภาษา',
    },
    dataSection: {
      en: 'Storage & Data Management',
      th: 'การจัดการข้อมูลและอุปกรณ์',
    },
    clearDataLabel: {
      en: 'Clear All Local Data',
      th: 'ล้างข้อมูลที่บันทึกไว้ทั้งหมด',
    },
    clearDataDesc: {
      en: 'Remove all saved profiles, screening answers, and cached results from your browser storage.',
      th: 'ลบข้อมูลประวัติ ผลการประเมินเบื้องต้น และข้อมูลแคชทั้งหมดจากพื้นที่จัดเก็บข้อมูลบนเครื่องนี้',
    },
    clearDataBtn: {
      en: 'Clear Data',
      th: 'ล้างข้อมูล',
    },
  },
};

// ─── Language helpers ────────────────---------------------------------------

/**
 * Get current language code ('en' | 'th'). Defaults to 'th'.
 */
export function getCurrentLang() {
  return localStorage.getItem(LANG_KEY) || 'th';
}

/**
 * Set the active language and notify the rest of the app.
 * @param {'en'|'th'} lang
 */
export function setLang(lang) {
  if (lang !== 'en' && lang !== 'th') return;
  localStorage.setItem(LANG_KEY, lang);
  window.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
  applyTranslations();
}

/**
 * Resolve a dot-notation key to the translated string.
 * Example: t('nav.home') → STRINGS.nav.home[currentLang]
 * @param {string} key
 * @returns {string}
 */
export function t(key) {
  const lang = getCurrentLang();
  const parts = key.split('.');
  let node = STRINGS;

  for (const part of parts) {
    if (node === undefined || node === null) return key;
    node = node[part];
  }

  if (node === undefined || node === null) return key;

  // If node is an object with lang keys, return the correct one
  if (typeof node === 'object' && node[lang] !== undefined) {
    return node[lang];
  }

  return typeof node === 'string' ? node : key;
}

/**
 * Walk the DOM and set textContent for every element with a [data-i18n] attr.
 * Also handles [data-i18n-placeholder] for placeholder text.
 */
export function applyTranslations() {
  // Text content
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const translated = t(el.dataset.i18n);
    if (translated !== el.dataset.i18n) {
      if (translated.includes('<') || translated.includes('&')) {
        el.innerHTML = translated;
      } else {
        el.textContent = translated;
      }
    }
  });

  // Placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    const translated = t(el.dataset.i18nPlaceholder);
    if (translated !== el.dataset.i18nPlaceholder) {
      el.placeholder = translated;
    }
  });

  // Update html lang attribute
  document.documentElement.lang = getCurrentLang();
}

/**
 * Bootstrap i18n: bind listeners and apply first translations.
 */
export function initI18n() {
  // Apply initial translations on DOM ready
  applyTranslations();

  // Listen for manual lang-toggle clicks (handled by nav module too)
  document.addEventListener('click', (e) => {
    const toggle = e.target.closest('[data-lang-toggle]');
    if (!toggle) return;
    const next = getCurrentLang() === 'en' ? 'th' : 'en';
    setLang(next);
  });

  // Re-translate whenever language changes externally
  window.addEventListener('langchange', () => {
    applyTranslations();
  });
}
