# Literature Review ฉบับแก้ไข: AI-Assisted Speech/Language Assessment for ASD

## บทสรุปสั้น

หลังตรวจ corpus ทั้งหมดใน ZIP ใหม่ พบว่าแนวคิดของ review เดิมถูกทาง แต่ต้องแก้ทั้งการคัด paper, ตัวเลขสถิติ, และระดับคุณภาพหลักฐาน รอบใหม่นี้คัดจาก master list 88 รายการ โดยมี PDF 79 ฉบับ และเลือก paper สุดท้าย 21 ฉบับ แยกเป็น core evidence, Thai/local background, broad review, และ future-only evidence

ข้อสรุปหลักคือ AI ด้าน speech, acoustic, และ transcript มีศักยภาพในการช่วยคัดกรองหรือสนับสนุนการประเมิน ASD แต่หลักฐานยังไม่พอสำหรับ claim ว่าใช้แทนการวินิจฉัยได้ จุดแข็งของ `asd-project` ควรวางเป็น decision-support + transcript/audio feature extraction + uncertainty gating + Thai validation readiness ไม่ใช่ diagnostic replacement

## 1. ภาพรวมหลักฐาน

วรรณกรรมที่ตรงกับโปรเจกต์แบ่งได้เป็น 5 กลุ่มหลัก:

1. Acoustic/prosody markers: Ma et al. (2024), Rybner et al. (2022), Mohanta et al. (2020), Yin et al. (2026), Chi et al. (2022), Radha et al. (2024), Georgiou & Paphiti (2026)
2. Transcript/NLP markers: Themistocleous et al. (2024), Assaf et al. (2025)
3. Severity and longitudinal quantification: Eni et al. (2025)
4. Clinical safety, multimodal decision support, and uncertainty handling: Megerian et al. (2022), Bae et al. (2025)
5. Thai/local clinical context: Tangviriyapaiboon et al. (2022, 2024), Srisinghasongkram et al. (2016), Chaturavitwong (2023)

## 2. Acoustic และ Prosody: มีสัญญาณจริง แต่ยังเปราะต่อ dataset shift

หลักฐานด้าน acoustic/prosody สนับสนุนว่าเสียงพูดมี marker ที่สัมพันธ์กับ ASD เช่น pitch/F0, prosody, formants, speech rate, spectral/energy features และ vocalization patterns. Ma et al. (2024) เป็น meta-analysis ที่เหมาะใช้เป็นฐานเหตุผล เพราะสังเคราะห์งาน natural-speech prosody โดยตรง ส่วน Rybner et al. (2022) สำคัญมากเพราะชี้ว่าประสิทธิภาพของ vocal-marker models อาจเปลี่ยนแรงเมื่อเปลี่ยน task หรือ corpus โดยรายงาน F1 ที่ต่างกันประมาณ 0.59-0.89 ใน setting การทดสอบต่างกัน

ดังนั้นการอ้างว่า acoustic model “แม่น” ต้องระวังมาก งานอย่าง Mohanta et al. (2020) และ Radha et al. (2024) มีประโยชน์เชิงวิธีวิทยา แต่ยังเป็นหลักฐานระดับ Moderate/Weak เพราะเป็น sample เล็ก ควบคุมสภาพแวดล้อม และไม่มี external validation ที่แข็งแรง ขณะที่ Yin et al. (2026) ให้ข้อมูล early acoustic prediction ที่น่าสนใจ แต่ต้องแก้ข้อมูลให้ถูก: ไม่ใช่ N=124 และไม่ใช่ CNN/Random Forest; paper ระบุ 88 infants, 28 ASD, best sigmoid-kernel SVM sensitivity 92.86%, specificity 93.33%, accuracy 93.18%

Georgiou & Paphiti (2026) ควรถูกลดเป็น future-only evidence เพราะเป็น medRxiv preprint, ยังไม่ peer-reviewed, เป็นผู้ใหญ่ 18 ASD + 18 neurotypical และ best discriminability ประมาณ 89% ไม่ใช่ n=50/91.2% ตาม review เดิม

## 3. Transcript/NLP: ตรงกับ asd-project มากที่สุด แต่ติดคอขวด transcription

