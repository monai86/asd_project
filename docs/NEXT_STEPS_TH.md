# แผนพัฒนาต่อและ Roadmap สำหรับคุยอาจารย์

> **โปรเจกต์:** AI-Assisted Program for Clinical Assessment of Autism  
> **สถานะ:** มี prototype ครบทั้ง parent public demo, clinician dashboard, audio-to-CHAT, Model Trust และ Project Atlas  
> **วันที่ update ล่าสุด:** 17 พฤษภาคม 2026

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

หน้า `project_dashboard/` ถูกยกระดับเป็น **Project Atlas + Model Trust Dashboard** แยกจาก Streamlit dashboard เดิมที่เน้น researcher/clinician workflow

สิ่งที่เสร็จแล้วใน v0.17.0:
- Parent Public Demo แบบ no-data-retention และ safe wording
- Shared 13-feature schema + versioned model bundle
- Model Trust metrics: threshold, calibration, decision curve, subgroup robustness, leave-one-corpus-out, model card
- Project Atlas section สำหรับ data inventory, corpus map, research evidence, glossary และ presentation mode

---

## 2. Feature ที่ควรทำต่อ

### 2.1 AI Transcript Reviewer

เพิ่มระบบช่วยตรวจ `.cha` หลังจาก ASR/CHAT formatter ก่อนนำไปคำนวณ feature

สิ่งที่ควรตรวจ:

- โครงสร้าง CHAT เช่น `@Begin`, `@End`, `@Participants`, `@ID`, speaker code
- punctuation ท้าย utterance
- speaker label ที่น่าสงสัย เช่น `*CHI:` แต่ประโยคเหมือนคำถามของผู้ใหญ่
- segment ที่ ASR confidence ต่ำ
- marker ที่ควรใช้ เช่น `xxx`, `&=laugh`, `[/]`, pause marker
- ภาษาไทย/อังกฤษที่อาจต้องใส่ language tag

หลักการใช้งาน:

- AI ทำหน้าที่ flag และเสนอแก้
- คนต้อง confirm ก่อน re-export `.cha`
- output ต้องบอก quality score และรายการ issue อย่างโปร่งใส

### 2.2 Therapist Progress Report

เพิ่ม report generator สำหรับนักบำบัดจากหลาย session ของเด็กคนเดียวกัน

เนื้อหา report:

- จำนวน session และช่วงอายุ
- MLU, MLUW, TTR, total words, total utterances
- echolalia ratio, unintelligible ratio, zero vocalization
- composite progress score
- summary ภาษาไทยที่ใช้คำปลอดภัยทางคลินิก
- caveat ว่าเป็นข้อมูลประกอบการติดตามพัฒนาการ ไม่ใช่ diagnosis

### 2.3 Thai Validation Track

เตรียมแผนเก็บ/ทดสอบข้อมูลภาษาไทย:

- หา baseline เด็กไทยตามอายุ
- ตรวจว่า Whisper ถอดเสียงเด็กไทยได้แม่นแค่ไหน
- วัด feature drift ระหว่าง gold transcript กับ ASR transcript
- retrain หรือ calibrate model เมื่อมีข้อมูลไทยเพียงพอ

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

### Phase 1: Project dashboard

- ใช้ `project_dashboard/` เป็นหน้ารวมเนื้อหาทั้งหมดของโปรเจกต์และ Model Trust
- เตรียม talking points จาก `docs/PROJECT_SUMMARY_TH.md`
- ใช้ `docs/DISCUSSION_TH.md` เป็นรายการคำถามท้ายการนำเสนอ

### Phase 2: Transcript review

- เพิ่มโมดูลตรวจ `.cha` แบบ rule-based ก่อน
- แสดง issue ใน dashboard เป็นตารางให้แก้/confirm
- เชื่อมกับ CHATTER validator และ `pylangacq` parse check

### Phase 3: Therapist report

- เพิ่ม report จาก `longitudinal_features.csv`
- เริ่มจาก Markdown/CSV export ก่อน
- ค่อยต่อยอดเป็น PDF/DOCX หากอาจารย์เห็นว่าจำเป็น

### Phase 4: Research readiness

- ทำ feature-drift test ระหว่าง gold `.cha` กับ ASR `.cha`
- เพิ่ม subgroup metrics และ confidence interval
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

หลีกเลี่ยงคำว่า:

- วินิจฉัย
- ยืนยันว่าเป็น ASD
- แทนแพทย์หรือนักบำบัด
- แม่นยำพอใช้จริงทางคลินิก
