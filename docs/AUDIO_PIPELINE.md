# Audio Pipeline (v0.15.0)

End-to-end pipeline that turns a raw session recording into a
TalkBank-spec ``.cha`` transcript with speaker labels and language tags.
Designed for child-therapy recordings in **Thai, English, or
TH+EN code-switching**, and runs entirely on **open-weight models** so
no HuggingFace token is required.

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
[6] Post-edit UI (dashboard)
     │   - Editable table: speaker / lang / text / delete per row
     │   - Re-export .cha + re-validate
     ▼
final .cha → data_loader → human review gate → screening risk estimate
```

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

### Dashboard

```bash
streamlit run app/dashboard.py
```
Navigate to **🎤 Audio Assessment**, upload a session, pick a Whisper
model + Language strategy, and click **Run pipeline**.  After it
finishes, switch to the **Segments** tab to post-edit and re-export.

## Therapist App Backend API Boundary

The browser-based `therapist-clinician-app` does not run Whisper,
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
- Core 14-feature schema values become preliminary feature output.
- Optional interaction/acoustic indicators may be included alongside the core schema.
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
summary or AI-assisted explanation.

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
python tests/test_audio_pipeline_v015.py     # v0.15.0 unit tests (25 tests)
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All utterances labelled MOT | Child pitch < threshold | Increase ``child_age_months``, or upload an enrollment clip |
| ``CHATTER skipped`` on dashboard | Java or chatter.jar missing | See [CHATTER validator setup](#chatter-validator-setup) |
| Many ``xxx`` in transcript | Whisper confidence low | Use ``model_size="medium"``, or strategy ``dual_pass`` |
| Thai words come out garbled | Whisper "tiny"/"base" too weak | Use at least ``"small"`` for Thai, or ``thai_specialized`` |
| Pipeline very slow | CPU + medium model + dual_pass | Drop to ``small`` and ``auto`` |