สาย transcript/NLP เป็นแกนที่ตรงกับ `asd-project` มากที่สุด เพราะโปรเจกต์คำนวณฟีเจอร์ภาษาที่ตีความได้ เช่น MLU, lexical diversity, turn-taking และ transcript quality. Themistocleous et al. (2024) สนับสนุนว่า narrative transcript + ML/NLP สามารถจำแนก ASD ได้ดีในภาษา/งานเฉพาะ ขณะที่ Assaf et al. (2025) ตรงกว่าเดิมมาก เพราะใช้ TalkBank speech transcripts และ linguistic features โดยรายงาน accuracy มากกว่า 86% ในหลาย dataset

แต่ข้อจำกัดของกลุ่มนี้คือระบบต้องมี transcript ที่เชื่อถือได้ หากใช้ ASR/diarization อัตโนมัติ เช่น faster-whisper + diarization ใน `asd-project` ต้องมี transcript QA, confidence reporting, และ human review path สำหรับกรณีเสียงไม่ชัดหรือภาษาถิ่น เพราะความผิดพลาดของ transcript จะไหลต่อไปยัง feature และ prediction ทั้งหมด

## 4. Thai Context: สำคัญมาก แต่ยังไม่ใช่ Thai speech-AI validation

งานไทยที่ควรเก็บไว้มี 4 บทบาท:

- Tangviriyapaiboon et al. (2022): TDAS psychometric validation ในเด็กไทย N=130; PDF ระบุ sensitivity 100% และ specificity 82.4%
- Tangviriyapaiboon et al. (2024): economic evaluation ของ TDAS ในบริบทไทย เหมาะใช้อธิบาย implementation/value ไม่ใช่ AI accuracy
- Srisinghasongkram et al. (2016): Thai two-step M-CHAT evidence; PDF abstract ระบุ high-risk language-delay N=109 และ low-risk TD N=732
- Chaturavitwong (2023): background ด้าน speech/language in ASD สำหรับบริบท SLP ไทย

ข้อสรุปคือ review ควรพูดว่า “จำเป็นต้องทำ Thai validation” ไม่ใช่ “หลักฐานไทยยืนยันว่าโมเดล speech AI ใช้ได้แล้ว” เพราะหลักฐานไทยใน ZIP ส่วนใหญ่เป็น clinical scale, screening, EEG/speech-discrimination, หรือ background ไม่ใช่โมเดล speech-AI ที่ validate กับเด็กไทยโดยตรง

## 5. Safety, Uncertainty, Severity: จุดแข็งที่ควรยึดเป็นแกน claim

Megerian et al. (2022) เป็นหลักฐานสำคัญมากต่อ design ของ `asd-project` เพราะเป็น AI-based medical device ที่มี indeterminate output เป็น risk-control mechanism. Paper รายงาน 425 study completers และในกลุ่มที่ได้ผล determinate มี sensitivity 98.4% และ specificity 78.9%; แต่มีเพียง 31.8% ที่ได้ determinate output ซึ่งแปลว่า safety design ต้องยอม abstain ในเคสยาก

Bae et al. (2025) เป็น benchmark ล่าสุดที่แข็งแรงกว่า review เดิมควรเพิ่มเข้ามา เพราะใช้ข้อมูล 1242 children อายุ 18-48 เดือน รวมเสียง interaction กับ M-CHAT/SCQ-L/SRS และรายงาน Stage 1 AUROC 0.942, accuracy 0.86; Stage 2 AUROC 0.914, accuracy 0.852; risk-category agreement กับ ADOS-2 79.59%

Eni et al. (2025) สนับสนุนการทำ graded severity scoring เพราะ ASDSpeech ใช้ 99,193 vocalizations จาก 197 ASD children และทดสอบกับเด็กอีก 61 คนที่มี ADOS-2 assessments มากกว่า 1 timepoint จุดนี้เข้ากับ `asd-project` มากกว่า binary diagnosis claim เพราะเหมาะกับ monitoring และ severity estimation

## 6. Fairness และ Generalizability ต้องเป็น claim หลัก ไม่ใช่ footnote

