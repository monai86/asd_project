# AI-Assisted Speech-Language ASD Screening Support (Term Paper)

Research prototype for extracting speech-language features from CHAT (`.cha`) transcripts and audio recordings to support ASD clinical assessment. Developed as a term paper project — **not a diagnostic tool**.

## ⚠️ Clinical Safety Boundary

This project is a **research prototype and educational demo**. It supports screening support, risk estimates, and progress tracking only. It does not diagnose ASD and does not replace clinician judgment. The model was trained on English-speaking public corpora and is **not validated for Thai children**.

---

## Web Applications (3 surfaces)

### 1. 🏠 Public Screening Support App (`public-screening/`)

Bilingual (Thai/English) parent-facing educational screening tool. Zero data retention — all state lives in `sessionStorage` only.

```bash
cd public-screening
npm install
npm run dev
```

**Pages:** Landing → Screening questionnaire (14 Likert questions) → Results gauge → Education FAQs  
**Deploy:** Cloudflare Pages — root: `public-screening/`, build: `npm run build`, output: `dist`

---

### 2. 🩺 Therapist / Clinician App (`therapist-clinician-app/`) [v1.0.0]

Modular human-in-the-loop workflow for speech therapists and clinicians. Includes utterance segmentation, timestamp alignment, 18+ linguistic features extraction, and printable reports. Runs in `MOCK_MODE=True` — no real data stored.


```bash
cd therapist-clinician-app
npm install
npm run dev
```

| Role | Email | Password |
|------|-------|----------|
| Therapist | `therapist@example.test` | `demo-password` |
| Clinician | `clinician@example.test` | `demo-password` |
| Admin | `admin@example.test` | `demo-password` |

**Features:** Case management · Session timelines · Transcript QA · AI decision support · Progress tracking · Markdown reports · Admin audit log  
**Deploy:** Cloudflare Pages — root: `therapist-clinician-app/`, build: `npm run build`, output: `dist`

---

### 3. 📊 Presentation Dashboard (`presentation-dashboard/`)

Data visualization dashboard for advisor presentations and project demos.

```bash
cd presentation-dashboard
npm install
npm run dev
```

**Features:** Model performance · Dataset explorer · Feature importance · LOCO cross-validation · Cohort explorer  
**Deploy:** Cloudflare Pages — root: `presentation-dashboard/`, build: `npm run build`, output: `dist`

---

## Python ML Backend (`src/`)

Research and reference code for the term paper. Not deployed — runs locally for model training, evaluation, and generating artifacts.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Pipeline (run in order)

```bash
python src/data_loader.py                   # build combined_features.csv + longitudinal_features.csv
python src/eda.py                           # summary stats + plots → reports/figures/
python src/classifier.py                    # sklearn models + trust metrics + model bundle
python scripts/compute_fairness_metrics.py  # fairness + calibration audit CSVs
python src/deep_learning.py                 # PyTorch MLP + Bi-LSTM baselines
python src/progress_tracking.py            # longitudinal analysis (Rollins + Flusberg)
```

### Key ML Results

| Model | Metric | Value |
|-------|--------|-------|
| LogReg (binary) | ROC-AUC | **0.9352** |
| LogReg (binary) | Sensitivity | 0.8462 |
| LogReg (binary) | Specificity | 0.9123 |
| TabularMLP | ROC-AUC | 0.9320 |
| UtteranceLSTM | ROC-AUC | 0.7193 |

---

## Data Sources (TalkBank / ASDBank)

### Cross-sectional (122 children)

| Corpus | Groups | Folder |
|--------|--------|--------|
| Eigsti | ASD 16 / DD 16 / TD 16 | `data/Eigsti/` |
| Nadig | ASD 13 / TD 25 | `data/Nadig/` |
| NYU-Emerson | ASD 30 | `data/NYU-Emerson/` |
| Flusberg | ASD 6 (session 1) | `data/Flusberg/` |

### Longitudinal (87 sessions, 12 children)

| Corpus | Children | Sessions |
|--------|----------|----------|
| Rollins | 5 | 21 |
| Flusberg | 6 | 64 |
| QuigleyMcNally | 2 | 2 |

---

## Features Extracted per `.cha` (14 features)

- **Productivity:** `total_utterances`, `total_words`
- **Complexity:** `mlu` (morphemes), `mluw` (words)
- **Lexical diversity:** `ttr` (type-token ratio)
- **ASD markers:** `unintelligible_count/ratio` (`xxx`/`yyy`), `zero_vocalization_count` (`0 .`), `nonverbal_vocalization_count`, `echolalia_count/ratio`, `pronoun_reversal_count`
- **Pragmatic:** `question_ratio`

