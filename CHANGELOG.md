# Changelog

> **โปรเจกต์:** AI-Assisted Clinical Assessment of Autism (Term Paper)  
> **รูปแบบ:** Semantic Versioning (MAJOR.MINOR.PATCH)  
> **วันที่ update ล่าสุด:** 17 พฤษภาคม 2026

---

## [v0.17.1] - 2026-05-17

### Added
- **Public access links** — README now surfaces the Hugging Face public app,
  GitHub Pages Project Atlas, and a short presenter guide so the project can
  be shared without digging through local setup instructions
- **Presenter guide** — added `docs/PRESENTER_GUIDE_TH.md` for a
  3-5 minute project walkthrough covering what the system does, what to show,
  and which claims to avoid

### Changed
- **Project entrypoint documentation** — README now highlights the public
  access path first, making the repository easier to demo for parents,
  advisors, and first-time viewers

---

## [v0.17.0] - 2026-05-17

### Added
- **Parent public demo** — เพิ่มหน้า Streamlit สำหรับผู้ปกครองแบบ Thai-first,
  no-data-retention, safe wording, parent concern checklist, optional audio
  privacy gate และ downloadable parent summary โดยไม่อ้างว่าเป็น diagnosis
- **Shared feature schema** — เพิ่ม `src/feature_schema.py` เป็น source of
  truth เดียวสำหรับ 13 features, positive/marker feature groups และ
  uncertainty thresholds เพื่อกัน feature order mismatch ระหว่าง training,
  dashboard และ model bundle
- **Model Trust metrics** — `src/classifier.py` สร้างไฟล์ใหม่สำหรับ dashboard:
  `binary_oof_predictions.csv`, `threshold_metrics.csv`,
  `calibration_bins.csv`, `decision_curve.csv`,
  `subgroup_performance.csv`, `leave_one_corpus_out.csv`
- **Model artifacts** — เพิ่ม `artifacts/screening_model.joblib`,
  `artifacts/model_card.json` และ `artifacts/feature_schema.json` สำหรับ
  versioned model loading, model card, data hash, thresholds และ caveats
- **Feature schema test** — เพิ่ม `tests/test_feature_schema.py` เพื่อตรวจว่า
  CSV, schema artifact และ feature order ของโมเดลตรงกัน
- **Project Atlas + Model Trust dashboard** — ยกระดับ `project_dashboard/`
  ด้วย Model Trust section, threshold playground, calibration view,
  decision curve, uncertainty zone, subgroup robustness, leave-one-corpus-out,
  model card, data inventory, corpus explorer, research evidence, glossary
  และ presentation mode
- **Static public Atlas build** — เพิ่ม `scripts/build_public_atlas.sh` และ
  `netlify.toml` เพื่อสร้าง bundle สำหรับ deploy dashboard presentation โดย
  ไม่ copy raw `.cha`, uploaded audio หรือ executable `.joblib` model

### Changed
- **Classifier schema** — sklearn classifier ใช้ 13 features รวม echolalia
  แล้ว; LogReg binary ROC-AUC ใหม่ = **0.9312**, sensitivity = **0.8462**,
  specificity = **0.9123**, PPV = **0.9167**, NPV = **0.8387**,
  Brier score = **0.0983**
- **Deep learning baselines** — rerun PyTorch baselines บน 13-feature schema:
  TabularMLP ROC-AUC = **0.9320**, accuracy/F1 = **0.8525**;
  UtteranceLSTM ROC-AUC = **0.7193**, accuracy/F1 = **0.6311**
- **Dashboard model loading** — Streamlit dashboard พยายามโหลด versioned
  model bundle ก่อน และ fallback ไป train runtime เฉพาะเมื่อ artifact ไม่มี
- **Audio privacy control** — หน้า Audio Assessment เพิ่มปุ่มลบ temp
  audio/transcript cache ของ session หลังตรวจ segment เสร็จ
- **README / dashboard docs** — อัปเดตวิธีรัน, output metrics, artifacts,
  Project Atlas และ Model Trust ให้ตรงกับ v0.17.0
- **Deployment readiness** — อัปเดต `docs/DEPLOYMENT.md` สำหรับ Streamlit
  Cloud, Hugging Face Spaces, Netlify/Cloudflare Pages และ Docker; ปรับ
  Streamlit CORS config ให้ไม่ถูก override ตอน startup

### Fixed
- **Multi-class CV stability** — แปลง label เป็น numpy string array เพื่อแก้
  `cross_val_predict` กับ pandas/pyarrow indexing ใน Python 3.13