QJR8K5QS หรือ Noor Project ควรถูกเพิ่ม เพราะตรงกับ gap เรื่อง fairness โดยตรง Paper นี้แสดงว่าผล mixed-gender อาจดูดี แต่ sensitivity ของ subgroup เช่น female samples อาจตกลงมาก นี่เป็นหลักฐานสำคัญว่าการรายงาน accuracy รวมอย่างเดียวไม่พอ

เมื่อรวมกับ Rybner et al. (2022) และ Rakotomanana & Rouhafzay (2025), gap ที่ควรเขียนชัดคือ: โมเดล speech AI สำหรับ ASD มีความเสี่ยงจาก corpus shift, task shift, sex/gender imbalance, language bias, และ tonal-language mismatch. สำหรับ `asd-project` จึงควรมี fairness/calibration audit และ subgroup reporting ก่อนอ้าง readiness ทางคลินิก

## 7. Quality Appraisal รอบใหม่

จาก final papers 21 ฉบับ:

- Strong: 7 ฉบับ ได้แก่ Srisinghasongkram 2016, Tangviriyapaiboon 2022, Ma 2024, Rybner 2022, Eni 2025, Megerian 2022, และ Bae 2025 ตาม design/scale/relevance
- Moderate: 12 ฉบับ เพราะมี relevance สูงแต่ยังมีข้อจำกัดเรื่อง sample, validation, corpus/language, หรือเป็น review-level evidence
- Weak: 2 ฉบับ คือ paper ที่เป็น preprint/adult-only หรือ conference/small controlled corpus เช่น Georgiou 2026 และ Radha 2024

จุดนี้แก้จาก review เดิมที่ให้ Strong 15/18 ซึ่งสูงเกินจริงสำหรับ field นี้

## 8. Research Gaps ที่ควรใช้ในรายงานใหม่

### Gap 1: Manual transcription และ transcript quality bottleneck

Transcript/NLP papers สนับสนุนแนวทางของ `asd-project` แต่ pipeline ต้องแสดง ASR/diarization uncertainty, transcript QA, และ human review option

### Gap 2: External validation และ dataset shift

Rybner et al. (2022), Assaf et al. (2025), และ Al Futaisi et al. (2025) ชี้ว่าผลลัพธ์ไม่ควรถูกสรุปจาก internal validation อย่างเดียว ต้องมี cross-corpus/external Thai validation

### Gap 3: Thai/tonal-language readiness

Thai clinical evidence สนับสนุนว่าต้องมี local validation แต่ยังไม่ยืนยันว่า speech-AI model ใช้กับเด็กไทยได้ทันที

### Gap 4: Forced binary decision risk

Megerian et al. (2022) และ Bae et al. (2025) สนับสนุนให้ใช้ uncertainty/indeterminate zone และ calibration แทนการบังคับตอบ ASD/TD ทุกเคส

### Gap 5: Severity and longitudinal monitoring

Eni et al. (2025) สนับสนุนการ quantify severity จาก speech features จึงเหมาะกับ progress tracking มากกว่า diagnostic replacement

## 9. ข้อความ claim ที่ปลอดภัยสำหรับ asd-project

ควรเขียนว่า:

> Existing evidence suggests that speech, acoustic, and transcript-based AI features may support ASD screening and progress monitoring. However, current evidence remains limited by small samples, corpus shift, language bias, subgroup fairness concerns, and insufficient external validation. Therefore, asd-project should be positioned as a research prototype and clinical decision-support aid for speech-language professionals, with uncertainty reporting and Thai validation as mandatory next steps.

ไม่ควรเขียนว่า:

> AI can diagnose ASD accurately from speech.

## 10. บทสรุป

Paper ที่คัดใหม่สมเหตุสมผลกว่า review เดิม เพราะเพิ่ม paper ที่หายไปและลดน้ำหนัก paper ที่เสี่ยง overclaim. ชุดใหม่เน้น speech/transcript/fairness/uncertainty โดยตรง และแยก Thai context ออกจาก AI model performance อย่างชัดเจน

ถ้าจะส่งอาจารย์หรือใช้ประกอบรายงาน ควรใช้ชุดไฟล์ใหม่ในโฟลเดอร์นี้แทน `generated_literature_review.md` เดิม
