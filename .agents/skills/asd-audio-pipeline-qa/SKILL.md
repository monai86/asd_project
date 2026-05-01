---
name: asd-audio-pipeline-qa
description: Quality-assure the asd-project audio-to-assessment pipeline from uploaded audio through Whisper transcription, diarization, CHAT formatting, pylangacq parsing, feature extraction, prediction, XAI display, and downloadable outputs. Use when changing src/audio_pipeline, src/evaluate_asr.py, app/dashboard.py audio assessment behavior, CHAT transcript generation, audio dependencies, tests, or documentation for Whisper, diarization, WER, and .cha processing.
---

# ASD Audio Pipeline QA

## Purpose

Verify that audio inputs become valid, auditable assessment inputs without silently corrupting speaker labels, CHAT format, feature counts, or prediction display.

## Files To Inspect

- `src/audio_pipeline/whisper_transcribe.py` for ASR model selection and segment structure.
- `src/audio_pipeline/diarization.py` for child/adult speaker assignment and pyannote fallback behavior.
- `src/audio_pipeline/chat_formatter.py` for CHAT syntax and metadata.
- `src/audio_pipeline/pipeline.py` for orchestration and file outputs.
- `src/evaluate_asr.py` for WER and gold transcript comparison.
- `src/data_loader.py` for `.cha` parsing and feature extraction.
- `app/dashboard.py` for upload flow, user controls, error handling, and downloadable `.cha`.
- `tests/test_audio_pipeline_smoke.py` and `tests/test_audio_pipeline_v015.py` for regression coverage.
- `docs/AUDIO_PIPELINE.md`, `README.md`, and `requirements.txt` for user-facing instructions.

## QA Workflow

1. Trace one representative input path: audio upload or CLI `.wav` -> transcription -> diarization -> CHAT -> features -> prediction -> dashboard output.
2. Check failure modes: missing audio backend, unsupported file type, empty transcript, no child speech, bad metadata, pyannote token missing, large file, and low-quality audio.
3. Validate CHAT output with `pylangacq` when possible.
4. Confirm speaker labels and metadata are explicit. Do not let uncertain diarization look authoritative.
5. Confirm feature extraction treats ASR artifacts, silence, unintelligible tokens, and nonverbal vocalizations consistently.
6. Confirm predictions from generated transcripts show appropriate caveats.
7. Update tests or recommend targeted smoke tests for changed behavior.

## Commands

Use only the checks relevant to the change:

```bash
python tests/test_audio_pipeline_smoke.py
python tests/test_audio_pipeline_v015.py
python -m src.audio_pipeline.pipeline path/to/recording.wav --model base --age-months 48 --sex male --group ASD
python src/evaluate_asr.py
```

If external model downloads or tokens are required, state that the check could not be completed locally and propose a smaller deterministic test.

## Audio-Specific Risks

- Child/adult diarization based on pitch can fail for noisy audio, atypical voices, overlapping speech, or adult female speakers.
- Whisper may normalize, omit, or hallucinate disfluencies relevant to language features.
- CHAT format errors can cause silent parsing failures or feature drift.
- ASR-derived features should not be evaluated as equivalent to gold TalkBank transcripts without WER/feature-drift checks.
- Uploaded audio and transcripts may contain sensitive health or child data.

## Output Format

Report:

- Pipeline path reviewed.
- Blocking issues.
- Non-blocking quality risks.
- Tests run or missing.
- Documentation updates needed.

Read [references/audio-checklist.md](references/audio-checklist.md) for a compact QA checklist.