- **Docker healthcheck** — เพิ่ม `curl` ใน production image เพราะ
  `HEALTHCHECK` เรียก `/_stcore/health`

## [v0.16.0] - 2026-05-07

### Added
- **Interactive project dashboard** — เพิ่ม `project_dashboard/`
  เป็น modern dashboard สำหรับรวบรวมเนื้อหาทั้งโปรเจกต์ โดยดึงข้อมูลจาก
  `data/` และ `reports/` มาให้เลือก filter/compare ได้ ครอบคลุม overview,
  dataset, feature reference, EDA workspace, screening controls, M-CHAT subset,
  audio workflow, segment QA preview, model results, report figures,
  progress tracking, first-vs-last comparison, clinical safety และ next steps
- **Next steps roadmap** — เพิ่ม `docs/NEXT_STEPS_TH.md` เพื่อสรุปแผนพัฒนา
  AI transcript reviewer, therapist progress report, Thai validation,
  และการใช้ project skills ทั้งหมดใน workflow ถัดไป

### Changed
- **Project dashboard parity** — ปรับหน้า dashboard ใหม่ให้ใกล้เคียง
  Streamlit เดิมมากขึ้น โดยเพิ่ม scatter, distribution, correlation heatmap,
  raw data preview, realtime-style project signal, feature documentation
  ครบ 13 ตัว และ progress trajectory
- **README.md** — เพิ่มวิธีรัน interactive project dashboard และอัปเดต
  project structure ให้รวม dashboard ใหม่กับ roadmap ใหม่
- **Project docs** — อัปเดต `docs/PROJECT_SUMMARY_TH.md` และ
  `docs/DISCUSSION_TH.md` ให้ชี้ไปยัง dashboard ใหม่และ roadmap ใหม่

### Fixed
- **Dashboard responsive layout** — แก้การ์ด metric, feature reference,
  correlation heatmap และ first-vs-last table ที่ข้อความ/ตารางล้นกรอบใน
  browser viewport แคบ

---

## [v0.15.2] - 2026-05-02

### Added
- **ASD-specific AI review skills** — เพิ่ม `asd-clinical-ml-reviewer`,
  `asd-audio-pipeline-qa`, และ `asd-advisor-report-writer` ใน `.agents/skills/`
  เพื่อช่วยตรวจ clinical ML validity, audio pipeline QA, และเอกสารสำหรับคุยอาจารย์
- **Project-scoped general workflow skills** — เพิ่ม `personal-data-analyst`,
  `personal-code-quality`, `personal-security-auditor`, `personal-researcher`,
  และ `personal-devops-deployer` เพื่อให้ agent มี workflow ที่เหมาะกับข้อมูล,
  code quality, security/privacy, research, และ deployment ของโปรเจกต์นี้

### Changed
- **README.md** — อัปเดต project structure ให้แสดง project-level skills ใหม่ทั้งหมด

---

## [v0.15.1] - 2026-05-01

### Added
- **Project-level AI workflow skill** — เพิ่ม `.agents/skills/project-update-workflow/`
  เพื่อให้ AI agents ใช้ workflow อัปเดต `README.md`, `CHANGELOG.md`, docs,
  commit message, GitHub push, และ release tag อย่างเป็นระบบ
- **Windsurf bridge rule** — เพิ่ม `.windsurf/rules/project-update-workflow.md`
  เพื่อให้ Windsurf ใช้ workflow เดียวกันได้แม้ไม่ได้อ่าน Agent Skills โดยตรง

### Changed
- **README.md** — อัปเดต project structure ให้รวม `.agents/` และ `.windsurf/` สำหรับ AI/project workflow
- **.gitignore** — อนุญาตให้ track Windsurf project rule โดยยัง ignore
  scratch files อื่นใน `.windsurf/`

---

## [v0.15.0] - 2026-04-26

### Added — Audio pipeline overhaul (production-grade)
- **TH+EN code-switching ASR** ใน `src/audio_pipeline/whisper_transcribe.py`
  - เพิ่ม `LanguageStrategy`: `auto` / `english` / `thai` / `dual_pass` / `thai_specialized`
  - Initial prompt 2 ภาษาสำหรับ child-therapy domain (toys, family, fillers)
  - Hallucination filter: drop segments ที่ `no_speech_prob>0.7`, `avg_logprob<-1.0`, repeated n-grams
  - Temperature fallback chain `[0.0, 0.2, 0.4, 0.6]` + `condition_on_previous_text=False`
  - Per-segment language tag บน `WordSegment` และ `UtteranceSegment`
  - Lazy-load `biodatlab/whisper-th-medium-combined` (Thai-fine-tuned, no HF token)
  - Default model: `base` → **`small`** (ดีกว่ามากบน child speech และ Thai)
