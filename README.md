# AI-Assisted Speech-Language ASD Screening Support (Term Paper)

Research prototype for extracting speech-language features from CHAT (`.cha`) transcripts and audio recordings to support ASD clinical assessment. Developed as a term paper project — **not a diagnostic tool**.

## Project Version Mapping
- **Project version:** `v1.6.1`
- **Therapist product version:** `v1.6.1`
- **Public screening app version:** `v1.6.1`
- **Presentation dashboard version:** `v1.6.1`

> Start with [`docs/PROJECT_SOURCE_OF_TRUTH.md`](./docs/PROJECT_SOURCE_OF_TRUTH.md).
> It defines which paths are active, legacy, generated, or research-only.

## ⚠️ Clinical Safety Boundary & Prototype Status

This project is a **research prototype and educational demo**. It supports screening support, concern level estimation, and progress tracking only. It does not diagnose ASD and does not replace clinician judgment. The model was trained on English-speaking public corpora and is **not validated for Thai children**.

### Prototype Status & Limitations
- **Persistent Therapist Workflow**: Therapist App v2 persists case, session,
  transcript, QA, attestation, feature, and report records through `apps/api`.
  Local API development defaults to durable JSON storage; browser session
  storage is only a lightweight UI/navigation cache and never stores audio
  bytes.
- **Repository Modes**: `json` is the default usable-prototype mode and
  survives API restarts. `memory` is for isolated tests or intentional demo
  resets. `sql` is PostgreSQL-ready but is not pilot-hardened yet.
- **Offline Boundary**: When the API is unreachable, the therapist app shows
  local workspace mode. Safe demo input remains available, but backend-required
  saves, QA, attestation, feature extraction, and finalization cannot report
  success.
- **Secure Upload Gate**: Demo mode remains metadata-only. Clinical pilot mode supports secure backend upload intent records only after guardian consent is granted; private audio/video storage must use signed URLs, encryption, retention, and audit logs.
- **Backend Boundaries**: `apps/api/` is the canonical Therapist App v2 API.
  The experimental audio-to-CHAT implementation remains in
  `src/audio_pipeline/`. `src/therapist_backend/` is retained only as a legacy
  research compatibility API.
- **Human Review Gate**: Generated transcripts require clinician review before preliminary feature outputs or AI-assisted explanation are interpreted.
- **Decision-Support AI Output**: All AI output is strictly designed for screening support (e.g., concern level, review priority, clinician review support) and must never be interpreted as an automated clinical conclusion.
- **Feature-Based ML Review**: Therapist App v2 can persist transparent review
  cues only after transcript attestation and feature extraction. The default
  provider is rule-based, outputs are not diagnostic, browser ML fallback is
  disabled, and cues are not inserted into reports automatically. See
  `docs/ML_DECISION_SUPPORT_MODEL_CARD.md`.
- **Gate 1 Status**: The latest reference-evidence artifact passes the
  preregistered engineering gate and is marked `promoted_candidate`. This does
  not activate diagnosis or establish clinical/Thai validation.

### Clinical Validation Limitations
- The project is not clinically validated and must not be used as a standalone clinical tool.
- The current model and demo workflow have not been validated for Thai children.
- ASR-generated transcripts may be inaccurate for children's speech, noisy audio, overlapping speech, or multilingual speech.
- Public datasets and mock records may not represent all populations, languages, care settings, or communication profiles.
- Model and rule-based outputs require human review by qualified professionals before interpretation.

---


## Web Applications

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

### 2. 🩺 Therapist App (`apps/therapist-app-v2/` + `apps/api/`)

The only active therapist frontend is the Next.js/React/TypeScript app. The
stable path is manual-first: create/open case, create session, upload reviewed
CHA, run QA, attest transcript, extract features, generate AI-assisted
decision-support review, edit/sign off a report, and export only after
therapist sign-off.

The simplified therapist path uses clean user-facing routes:
Home → `/record` → `/results` → `/review-transcript` → `/report-summary`.
`/transcript` remains a backward-compatible alias for transcript review.
Audio, CHA, and pasted-transcript quick starts enter through `/record` query
modes while workflow state remains local/mock.

