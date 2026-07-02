# Audio Pipeline

The audio pipeline is the local research entry point for the **Clinical Speech
Artifact Pipeline**. It turns a raw session recording into an ASR-generated
CHAT draft, a reviewable transcript source, a regenerated TalkBank-spec
``.cha`` export, and descriptive feature artifacts. It stops before ML
decision support.

The pipeline is designed for child-therapy recordings in **Thai, English, or
TH+EN code-switching**. ASR-generated output is always a draft until a
therapist reviews, corrects, and attests the transcript.

```
audio (.wav/.mp3/...)
     │
     ▼
[1] Whisper ASR (faster-whisper, "small" by default)
     │   - TH+EN strategies: auto / english / thai / dual_pass /
     │     thai_specialized
     │   - Hallucination filter (no_speech_prob, avg_logprob, repeated
     │     n-grams, prompt-leak)
     │   - Per-segment language tag
     ▼
[2] Diarization (speechbrain ECAPA-TDNN + sklearn AgglomerativeClustering)
     │   - 192-dim embeddings, cosine clustering
     │   - Cluster scoring: F0 (age-aware) + duration + (optional)
     │     enrollment cosine
     │   - Falls back to pitch heuristic for short utterances
     ▼
[3] Segmentation (clean_segments)
     │   - Drop <0.2s segments
     │   - Split at long internal silences
     │   - Merge same-speaker neighbours <0.3s apart
     ▼
[4] CHAT formatter (TalkBank spec)
     │   - @Languages (single or comma-separated for code-switching)
     │   - @Participants / @ID / @Date / @Coder / @Activities / @Media
     │   - Word codes: xxx, &-um/&-เอ่อ, [/], (.) (..) (...)
     │   - Inline [- eng] / [- tha] for code-switching
     │   - 0-vocalization markers, &=vocalization
     ▼
[5] CHATTER validator (Java subprocess, optional)
     │   - Auto-fix trailing whitespace + missing terminators
     │   - Reports remaining errors/warnings
     ▼
.cha file
     │
     ▼
[6] Therapist review / correction
     │   - Correct speaker / language / text / timing concerns
     │   - Attest transcript quality before report-eligible features
     ▼
Reviewed Transcript Source
     │
     ├─▶ CHAT export artifact (.cha)
     ├─▶ Linguistic Transcript Features
     └─▶ Audio/Acoustic Context Features
```

The reviewed transcript lines are the trusted speech source. Generated CHAT
files are export artifacts derived from those lines, not a separate source of
truth. Feature extraction from an unattested ASR draft is allowed only for
engineering/debug workflows with explicit labeling.

## Quickstart

### Python API

```python
from src.audio_pipeline import audio_to_cha

result = audio_to_cha(
    "session.wav",
    output_path="session.cha",
    model_size="small",            # "tiny" / "base" / "small" / "medium"
    strategy="auto",               # see below
    child_age_months=48,           # drives the F0 threshold
    enrollment_audio_path=None,    # optional: short clip of the child
    child_id="CHI001",
    child_group="ASD",
)

print(result.chat_text)
print(result.validation.summary())
```

### CLI

```bash
python -m src.audio_pipeline.pipeline session.wav \
    --model small --strategy auto --age-months 48
```

### Clinical Speech Artifact Package

Build an offline package from a reviewed `.cha` file:

```bash
python3 scripts/build_clinical_speech_artifact_package.py \
  --session-id demo-session \
  --reviewed-cha tests/fixtures/reference_feature_parity/english_toyplay.cha \
  --output-root artifacts/clinical_speech
```

With linked audio context:

```bash
python3 scripts/build_clinical_speech_artifact_package.py \
  --session-id demo-session \
  --reviewed-cha reviewed.cha \
  --audio session.wav \
  --output-root artifacts/clinical_speech
```

With an ASR draft retained for provenance:

```bash
python3 scripts/build_clinical_speech_artifact_package.py \
  --session-id demo-session \
  --asr-draft-cha asr_draft.cha \
  --reviewed-cha reviewed.cha \
  --audio session.wav \
  --output-root artifacts/clinical_speech
```

