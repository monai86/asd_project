# AI-Assisted Clinical Assessment of Autism (Term Paper)

End-to-end pipeline for extracting speech-language features from raw audio
(via Whisper) or CHAT (`.cha`) transcripts and building:

1. **Screening classifier** (ASD / DD / TD) from cross-sectional corpora
   — LogReg reaches **AUC 0.93** on binary ASD vs non-ASD.
2. **Longitudinal progress tracker** — detects improvement patterns
   in 9/12 children across multiple therapy sessions.
3. **Audio-to-assessment pipeline** — upload `.wav` → Whisper ASR →
   diarization → CHAT transcript → features → prediction, all in the
   interactive dashboard.

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
python src/classifier.py         # ASD/DD/TD classification (sklearn)
python src/deep_learning.py      # PyTorch MLP + Bi-LSTM
python src/progress_tracking.py  # longitudinal analysis (Rollins + Flusberg)
python src/evaluate_asr.py       # (optional) WER evaluation of the audio pipeline
streamlit run app/dashboard.py   # interactive dashboard
```

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
```

## Deployment

See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) for Streamlit Community Cloud,
and self-host Docker instructions.

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
│   ├── eda.py                            # exploratory data analysis
│   ├── classifier.py                     # sklearn classifiers (AUC 0.93)
│   ├── deep_learning.py                  # PyTorch MLP + Bi-LSTM
│   ├── progress_tracking.py              # longitudinal trends + composite
│   └── evaluate_asr.py                   # WER of Whisper vs gold .cha
├── app/
│   └── dashboard.py                      # Streamlit dashboard (6 pages)
├── tests/
│   └── test_audio_pipeline_smoke.py
├── reports/
│   ├── figures/                          # saved plots
│   └── metrics/                          # saved metrics CSVs
├── docs/                                 # documentation
│   ├── DEPLOYMENT.md                     # deployment guide
│   ├── DEVELOPMENT.md                    # workflow + version tracking
│   ├── PROJECT_SUMMARY_TH.md             # project summary (Thai)
│   ├── DISCUSSION_TH.md                  # discussion points for advisor
│   ├── REFERENCES.md                    # bibliography
│   ├── SUMMARY_TH.md                     # original Thai summary
│   └── VERSION_UPDATE_CHECKLIST.md       # version update checklist
├── .streamlit/
│   └── config.toml                       # theme + upload size
├── Dockerfile                            # production container
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
- **ASD-relevant markers:** `unintelligible_count/ratio` (`xxx`/`yyy`), `zero_vocalization_count` (`0 .`), `nonverbal_vocalization_count` (`&=gasp`, `&=laugh`, ...)
- **Pragmatic:** `question_ratio`