- **Speaker diarization ที่ไม่ต้อง HF token** — `EmbeddingDiarizer`
  - ใช้ `speechbrain/spkrec-ecapa-voxceleb` (192-dim ECAPA-TDNN embeddings)
  - `sklearn.AgglomerativeClustering` (cosine, distance_threshold=0.5, max_speakers=4)
  - Age-aware F0 thresholds: 300/260/220/180 Hz ตามช่วงอายุ
  - Cluster scoring: weighted F0 + duration + (optional) enrollment cosine
  - Fallback ลง pitch heuristic เมื่อ utterance สั้นเกินจะ embed
  - Speaker enrollment: รับ reference clip 5-10 วินาที
- **silero-VAD** (`src/audio_pipeline/vad.py`) — VAD cleaner กว่า Whisper-internal
- **Re-segmentation** (`src/audio_pipeline/segmentation.py`) — `clean_segments`,
  `filter_to_speech_regions` (drop <0.2s, split ที่ silence ยาว, merge same-speaker
  ที่ห่าง <0.3s)
- **CHAT formatter ตรง TalkBank spec** — เขียนใหม่หมด (`src/audio_pipeline/chat_formatter.py`)
  - `@Languages` auto-detects single (eng/tha) vs code-switching
  - `@Participants` / `@ID` (10 pipe-separated fields) / `@Date` / `@Coder` / `@Activities` / `@Time Duration` / `@Media`
  - Word-level codes: `xxx`, `&-um`/`&-uh`/`&-เอ่อ`/`&-อืม` fillers,
    `[/]` repetition, `(.)`/`(..)`/`(...)` pauses
  - **Inline language switch markers** `[- eng]` / `[- tha]` สำหรับ code-switching
  - Sentence terminators `. ? !` preserved; auto-added when missing
  - 0-vocalization markers (`*CHI: 0 .`) สำหรับช่วงเด็กเงียบยาว (capped 3)
  - `&=vocalization` สำหรับ non-verbal long segments
- **CHATTER validator integration** (`src/audio_pipeline/chatter_validator.py`)
  - Java subprocess wrapper รอบ TalkBank's `chatter` JAR
  - Auto-fix safe issues (trailing whitespace, missing terminators) — idempotent
  - Graceful skip ถ้า Java/JAR ไม่มี (validation marked as skipped)
  - Parse output เป็น `ValidationReport(errors, warnings, fixed_count)`
- **Post-edit UI ใน dashboard** — Segments tab เปลี่ยนเป็น `st.data_editor`:
  - Editable columns: delete checkbox, speaker dropdown, lang, text, min_conf
  - **Re-export .cha** button — ใช้ edited utterances ไป regenerate + revalidate
  - Pipeline result cached ใน `st.session_state` เพื่อรอด rerun ที่ data_editor trigger

### Tests
- เพิ่ม `tests/test_audio_pipeline_v015.py` — **25 unit tests** ครอบคลุม:
  hallucination filter, dual-pass merge, age-aware F0, segmentation,
  CHAT formatter (TH+EN code-switching, fillers, repetition, pauses,
  zero-vocalization, terminators), CHATTER auto_fix idempotency

### Docs
- เพิ่ม `docs/AUDIO_PIPELINE.md` — full architecture, language strategies,
  diarizer tuning, CHATTER setup, optional pyannote upgrade with HF_TOKEN
  explainer, troubleshooting matrix

### Dependencies
- `requirements.txt`: เพิ่ม `speechbrain>=1.0.0`, `torchaudio>=2.0`
  (silero-VAD ดาวน์โหลดผ่าน `torch.hub` ตอน runtime)
- `pyannote.audio` ยังเป็น **optional** (commented) — ต้องการ HF_TOKEN

### Notes
- **ไม่ต้อง HF_TOKEN** สำหรับ pipeline หลัก — ทุก model ใช้ open weights
- รองรับ **Thai + English code-switching** ตามคำขอ
- Backward-compatible: `audio_to_cha` API เดิมยัง work — แค่มี kwargs
  ใหม่ (`strategy`, `enrollment_audio_path`, `activities`, `validate`)
  เป็น optional

---

## [v0.14.1] - 2026-04-26