---

## Audio Pipeline

End-to-end `.wav` → `.cha` pipeline using Whisper ASR + speaker diarization.

```bash
python -m src.audio_pipeline.pipeline recording.wav \
    --model small --age-months 48 --sex male --group ASD
# → writes recording.cha next to recording.wav
```

**Diarization backends:**
- `EmbeddingDiarizer` (default) — ECAPA-TDNN embeddings, no HF token needed
- `PyannoteDiarizer` (optional) — SOTA, requires `HF_TOKEN`

---

## Research Support Scripts

```bash
python scripts/paper_scout.py --tag speech --tag audio --save   # ASD/AI paper discovery
python scripts/build_zotero_import.py                           # Zotero RIS export
python scripts/compute_fairness_metrics.py                      # fairness + calibration CSVs
```

See `docs/literature/PAPER_SCOUT.md` for full workflow. Reports saved to `docs/literature/scout_reports/`.

---

## Tests

```bash
pytest tests/ -q                                 # run all tests
pytest tests/test_feature_schema.py -q          # 14-feature schema alignment
pytest tests/test_fairness_metrics.py -q        # fairness metrics
pytest tests/test_transcript_reviewer.py -q     # CHAT transcript QA
pytest tests/test_clinical_workflow.py -q       # therapist app mock backend
```

---

## Project Structure

```
asd-project/
├── public-screening/              # 🌐 Web app 1: Public screening support
├── therapist-clinician-app/       # 🩺 Web app 2: Therapist/clinician prototype
├── presentation-dashboard/        # 📊 Web app 3: Advisor presentation dashboard
├── src/
│   ├── audio_pipeline/            # .wav → .cha (Whisper + diarization + CHAT)
│   ├── clinical_workflow/         # Mock therapist prototype models & repository
│   ├── data_loader.py             # CHAT → features CSV
│   ├── feature_schema.py          # Shared 14-feature schema
│   ├── classifier.py              # sklearn classifiers + trust metrics
│   ├── fairness_metrics.py        # ECE, Brier, group fairness
│   ├── deep_learning.py           # PyTorch MLP + Bi-LSTM
│   ├── progress_tracking.py       # Longitudinal trends + composite score
│   ├── transcript_reviewer.py     # Rule-based CHAT QA
│   ├── therapist_report.py        # Progress report generator
│   ├── speech_therapist_assistant.py  # Therapist interpretation layer
│   └── evaluate_asr.py            # WER evaluation
├── scripts/
│   ├── compute_fairness_metrics.py
│   ├── paper_scout.py
│   └── build_zotero_import.py
├── tests/                         # pytest test suite
├── data/                          # Raw .cha corpora + generated CSVs
├── artifacts/                     # screening_model.joblib, model_card.json, feature_schema.json
├── reports/
│   ├── figures/                   # Saved plots
│   ├── metrics/                   # Evaluation CSVs
│   └── progress_reports/          # Sample therapist reports
├── docs/                          # Documentation
│   ├── DEPLOYMENT.md              # Cloudflare Pages deploy guide
│   ├── PROJECT_SUMMARY_TH.md     # Thai project summary
│   ├── DISCUSSION_TH.md           # Advisor discussion points
│   ├── REFERENCES.md              # Bibliography (37+ papers)
│   ├── THAI_VALIDATION_READINESS_TH.md
│   ├── PRESENTER_GUIDE_TH.md
│   └── literature/                # Paper scout outputs, Zotero imports
├── .agents/skills/                # Project-level AI agent skills
├── CHANGELOG.md
├── CONTEXT.md                     # Canonical glossary
└── requirements.txt
```

---

## Deployment

See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) for full Cloudflare Pages setup for all 3 web apps and Python ML backend local usage.

---

## Key Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/PROJECT_SUMMARY_TH.md`](./docs/PROJECT_SUMMARY_TH.md) | สรุปโปรเจกต์ภาษาไทย |
| [`docs/DISCUSSION_TH.md`](./docs/DISCUSSION_TH.md) | ประเด็นคุยกับอาจารย์ |
| [`docs/REFERENCES.md`](./docs/REFERENCES.md) | Bibliography 37+ papers |
| [`docs/THAI_VALIDATION_READINESS_TH.md`](./docs/THAI_VALIDATION_READINESS_TH.md) | Thai validation readiness |
| [`docs/PRESENTER_GUIDE_TH.md`](./docs/PRESENTER_GUIDE_TH.md) | คู่มือนำเสนอ 3-5 นาที |
| [`CONTEXT.md`](./CONTEXT.md) | Shared glossary |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history |
