# 📊 สรุปโปรเจกต์ — สิ่งที่ทำไปแล้วทั้งหมด

> **ชื่อโปรเจกต์:** การประยุกต์ใช้ปัญญาประดิษฐ์เพื่อสนับสนุนการประเมินทางคลินิกสำหรับเด็กออทิสติก
> *(AI-Assisted Program for Clinical Assessment of Autism)*
>
> **ผู้จัดทำ:** นักศึกษาคณะเทคนิคการแพทย์ ปี 3 มหาวิทยาลัยมหิดล
> **ประเภท:** Term Paper
> **วันที่ update ล่าสุด:** 5 มิถุนายน 2026

📖 **เอกสารคู่กัน:** [DISCUSSION_TH.md](./DISCUSSION_TH.md) — สิ่งที่ต้องคุยกับอาจารย์ / Roadmap / Ethics

📌 **เอกสารต่อยอด:** [NEXT_STEPS_TH.md](./NEXT_STEPS_TH.md) — แผนพัฒนา transcript QA, Progress Report, Thai ASR Drift Simulation และ Thai validation protocol

📌 **Dashboard ล่าสุด:** ใช้ `presentation-dashboard/` เป็น **Advisor Presentation Dashboard** สำหรับอธิบายข้อมูลทั้งหมดของโปรเจกต์และแสดงความน่าเชื่อถือของโมเดล เช่น threshold, calibration, decision curve, subgroup robustness, model card และ Thai ASR Drift Simulation

📌 **Public demo:** มี 3 web apps หลัก: `public-screening/`, `therapist-clinician-app/`, และ `presentation-dashboard/`; ดูสคริปต์พูดสั้น ๆ ได้ที่ `docs/PRESENTER_GUIDE_TH.md`

---

## 1. ที่มาและเป้าหมาย

จากการปรึกษาอาจารย์ อาจารย์เสนอแนว 3 ทาง:

1. **Video assessment** — ให้ AI วิเคราะห์วิดีโอเด็กขณะคุยกับนักบำบัด แล้วให้คะแนนตาม scale
2. **Progress tracking** — ประเมินว่าเด็กที่เข้ารับการบำบัดทุกสัปดาห์มีพัฒนาการดีขึ้นหรือไม่
3. **Screening tool** — ช่วยพ่อแม่ประเมินเบื้องต้นว่าลูกเสี่ยง ASD หรือไม่