When `--asr-draft-cha` is provided, the package also writes
`quality_report.json`. That report compares the ASR draft with the reviewed
transcript using engineering QA metrics: WER, CER, position-aligned speaker
label accuracy, utterance-count delta, line edit rate, line-level edit summary,
and canonical feature drift. These metrics measure review burden and pipeline
quality only; the reviewed transcript remains the source of truth.

For a 10-30 session benchmark set, run the benchmark reporter against ASR draft
and reviewed transcript pairs:

```bash
python3 scripts/benchmark_clinical_speech_artifacts.py \
  --case demo-session:asr_draft.cha:reviewed.cha \
  --output-dir artifacts/clinical_speech_benchmark/demo-run
```

The benchmark output includes `benchmark_summary.json` and
`benchmark_cases.csv` with mean WER, CER, speaker-label accuracy, line edit
rate, and feature drift across all cases.

For repeatable benchmark sets, use `--cases-json`:

```json
{
  "cases": [
    {
      "session_id": "demo-session",
      "language": "eng",
      "cohort": "pilot-smoke",
      "asr_draft_cha": "asr_draft.cha",
      "reviewed_cha": "reviewed.cha"
    }
  ]
}
```

The package is an offline artifact contract. It does not invoke ML decision
support and does not produce diagnosis, ASD probability, or clinical validation
claims.

## Therapist App Backend API Boundary

The browser-based `apps/lingualens-app` does not run Whisper,
diarization, CHATTER validation, or Python `audio_pipeline` code directly.
Real audio-to-CHAT processing requires a backend service boundary that accepts
an uploaded audio/video record, runs the Python pipeline server-side, and
returns review-gated artifacts to the frontend.

Suggested routes for a future backend:

| Route | Purpose |
|---|---|
| `POST /api/sessions/:sessionId/process-audio` | Submit an audio processing job for a session and audio file metadata record. |
| `GET /api/jobs/:jobId` | Poll processing status and error details. |
| `GET /api/sessions/:sessionId/transcript` | Return generated CHAT transcript text and speaker-labeled lines. |
| `PATCH /api/transcripts/:transcriptId/lines/:lineId` | Save one therapist transcript-line correction with version conflict protection. |
| `GET /api/sessions/:sessionId/features` | Return extracted Core 14-feature schema values plus optional interaction/acoustic indicators. |
| `GET /api/sessions/:sessionId/qa` | Return transcript QA status, score, and issues. |

Processing jobs should expose both a coarse `status` and a more specific
`stage`. The coarse status is one of `queued`, `processing`, `completed`, or
`failed`. The stage should use this progression when available:
`queued`, `transcribing`, `diarizing`, `chat_formatting`, `qa_running`,
`features_running`, `awaiting_review`, `completed`, or `failed`.

When a backend only reports `status=processing`, the frontend treats the stage
as `transcribing` until a more specific stage arrives. `completed` audio jobs
map the session to `transcript_ready`/`awaiting_review`, not to final clinical
completion.

Expected frontend mapping:

- CHAT transcript text becomes the session transcript record.
- Utterances become transcript lines with speaker labels, confidence, and optional timing markers.
- QA output becomes transcript QA status and issue details.
- Linguistic transcript features become preliminary feature output only after review gates.
- Audio/acoustic context features may be displayed as quality and context indicators.
- AI-assisted screening support output, if provided, must remain gated behind transcript review.

ASR-generated transcripts are not final clinical records. The frontend marks
backend-generated transcripts as awaiting therapist review, feature outputs as
preliminary, and AI-assisted explanation as requiring transcript review until a
qualified therapist or clinician approves the transcript.

The therapist app also supports manual `.cha` upload in the session detail and
transcript QA views. Uploaded CHAT metadata lines, speaker tiers, source line
numbers, and optional timing markers are preserved for review. If a therapist
edits a transcript line, existing feature output is marked stale and the user
must explicitly re-run feature extraction before using the refreshed feature
summary. ML or AI-assisted review support is a later consumer, not part of the
artifact pipeline itself.

## Language strategies

| Strategy | Speed | Best for |
|---|---|---|
| `auto` (default) | Fast (1×) | Single language; Whisper detects per-segment |
| `english` | Fast (1×) | Force English (clean monolingual recordings) |
| `thai` | Fast (1×) | Force Thai |
| `dual_pass` | Slow (2×) | TH+EN code-switching — runs both passes and picks per-segment winner by ``avg_logprob`` |
| `thai_specialized` | Medium | Thai-heavy recordings — uses ``biodatlab/whisper-th-medium-combined`` |

