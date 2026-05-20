# แผนพัฒนาต่อและ Roadmap สำหรับคุยอาจารย์

> **โปรเจกต์:** AI-Assisted Program for Clinical Assessment of Autism  
> **สถานะ:** มี prototype ครบทั้ง Pastel unified dashboard, parent public demo, clinician workflow, audio-to-CHAT, Model Trust/Fairness, Transcript QA, therapist progress reports, AI Speech Therapist Assistant, Clinician Workflow Simulator และ Thai Validation Readiness Pack
> **วันที่ update ล่าสุด:** 20 พฤษภาคม 2026

เอกสารนี้สรุปว่าจะจัดการโปรเจกต์ต่ออย่างไร หลังจากมี pipeline หลักและ interactive dashboard รวมเนื้อหาทั้งหมดของโปรเจกต์แล้ว

---

## 1. เป้าหมายระยะสั้น

เป้าหมายถัดไปคือทำให้โปรเจกต์เล่าได้ชัดและ demo ได้ครบ workflow:

```text
ไฟล์เสียง / CHAT transcript
→ ถอดเสียงและจัดเป็น .cha
→ ตรวจทาน transcript
→ สกัด speech-language features
→ screening risk estimate
→ progress report สำหรับนักบำบัด
```

หน้า public หลักใช้ **Pastel unified dashboard** (`app/dashboard_unified.py`) เป็นหน้าเดียวสำหรับ parent demo, clinician workflow, Model Trust/Fairness และ project presentation ส่วน `project_dashboard/` คงไว้เป็น legacy static reference เท่านั้น

สิ่งที่เสร็จแล้วถึง v0.19.0:
- Parent Public Demo แบบ no-data-retention และ safe wording
- Shared 13-feature schema + versioned model bundle
- Model Trust metrics: threshold, calibration, fairness audit, decision curve, subgroup robustness, leave-one-corpus-out, model card
- Pastel dashboard section สำหรับ data inventory, corpus map, research evidence, glossary และ presentation mode
- AI Transcript Reviewer สำหรับตรวจ `.cha` structure, speaker tier, utterance quality, marker counts, Thai language tag readiness, ASR confidence และ parse readiness
- Therapist Progress Report Generator จาก `longitudinal_features.csv` พร้อม Markdown/PDF export
- AI Speech Therapist Assistant สำหรับสรุป transcript quality, speech-language patterns, screening risk estimate และ progress trends ให้ therapist review
- Clinician Workflow Simulator สำหรับ demo transcript QA, screening pattern interpretation และ progress case brief ในหน้าเดียว
- Thai Validation Readiness documentation ที่ระบุชัดว่ายังไม่มี Thai validation data และยังไม่ใช่เครื่องมือวินิจฉัย

---

## 2. Feature ที่ควรทำต่อ

### 2.1 AI Transcript Reviewer

สถานะ: implemented ใน v0.18.0 และ enhanced ใน v0.19.0 เป็น rule-based reviewer หลังจาก ASR/CHAT formatter ก่อนนำไปคำนวณ feature

สิ่งที่ควรตรวจ:

- โครงสร้าง CHAT เช่น `@Begin`, `@End`, `@Participants`, `@ID`, speaker code
- punctuation ท้าย utterance
- speaker label ที่น่าสงสัย เช่น `*CHI:` แต่ประโยคเหมือนคำถามของผู้ใหญ่
- segment หรือ metadata ที่ ASR/diarization confidence ต่ำ
- marker ที่ควรใช้ เช่น `xxx`, `&=laugh`, `[/]`, pause marker
- ภาษาไทย/อังกฤษที่อาจต้องใส่ language tag เช่น `@Languages: eng, tha`

หลักการใช้งาน:

- AI ทำหน้าที่ flag และเสนอแก้
- คนต้อง confirm ก่อน re-export `.cha`
- output ต้องบอก quality score และรายการ issue อย่างโปร่งใส

### 2.2 Therapist Progress Report

สถานะ: implemented ใน v0.18.0 และเพิ่ม PDF export ใน v0.19.0 เป็น report generator สำหรับนักบำบัดจากหลาย session ของเด็กคนเดียวกัน

