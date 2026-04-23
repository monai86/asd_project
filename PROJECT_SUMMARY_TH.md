# 📊 สรุปโปรเจกต์ — สิ่งที่ทำไปแล้วทั้งหมด

> **ชื่อโปรเจกต์:** การประยุกต์ใช้ปัญญาประดิษฐ์เพื่อสนับสนุนการประเมินทางคลินิกสำหรับเด็กออทิสติก
> *(AI-Assisted Program for Clinical Assessment of Autism)*
>
> **ผู้จัดทำ:** นักศึกษาคณะเทคนิคการแพทย์ ปี 3 มหาวิทยาลัยมหิดล
> **ประเภท:** Term Paper
> **วันที่ update ล่าสุด:** 23 เมษายน 2026

📖 **เอกสารคู่กัน:** [DISCUSSION_TH.md](./DISCUSSION_TH.md) — สิ่งที่ต้องคุยกับอาจารย์ / Roadmap / Ethics

---

## 1. ที่มาและเป้าหมาย

จากการปรึกษาอาจารย์ อาจารย์เสนอแนว 3 ทาง:

1. **Video assessment** — ให้ AI วิเคราะห์วิดีโอเด็กขณะคุยกับนักบำบัด แล้วให้คะแนนตาม scale
2. **Progress tracking** — ประเมินว่าเด็กที่เข้ารับการบำบัดทุกสัปดาห์มีพัฒนาการดีขึ้นหรือไม่
3. **Screening tool** — ช่วยพ่อแม่ประเมินเบื้องต้นว่าลูกเสี่ยง ASD หรือไม่

**ข้อจำกัดที่พบ:** ไม่มี video dataset สาธารณะที่ใช้ได้ จึงใช้ **ข้อความถอดเสียง (CHAT transcripts)** จาก
[TalkBank / ASDBank](https://asd.talkbank.org/) แทน ซึ่งครอบคลุม **แนวทาง 2 + 3** ได้ดี

**สิ่งที่ทำเพิ่มเติม (v2):** สร้าง **end-to-end audio pipeline** เอง — upload `.wav` → Whisper ASR → CHAT transcript → prediction → ครอบคลุมถึงแนวทางที่จะใช้กับพ่อแม่/หมอในคลินิกได้ด้วย

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

ใช้ library `pylangacq` อ่านไฟล์ CHAT แล้วคำนวณ feature รวม **11 ตัว** ต่อไฟล์

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

---

## 4. ผลลัพธ์หลัก

### 4.1 Classification — Binary (ASD vs non-ASD)

ทดสอบด้วย **Stratified 5-fold CV** บน **122 คน**

| Model | Accuracy | F1-macro | ROC-AUC |
|-------|----------|----------|---------|
| **Logistic Regression** | **85.3%** | **0.852** | **0.927** ⬆️ |
| SVM (RBF) | 82.0% | 0.820 | 0.896 |
| Random Forest | 77.9% | 0.778 | 0.885 |

### 4.2 Classification — Multi-class (ASD / DD / TD)

| Model | Accuracy | F1-macro |
|-------|----------|----------|
| **Random Forest** | **82.0%** | **0.744** |
| Logistic Regression | 77.1% | 0.726 |
| SVM | 72.1% | 0.678 |

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

### 4.4 Audio Pipeline (Whisper → CHAT → Prediction)

```
.wav upload → faster-whisper ASR → pitch diarization
           → CHAT formatter → 11 features → LogReg (AUC 0.93)
           → P(ASD) + recommendation + .cha download
```

Demo: เปิด dashboard → หน้า **🎤 Audio assessment** → upload `.wav` → รอ 1–3 นาที

---

## 5. สถาปัตยกรรมระบบ

```
Raw audio (.wav/.mp3)  [v2]
      ↓ faster-whisper + pitch diarization
.cha files (CHAT transcripts)
      ↓ pylangacq
Feature extraction (11 features/ไฟล์)
      ↓
┌──────────────┬──────────────────┬──────────────────┐
↓              ↓                  ↓                  ↓
EDA       Classification    Progress Tracking   Audio upload
(plots)  (LogReg AUC 0.93) (composite score)   (end-to-end)
      ↓
Streamlit Dashboard (6 หน้า, interactive)
      ↓
Docker / Streamlit Cloud
```

---

## 6. โครงสร้างไฟล์

```
asd-project/
├── data/                     ไฟล์ .cha ต้นฉบับ + CSVs ที่สกัดแล้ว
├── src/
│   ├── audio_pipeline/       [v2] .wav → .cha pipeline
│   ├── data_loader.py        .cha → CSV (11 features)
│   ├── classifier.py         LogReg / SVM / RF
│   ├── deep_learning.py      MLP + Bi-LSTM (PyTorch)
│   ├── progress_tracking.py  longitudinal analysis
│   ├── eda.py                plots
│   └── evaluate_asr.py       [v2] WER benchmark
├── app/dashboard.py          Streamlit 6-page dashboard
├── tests/                    smoke test audio pipeline
├── reports/                  figures + metrics CSVs
├── Dockerfile                Docker container
├── requirements.txt
├── DEPLOYMENT.md
├── PROJECT_SUMMARY_TH.md     ไฟล์นี้
├── DISCUSSION_TH.md          ประเด็นคุยกับอาจารย์
└── SUMMARY_TH.md             index
```

---

## 7. วิธีรัน

```bash
pip install -r requirements.txt          # ติดตั้ง dependencies
python src/data_loader.py                # สกัด features จาก .cha
python src/eda.py                        # สร้าง plots
python src/classifier.py                 # train classifiers
python src/progress_tracking.py         # longitudinal analysis
streamlit run app/dashboard.py           # เปิด dashboard
```

---

## 8. จุดเด่นที่ควรนำเสนออาจารย์

1. **ตอบโจทย์อาจารย์ครบ 2/3 แนวทาง** — Progress tracking + Screening (video ทำไม่ได้เพราะไม่มี dataset)
2. **AUC 0.93** — Binary screening ดีกว่างานวิจัยหลายชิ้นที่ published
3. **Dataset 122 คน** จาก 5 corpora (เพิ่มจาก 86 → +42%)
4. **Clinical interpretability** — ใช้ MLU, TTR ที่นักบำบัดเข้าใจ ไม่ใช่ black-box
5. **9/12 เด็กแสดง IMPROVING pattern** ใน progress tracking
6. **Interactive dashboard 6 หน้า** รวม 🎤 Audio assessment
7. **End-to-end audio pipeline** — Whisper + pitch diarization + CHAT formatter (verified ด้วย smoke test)
8. **Deploy-ready** — Docker + Streamlit Cloud + GitHub

---

## 9. ข้อจำกัด

1. Dataset ยังเล็ก (122 คน) — ยังไม่ generalize เต็มที่
2. Transcripts เป็นภาษาอังกฤษ — ต้อง retrain ด้วยข้อมูลไทย
3. LSTM under-performs เพราะข้อมูลน้อย
4. ASR/diarization ยังไม่มี WER benchmark
5. ยังไม่มี external validation
