---
title: ASD Screening Tool
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.57.0
app_file: app.py
python_version: 3.11
pinned: false
---

# AI-Assisted Clinical Assessment of Autism (Term Paper)

End-to-end pipeline for extracting speech-language features from raw audio
(via Whisper) or CHAT (`.cha`) transcripts and building:

1. **Screening classifier** (ASD / DD / TD) from cross-sectional corpora
   — 13-feature LogReg reaches **AUC 0.931** on binary ASD vs non-ASD
   with sensitivity/specificity/PPV/NPV, calibration, threshold, and
   uncertainty metrics exported for audit.
2. **Longitudinal progress tracker** — detects improvement patterns
   in 9/12 children across multiple therapy sessions.
3. **Audio-to-assessment pipeline** — upload `.wav` → Whisper ASR →
   diarization → CHAT transcript → features → prediction, all in the
   interactive dashboard.
4. **Per-prediction explainability (XAI)** — every screening result is
   accompanied by a SHAP-equivalent decomposition showing how each
   feature pushed the log-odds toward ASD or non-ASD, so clinicians can
   audit and trust the AI's decision.
5. **Uncertainty band (40–60%)** — predictions with P(ASD) inside the
   indeterminate zone are reported as *UNCERTAIN, recommend further
   assessment* instead of forcing a binary verdict, mirroring the
   FDA-cleared device by Megerian et al. (2022).
6. **Graded severity scoring (0–10)** — beyond the binary verdict the
   Screening Tool reports three clinically meaningful sub-scores:
   *ASD severity*, *communication strength*, and *ASD-marker burden*,
   inspired by the ASDSpeech work of Eni et al. (2025).
7. **Parent public demo** — a Thai-first, no-data-retention Streamlit flow
   for parents that summarizes concern level and next steps without making
   diagnostic claims. Audio upload is optional and gated by privacy consent.
8. **Model Trust Dashboard** — threshold playground, confusion matrix,
   calibration bins, Brier score, decision curve, uncertainty zone,
   subgroup robustness, leave-one-corpus-out stress test, and model card.
9. **Interactive Project Atlas** — a separate modern dashboard that
   explains the full project story, data inventory, corpus map, feature
   dictionary, EDA workspace, screening controls, audio/CHAT workflow,
   model trust, progress tracking, research evidence, safety, limitations,
   and presentation flow.

## Public access

Use these links when you want to show the project to parents, advisors,
or anyone who does not have the repo locally:

- **Parent / clinician public app:** <https://paoo4511-asd-screening-tool.hf.space>
- **Project Atlas + Model Trust dashboard:** <https://monai86.github.io/asd_project/>
- **Short presenter guide:** `docs/PRESENTER_GUIDE_TH.md`

Recommended demo flow:

1. Open the public app for a safe parent-friendly screening demo.
2. Open the Project Atlas dashboard to explain the full structure, data,
   metrics, and limitations.
3. Use the presenter guide as a 3-5 minute narrative when explaining the
   project to someone new.

## Data sources (TalkBank / ASDBank)

### Cross-sectional (classifier, 122 children)

| Corpus        | Groups                              | Folder |
|---------------|-------------------------------------|--------|
| Eigsti        | ASD 16 / DD 16 / TD 16              | `data/Eigsti/` |
| Nadig         | ASD 13 / TD 25 (read from `@ID`)    | `data/Nadig/` |
| NYU-Emerson   | ASD 30                              | `data/NYU-Emerson/` |
| Flusberg      | ASD 6 (session 1 only)              | `data/Flusberg/` |

### Longitudinal (progress tracker, 87 sessions / 12 children)

| Corpus        | Children | Sessions |
|---------------|---------:|---------:|
| Rollins       | 5        | 21 |
| Flusberg      | 6        | 64 |
| QuigleyMcNally (partial) | 2 | 2 |

## Setup

```bash
pip install -r requirements.txt
```

## Pipeline

Run in order:

```bash
python src/data_loader.py        # build combined_features.csv + longitudinal_features.csv
python src/eda.py                # summary stats + plots -> reports/figures/
python src/classifier.py         # sklearn models + trust metrics + model bundle
python src/deep_learning.py      # PyTorch MLP + Bi-LSTM
python src/progress_tracking.py  # longitudinal analysis (Rollins + Flusberg)
python src/evaluate_asr.py       # (optional) WER evaluation of the audio pipeline
streamlit run app/dashboard.py   # interactive dashboard
streamlit run app/dashboard_unified.py  # optional unified dashboard foundation
```

## Interactive project dashboard

For a polished and interactive overview of the full project, use the
standalone modern dashboard:

```bash
python3 -m http.server 8080 --bind 127.0.0.1
# open http://127.0.0.1:8080/project_dashboard/
```

The page lives in `project_dashboard/` and reuses the current data,
metrics, figures, and model artifacts under `data/`, `reports/`, and
`artifacts/`. It now includes a **Model Trust** section and a **Project
Atlas** section for presenting data, validation, limitations, and research
evidence in a more presentation-ready web layout.

## Audio pipeline (Whisper → CHAT)

The project includes an end-to-end module that turns raw audio into a
`.cha` transcript the rest of the pipeline can consume:

```bash
python -m src.audio_pipeline.pipeline recording.wav \
    --model base --age-months 48 --sex male --group ASD
# -> writes recording.cha next to recording.wav
```

From the dashboard, pick the **🎤 Audio assessment** page to do the same
thing interactively: upload a `.wav`/`.mp3`, pick a Whisper size, and
get features + ASD probability + a downloadable `.cha`.

The module has two diarization backends:

- **PitchHeuristicDiarizer** (default) — uses librosa's `pyin` F0
  estimate to separate child (high F0) from adult.  Zero external
  dependencies beyond the ones in `requirements.txt`.
- **PyannoteDiarizer** (optional) — uses
  `pyannote/speaker-diarization-3.1` for SOTA results.  Requires a
  HuggingFace token in `HF_TOKEN` and `pip install pyannote.audio`.

## Tests

```bash
python tests/test_audio_pipeline_smoke.py    # CHAT formatter round-trip via pylangacq
python tests/test_audio_pipeline_v015.py     # deterministic audio pipeline unit tests
python tests/test_feature_schema.py          # shared 13-feature schema alignment
python -m py_compile src/feature_schema.py src/classifier.py app/dashboard.py
```

The classifier also writes dashboard-ready validation assets:

- `reports/metrics/threshold_metrics.csv`
- `reports/metrics/calibration_bins.csv`
- `reports/metrics/decision_curve.csv`
- `reports/metrics/subgroup_performance.csv`
- `reports/metrics/leave_one_corpus_out.csv`
- `artifacts/screening_model.joblib`
- `artifacts/model_card.json`

Current deep-learning baselines on the same 13-feature schema:
TabularMLP reaches ROC-AUC `0.9320`; UtteranceLSTM reaches ROC-AUC `0.7193`.
This supports the current project interpretation that compact clinical
language features remain stronger than sequence deep learning on this small
dataset.

## Deployment

See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) for Streamlit Community Cloud,
Hugging Face Spaces, static Project Atlas, and self-host Docker instructions.

Build the public static Atlas bundle without raw CHAT transcripts or the
executable model bundle:

```bash
bash scripts/build_public_atlas.sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist/public_atlas
# open http://127.0.0.1:8080/
```

Quick local Docker run:

```bash
docker build -t asd-dashboard .
docker run -p 8501:8501 asd-dashboard   # open http://localhost:8501
```

## Project structure

