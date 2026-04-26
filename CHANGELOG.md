# Changelog

> **โปรเจกต์:** AI-Assisted Clinical Assessment of Autism (Term Paper)  
> **รูปแบบ:** Semantic Versioning (MAJOR.MINOR.PATCH)  
> **วันที่ update ล่าสุด:** 26 เมษายน 2026

---

## [v0.11.0] - 2026-04-26

### Added
- **Echolalia detection (`echolalia_count`, `echolalia_ratio`)** — feature
  ใหม่ใน `src/data_loader.py` ที่ตรวจจับ utterance ของ CHI ที่
  *ซ้ำคำพูด verbatim* (≥2 content tokens) ของ utterance ใด ๆ
  ภายใน 5 ประโยคก่อนหน้า (รวม self-repetition)
- เพิ่ม column ใน `data/combined_features.csv` (122 rows) และ
  `data/longitudinal_features.csv` (87 rows)
- Screening Tool dashboard ตอนนี้รับ input echolalia ผ่าน form
- Feature reference page อธิบาย echolalia ทาง clinical

### Changed
- `FEATURES` list ใน `app/dashboard.py` เพิ่มจาก 11 → **13 features**
- Re-trained Logistic Regression classifier ด้วย 13 features

### Empirical findings (เบื้องต้น)
จาก dataset ของเรา (122 children):
- **ASD:** echolalia_ratio mean = 0.028, max = 0.169
- **DD:**  echolalia_ratio mean = 0.014, max = 0.096
- **TD:**  echolalia_ratio mean = 0.014, max = 0.054

ASD มี echolalia สูงกว่า TD/DD ~2 เท่า ตรงกับ clinical literature

### Rationale
Prizant (1983) "Echolalia in autism" — echolalia เป็น core ASD marker
ที่ Kanner (1943) ระบุไว้ในนิยามแรกของ autism. การเพิ่ม feature นี้
ปิดช่องว่างใหญ่ของ feature set เดิมที่ไม่มี repetition-based marker

---

## [v0.10.0] - 2026-04-26

### Added
- **Per-prediction explainability (SHAP-equivalent)** — ใน Screening Tool page เพิ่ม
  visualization อธิบายว่าแต่ละ feature ส่งผลต่อ prediction ของเด็กคนนั้น ๆ
  อย่างไร (contribution to log-odds = `coef × standardised value`) ช่วยให้
  speech therapist เข้าใจและไว้ใจผลของ AI มากขึ้น
- แสดง breakdown: `intercept + sum(contributions) = logit → P(ASD)`

### Rationale
อ้างอิงจาก Jeon et al. (2024) "Reliable ASD Diagnosis for Pediatrics Using
Machine Learning and Explainable AI" — XAI ช่วยให้ clinician trust model มากขึ้น

---

## [v0.9.0] - 2026-04-26

### Added
- **CHANGELOG.md** — บันทึก version history ของโปรเจกต์ทั้งหมด เพื่อติดตามการพัฒนา
- **REFERENCES.md** — รวบรวม bibliography ทั้งหมด (37+ รายการ) พร้อมคำอธิบายว่าทำไมใช้อ้างอิงแต่ละตัว

---

## [v0.8.0] - 2026-04-25

### Changed
- **Removed HuggingFace Spaces** — ลบส่วน HF Spaces ออกจาก project ทั้งหมด (DEPLOYMENT.md, Dockerfile)
- **Reverted Dockerfile port** — กลับมาใช้ port 8501 (standard Streamlit) แทน 7860
- **Removed HF-specific comments** — ลบ comment ที่เกี่ยวกับ HF Spaces ออกจาก Dockerfile
- **Updated DEPLOYMENT.md** — ลบ section HuggingFace Spaces ออก เหลือแค่ Streamlit Community Cloud + Self-host Docker

### Added
- **REFERENCES.md** — Full bibliography สำหรับ term paper (clinical linguistics, ASD criteria, tools, methods)

### Removed
- **Git branches** `hf-clean`, `hf-deploy` — ลบ local branches ที่ใช้ทดสอบ HF Spaces

---

## [v0.7.0] - 2026-04-24

### Changed
- **Dockerfile port** — เปลี่ยนจาก 8501 เป็น 7860 (HuggingFace Spaces requirement)
- **Dockerfile comments** — เพิ่ม comment อธิบายว่าเป็น HF-specific
- **README.md** — เพิ่ม YAML header สำหรับ HuggingFace Spaces

### Added
- **Graceful data handling** — dashboard จัดการ missing data files (FileNotFoundError) และ empty DataFrames อย่างสงบ
- **Empty DataFrame guards** — เพิ่ม `if df.empty: return` ใน page_overview, page_eda, page_screening, page_progress

### Fixed
- **HF Spaces binary file rejection** — ใช้ orphan branch + commit squashing เพื่อเอา binary files ออก
- **HF Spaces YAML metadata warning** — เพิ่ม YAML header ใน README.md

---

## [v0.6.0] - 2026-04-23

### Added
- **PROJECT_SUMMARY_TH.md** — สรุปสิ่งที่ทำไปแล้วทั้งหมด (dataset, features, ผลลัพธ์, โครงสร้างระบบ, วิธีรัน)
- **DISCUSSION_TH.md** — ส่วนคุยกับอาจารย์ (3 scenarios, roadmap, จริยธรรม, 11 คำถาม)
- **SUMMARY_TH.md (updated)** — เปลี่ยนเป็น index ที่ชี้ไปสองไฟล์ข้างต้น + เก็บเนื้อหาเดิมไว้ด้านล่าง