เนื้อหา report:

- จำนวน session และช่วงอายุ
- MLU, MLUW, TTR, total words, total utterances
- echolalia ratio, unintelligible ratio, zero vocalization
- composite progress score
- summary ภาษาไทยที่ใช้คำปลอดภัยทางคลินิก
- caveat ว่าเป็นข้อมูลประกอบการติดตามพัฒนาการ ไม่ใช่ข้อสรุปทางการแพทย์

### 2.3 Thai Validation Track

สถานะ: readiness documentation เสร็จแล้ว แต่ยังไม่มี Thai clinical validation data ดังนั้นยังไม่สามารถ claim ความแม่นยำในเด็กไทยได้

แผนเก็บ/ทดสอบข้อมูลภาษาไทย:

- หา baseline เด็กไทยตามอายุ
- ตรวจว่า Whisper ถอดเสียงเด็กไทยได้แม่นแค่ไหน
- วัด feature drift ระหว่าง gold transcript กับ ASR transcript
- retrain หรือ calibrate model เมื่อมีข้อมูลไทยเพียงพอ

### 2.4 Clinical Readiness Pack

สิ่งที่ v0.18.0 เพิ่มเพื่อให้ demo ปลอดภัยขึ้น:

- Pastel dashboard หน้า Clinical Readiness แสดง current prototype status, Thai clinical prerequisites, transcript QA workflow และ therapist report workflow
- Streamlit หน้า Transcript QA & Reports สำหรับ upload `.cha`, ดู quality score, issue table, marker counts และสร้างรายงาน Markdown
- `artifacts/model_card.json` เพิ่ม `thai_validation_status: "not_yet_validated"`
- `docs/THAI_VALIDATION_READINESS_TH.md` อธิบายว่า demo พิสูจน์ workflow และ governance readiness แต่ไม่พิสูจน์ Thai clinical accuracy

### 2.5 AI Speech Therapist Assistant

สถานะ: implemented เป็น rule-based/template-based assistant layer สำหรับ clinical decision support

สิ่งที่ทำได้:

- สรุปผล Transcript QA ว่า usable / needs human review / not usable
- อธิบาย speech-language pattern จาก 13-feature schema แบบปลอดภัย
- สรุป screening risk estimate โดยใช้คำว่า risk estimate และ screening support
- สรุป progress trend จากหลาย session และสร้าง therapist-facing case brief

สิ่งที่ทำไม่ได้:

- ไม่แทนนักบำบัดหรือแพทย์
- ไม่พิสูจน์ความแม่นยำกับเด็กไทยถ้ายังไม่มี Thai validation data
- ไม่ควรใช้โดยไม่มี human-in-the-loop review

### 2.6 v0.19.0 Clinical Readiness Enhancements

สิ่งที่เพิ่มเพื่อทำให้ demo พร้อมคุยเชิง governance มากขึ้น โดยยังไม่ใช้ Thai child data:

- Transcript QA ตรวจ Thai character mismatch กับ `@Languages` และสรุป average ASR confidence หากมี metadata
- Fairness/calibration script สร้าง `fairness_metrics.csv` และ `calibration_summary.csv` จาก public English-speaking corpora เพื่อดู model behavior ตาม sex, age band และ corpus
- Streamlit Model Trust & Fairness view แสดง ECE, Brier score, group TPR/FPR และ demographic parity difference
- Therapist report export เป็น PDF สำหรับใช้เป็นตัวอย่างเอกสาร progress tracking
- Clinician Workflow Simulator แสดง three-stage workflow: Transcript QA → Screening & Patterns → Progress & Case Brief

ข้อจำกัดสำคัญ: fairness/calibration metrics ชุดนี้เป็น readiness audit บนข้อมูลเดิม ไม่ใช่หลักฐานความแม่นยำสำหรับเด็กไทย และยังต้อง external validation เมื่อมี Thai dataset

---

## 3. การใช้ Skills ในโปรเจกต์นี้

