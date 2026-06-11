# Design Spec: Speech Assessment Audio Pipeline & Feature Extraction Upgrades

**Date:** 2026-06-12  
**Status:** Approved by User  
**Domain Scope:** Audio Processing Pipeline, CHAT Transcript, Clinical Feature Extraction (Bilingual TH+EN Support)

---

## 1. Goal & Context

This specification outlines the upgrades to the **Audio Processing Pipeline** and **Clinical Feature Extraction** components. The primary objective is to make the system highly accurate and reliable for child speech assessment in Thai, English, and Thai-English code-switching (bilingual) contexts, suitable for a web-based therapist application.

### Key Problems Solved
1. **Low ASR Accuracy on Local CPU:** Local Whisper `small` has high WER on child speech and Thai, often resulting in empty transcripts or hallucinations.
2. **Thai Word Segmentation Issues:** Thai has no spaces, causing standard CHAT formatters and `pylangacq` to treat entire Thai sentences as single words. This invalidates MLU, TTR, and Echolalia measurements.
3. **Short Utterance Diarization Bias:** Short utterances (<0.4s) fail ECAPA embedding and pitch estimation, causing them to silently default to `MOT` (Adult Speaker), which deletes valid child utterances and skews MLU.
4. **Missing Thai Clinical Features:** Clinical features like Pronoun Reversals and Restricted Interest Words are currently defined for English only, returning `0` for all Thai sessions.
5. **ASR Dual-Pass Duplications:** The English/Thai dual-pass merge logic creates duplicate utterances when segments overlap slightly.

---

## 2. Proposed Changes & Architecture

```
[Raw Audio Session File]
           │
           ▼
┌────────────────────────────────────────┐
│     [1] ASR Stage (whisper_transcribe)  │
│  - Try OpenAI Whisper API (large-v3)   │
│  - Local Fallback: faster-whisper      │
└──────────────────┬─────────────────────┘
                   │  Utterance segments + Timestamps
                   ▼
┌────────────────────────────────────────┐
│     [2] Diarization Stage (diarization)│
│  - Compute ECAPA/Pyannote for long segs│
│  - Context-Aware sliding-window for   │
│    short segments (<0.4s)              │
└──────────────────┬─────────────────────┘
                   │  Speaker-assigned segments
                   ▼
┌────────────────────────────────────────┐
│     [3] Formatting Stage (chat_format) │
│  - Run PyThaiNLP on Thai segments      │
│  - Insert space-separated words into   │
│    CHAT Tiers (.cha)                   │
└──────────────────┬─────────────────────┘
                   │  Bilingual Space-Separated CHAT (.cha)
                   ▼
┌────────────────────────────────────────┐
│   [4] Feature Extraction (data_loader) │
│  - Thai Pronoun Reversals Regex        │
│  - Thai Restricted Interests Dict      │
│  - Token-level Thai Echolalia match    │
└────────────────────────────────────────┘
```

### Component 1: Hybrid ASR Strategy (`whisper_transcribe.py`)
- Introduce a new language strategy: `api_openai` (and check for `OPENAI_API_KEY` in environment variables).
- Use the official OpenAI Python client to transcribe via the `whisper-1` model (runs on OpenAI's cloud-hosted `large-v3` architecture).
- Map OpenAI's segment-level timestamps and tokens back into the project's internal `UtteranceSegment` and `WordSegment` classes.
- Ensure the local `faster-whisper` fallback remains fully functional and explicitly logs warnings instead of silently failing.
- Refine the dual-pass merger logic to discard duplicate segments if they overlap significantly.

### Component 2: Context-Aware Diarization Heuristics (`diarization.py`)
- Improve the fallback speaker assignment for short segments (<0.4s).
- Introduce a **Contextual Speaker Continuity Filter**:
  - If a segment is too short to extract embeddings or pitch, check if it falls within the turn of a neighboring speaker (e.g., gap < 0.8s between previous and current utterance from the same speaker).
  - If it is surrounded by a single speaker on both sides, assign it to that speaker.
  - Only default to `MOT` if no local context is available.

### Component 3: Thai Word Segmentation in CHAT (`chat_formatter.py`)
- Integrate the `pythainlp` library.
- In `_render_utterance_body`, check if the segment text contains Thai characters.
- If it does, run `pythainlp.tokenize.word_tokenize(text, engine='newcut')`.
- Join the tokenized words with space characters before rendering to the speaker tier.
- Keep English and other languages space-separated as normal.

### Component 4: Thai-Specific Clinical Feature Extraction (`chat_feature_extractor.py`)
- Expand **Pronoun Reversals** to support Thai:
  - Detect first-person/second-person pronoun confusion (e.g., child referring to themselves as "เธอ/คุณ" or using "หนู/ผม" incorrectly).
- Expand **Restricted Interests** with Thai equivalents:
  - Add terms like `"รถไฟ"`, `"ล้อ"`, `"ไดโนเสาร์"`, `"ตัวเลข"`, `"แผนที่"`, `"ตาราง"`.
- Refine **Echolalia** to match on PyThaiNLP tokens rather than whitespace.

---

## 3. Security, Privacy, and Consent Compliance

- **Guardian Consent Gate:** Cloud ASR will only run if explicit guardian consent is granted (`guardian_consent = true` in the session's active case metadata), complying with `docs/PRIVACY_AND_CONSENT.md`.
- **No Model Training:** OpenAI API terms explicitly state that data sent via the API is not used for model training. Audio is retained on their servers for a maximum of 30 days only for abuse monitoring.
- **Encrypted Local Storage:** Audio is stored in private encrypted directories or bucket-equivalent storage. The API request sends the audio file dynamically from secure storage.

---

## 4. Verification & Testing Plan

### Automated Unit Tests
- Add unit tests in `tests/test_audio_pipeline_v015.py` to:
  - Verify `pythainlp` word segmentation produces clean space-separated lines.
  - Verify context-aware diarization assigns short segments correctly to the local speaker instead of defaulting to `MOT`.
  - Test Thai pronoun reversals and restricted interest word matching.
- Run tests:
  ```bash
  python tests/test_audio_pipeline_v015.py
  ```

### Manual Verification
- Upload a sample Thai-English bilingual audio session on the dashboard.
- Run the pipeline with the OpenAI API strategy and verify that the generated transcript correctly divides Thai words and contains no duplicates.
- Inspect the extracted feature values in the dashboard to confirm pronoun reversals and restricted interest words are successfully counted.