### Changed
- **Documentation structure** — แยก project summary และ discussion points ออกจากกันเพื่อให้อ่านง่ายขึ้น

---

## [v0.5.0] - 2026-04-22

### Added
- **DEPLOYMENT.md** — Deployment guide สำหรับ Streamlit Community Cloud + HuggingFace Spaces + Docker
- **Dockerfile** — Production container สำหรับ deployment
- **.dockerignore** — Exclude large corpora จาก Docker image
- **.streamlit/config.toml** — Streamlit configuration (maxUploadSize = 500 MB, theme)
- **packages.txt** — System dependencies สำหรับ Docker (ffmpeg, libsndfile1)
- **Updated README.md** — เพิ่ม pipeline commands, data sources table, audio pipeline section
- **Updated SUMMARY_TH.md** — เพิ่ม deployment options, Docker/Streamlit Cloud

---

## [v0.4.0] - 2026-04-21

### Added
- **Audio upload page** (🎤 Audio assessment) — ใน Streamlit dashboard อัปโหลด `.wav`/`.mp3` → Whisper ASR → diarization → CHAT → features → prediction
- **Audio pipeline CLI** — `python -m src.audio_pipeline.pipeline recording.wav` สร้าง `.cha` จาก audio
- **Smoke test** — `tests/test_audio_pipeline_smoke.py` ทดสอบ CHAT formatter round-trip ผ่าน pylangacq
- **ASR evaluation script** — `src/evaluate_asr.py` คำนวณ WER กับ TalkBank ground-truth

### Changed
- **Dashboard** — เพิ่ม page ที่ 6 (Audio assessment) เข้าไปใน navigation

---

## [v0.3.0] - 2026-04-20

### Added
- **Streamlit dashboard** (`app/dashboard.py`) — 6 pages interactive:
  1. Overview — hero + summary stats
  2. Feature reference — อธิบาย 11 features พร้อม clinical meaning
  3. EDA — interactive boxplots, correlation heatmap, pairplot
  4. Screening — Logistic Regression prediction + feature importance
  5. Progress tracker — longitudinal trajectories + composite score
  6. Audio assessment — upload audio → end-to-end prediction
- **Custom CSS** — polished UI ด้วย gradient backgrounds, cards, metric cards, hero sections
- **Feature documentation** — FEATURE_DOCS dictionary อธิบายแต่ละ feature พร้อม icon, clinical meaning, direction

---

## [v0.2.0] - 2026-04-19

### Added
- **Audio pipeline** (`src/audio_pipeline/`) — end-to-end .wav → .cha:
  - `whisper_transcribe.py` — faster-whisper wrapper (word-level segments + confidence)
  - `diarization.py` — PitchHeuristicDiarizer (F0-based) + PyannoteDiarizer (SOTA)
  - `chat_formatter.py` — Convert utterances → valid CHAT format (@Begin, @ID, *CHI:, %tim:)
  - `pipeline.py` — Wire all 3 components together
- **requirements.txt** — Updated ด้วย faster-whisper, librosa, soundfile, jiwer
- **11 features** — Full feature extraction จาก CHAT (mlu, ttr, unintelligible, zero_vocalization, etc.)

---

## [v0.1.0] - 2026-04-18

### Added
- **Data loader** (`src/data_loader.py`) — Read CHAT files จาก 5 corpora:
  - Eigsti (ASD 16 / DD 16 / TD 16)
  - Nadig (ASD 13 / TD 25)
  - NYU-Emerson (ASD 30)
  - Flusberg (ASD 6, longitudinal)
  - Rollins (5 เด็ก, 21 sessions)
  - QuigleyMcNally (ASD 10 / TD 9)
- **Feature extraction** — 11 features ต่อไฟล์ (mlu, ttr, unintelligible, zero_vocalization, question_ratio, etc.)
- **Combined dataset** — `data/combined_features.csv` (122 children)
- **Longitudinal dataset** — `data/longitudinal_features.csv` (87 sessions, 12 children)

### Added
- **Classifier** (`src/classifier.py`) — Logistic Regression, SVM, Random Forest:
  - Binary: ASD vs non-ASD (AUC 0.93)
  - Multi-class: ASD / DD / TD
  - Stratified 5-fold CV
- **Deep learning** (`src/deep_learning.py`) — TabularMLP + Bi-LSTM:
  - MLP on hand-engineered features
  - Bi-LSTM on utterance sequences

### Added
- **EDA** (`src/eda.py`) — Summary stats + plots:
  - Group counts, age distribution
  - Feature boxplots by group
  - Correlation heatmap
  - Feature pairplot

### Added
- **Progress tracking** (`src/progress_tracking.py`) — Longitudinal analysis:
  - Linear regression per child-feature
  - Composite score (z-score aggregation)
  - 9/12 เด็กแสดง IMPROVING pattern

---

## Versioning Policy

- **MAJOR** — เปลี่ยนโครงสร้างใหญ่, breaking changes, ลบ features ที่สำคัญ
- **MINOR** — เพิ่ม features ใหม่, backward compatible
- **PATCH** — Bug fixes, small improvements, documentation updates

---

## Future Roadmap

### v0.10.0 (Planned)
- [ ] เพิ่ม echolalia ratio feature
- [ ] เพิ่ม pronoun reversal detection
- [ ] เพิ่ม turn-taking latency
- [ ] Thai Whisper fine-tuning (ถ้ามีข้อมูลไทย)

### v1.0.0 (Target)
- [ ] External validation กับ dataset ไทย
- [ ] Mobile app MVP
- [ ] IRB approval + pilot study