```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

cd ../../apps/therapist-app-v2
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

See `docs/PROFESSOR_DEMO_SCRIPT.md` and
`docs/MVP_VS_EXPERIMENTAL_SCOPE.md` for the walkthrough, scope boundary, and
feature-to-endpoint verification table.

The former `therapist-clinician-app/` Vite/Capacitor surface is retired and is
not repository source. Generated folders from previous local builds may be
deleted.

---

### 3. 📊 Presentation Dashboard (`presentation-dashboard/`)

Data visualization dashboard for advisor presentations and project demos.

```bash
cd presentation-dashboard
npm install
npm run dev
```

**Features:** Model performance · Dataset explorer · Feature importance · LOCO cross-validation · Cohort explorer · Thai ASR Drift Simulation  
**Deploy:** Cloudflare Pages — root: `presentation-dashboard/`, build: `npm run build`, output: `dist`

---

## Python ML and Audio Research Layer (`packages/` + `src/`)

Research and reference code for model training, evaluation, audio processing,
and artifact generation. New product API routes belong in `apps/api`, not
`src/therapist_backend`.

### CLAN-Derived Metrics

The TalkBank/CHILDES reference pipeline can run CLAN batch jobs and parse
completed KIDEVAL output into `data/reference/english_child_clan_features.csv`.
These rows are kept separate from the Python-derived reference features and are
descriptive research artifacts only. The Reference Comparison API can expose
matched CLAN-Derived Metrics in a separate `clan_metric_comparisons` section;
the therapist Transcript tab displays that section separately when backend
Reference Comparison is configured and matched CLAN metrics are available.
The therapist API also exposes `GET /api/sessions/{session_id}/qa` so the
Transcript tab can use backend CHAT/CLAN readiness checks before unlocking
Reference Comparison; mock mode remains a lightweight local QA preview and does
not pretend to validate CLAN readiness.

The reference pipeline also writes
`data/reference/english_child_reference_coverage.csv` and
`docs/REFERENCE_COHORT_COVERAGE.md` to summarize which age/task/group cells are
ready for cautious descriptive comparison and which cells remain low-count. The
current reference snapshot includes 1,961 Python-derived feature rows and 1,961
matched CLAN-Derived Metric rows across the Phase 1 and Phase 2 transcript
intake corpora. Reference feature rows include `age_months_source` and
`age_months_source_detail` so CHAT header ages and official-path fallbacks for
NewEngland/Rescorla remain auditable.

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

These are legacy benchmark results on 122 public-corpus records. The current
reference-evidence Gate 1 pipeline is separate and participant-grouped.

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

### Build reference-evidence artifacts

Reference evidence is English-only, descriptive, and opt-in. It does not
produce probabilities, predicted classes, rankings, or diagnosis.

```bash
export ML_REFERENCE_PSEUDONYMIZATION_KEY='replace-with-32-or-more-secret-bytes'
python scripts/build_ml_reference_evidence.py \
  --combined data/combined_features.csv \
  --curated data/curated_group_features.csv \
  --output-dir artifacts/reference_evidence/candidate-v1 \
  --artifact-version candidate-v1 \
  --feature-parity-passed
```

Artifact promotion is manual and approval-recorded. See
[`docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md`](./docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md).

---

## Tests

```bash
PYTHONPATH=apps/api:src pytest -m "not audio" -q # core + active API tests
pytest tests/test_feature_schema.py -q          # 14-feature schema alignment
pytest tests/test_fairness_metrics.py -q        # fairness metrics
pytest tests/test_transcript_reviewer.py -q     # CHAT transcript QA
pytest tests/test_clinical_workflow.py -q       # therapist app mock backend
pytest tests/test_clinical_pilot_backend_contract.py -q
```

Full maintained-project verification:

```bash
bash scripts/check_project.sh
```

---

## Project Structure

```
asd-project/
├── public-screening/              # 🌐 Web app 1: Public screening support
├── apps/
│   ├── therapist-app-v2/          # 🩺 Active Next.js therapist frontend
│   └── api/                       # Therapist workflow FastAPI
├── presentation-dashboard/        # 📊 Web app 3: Advisor presentation dashboard
├── src/
│   ├── audio_pipeline/            # .wav → .cha (Whisper + diarization + CHAT)
│   ├── clinical_workflow/         # Legacy/research workflow compatibility
│   ├── therapist_backend/         # Legacy research API compatibility
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
│   ├── simulate_thai_drift.py      # Synthetic Thai ASR drift simulation
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
├── PROJECT_STATUS.md              # Current maintained status
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
| [`docs/THAI_VALIDATION_READINESS_TH.md`](./docs/THAI_VALIDATION_READINESS_TH.md) | Thai validation readiness and Thai ASR Drift Simulation boundary |
| [`docs/PRESENTER_GUIDE_TH.md`](./docs/PRESENTER_GUIDE_TH.md) | คู่มือนำเสนอ 3-5 นาที |
| [`CONTEXT.md`](./CONTEXT.md) | Shared glossary |
| [`docs/PROJECT_SOURCE_OF_TRUTH.md`](./docs/PROJECT_SOURCE_OF_TRUTH.md) | Active/legacy/generated architecture map |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history |
| [`docs/ML_DECISION_SUPPORT_MODEL_CARD.md`](./docs/ML_DECISION_SUPPORT_MODEL_CARD.md) | ML and reference-evidence scope, gates, and limitations |
| [`docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md`](./docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md) | Artifact approval, promotion, rollback, and incident runbook |