### Fixed
- **Streamlit deprecation warnings** — แก้ `use_container_width=True` → `width='stretch'` ใน dashboard.py
- **Documentation consistency** — อัปเดต PROJECT_SUMMARY_TH.md และ DISCUSSION_TH.md ให้ตรงกับ features ปัจจุบัน

### Changed
- **Project overview tags** — เพิ่ม new feature tags ใน Screening Tool และ Audio Assessment pages
- **Feature count** — อัปเดตจาก 11 เป็น 13 features (รวม echolalia)

---

## [v0.14.0] - 2026-04-26

### Added
- **Multi-modal input** — เพิ่ม **M-CHAT-R parent questionnaire** (10-item
  subset) ใน Screening Tool form ทำให้ system รับ input จาก 2 modalities:
  1. **Speech features** (CHAT-derived, 13 features)
  2. **Parent report** (M-CHAT-R, 10 yes/no items)
- เพิ่มฟังก์ชัน:
  - `MCHAT_ITEMS` (10 items + concerning direction)
  - `mchat_severity()` (count concerning answers → 0-10 score)
  - `fuse_severity()` (late-fusion of two modalities)
- แสดง 3 score cards ใหม่: Speech-only · M-CHAT-R · **Combined**
- ทำงานเฉพาะเมื่อตอบ ≥5 ข้อ ไม่ตอบเลยก็ใช้ speech-only ปกติ

### Rationale
อ้างอิง **Abbas et al. (2020)** Multi-modular AI สำหรับ ASD diagnosis ที่
รวม questionnaire + video + clinician input ได้ AUC สูงกว่า single
modality, และ **Megerian et al. (2022)** FDA-cleared device ที่ใช้
3 modalities (caregiver questionnaire + home video + HCP questionnaire).

M-CHAT-R เป็น standard screening tool ที่ใช้กันทั่วโลก (Robins et al. 2009)
เหมาะที่จะเป็น modality ที่ 2 เพราะ:
- ไม่ต้องการ training data เพิ่ม (rule-based scoring)
- Parent-friendly (ไม่ต้องการ expert)
- Complementary signal (พฤติกรรมที่ไม่อยู่ใน speech transcript)

---

## [v0.13.0] - 2026-04-26

### Added
- **Graded severity scoring (0–10)** ใน Screening Tool — แสดง 3 score
  ที่ map จาก z-score ผ่าน sigmoid:
  1. **ASD severity** — sigmoid(logit) × 10 (สอดคล้องกับ P(ASD))
  2. **Communication strength** — score รวมของ positive features
     (MLU, TTR, words, utterances, questions)
  3. **ASD-marker burden** — score รวมของ negative features
     (echolalia, unintelligible, zero/non-verbal vocalization)
- เพิ่ม `compute_severity()` helper, `POSITIVE_FEATURES`, `MARKER_FEATURES`
- Score cards พร้อม traffic-light colour coding (green/amber/red)

### Rationale
อ้างอิง Eni et al. (2025) **ASDSpeech** — paper แสดงว่า speech-based AI
สามารถ quantify *ระดับความรุนแรง* ของ social communication symptoms ได้
แม่นยำกว่าการบอกแค่ binary yes/no, ตรงกับ ADOS-2 scale.

Graded score มีประโยชน์สำหรับ:
- Speech therapist: วางแผน intervention ตาม sub-scores
- Progress tracking: ดู trajectory ของ score แต่ละมิติ
- Communication: อธิบายผลให้ผู้ปกครองเข้าใจง่ายกว่า binary

---

## [v0.12.0] - 2026-04-26

### Added
- **Uncertainty band (40–60%)** ใน Screening Tool และ Audio Assessment —
  ถ้า P(ASD) อยู่ระหว่าง [0.40, 0.60) ระบบจะรายงานว่า
  *UNCERTAIN — recommend further assessment* แทน HIGH/LOW risk
- เพิ่มค่าคงที่ `UNCERTAIN_LOW`, `UNCERTAIN_HIGH` และฟังก์ชัน `classify_risk()`
  ใน `app/dashboard.py` ใช้ร่วมกันทั้ง 2 หน้า
- Gauge bands ใน Screening Tool ปรับให้สอดคล้องกับ uncertainty zone
  (เขียว → เหลือง 40-60% → แดง)

### Rationale
อ้างอิง Megerian et al. (2022) — FDA-cleared CADx device สำหรับ ASD diagnosis
มี output 3 ทาง (positive / negative / **indeterminate**) ลด over-confident
prediction เมื่อข้อมูลไม่เพียงพอ ปลอดภัยกว่าใน clinical setting

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