| Skill | ใช้เมื่อ | ผลลัพธ์ที่ควรได้ |
|------|---------|------------------|
| `asd-audio-pipeline-qa` | แก้ audio → CHAT → prediction | checklist ความถูกต้องของ ASR, diarization, CHAT, feature |
| `asd-clinical-ml-reviewer` | แก้ classifier, XAI, severity, report wording | ลด data leakage, overclaim และ clinical risk |
| `asd-advisor-report-writer` | เตรียมเอกสารไทย/คุยอาจารย์ | summary, discussion points, wording ที่ปลอดภัย |
| `personal-data-analyst` | ทำตาราง/กราฟ progress | summary table, trend chart, report metric |
| `personal-code-quality` | เพิ่ม feature/test/refactor | code ที่ maintain ได้พร้อม test |
| `personal-security-auditor` | มี audio/transcript เด็กหรือ deploy | privacy checklist และ hardening plan |
| `personal-researcher` | เพิ่ม references หรือเทียบวิธี | source-backed synthesis |
| `personal-devops-deployer` | เตรียม demo/deploy | runbook, deploy checklist, rollback |
| `project-update-workflow` | หลังทุกการเปลี่ยนสำคัญ | README, CHANGELOG, docs, version consistency |

---

## 4. ลำดับงานที่แนะนำ

### Phase 1: Pastel dashboard

- ใช้ `app/dashboard_unified.py` เป็นหน้ารวมเนื้อหาทั้งหมดของโปรเจกต์และ Model Trust
- เตรียม talking points จาก `docs/PROJECT_SUMMARY_TH.md`
- ใช้ `docs/DISCUSSION_TH.md` เป็นรายการคำถามท้ายการนำเสนอ

### Phase 2: Transcript review

- เพิ่มโมดูลตรวจ `.cha` แบบ rule-based ก่อน
- แสดง issue ใน dashboard เป็นตารางให้แก้/confirm
- เชื่อมกับ CHATTER validator และ `pylangacq` parse check

### Phase 3: Therapist report

- เพิ่ม report จาก `longitudinal_features.csv`
- เริ่มจาก Markdown/PDF export ก่อน
- ค่อยต่อยอดเป็น DOCX หากอาจารย์เห็นว่าจำเป็น

### Phase 4: Research readiness

- ทำ feature-drift test ระหว่าง gold `.cha` กับ ASR `.cha`
- เพิ่ม subgroup metrics, fairness/calibration audit และ confidence interval
- เตรียม protocol สำหรับข้อมูลไทยและ IRB

---

## 5. คำถามที่ควรขอคำแนะนำจากอาจารย์

1. ควรให้แกนหลักของ term paper เป็น screening, progress tracking หรือ audio-to-report?
2. หากเพิ่ม AI transcript reviewer อาจารย์เห็นว่าเพียงพอสำหรับ demo หรือควรมี human review form ที่ละเอียดกว่า?
3. Report สำหรับนักบำบัดควรเชื่อมกับ assessment scale ใดในบริบทไทย?
4. มีโอกาสเข้าถึงข้อมูลเสียง/วิดีโอเด็กไทยหรือไม่ และต้องผ่าน IRB ขั้นตอนไหน?
5. สำหรับ term paper รอบนี้ ควรหยุดที่ demo prototype หรือขยายไป validation study?

---

## 6. Clinical Safety

ทุก output ของระบบควรใช้คำว่า:

- ช่วยคัดกรอง
- risk estimate
- decision support
- progress tracking
- ควรประเมินเพิ่มเติมโดยผู้เชี่ยวชาญ
- ต้องมี human-in-the-loop
- ต้องผ่าน external validation ก่อนใช้งานจริง

หลีกเลี่ยงคำว่า:

- วินิจฉัย
- ใช้ถ้อยคำที่สื่อว่าเป็นการยืนยัน ASD
- แทนแพทย์หรือนักบำบัด
- แม่นยำพอใช้จริงทางคลินิก

ถ้าพูดถึง parent screening tools ภายนอก ให้บอกว่าเป็น established tools ที่ต้องตรวจ permission/licensing ก่อนทำ electronic หรือ commercial use และไม่ควร copy คำถาม M-CHAT-R/F เข้าในโปรเจกต์นี้