**ข้อจำกัดที่พบ:** ไม่มี video dataset สาธารณะที่ใช้ได้ จึงใช้ **ข้อความถอดเสียง (CHAT transcripts)** จาก
[TalkBank / ASDBank](https://asd.talkbank.org/) แทน ซึ่งครอบคลุม **แนวทาง 2 + 3** ได้ดี

**สิ่งที่ทำเพิ่มเติม (v2):** สร้าง **end-to-end audio pipeline** เอง — upload `.wav` → Whisper ASR → CHAT transcript → acoustic profile → human review gate → screening risk estimate → ครอบคลุมถึงแนวทางที่จะใช้กับพ่อแม่/หมอในคลินิกได้ด้วย

**สิ่งที่ทำเพิ่มเติม (v3):** เพิ่ม **Parent Public Demo** แบบ no-data-retention สำหรับผู้ปกครอง, สร้าง **versioned model bundle**, รวม schema 14 features ให้ตรงกันทั้งระบบ และเพิ่ม **Model Trust Dashboard** เพื่ออธิบายความน่าเชื่อถือของโมเดลอย่างโปร่งใส

**สิ่งที่ทำเพิ่มเติม (v1.3.0 / Capacitor & Reference readiness update):** บรรจุแอปพลิเคชันฝั่งนักบำบัดให้ใช้งานเป็นแบบ native iOS ผ่าน Capacitor, ปรับโฉมดีไซน์ UI คลินิกใหม่แบบ Crimson Oasis (Wine Ink, Glassmorphism, SVG Icons), เสริมระบบความปลอดภัยในการเข้าถึงไฟล์ (Path Traversal Protection), เชื่อมต่อ API CRUD สมบูรณ์สำหรับ Caseload/Consent/Hydration ใน API mode และยกระดับการดึงข้อมูลวิจัยอ้างอิงเชิงลึกด้วย CLAN KIDEVAL parsing พร้อมระบบตรวจเช็คความพร้อมข้อมูล (Reference Readiness Index) เพื่อเตือนใน UI comparison panel เมื่อพบกรณีกลุ่มตัวอย่างต่ำ (low_n)

**สิ่งที่ทำเพิ่มเติม (v1.4.0 / CLANc Batchalign & Privacy hardening):** บูรณาการ Batchalign2 และคำสั่ง UnixCLAN (`check`/`kideval`) ทำงานแบบเบื้องหลัง (Background Tasks) เมื่อนักบำบัดลงนามรับรอง transcript, พัฒนาความยาวเฉลี่ยคำพูดภาษาไทยรายพยางค์ (`MLU-s`) และคำ (`MLU-w`) โดยใช้ PyThaiNLP, ปรับปรุงสคริปต์ `evaluate_asr.py` ให้คำนวณ CER และแบ่งคำไทย, และยกระดับความเป็นส่วนตัว (Privacy Hardening) ให้ De-identify/Orphan ข้อมูล session/notes/goals/reports ทั้งหมดเมื่อถอนความยินยอม (Consent Status "declined")

**สิ่งที่ทำเพิ่มเติม (v1.5.0 / Postgres & Storage Integration):** พัฒนาคลาส `PostgresSupabaseRepository` สำหรับเชื่อมต่อกับระบบฐานข้อมูล Supabase (PostgreSQL) ผ่าน `supabase-py` SDK แทน mock repository เดิม ทำให้รองรับการบันทึกข้อมูล cases, sessions, transcripts, consents, reports และ audit logs ได้จริง พร้อมทั้งเพิ่ม `REPOSITORY_MODE` สำหรับเปิด-ปิดการใช้งานระหว่าง mock และ postgres, พัฒนาระบบอัปโหลดไฟล์เสียงไปยัง Supabase Storage แบบปลอดภัยผ่าน Signed Upload URLs โดยใช้ FileStorageAdapter ของหน้าบ้าน และเพิ่มชุดทดสอบการทำงานของ repository และ storage อัปโหลด

**สถานะปัจจุบัน (v1.5.0 / Postgres & Storage Integration - advisor-demo readiness):** โปรเจกต์มี prototype ครบสำหรับ screening support,
progress tracking, audio-to-CHAT, transcript QA, therapist Progress Report,
clinician workflow simulator, model trust/fairness audit, FastAPI pilot boundary,
Thai ASR Drift Simulation, acoustic profile แบบ descriptive-only, human review gate และ
Model Trust ที่รายงาน confidence interval / subgroup reliability แล้ว รวมถึงระบบฐานข้อมูลและการจัดเก็บไฟล์เสียงจริงผ่าน Supabase
แกนที่ยังไม่เสร็จคือ **external Thai validation / pilot study** และการเก็บหลักฐานทางคลินิกจริงในบริบทไทย ส่วน Paper/Literature
workflow เป็นเครื่องมือสนับสนุนการอ่านงานวิจัย เพื่อหา research gap และ
แนวทางพัฒนาต่อ ไม่ใช่ feature หลักของระบบ

---

## 2. ชุดข้อมูลที่ใช้

### 2.1 Cross-sectional (ใช้ฝึก classifier)

| Corpus | Design | จำนวน | กลุ่ม |
|--------|--------|-------|-------|
| **Eigsti** | Cross-sectional | 48 คน | ASD 16, DD 16, TD 16 |
| **Nadig** | Cross-sectional | 38 คน | ASD 13, TD 25 (ตรวจจาก `@ID` header) |
| **NYU-Emerson** | Cross-sectional + video/audio | 30 คน | ASD 30 (ทั้งหมด) |
| **Flusberg** | Longitudinal → ใช้ session 1 | 6 คน | ASD 6 |
| **รวม** | | **122 คน** | **ASD 65 · TD 41 · DD 16** |

### 2.2 Longitudinal (ใช้ติดตามพัฒนาการ)

| Corpus | เด็ก | Sessions |
|--------|------|----------|
| **Rollins** | 5 | 21 sessions |
| **Flusberg** | 6 | 64 sessions |
| **Quigley** (partial) | 2 | 2 sessions |
| **รวม** | **12 เด็ก** | **87 sessions** |

**ข้อค้นพบสำคัญจาก data:**
- Nadig **ไม่ใช่ ASD ทั้งหมด** ตามที่ `0types.txt` บอก — มี TD 25 คน, ASD 13 คน เป็น case-control design ต้องอ่าน label จาก `@ID` header โดยตรง
- **QuigleyMcNally** เป็น **mother speech** (`*MOT:`) ไม่มี child utterances — เลยงดออกจาก classification dataset
- ใช้ **session 1** ของ Flusberg ใน classifier เพื่อหลีกเลี่ยง **repeated measures bias**

---

## 3. Features ที่สกัดออกมาจากไฟล์ `.cha`

ใช้ library `pylangacq` อ่านไฟล์ CHAT แล้วคำนวณ feature หลักรวม **14 ตัว** ต่อไฟล์

### 3.1 ตารางสรุป

| กลุ่ม | Feature | ตัวอย่างค่า | แนวที่คาดหวัง |
|------|---------|-------------|---------------|
| **Demographics** | `age_months` | 48.0 | (control ตัวแปร) |
| | `sex` | male / female | (control ตัวแปร) |
| **Productivity** | `total_utterances` | 180 | TD > ASD |
| | `total_words` | 400 | TD > ASD |
| **Complexity** | `mlu` (morphemes) | 2.5 | TD > ASD |
| | `mluw` (words) | 2.3 | TD > ASD |
| **Lexical diversity** | `ttr` | 0.40 | TD > ASD (โดยทั่วไป) |
| **ASD markers** | `unintelligible_count` | 10 | ASD > TD |
| | `unintelligible_ratio` | 0.06 | ASD > TD |
| | `zero_vocalization_count` | 5 | ASD > TD |
| | `nonverbal_vocalization_count` | 8 | ASD > TD |
| | `echolalia_count` | 3 | ASD > TD |
| | `echolalia_ratio` | 0.02 | ASD > TD |
| | `pronoun_reversal_count` | 1 | heuristic marker |
| **Pragmatic** | `question_ratio` | 0.08 | TD > ASD |

> **หมายเหตุ:** ทุก feature คำนวณจาก **เฉพาะคำพูดของเด็ก (`*CHI:`)** ไม่นับคำพูดของผู้ตรวจ (`*INV:`) หรือผู้ปกครอง (`*MOT:`)

### 3.2 Composite Score สำหรับ Progress Tracking

```
composite = mean over 7 features of:
    direction × (feature - mean) / std
```

- `direction = +1` สำหรับ features ที่ **สูง = ดี** (`mlu`, `mluw`, `ttr`, `total_words`, `total_utterances`)
- `direction = -1` สำหรับ features ที่ **ต่ำ = ดี** (`unintelligible_ratio`, `zero_vocalization_count`)

**ผลลัพธ์:** `+` = ดีกว่าค่าเฉลี่ย · `−` = ต่ำกว่าค่าเฉลี่ย · **เพิ่มขึ้นเรื่อย ๆ** = กำลังพัฒนา ✅

### 3.3 Features ขั้นสูงที่เพิ่มเติม (v0.10.0 - v0.14.0)

นอกเหนือจาก 14 transcript features ข้างต้น ยังมีฟีเจอร์พิเศษสำหรับ screening ขั้นสูง:

| Feature | คำอธิบาย | ประโยชน์ทางคลินิก |
|---------|-----------|----------------|
| **Per-estimate Explainability (XAI)** | แสดง SHAP-equivalent contribution ของแต่ละ feature | ให้คลินิกเห็นว่า feature ใดผลัก screening risk estimate |
| **Uncertainty Band (40-60%)** | คาดการณ์ในช่วงนี้ = UNCERTAIN | ลดความมั่นใจมากเกินไป ตาม FDA-cleared device |
| **Graded Severity Scoring (0-10)** | 3 sub-scores: ASD severity, communication strength, marker burden | ให้รายละเอียดมากกว่า binary classification |
| **Multi-modal Input (Parent Concern Checklist)** | checklist ผู้ปกครอง 10 ข้อที่โปรเจกต์เขียนเอง + late-fusion | เพิ่มข้อมูลจากผู้ปกครอง ตาม multi-modular pipeline โดยไม่ดัดแปลง M-CHAT-R/F |
| **Echolalia Detection** | นับ utterances ที่ซ้ำตำแหน่งเดิมใน 5 ครั้งล่าสุด | Detect core ASD symptom จาก speech pattern |

---

## 4. ผลลัพธ์หลัก

### 4.1 Classification — Binary (ASD vs non-ASD)

ทดสอบด้วย **Stratified 5-fold CV** บน **122 คน**

| Model | Accuracy | F1-macro | ROC-AUC | Sensitivity | Specificity |
|-------|----------|----------|---------|-------------|-------------|
| **Logistic Regression** | **86.9%** | **0.869** | **0.935** ⬆️ | **0.846** | **0.895** |
| SVM (RBF) | 85.3% | 0.852 | 0.917 | 0.815 | 0.895 |
| Random Forest | 83.6% | 0.836 | 0.903 | 0.800 | 0.877 |

Model Trust เพิ่มเติม:
- LogReg PPV = **0.902**, NPV = **0.836**, Brier score = **0.096**
- 95% CI ของ AUC = **0.892-0.971** จาก bootstrap 1,000 รอบ
- Uncertainty zone 40-60% มี **9/122 เคส** ที่ระบบควร abstain / แนะนำประเมินเพิ่ม
- มี threshold metrics, calibration bins, decision curve, subgroup reliability, fairness audit และ leave-one-corpus-out สำหรับใช้ audit ใน dashboard

### 4.1.1 Deep Learning Baselines

| Model | Accuracy | F1-macro | ROC-AUC |
|-------|----------|----------|---------|
| **TabularMLP** | 85.3% | 0.853 | **0.932** |
| UtteranceLSTM | 63.1% | 0.631 | 0.719 |

ข้อสรุป: MLP บน hand-engineered transcript features ทำได้ใกล้เคียง LogReg มาก แต่
Bi-LSTM จาก sequence utterance ยังตามหลังชัดเจน สะท้อนว่า dataset ยังเล็กและ
feature engineering ที่ clinician เข้าใจยังเป็นแกนที่เหมาะที่สุดในรอบนี้

### 4.2 Classification — Multi-class (ASD / DD / TD)

| Model | Accuracy | F1-macro |
|-------|----------|----------|
| **Random Forest** | **82.8%** | **0.775** |
| Logistic Regression | 78.7% | 0.743 |
| SVM | 74.6% | 0.706 |

### 4.3 Progress Tracking

**9/12 เด็กแสดง IMPROVING pattern** (composite score เพิ่มขึ้น):

| เด็ก | Corpus | Features ที่ดีขึ้น | Δ Composite |
|------|--------|-------------------|-------------|
| **Roger** | Rollins | **7/7** | **+2.22** 🏆 |
| **Carl** | Rollins | 6/7 | **+1.28** |
| Sid | Rollins | 7/7 | +0.61 |
| Rick | Flusberg | 5/7 | +0.60 |
| Josh | Rollins | 5/7 | +0.45 |

**Trends ที่มีนัยสำคัญ (p < 0.05):**
- **Mars**: `total_words` เพิ่ม 46 คำ/session (r = 0.98, p = 0.004)
- **Carl**: `ttr` พุ่งขึ้นต่อเนื่อง (r = 0.97, p = 0.03)
- **Rick**: `mlu`/`mluw` เพิ่ม 11 sessions (r = 0.89, p = 0.0002)

### 4.4 Audio Pipeline (Whisper → CHAT → Screening risk estimate)

```
.wav upload → faster-whisper ASR → pitch diarization
           → CHAT formatter → acoustic profile → 14 transcript features
           → human review gate → screening risk estimate + .cha download
```

Demo: เปิด dashboard → หน้า **🎤 Audio assessment** → upload `.wav` → รอ 1–3 นาที

---

## 5. สถาปัตยกรรมระบบ

```
Raw audio (.wav/.mp3)  [v2]
      ↓ faster-whisper + pitch diarization
.cha files (CHAT transcripts)
      ↓ pylangacq
Feature extraction (14 features/ไฟล์)
      ↓
┌──────────────┬──────────────────┬──────────────────┐
↓              ↓                  ↓                  ↓
EDA       Classification    Progress Tracking   Audio upload
(plots)  (LogReg AUC 0.935) (composite score)  (end-to-end)
      ↓
Python ML backend + FastAPI pilot boundary
      ↓
3 Vite web apps: Public Screening / Therapist-Clinician / Advisor Dashboard
      ↓
Cloudflare Pages-ready static web surfaces + local Python research backend
```

---

## 6. โครงสร้างไฟล์

```
asd-project/
├── public-screening/         parent-facing screening support app
├── therapist-clinician-app/  therapist/clinician workflow app
├── presentation-dashboard/   advisor presentation dashboard
├── data/                     ไฟล์ .cha ต้นฉบับ + CSVs ที่สกัดแล้ว
├── src/
│   ├── audio_pipeline/       [v2] .wav → .cha pipeline
│   ├── therapist_backend/    FastAPI pilot boundary
│   ├── data_loader.py        .cha → CSV (14 features)
│   ├── classifier.py         LogReg / SVM / RF
│   ├── deep_learning.py      MLP + Bi-LSTM (PyTorch)
│   ├── progress_tracking.py  longitudinal analysis
│   ├── transcript_reviewer.py ตรวจคุณภาพ CHAT transcript
│   ├── therapist_report.py   therapist progress reports
│   ├── speech_therapist_assistant.py decision-support summaries
│   ├── eda.py                plots
│   └── evaluate_asr.py       optional WER benchmark
├── scripts/
│   ├── compute_fairness_metrics.py fairness + calibration audit
│   ├── simulate_thai_drift.py Thai ASR Drift Simulation
│   ├── paper_scout.py        research support: หา paper/gap
│   └── build_zotero_import.py research support: จัด reference
├── tests/                    unit/smoke tests สำหรับ pipeline และ reports
├── docs/literature/          paper scout, screening, Zotero import outputs
├── reports/                  figures + metrics CSVs
├── requirements.txt
├── docs/DEPLOYMENT.md
├── docs/PROJECT_SUMMARY_TH.md ไฟล์นี้
├── docs/NEXT_STEPS_TH.md     roadmap ปัจจุบัน
└── docs/SUMMARY_TH.md        index
```

---

## 7. วิธีรัน

```bash
pip install -r requirements.txt           # ติดตั้ง Python dependencies
python src/data_loader.py                 # สกัด features จาก .cha
python src/eda.py                         # สร้าง plots
python src/classifier.py                  # train classifiers
python src/progress_tracking.py           # longitudinal analysis
python scripts/compute_fairness_metrics.py
python scripts/simulate_thai_drift.py     # สร้าง Thai ASR Drift Simulation JSON
cd presentation-dashboard && npm run dev  # เปิด Advisor Dashboard
cd therapist-clinician-app && npm run dev # เปิด Therapist app
cd public-screening && npm run dev        # เปิด Public Screening app
```

เครื่องมือสำหรับ research-gap review ไม่ใช่ pipeline หลัก:

```bash
python scripts/paper_scout.py --tag speech --tag audio --save
python scripts/build_zotero_import.py
```

---

## 8. จุดเด่นที่ควรนำเสนออาจารย์

1. **ตอบโจทย์อาจารย์ครบ 2/3 แนวทาง** — Progress tracking + Screening (video ทำไม่ได้เพราะไม่มี dataset)
2. **AUC 0.935 + Model Trust** — Binary screening มี AUC, sensitivity,
   specificity, PPV/NPV, calibration/Brier, threshold playground และ
   decision curve ให้ตรวจสอบ ไม่ได้โชว์แค่ accuracy
3. **Dataset 122 คน** จาก 5 corpora (เพิ่มจาก 86 → +42%)
4. **Clinical interpretability** — ใช้ MLU, TTR ที่นักบำบัดเข้าใจ ไม่ใช่ black-box
5. **9/12 เด็กแสดง IMPROVING pattern** ใน progress tracking
6. **3 web apps พร้อม demo** — แยก parent public screening, therapist workflow และ advisor presentation dashboard ชัดเจน
7. **End-to-end audio pipeline** — Whisper + pitch diarization + CHAT formatter (verified ด้วย smoke test)
8. **Cloudflare Pages-ready web surfaces** — ทั้ง 3 Vite apps build/deploy เป็น static web surfaces ได้ ส่วน Python backend ใช้ local/pilot research boundary
9. **Parent Public Demo** — มีหน้า public-safe สำหรับผู้ปกครองแบบไม่เก็บข้อมูล ใช้ parent concern checklist และ safe wording
10. **Advisor dashboard + Model Trust** — มี dashboard สำหรับ overview, dataset, feature reference, model trust, calibration, decision curve, subgroup robustness, progress trajectory, Thai ASR Drift Simulation, research evidence, glossary และ limitations
11. **Transcript QA + therapist report + clinician simulator** — มี workflow สำหรับตรวจ `.cha`, สรุป speech-language pattern และสร้าง case brief โดยยังยืนยัน human-in-the-loop
12. **Research-gap support** — มีสคริปต์ช่วยรวบรวม paper ASD/AI เพื่อดูทิศทางงานวิจัยปัจจุบันและหา gap สำหรับพัฒนาต่อ แต่ไม่นับเป็น feature หลักของ prototype
13. **Advisor-ready trust upgrade** — เพิ่ม 14th feature (`pronoun_reversal_count`), acoustic profile แบบ descriptive-only, 95% CI, subgroup reliability flag, Thai ASR Drift Simulation และ human review gate ก่อนแปลผล screening risk estimate

### 8.1 วิธีเปิด Advisor dashboard

```bash
cd presentation-dashboard
npm run dev
```

---

## 9. ข้อจำกัด

1. Dataset ยังเล็ก (122 คน) — ยังไม่ generalize เต็มที่
2. Transcripts เป็นภาษาอังกฤษ — ต้อง retrain ด้วยข้อมูลไทย
3. LSTM under-performs เมื่อเทียบกับ LogReg/TabularMLP เพราะข้อมูลยังเล็ก
4. ASR/diarization ยังไม่มี benchmark ภาษาไทยจาก gold transcript ที่เพียงพอ
5. ยังไม่มี external validation / prospective pilot กับเด็กไทย
6. Literature/Paper Scout เป็นข้อมูลประกอบการหา research gap เท่านั้น ไม่ใช่หลักฐาน validation ของระบบ และยังต้องอ่าน abstract/full text ก่อนนำไป cite

---

## 10. งานถัดไปที่ควรทำ

1. **Thai validation protocol** — เขียนแผน pilot: consent, IRB, inclusion/exclusion, gold transcript, ASR WER, feature drift และ calibration endpoint
2. **Demo QA ก่อนส่ง/พรีเซนต์** — smoke test 3 web apps, transcript QA, Progress Report export/print, fairness tables และ Thai ASR Drift Simulation
3. **Evidence wording** — ปรับรายงานให้ชัดว่า AUC 0.935 เป็นผลบน public English-speaking corpora ไม่ใช่ความแม่นยำในเด็กไทย
4. **Research-gap review** — อ่าน/คัด paper จาก `docs/literature/` เพื่อระบุว่าในปัจจุบันยังขาดอะไร เช่น Thai child speech validation, ASR-to-feature drift, clinical workflow validation หรือ multimodal dataset
5. **Optional next build** — ถ้ามีเวลาหรืออาจารย์ต้องการ ให้เพิ่ม DOCX report export หรือ human review form สำหรับแก้ `.cha` ก่อน re-export