```
asd-project/
├── data/                                 # raw .cha files + generated CSVs
│   ├── Eigsti/ Nadig/ NYU-Emerson/
│   ├── Flusberg/ Rollins/ QuigleyMcNally/
│   ├── combined_features.csv             # 122 rows (classification)
│   └── longitudinal_features.csv         # 87 rows (progress tracking)
├── src/
│   ├── audio_pipeline/                   # .wav -> .cha
│   │   ├── whisper_transcribe.py         #   faster-whisper wrapper
│   │   ├── diarization.py                #   pyannote + pitch heuristic
│   │   ├── chat_formatter.py             #   write valid CHAT transcripts
│   │   └── pipeline.py                   #   orchestrator (audio_to_cha)
│   ├── data_loader.py                    # CHAT -> features CSV
│   ├── feature_schema.py                  # shared 13-feature model schema
│   ├── eda.py                            # exploratory data analysis
│   ├── classifier.py                     # sklearn classifiers + trust metrics
│   ├── deep_learning.py                  # PyTorch MLP + Bi-LSTM
│   ├── progress_tracking.py              # longitudinal trends + composite
│   └── evaluate_asr.py                   # WER of Whisper vs gold .cha
├── app/
│   ├── dashboard.py                      # Streamlit dashboard + parent public demo
│   └── dashboard_unified.py              # unified dashboard foundation (all 10 routes wired)
├── project_dashboard/                    # Project Atlas + Model Trust dashboard
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── scripts/
│   └── build_public_atlas.sh              # sanitized static deploy bundle
├── tests/
│   └── test_audio_pipeline_smoke.py
├── reports/
│   ├── figures/                          # saved plots
│   └── metrics/                          # saved metrics CSVs
├── artifacts/
│   ├── screening_model.joblib             # versioned screening model bundle
│   ├── model_card.json                    # intended use + caveats
│   └── feature_schema.json                # dashboard/app schema contract
├── docs/                                 # documentation
│   ├── DEPLOYMENT.md                     # deployment guide
│   ├── DEVELOPMENT.md                    # workflow + version tracking
│   ├── PROJECT_SUMMARY_TH.md             # project summary (Thai)
│   ├── DISCUSSION_TH.md                  # discussion points for advisor
│   ├── NEXT_STEPS_TH.md                  # roadmap for next development
│   ├── REFERENCES.md                     # bibliography
│   ├── SUMMARY_TH.md                     # original Thai summary
│   ├── VERSION_UPDATE_CHECKLIST.md       # version update checklist
│   └── literature/                       # raw bibliography exports
│       └── consensus_papers_2026-04-26.csv
├── .agents/
│   └── skills/                            # project-level AI agent skills
│       ├── project-update-workflow/       # docs/version/GitHub workflow
│       ├── asd-clinical-ml-reviewer/      # clinical ML validity + safety review
│       ├── asd-audio-pipeline-qa/         # Whisper/diarization/CHAT QA
│       ├── asd-advisor-report-writer/     # Thai advisor/report workflow
│       ├── personal-data-analyst/         # CSV/EDA/metrics/report analysis
│       ├── personal-code-quality/         # code review, tests, refactors
│       ├── personal-security-auditor/     # privacy/security review
│       ├── personal-researcher/           # literature and source-backed research
│       └── personal-devops-deployer/      # Streamlit/Docker/deploy workflow
├── .windsurf/
│   └── rules/
│       └── project-update-workflow.md     # Windsurf bridge rule
├── .streamlit/
│   └── config.toml                       # theme + upload size
├── Dockerfile                            # production container
├── netlify.toml                          # static Atlas deploy config
├── packages.txt                          # Streamlit Cloud apt deps
├── CHANGELOG.md                          # version history
├── requirements.txt
└── README.md
```

## Features extracted per `.cha`

- **Demographics:** `age_months`, `sex`, `group`, `corpus`
- **Productivity:** `total_utterances`, `total_words`
- **Complexity:** `mlu` (morphemes), `mluw` (words)
- **Lexical diversity:** `ttr` (type-token ratio)
- **ASD-relevant markers:** `unintelligible_count/ratio` (`xxx`/`yyy`), `zero_vocalization_count` (`0 .`), `nonverbal_vocalization_count` (`&=gasp`, `&=laugh`, ...), `echolalia_count/ratio` (verbatim repetition of recent utterances)
- **Pragmatic:** `question_ratio`