## Speaker enrollment

The dashboard's *Speaker enrollment* expander accepts a 5–10 s clip of
the child speaking.  We compute one ECAPA embedding from it and use
cosine similarity to the cluster centroids to **break ties** when
choosing which cluster is CHI.  This is especially helpful when the
child's pitch overlaps with an adult female's range.

## Tuning the diarizer

`EmbeddingDiarizerConfig` exposes:

| Field | Default | Effect |
|---|---|---|
| `distance_threshold` | 0.5 | Lower → more clusters |
| `max_speakers` | 4 | Hard cap |
| `min_embed_duration` | 0.4 s | Below this, fall back to F0 heuristic |
| `weight_f0` | 1.0 | Importance of pitch in CHI selection |
| `weight_duration` | 0.3 | Importance of "kids speak in shorter bursts" |
| `weight_enrollment` | 2.0 | Strength of the enrollment-cosine signal |

Age-aware F0 thresholds (Hz):

| Age | Threshold |
|---|---|
| 0–3 yr | 300 |
| 4–6 yr | 260 |
| 7–12 yr | 220 |
| >12 yr | 180 |
| Unknown | 230 |

Check local diarization readiness without an audio file:

```bash
python3 scripts/check_diarization_runtime.py \
  --age-months 48 \
  --max-speakers 3
```

The command reports the selected backend (`speechbrain_embedding`,
`pitch_heuristic`, `pyannote`, or `unavailable`), missing dependency fallback
reason, age-aware F0 threshold, and tunable config. Use this before running a
real audio job so speaker-label quality issues can be separated from transcript
review and benchmark issues.

## CHATTER validator setup

CHATTER (https://talkbank.org/software/chatter.html) is the official
TalkBank tool for checking ``.cha`` files.  Without it, the pipeline
still produces output but ``validation.skipped == True``.

1. Install Java 8+:
   - macOS: ``brew install --cask temurin``
   - Ubuntu: ``apt install default-jre-headless``
2. Download CHATTER's JAR.
3. Either:
   - Set ``CHATTER_JAR=/path/to/chatter.jar``, or
   - Drop ``chatter.jar`` next to ``src/audio_pipeline/``, or
   - Place at ``~/.local/share/chatter/chatter.jar``

## Optional upgrade: pyannote 3.1 (needs HF token)

`pyannote/speaker-diarization-3.1` is sometimes more accurate than the
ECAPA + clustering default, but it is **gated** on HuggingFace.

### What is HF_TOKEN?

A free HuggingFace API key.  HuggingFace is a model-hosting platform
(like GitHub for ML models).  Some models are "gated" — the maintainers
want to track who downloads them, so you must:

1. Create a free account at https://huggingface.co/join
2. Generate a read-only token at https://huggingface.co/settings/tokens
3. Accept the model terms at
   https://huggingface.co/pyannote/speaker-diarization-3.1
4. Set ``HF_TOKEN=hf_...`` in your shell or ``.env``
5. ``pip install pyannote.audio>=3.1.0``
6. Pass ``prefer_pyannote=True`` to ``audio_to_cha(...)``

The pipeline will use pyannote when available and fall back to the
default ECAPA diarizer otherwise.

## Tests

```bash
python tests/test_audio_pipeline_smoke.py    # legacy smoke test
python tests/test_audio_pipeline.py
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All utterances labelled MOT | Child pitch < threshold | Increase ``child_age_months``, or upload an enrollment clip |
| ``CHATTER skipped`` on dashboard | Java or chatter.jar missing | See [CHATTER validator setup](#chatter-validator-setup) |
| Many ``xxx`` in transcript | Whisper confidence low | Use ``model_size="medium"``, or strategy ``dual_pass`` |
| Thai words come out garbled | Whisper "tiny"/"base" too weak | Use at least ``"small"`` for Thai, or ``thai_specialized`` |
| Pipeline very slow | CPU + medium model + dual_pass | Drop to ``small`` and ``auto`` |
