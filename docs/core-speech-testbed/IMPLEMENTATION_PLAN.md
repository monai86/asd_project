# LinguaLens v1.7.0 Core Speech-to-CHAT Testbed Implementation Plan

Status: approved implementation plan; execution begins from the audited WIP baseline.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a verified local/testbed vertical slice that turns a non-identifying synthetic audio upload into a real `local_faster_whisper` draft, therapist-reviewed and attested transcript, deterministic `.cha` artifact, deterministic descriptive features, and Findings with complete provenance and limitations.

**Architecture:** Keep `apps/lingualens-app/` and `apps/api/` as the only product surfaces. The API stores the original asset unchanged, creates a versioned normalized working asset, invokes ASR through the existing provider boundary, and preserves raw provider output beneath therapist-reviewed mapping and transcript layers. Every downstream artifact is version-bound and fail-closed: QA, CHAT round-trip, features, and Findings reject stale or structurally invalid inputs rather than using mock or manual fallbacks.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/Alembic, private/local storage adapters, Python media decoding/normalization with a pinned decoder, faster-whisper/CTranslate2, PyThaiNLP or the evidence-selected pinned tokenizer, Next.js/React/TypeScript, pytest, Vitest/Testing Library.

---

## Outcome and milestone boundary

The required v1.7.0 path is:

```mermaid
flowchart LR
    A["Synthetic audio file upload"] --> B["Server decode, validate, normalize"]
    B --> C["local_faster_whisper draft"]
    C --> D["Therapist transcript correction"]
    D --> E["Therapist-confirmed speaker mapping"]
    E --> F["QA and limitation review"]
    F --> G["Version-bound attestation"]
    G --> H["Canonical CHAT export"]
    H --> I["Semantic and deterministic round-trip"]
    I --> J["Deterministic descriptive features"]
    J --> K["Findings with provenance and limitations"]
```

Milestone defaults:

- maximum decoded duration: `900` seconds per file;
- maximum source size: `100 * 1024 * 1024` bytes;
- normal ASR provider: `local_faster_whisper`;
- no automatic mock, manual, sample, browser, local-to-cloud, or cross-provider fallback;
- browser recording remains preserved but marked experimental/unavailable and is not a completion gate;
- automatic diarization remains optional and experimental;
- ML, reference comparisons, norms, diagnostic classification, production rollout, and longer-recording support are outside this milestone.

Supported formats at the first green gate are WAV and MP3 because the current environment has verified `libsndfile` support for them. M4A and WebM may be enabled only after the same pinned decoder used by the server passes format fixtures and records its version; the UI must render them as unavailable until then.

## Current-state evidence and gaps

| Area | Current evidence | Required change |
|---|---|---|
| Upload | `AudioUploadRequest` accepts client duration and defaults to 250 MB | Decode server-side, enforce 100 MB/900 seconds, persist source and normalized lineage |
| Storage | Original object is stored; no normalized asset record exists | Preserve original and add immutable normalized working asset plus checksums/tool provenance |
| ASR | Registry prefers mock; local Whisper provider is a stub | Add real `local_faster_whisper`, make it the normal upload provider, fail explicitly |
| Jobs | `allow_fallback_to_mock` exists and frontend requests `"mock"` | Remove fallback from normal requests; add typed retry/idempotency/completeness outcomes |
| Draft | Non-`CHI` lines are rewritten to `UNK` | Preserve provider label and use neutral temporary identifiers only |
| Speaker mapping | No versioned reviewed mapping layer | Add immutable mapping confirmation tied to transcript version |
| QA | Generic `override_qa_failure` can attest failed QA | Replace with typed blockers and version-bound limitation acknowledgments |
| CHAT | Basic parser/export exists; no semantic round-trip gate | Pin subset/parser/serializer and add structured loss detection plus deterministic checksum |
| Features | `BasicFeatureProvider` uses `[\w']+` and `tokenizer_version=None` | Add Thai-aware pinned tokenizer and explicit feature statuses/formulas/provenance |
| Findings | Descriptive cards exist but defaults and provenance are incomplete | Render only backend values/statuses, sample size, formulas, provenance, limitations |
| Tests | Narrow backend paths pass; no real golden audio E2E | Add generated versioned fixtures, provider integration tests, benchmarks, and full vertical slice |

## Files and responsibilities

Create focused modules rather than adding more responsibilities to the already large service files:

- `apps/api/app/schemas/speech_pipeline.py` — typed, versioned audio, ASR, mapping, QA, CHAT, feature, and provenance contracts.
- `apps/api/app/services/audio_media_service.py` — source probing, decoder capability checks, checksums, normalization, and beginning/end preservation.
- `apps/api/app/services/asr_providers/local_faster_whisper_provider.py` — provider adapter only; no route or workflow policy.
- `apps/api/app/services/asr_completeness_service.py` — empty/partial/gap/timestamp integrity checks.
- `apps/api/app/services/speaker_mapping_service.py` — reviewed mapping, merge/split dispositions, confirmation, and staleness.
- `apps/api/app/services/qa_policy_service.py` — versioned blocker/limitation classification, escalation, acknowledgment, and attestation eligibility.
- `apps/api/app/services/chat_roundtrip_service.py` — canonical comparison, deterministic export verification, and structured differences.
- `apps/api/app/services/tokenizer_service.py` — pinned tokenizer profile loading and fail-closed Thai/Thai-English segmentation.
- `apps/api/app/services/providers/descriptive_v170_provider.py` — the v1.7.0 feature formulas and statuses.
- `apps/api/app/services/findings_service.py` — immutable descriptive Findings projection; no ML or norms.
- `apps/api/app/db/migrations/versions/0013_add_v170_speech_pipeline_records.py` — durable version/provenance records.
- `apps/lingualens-app/src/features/sessions/intake/audio-file-upload-panel.tsx` — real file selection, limits, formats, upload progress, actionable errors.
- `apps/lingualens-app/src/features/sessions/transcript/speaker-mapping-panel.tsx` — mapping review and confirmation.
- `apps/lingualens-app/src/features/sessions/transcript/qa-limitations-panel.tsx` — typed blockers and acknowledgments.
- `apps/lingualens-app/src/features/sessions/findings/descriptive-feature-card.tsx` — value/status/formula/provenance/limitation presentation.
- `tests/fixtures/audio/v1.7.0/manifest.json` — fixture identities, composition, checksums, transcripts, timing, and expected coverage.
- `scripts/generate_v170_golden_audio.py` — deterministic PCM composition of committed non-identifying synthetic seed clips.
- `scripts/benchmark_v170_asr.py` — machine-readable runtime/resource/completeness benchmark.
- `docs/CHAT_SUBSET_SPEC.md`, `docs/FEATURE_V1_SPEC.md`, and `docs/AUDIO_GOLDEN_FIXTURES.md` — versioned public engineering contracts.

Existing `apps/api/app/services/audio_job_service.py`, `transcript_service.py`, `cha_service.py`, `feature_service.py`, `apps/lingualens-app/src/lib/workflow.ts`, and `session-workspace-model.tsx` remain orchestrators and adapters. Research modules under `src/` are evidence and compatibility surfaces only; product code must not import them.

## Work package sequence and gates

| Package | Delivers | Entry condition | Exit evidence |
|---|---|---|---|
| A | Typed contracts, config, persistence | Decisions in ADR 0018–0020 accepted | Schema/migration tests pass in JSON and SQL repositories |
| B | Server-verified audio and golden assets | Package A | 1/5/15-minute accepted; over-15-minute rejected before ASR |
| C | Real local ASR and draft integrity | Package B | Thai and Thai-English drafts from real provider; no mock fallback |
| D | Speaker review, QA, attestation | Package C | Current complete mapping and reviewed limitations required |
| E | CHAT subset and round-trip | Package D | Semantic equality and deterministic export checksum |
| F | Deterministic features and Findings | Package E | Golden numerators/denominators/statuses and provenance match |
| G | Benchmarks and vertical-slice release gate | Packages A–F | Reproducible E2E evidence and evidence-derived timeout profile |

## Execution preflight

The worktree inspected while this plan was written contains substantial
pre-existing modified, deleted, and untracked work unrelated to v1.7.0. Before
Task 1, run:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

Record the intended committed base, then use the
`superpowers:using-git-worktrees` skill to create an isolated
`codex/v1.7.0-speech-to-chat` worktree. Do not reset, clean, stash, overwrite,
or carry the current WIP into that worktree without explicit owner approval.
Ensure this plan and ADR 0018–0020 are present in the selected base or copy only
those reviewed documentation changes after approval.

### Task 1: Freeze v1.7.0 configuration and specification contracts

**Files:**

- Create: `docs/CHAT_SUBSET_SPEC.md`
- Create: `docs/FEATURE_V1_SPEC.md`
- Create: `docs/AUDIO_GOLDEN_FIXTURES.md`
- Modify: `apps/api/app/core/config.py`
- Create: `apps/api/.env.example`
- Modify: `README.md`
- Test: `apps/api/tests/test_v170_config.py`

- [ ] **Step 1: Write failing configuration tests**

```python
from app.core.config import Settings


def test_v170_audio_defaults_are_15_minutes_and_100_mb():
    settings = Settings()
    assert settings.max_audio_duration_seconds == 900
    assert settings.max_audio_file_size_mb == 100
    assert settings.audio_normalization_sample_rate_hz == 16_000
    assert settings.audio_normalization_channels == 1
    assert settings.audio_normalization_format == "wav_pcm_s16le"
    assert settings.default_audio_asr_provider == "local_faster_whisper"


def test_m4a_and_webm_are_not_enabled_without_verified_decoder_profiles():
    settings = Settings()
    assert settings.parsed_supported_audio_formats == ("wav", "mp3")
```

- [ ] **Step 2: Run the tests and confirm the old defaults fail**

Run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_config.py -q
```

Expected: failures showing the current `250` MB limit and missing duration, normalization, provider, and format settings.

- [ ] **Step 3: Add typed milestone settings and validation**

Add these fields to `Settings` and load them through the existing `LINGUALENS_*` environment mapping:

```python
max_audio_file_size_mb: int = 100
max_audio_duration_seconds: int = 900
supported_audio_formats_csv: str = "wav,mp3"
audio_normalization_sample_rate_hz: int = 16_000
audio_normalization_channels: int = 1
audio_normalization_format: str = "wav_pcm_s16le"
default_audio_asr_provider: str = "local_faster_whisper"
asr_runtime_profile_path: str = "artifacts/v1.7.0/asr_runtime_profile.json"
chat_subset_version: str = "lingualens-chat-v1.7.0"
chat_parser_version: str = "lingualens-chat-parser-v1.7.0"
chat_serializer_version: str = "lingualens-chat-serializer-v1.7.0"
qa_rule_version: str = "speech-qa-v1.7.0"
feature_schema_version: str = "descriptive-features-v1.7.0"
tokenizer_profile_path: str = "artifacts/v1.7.0/tokenizer_profile.json"

@property
def parsed_supported_audio_formats(self) -> tuple[str, ...]:
    return tuple(
        item.strip().lower()
        for item in self.supported_audio_formats_csv.split(",")
        if item.strip()
    )
```

Add model validation requiring positive limits, exactly one normalization channel, and a runtime profile for `local_faster_whisper` outside mock-only test configuration. Do not add a 60-minute or 250 MB compatibility setting.

- [ ] **Step 4: Write the three specs with executable rules**

`CHAT_SUBSET_SPEC.md` must enumerate supported headers, `@Participants`, `@ID`, `@Media`, speaker tiers, continuation lines, media bullets, supported dependent tiers/annotations, opaque preservation, blocking unsupported content, UTF-8/NFC, `\n`, canonical header and participant ordering, escaping, exact generated timestamps, parser/serializer versions, and structured round-trip errors.

`FEATURE_V1_SPEC.md` must give formulas, counting rules, minimum sample rules, exclusions, statuses, numerator/denominator requirements, tokenizer profile fields, staleness triggers, and the prohibition on thresholds/norms/diagnosis.

`AUDIO_GOLDEN_FIXTURES.md` must define synthetic-only content, fixture assembly, duration classes, decoder format matrix, source and generated checksums, expected transcript/timing artifacts, benchmark repetitions, machine metadata, and artifact regeneration commands.

- [ ] **Step 5: Expose the same limits and formats through a read-only capability endpoint**

Add `GET /api/v1/audio/capabilities` in `apps/api/app/api/v1/routes/jobs.py` returning:

```json
{
  "milestone": "v1.7.0-testbed",
  "max_size_bytes": 104857600,
  "max_duration_seconds": 900,
  "supported_formats": ["wav", "mp3"],
  "normalization": {
    "channels": 1,
    "sample_rate_hz": 16000,
    "format": "wav_pcm_s16le"
  },
  "browser_recording": {
    "state": "experimental_unavailable",
    "blocks_milestone": false
  }
}
```

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_config.py -q
```

Expected: all configuration and capability tests pass.

Commit:

```bash
git add apps/api/app/core/config.py apps/api/app/api/v1/routes/jobs.py apps/api/.env.example apps/api/tests/test_v170_config.py docs/CHAT_SUBSET_SPEC.md docs/FEATURE_V1_SPEC.md docs/AUDIO_GOLDEN_FIXTURES.md README.md
git commit -m "docs: freeze v1.7 speech pipeline contracts" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 2: Add versioned speech-pipeline domain records and durable persistence

**Files:**

- Create: `apps/api/app/schemas/speech_pipeline.py`
- Modify: `apps/api/app/schemas/clinical.py`
- Modify: `apps/api/app/db/models.py`
- Create: `apps/api/app/db/migrations/versions/0013_add_v170_speech_pipeline_records.py`
- Modify: `apps/api/app/repositories/mock_repository.py`
- Modify: `apps/api/app/repositories/sqlalchemy_repository.py`
- Test: `apps/api/tests/test_speech_pipeline_persistence.py`

- [ ] **Step 1: Write JSON and SQL round-trip tests before defining the records**

The tests must persist and reload:

```python
assert reloaded_audio.source_checksum_sha256 == source_sha
assert reloaded_audio.normalized_asset.normalized_checksum_sha256 == normalized_sha
assert reloaded_mapping.transcript_version == 3
assert reloaded_mapping.entries[0].temporary_speaker_id == "SPK_01"
assert reloaded_mapping.entries[0].confirmed_chat_code == "CHI"
assert reloaded_attestation.speaker_mapping_version == 2
assert reloaded_acknowledgment.validator_version == "speech-qa-v1.7.0"
assert reloaded_export.round_trip.status == "verified"
assert reloaded_feature.features[0].status == "unavailable"
```

Run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_speech_pipeline_persistence.py -q
```

Expected: collection/model/import failures before the new records exist.

- [ ] **Step 2: Define explicit enums and immutable version records**

Create these types in `speech_pipeline.py` and re-export them from `clinical.py` for compatibility:

```python
class FeatureResultStatus(str, Enum):
    available = "available"
    unavailable = "unavailable"
    insufficient_data = "insufficient_data"
    experimental = "experimental"
    stale = "stale"
    failed = "failed"


class QaDisposition(str, Enum):
    integrity_blocker = "integrity_blocker"
    acknowledgeable_limitation = "acknowledgeable_limitation"


class NormalizedAudioAsset(BaseModel):
    asset_version: int
    object_key: str
    normalized_checksum_sha256: str
    format: Literal["wav_pcm_s16le"]
    duration_ms: int
    sample_rate_hz: int
    channels: Literal[1]
    frame_count: int
    decoder_name: str
    decoder_version: str
    conversion_command_profile: str
    source_audio_file_id: str
    source_asset_version: int
    created_at: datetime


class SpeakerMappingEntry(BaseModel):
    temporary_speaker_id: str
    confirmed_chat_code: str | None
    participant_role: str
    disposition: Literal["target", "non_target", "unknown", "merged"]
    merged_into_temporary_speaker_id: str | None = None
    affected_utterance_ids: list[str] = Field(default_factory=list)


class ReviewedSpeakerMapping(BaseModel):
    mapping_id: str
    mapping_version: int
    transcript_id: str
    transcript_version: int
    entries: list[SpeakerMappingEntry]
    confirmed_by_user_id: str
    confirmed_by_role: str
    confirmed_at: datetime
    status: Literal["draft", "confirmed", "stale"]


class LimitationAcknowledgment(BaseModel):
    acknowledgment_id: str
    limitation_code: str
    severity: str
    affected_resource_id: str
    affected_resource_version: str
    affected_stage: str
    affected_feature_id: str | None = None
    therapist_user_id: str
    therapist_role: str
    acknowledged_at: datetime
    structured_reason: str
    note: str = ""
    validator_version: str
    request_audit_id: str
    status: Literal["current", "stale"]
```

Add typed records for ASR profile/provenance, attestation, CHAT export/round-trip, tokenizer profile, and Findings projection using the same explicit source-version fields.

- [ ] **Step 3: Persist first-class version records**

Migration `0013` must create tables for:

- `normalized_audio_assets`;
- `speaker_mappings`;
- `transcript_attestations`;
- `limitation_acknowledgments`;
- `chat_exports`;
- `findings_results`.

Use organization/session/transcript foreign keys where applicable, immutable version columns, JSON payload columns only for the typed detail envelope, checksum columns for indexed lookup, and unique constraints for `(resource_id, version)`. Add normalized/source lineage columns to `audio_files`, ASR raw-label/provenance fields to transcript JSON payloads, and mapping/attestation/round-trip/tokenizer source versions to feature records.

- [ ] **Step 4: Implement repository parity**

Both repositories must expose the same methods:

```python
create_normalized_audio_asset(record)
get_current_normalized_audio_asset(audio_file_id)
create_speaker_mapping(record)
get_current_speaker_mapping(transcript_id)
create_limitation_acknowledgment(record)
list_current_acknowledgments(transcript_id)
create_transcript_attestation(record)
create_chat_export(record)
create_findings_result(record)
mark_downstream_stale(transcript_id, causes)
```

The update path must retain old versions for audit and change only current links/statuses.

- [ ] **Step 5: Run migration and repository tests**

Run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_speech_pipeline_persistence.py tests/test_workflow.py -q -k "round_trip or stale or repository"
```

Expected: JSON-file and SQL repositories preserve identical typed values and immutable history.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/schemas/speech_pipeline.py apps/api/app/schemas/clinical.py apps/api/app/db/models.py apps/api/app/db/migrations/versions/0013_add_v170_speech_pipeline_records.py apps/api/app/repositories/mock_repository.py apps/api/app/repositories/sqlalchemy_repository.py apps/api/tests/test_speech_pipeline_persistence.py
git commit -m "feat: persist v1.7 speech artifact lineage" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 3: Build versioned synthetic golden audio fixtures

**Files:**

- Create: `tests/fixtures/audio/v1.7.0/seed/thai_only.wav`
- Create: `tests/fixtures/audio/v1.7.0/seed/thai_english.wav`
- Create: `tests/fixtures/audio/v1.7.0/seed/overlap.wav`
- Create: `tests/fixtures/audio/v1.7.0/formats/verified_sample.mp3`
- Create: `tests/fixtures/audio/v1.7.0/manifest.json`
- Create: `tests/fixtures/audio/v1.7.0/expected/*.json`
- Create: `scripts/generate_v170_golden_audio.py`
- Create: `apps/api/tests/test_v170_audio_fixture_manifest.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write manifest validation tests**

The test must reject identifying metadata, missing provenance, incorrect hashes, mutable filenames, and duration-class mismatch. It must assert fixture cases for:

```python
required_cases = {
    "thai_1m",
    "thai_english_5m",
    "thai_english_15m",
    "thai_english_15m_plus_5s",
    "two_speakers_correct",
    "swapped_clusters",
    "unknown_speaker",
    "more_than_two_speakers",
    "diarization_unavailable",
    "overlapping_speech",
}
assert required_cases <= set(manifest["cases"])
```

- [ ] **Step 2: Commit only short non-identifying seed clips**

Each seed must be synthetic, contain no real name or identifier, and have a checked-in transcript/timing description. Record synthetic voice/tool, voice identifier, generation date, license, language, script checksum, PCM properties, duration, and SHA-256. Human review must confirm that the spoken content matches the seed transcript. The committed MP3 format fixture carries the same semantic content as a WAV seed and records encoder provenance, decoded duration, and source checksum.

- [ ] **Step 3: Generate long fixtures deterministically**

The generator must use Python's `wave` module for frame-exact concatenation and silence insertion, never a platform media player. It writes generated files only to `.local/golden-audio/v1.7.0/`, verifies expected frame counts, and refuses to overwrite a file whose checksum differs without `--rebuild`.

Required command:

```bash
python scripts/generate_v170_golden_audio.py \
  --manifest tests/fixtures/audio/v1.7.0/manifest.json \
  --output .local/golden-audio/v1.7.0
```

Expected generated decoded durations:

```text
thai_1m                    60000 ms
thai_english_5m           300000 ms
thai_english_15m          900000 ms
thai_english_15m_plus_5s  905000 ms
```

- [ ] **Step 4: Store expected artifacts per case**

Each `expected/*.json` must include source transcript, temporary speaker labels, beginning/end anchors, expected segment order, accepted timestamp bounds for ASR evaluation, reviewed mapping, canonical CHAT checksum, tokenizer profile, feature numerators/denominators/values, and known limitations. Provider output text is evaluated against the reviewed gold; it is not copied into the provider result.

- [ ] **Step 5: Run fixture checks**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_audio_fixture_manifest.py -q
```

Expected: all manifest, privacy, duration, and checksum assertions pass.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/audio/v1.7.0 scripts/generate_v170_golden_audio.py apps/api/tests/test_v170_audio_fixture_manifest.py .gitignore
git commit -m "test: add versioned synthetic audio fixtures" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 4: Decode, validate, and normalize audio before job creation

**Files:**

- Create: `apps/api/app/services/audio_media_service.py`
- Modify: `apps/api/app/services/storage_service.py`
- Modify: `apps/api/app/services/audio_job_service.py`
- Modify: `apps/api/app/api/v1/routes/jobs.py`
- Modify: `requirements.txt`
- Test: `apps/api/tests/test_audio_media_service.py`
- Test: `apps/api/tests/test_audio_intake_limits.py`

- [ ] **Step 1: Write server-authoritative intake tests**

Cover:

- a client claiming `60` seconds for a decoded `905`-second file is rejected;
- a renamed unsupported file is rejected by decoded format, not extension;
- a `100 MB + 1 byte` object is rejected before decoding;
- exact `900` seconds is accepted and `900.001` seconds is rejected;
- the source file remains byte-identical;
- normalization is mono, 16 kHz, signed 16-bit PCM WAV;
- source and normalized checksums differ when conversion occurs and both persist;
- first and final source frames are represented in the normalized duration/frame count;
- WAV and MP3 pass; M4A/WebM remain capability-unavailable until their decoder fixtures pass.

- [ ] **Step 2: Resolve private object paths through the storage adapter**

Extend `BaseStorageAdapter` with read-only processing methods:

```python
def open_source_for_processing(self, audio_file: AudioFileMetadata) -> BinaryIO: ...
def persist_normalized_asset(
    self,
    audio_file: AudioFileMetadata,
    source: BinaryIO,
    *,
    content_type: str,
) -> str: ...
```

Local storage resolves and validates the opaque key beneath its configured root. Supabase storage downloads through the private service client into a bounded temporary file. Neither adapter returns a public URL or logs the original filename, storage key, or bytes.

- [ ] **Step 3: Implement a decoder capability registry and media probe**

`probe_audio()` must read the actual stored bytes and return:

```python
DecodedAudioMetadata(
    detected_format="wav",
    duration_ms=900_000,
    frame_count=14_400_000,
    sample_rate_hz=16_000,
    channels=1,
    decoder_name="soundfile",
    decoder_version="0.14.0",
)
```

The registry enables a format only when a boot-time capability check and its committed decode fixture pass. Do not infer support from extension, MIME type, browser metadata, or faster-whisper's transitive dependencies.

- [ ] **Step 4: Enforce size and decoded duration before creating an ASR job**

Move processing-job creation after:

```python
if actual_size_bytes > settings.max_audio_file_size_mb * 1024 * 1024:
    raise AudioIntakeError("audio_size_limit_exceeded", ...)
if decoded.duration_ms > settings.max_audio_duration_seconds * 1000:
    raise AudioIntakeError("audio_duration_limit_exceeded", ...)
```

Return structured errors with configured limit, actual value, unit, supported formats, and remediation. Do not truncate, split, partially process, or enqueue a job after either failure.

- [ ] **Step 5: Normalize without replacing the source**

Use the v1.7.0 baseline stack—SoundFile `0.14.0` with its reported
libsndfile version for decoding, NumPy `2.4.4` channel mixing, SciPy `1.17.1`
`resample_poly` for rational resampling, and SoundFile PCM-S16LE WAV writing.
Write a deterministic mono 16 kHz working copy, and persist
source size/checksum/detected format plus normalized
size/checksum/format/sample rate/channels/frame count/duration and every tool
version/profile. Verify duration and boundary-frame preservation before
marking `normalization_status="verified"`. The stereo/resampled fixture must
prove both source and normalized checksums are retained; the original object is
never replaced even if normalized bytes happen to match.

- [ ] **Step 6: Run focused audio tests**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_audio_media_service.py tests/test_audio_intake_limits.py -q
```

Expected: exact-limit fixtures pass, the over-limit fixture returns `audio_duration_limit_exceeded`, and no rejected case creates a processing job.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/services/audio_media_service.py apps/api/app/services/storage_service.py apps/api/app/services/audio_job_service.py apps/api/app/api/v1/routes/jobs.py apps/api/tests/test_audio_media_service.py apps/api/tests/test_audio_intake_limits.py requirements.txt
git commit -m "feat: verify and normalize v1.7 audio intake" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 5: Implement the real `local_faster_whisper` provider

**Files:**

- Modify: `apps/api/app/services/asr_providers/base.py`
- Modify: `apps/api/app/services/asr_providers/local_whisper_provider.py`
- Modify: `apps/api/app/services/asr_providers/registry.py`
- Create: `apps/api/app/services/asr_profiles.py`
- Modify: `requirements.txt`
- Test: `apps/api/tests/test_local_faster_whisper_provider.py`
- Test: `apps/api/tests/test_asr_provider_registry.py`

- [ ] **Step 1: Write provider-contract tests with an injected fake Whisper model**

Assert:

```python
assert provider.provider_id == "local_faster_whisper"
assert result.status == "completed"
assert [s.temporary_speaker_id for s in result.segments] == ["UNK", "UNK"]
assert result.segments[0].start_ms <= result.segments[0].end_ms
assert result.provenance.model_checksum_sha256 == pinned_checksum
assert result.provenance.temperature == 0.0
assert result.provenance.word_timestamps is True
assert result.provenance.normalized_audio_asset_version == 1
```

Also assert missing model, wrong model checksum, missing CTranslate2, missing decoder, and unverified runtime profile return structured `unavailable`; none invoke mock/manual/cloud providers.

- [ ] **Step 2: Replace provider-specific output with a canonical draft contract**

Change the base interface to receive a typed `TranscriptionInput` containing a verified normalized asset handle and a pinned decoding profile. Return `CanonicalTranscriptionDraft` with stable segment IDs, millisecond timestamps, text, `SPK_nn`/`UNK`, genuinely supported confidence only, provider warnings, source/normalized asset versions, and full provider/model/runtime provenance.

Raw faster-whisper segment and word data must be stored as a private provider artifact reference or typed provenance payload; routes and frontend code consume only the canonical draft.

- [ ] **Step 3: Load only immutable model artifacts**

`PinnedAsrProfile` must contain:

```python
model_identifier: str
model_revision: str
model_artifact_path: Path
model_checksum_sha256: str
faster_whisper_version: str
ctranslate2_version: str
decoder_name: str
decoder_version: str
device: Literal["cpu", "cuda", "auto"]
compute_type: str
language_mode: Literal["th", "auto"]
beam_size: int
temperature: float
vad_filter: bool
word_timestamps: bool
condition_on_previous_text: bool
```

Availability checks must hash and match the model artifact, verify package/runtime versions, and reject floating identifiers or unexpected decoding values.

- [ ] **Step 4: Use explicit deterministic decoding parameters**

Invoke faster-whisper with every output-affecting parameter provided explicitly. The golden path uses temperature `0.0`; changing temperature, beam, VAD, language mode, prompt, model artifact, or package version changes the profile checksum and invalidates downstream artifacts.

Do not copy the research module's `api_openai` fallback, Thai-model fallback, stdout logging, or direct `.cha` generation.

Pin the exact faster-whisper and CTranslate2 versions selected by Task 13 in
the runtime profile and installation requirements before the vertical gate is
allowed to pass.

- [ ] **Step 5: Register the provider without making mock the default**

The registry must resolve `get_default()` from typed configuration and reject a configured mock/manual provider for the normal `audio-upload` workflow. Mock and manual providers remain callable only from explicitly identified test/demo or separate manual-entry operations.

- [ ] **Step 6: Run provider tests**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_local_faster_whisper_provider.py tests/test_asr_provider_registry.py -q
```

Expected: canonical output and provenance tests pass; missing dependencies fail explicitly; a registry test proves no fallback provider is called.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/services/asr_providers/base.py apps/api/app/services/asr_providers/local_whisper_provider.py apps/api/app/services/asr_providers/registry.py apps/api/app/services/asr_profiles.py apps/api/tests/test_local_faster_whisper_provider.py apps/api/tests/test_asr_provider_registry.py requirements.txt
git commit -m "feat: add local faster-whisper ASR provider" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 6: Make transcription jobs fail-closed, retryable, idempotent, and completeness-aware

**Files:**

- Create: `apps/api/app/services/asr_completeness_service.py`
- Modify: `apps/api/app/services/audio_job_service.py`
- Modify: `apps/api/app/tasks/job_queue.py`
- Modify: `apps/api/app/api/v1/routes/jobs.py`
- Modify: `apps/api/app/schemas/clinical.py`
- Test: `apps/api/tests/test_transcription_job_lifecycle.py`
- Test: `apps/api/tests/test_asr_completeness_service.py`

- [ ] **Step 1: Write lifecycle and completeness failures first**

Tests must cover:

- unavailable provider creates a `failed` job with `provider_unavailable`, preserves source/normalized assets, and exposes retry;
- an empty provider result is `asr_empty_result`;
- reversed/out-of-range timestamps are blockers;
- a missing beginning or ending speech anchor is a blocker;
- large unexplained gaps are typed outcomes using versioned escalation rules;
- provider-reported partial failure is not `completed`;
- repeated create requests return the same active/completed job;
- retry of a failed job creates attempt `n + 1` with a link to the failed attempt;
- retry cannot change the source/normalized asset silently;
- mock/manual/cloud providers are never invoked;
- no job starts without verified normalization.

- [ ] **Step 2: Define a deterministic idempotency identity**

Compute:

```python
idempotency_material = {
    "audio_file_id": audio.audio_file_id,
    "source_asset_version": audio.asset_version,
    "normalized_asset_version": normalized.asset_version,
    "normalized_checksum": normalized.normalized_checksum_sha256,
    "provider_id": provider.provider_id,
    "asr_profile_checksum": profile.profile_checksum_sha256,
}
idempotency_key = canonical_json_sha256(idempotency_material)
```

The create endpoint returns an existing active or completed job with this key. `POST /jobs/{job_id}/retry` is the only path that creates a new attempt after a failed/unavailable job.

- [ ] **Step 3: Remove fallback request fields from the normal contract**

Remove `allow_fallback_to_mock`, `draft_text`, and default `"mock"` from `TranscriptionJobRequest`. Use:

```python
class TranscriptionJobRequest(BaseModel):
    audio_file_id: str
    provider_id: str = "local_faster_whisper"
    expected_source_asset_version: int
    expected_normalized_asset_version: int
```

Keep manual transcript creation under `/transcripts/manual`; it never creates an ASR job or ASR provenance.

- [ ] **Step 4: Validate segment and media completeness**

The completeness result must report detected speech intervals, segment intervals, beginning/end coverage, covered/uncovered speech duration, unexplained gaps, overlap duration, reversed/out-of-range segments, and rule version.

Use fixture-derived thresholds from the checked-in runtime/QA profile. If the profile is absent, the provider is unavailable; do not insert a guessed timeout or gap threshold. Unsafe partial results fail the job. Structurally valid but limited coverage becomes a typed limitation that must be acknowledged later.

- [ ] **Step 5: Source timeout from benchmark evidence**

Load `timeout_seconds` from the selected immutable ASR runtime profile. The worker records cold/warm mode, start/end monotonic times, CPU time, peak resident memory, timeout profile checksum, and termination reason. A missing or mismatched profile is `runtime_profile_unavailable`, not a default timeout.

- [ ] **Step 6: Normalize draft creation**

`create_draft_transcript_from_result()` must:

- preserve the raw provider label in `source_speaker_label`;
- assign a neutral `temporary_speaker_id`;
- never create `CHI`, `THE`, `THER`, or `INV` from ASR/diarization;
- preserve segment IDs/timestamps/text/provider warnings;
- bind the transcript to exact audio, normalized asset, ASR profile, and draft versions;
- start speaker mapping, QA, and attestation as incomplete.

- [ ] **Step 7: Run lifecycle tests**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_transcription_job_lifecycle.py tests/test_asr_completeness_service.py -q
```

Expected: all failure, retry, idempotency, completeness, and no-fallback assertions pass.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/services/asr_completeness_service.py apps/api/app/services/audio_job_service.py apps/api/app/tasks/job_queue.py apps/api/app/api/v1/routes/jobs.py apps/api/app/schemas/clinical.py apps/api/tests/test_transcription_job_lifecycle.py apps/api/tests/test_asr_completeness_service.py
git commit -m "feat: harden transcription job lifecycle" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 7: Replace metadata-only file upload UI with the real upload lifecycle

**Files:**

- Create: `apps/lingualens-app/src/features/sessions/intake/audio-file-upload-panel.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/intake/session-intake-steps.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/intake/session-intake-view.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts`
- Modify: `apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx`
- Modify: `apps/lingualens-app/src/lib/workflow.ts`
- Test: `apps/lingualens-app/src/__tests__/audio-file-upload-panel.test.tsx`
- Test: `apps/lingualens-app/src/__tests__/session-intake-flow.test.tsx`
- Test: `apps/lingualens-app/src/__tests__/session-workspace-audio-auth.test.tsx`

- [ ] **Step 1: Write UI tests for visible limits and actionable failures**

Assert the panel shows `15 minutes`, `100 MB`, and the formats returned by `/audio/capabilities` before selection. Test:

- client-side early warning for size while retaining server authority;
- backend decoded-duration rejection even when browser metadata appears valid;
- unsupported format message naming supported formats;
- provider unavailable/missing model/normalization failure;
- retry button only for retryable failed jobs;
- no “use mock” or silent paste/manual transition;
- a completed job opens the backend draft;
- no patient transcript/audio content appears in console output.

- [ ] **Step 2: Add a real file source state**

Replace the metadata-only `handleAudioUpload()` with a selected `File` held in component memory until explicit upload confirmation. The view model must track:

```typescript
type AudioFileUploadState =
  | { state: "idle" }
  | { state: "selected"; file: File }
  | { state: "uploading"; file: File; progress: number }
  | { state: "verifying"; audioFileId: string }
  | { state: "normalizing"; audioFileId: string }
  | { state: "transcribing"; audioFileId: string; jobId: string }
  | { state: "needs_review"; transcriptId: string }
  | { state: "failed"; code: string; message: string; retryable: boolean };
```

- [ ] **Step 3: Complete every backend step in order**

The service sequence is:

```text
GET  /audio/capabilities
POST /sessions/{session}/audio/upload
PUT  signed/local upload URL
POST /audio/{audio}/complete-upload
POST /audio/{audio}/verify-and-normalize
POST /sessions/{session}/audio/process
GET  /jobs/{job} until terminal
GET  /transcripts/{transcript} when needs_review
```

The server recomputes source size/checksum/duration; client values are display and transport-integrity hints only.

- [ ] **Step 4: Preserve browser recording behind an explicit capability state**

Keep `browser-audio-recorder.tsx` and `experimental-transcription-service.ts` intact enough for future work, but render recording as `Experimental — unavailable in v1.7.0 testbed` unless an explicit local-development capability enables it. It must not call the normal file-upload path, produce a hardcoded transcript, or affect milestone completion.

- [ ] **Step 5: Remove silent frontend fallbacks**

Delete normal-upload branches that request `"mock"`, construct sample CHAT, suggest that paste is an ASR result, or swallow polling network errors indefinitely. Retain manual paste and `.cha` import as separately selected source workflows with their own provenance labels.

- [ ] **Step 6: Run frontend tests**

```bash
cd apps/lingualens-app
npm test -- src/__tests__/audio-file-upload-panel.test.tsx src/__tests__/session-intake-flow.test.tsx src/__tests__/session-workspace-audio-auth.test.tsx
```

Expected: all upload, capability, error, retry, and experimental-recording tests pass independently and in the same order.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/src/features/sessions/intake/audio-file-upload-panel.tsx apps/lingualens-app/src/features/sessions/intake/session-intake-steps.tsx apps/lingualens-app/src/features/sessions/intake/session-intake-view.tsx apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx apps/lingualens-app/src/lib/workflow.ts apps/lingualens-app/src/__tests__/audio-file-upload-panel.test.tsx apps/lingualens-app/src/__tests__/session-intake-flow.test.tsx apps/lingualens-app/src/__tests__/session-workspace-audio-auth.test.tsx
git commit -m "feat: upload testbed audio through verified backend flow" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 8: Add therapist-reviewed speaker mapping without overwriting provider labels

**Files:**

- Create: `apps/api/app/services/speaker_mapping_service.py`
- Modify: `apps/api/app/api/v1/routes/transcripts.py`
- Modify: `apps/api/app/services/transcript_service.py`
- Modify: `apps/api/app/schemas/clinical.py`
- Create: `apps/lingualens-app/src/features/sessions/transcript/speaker-mapping-panel.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts`
- Test: `apps/api/tests/test_speaker_mapping.py`
- Test: `apps/lingualens-app/src/__tests__/speaker-mapping-panel.test.tsx`

- [ ] **Step 1: Write mapping invariants**

Backend tests must cover:

- correct two-speaker mapping;
- swapped provider clusters corrected by the therapist;
- one unknown/non-target speaker;
- more than two speakers;
- diarization unavailable;
- overlapping speech;
- explicit merge of duplicate clusters;
- per-utterance reassignment to split an incorrectly grouped cluster;
- ambiguous duplicate required role without an explicit merge;
- unknown segment speaker;
- confirmation tied to authenticated therapist, timestamp, transcript version;
- transcript edit/remap invalidates confirmation and downstream state.

- [ ] **Step 2: Add mapping endpoints**

```text
GET  /transcripts/{id}/speaker-mapping
PUT  /transcripts/{id}/speaker-mapping
POST /transcripts/{id}/speaker-mapping/confirm
```

`PUT` saves a draft with `expected_transcript_version` and `expected_mapping_version`. `POST /confirm` validates all referenced temporary speaker IDs and affected utterances, rejects ambiguity, and stores authenticated user/role/time. Two source clusters may map to one CHAT code only when the mapping contains an explicit merge relation.

- [ ] **Step 3: Preserve raw and reviewed layers**

Each draft segment retains:

```json
{
  "temporary_speaker_id": "SPK_02",
  "source_speaker_label": "speaker_1",
  "source_provider": "optional_diarizer",
  "source_provider_metadata": {},
  "reviewed_chat_code": "CHI",
  "reviewed_mapping_version": 2
}
```

Changing the reviewed layer never mutates the first four raw fields.

- [ ] **Step 4: Build the mapping review UI**

The panel must list every temporary speaker, all affected segments with audio seek controls, current disposition, CHAT code, participant role, merge target, and per-utterance split assignments. “Confirm mapping” remains disabled until every required segment is mapped and all affected segments have been reviewed.

- [ ] **Step 5: Gate workflow actions**

QA completion, attestation, role-dependent feature extraction, and `.cha` export must return typed blockers for missing/stale/incomplete/ambiguous mapping. The frontend shows the exact affected speaker/segment and routes the therapist back to the mapping panel.

- [ ] **Step 6: Run backend and frontend tests**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_speaker_mapping.py -q

cd ../lingualens-app
npm test -- src/__tests__/speaker-mapping-panel.test.tsx
```

Expected: all fixture cases and stale/ambiguity gates pass.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/services/speaker_mapping_service.py apps/api/app/api/v1/routes/transcripts.py apps/api/app/services/transcript_service.py apps/api/app/schemas/clinical.py apps/api/tests/test_speaker_mapping.py apps/lingualens-app/src/features/sessions/transcript/speaker-mapping-panel.tsx apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts apps/lingualens-app/src/__tests__/speaker-mapping-panel.test.tsx
git commit -m "feat: require therapist-confirmed speaker mapping" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 9: Replace generic QA override with blockers, limitations, escalation, and attestation

**Files:**

- Create: `apps/api/app/services/qa_policy_service.py`
- Create: `apps/api/app/services/qa_rules_v170.py`
- Modify: `apps/api/app/services/transcript_service.py`
- Modify: `apps/api/app/api/v1/routes/transcripts.py`
- Modify: `apps/api/app/schemas/clinical.py`
- Modify: `apps/api/app/services/feature_service.py`
- Create: `apps/lingualens-app/src/features/sessions/transcript/qa-limitations-panel.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts`
- Test: `apps/api/tests/test_v170_qa_policy.py`
- Test: `apps/lingualens-app/src/__tests__/qa-limitations-panel.test.tsx`

- [ ] **Step 1: Parameterize every required integrity blocker**

Use stable issue codes:

```python
INTEGRITY_BLOCKER_CODES = {
    "SOURCE_AUDIO_MISSING",
    "SOURCE_AUDIO_UNVERIFIED",
    "NORMALIZED_AUDIO_MISSING",
    "NORMALIZED_AUDIO_CORRUPT",
    "NORMALIZED_AUDIO_TRUNCATED",
    "AUDIO_LINEAGE_MISMATCH",
    "AUDIO_CHECKSUM_MISMATCH",
    "AUDIO_SIZE_LIMIT_EXCEEDED",
    "AUDIO_DURATION_LIMIT_EXCEEDED",
    "TRANSCRIPT_AUDIO_VERSION_MISMATCH",
    "TRANSCRIPT_STALE",
    "SPEAKER_MAPPING_MISSING",
    "SPEAKER_MAPPING_STALE",
    "SPEAKER_MAPPING_INCOMPLETE",
    "SPEAKER_MAPPING_AMBIGUOUS",
    "SEGMENT_SPEAKER_UNMAPPED",
    "TIMESTAMP_ORDER_INVALID",
    "TIMESTAMP_RANGE_INVALID",
    "TIMESTAMP_OVERLAP_INVALID",
    "BEGINNING_COVERAGE_FAILED",
    "ENDING_COVERAGE_FAILED",
    "TRANSCRIPT_MATERIALLY_INCOMPLETE",
    "TRANSCRIPT_EMPTY",
    "ATTESTATION_VERSION_STALE",
    "CHAT_ROUND_TRIP_FAILED",
    "CHAT_CONTENT_MUTATED",
    "CHAT_UNSUPPORTED_CONTENT_BLOCKING",
    "PROVENANCE_VERSION_MISMATCH",
    "CONSENT_INVALID",
    "ACCESS_UNAUTHORIZED",
    "UPSTREAM_JOB_FAILED",
    "UPSTREAM_PARTIAL_UNSAFE",
}
```

Each code gets a fixture that proves QA completion, attestation, CHAT export, role-dependent features, Findings completion, report generation/sign-off, and export remain blocked.

- [ ] **Step 2: Parameterize acknowledgeable limitations and escalation**

Use typed limitation codes for short sample, reduced-but-reviewable intelligibility, below-target-but-valid timestamp coverage, optional CHAT metadata absence, unavailable optional feature/token metric, manual mapping after unavailable diarization, interpretation-limiting audio quality, and non-required export metadata omission.

Every rule returns either:

```python
QaOutcome(
    code="LOW_INTELLIGIBILITY",
    disposition=QaDisposition.acknowledgeable_limitation,
    severity="warning",
    rule_version="speech-qa-v1.7.0",
    affected_resources=[...],
    remediation="Review uncertain utterances and confirm retained text.",
)
```

or the explicit escalated blocker code when reliable representation fails. Free-text classification is not allowed.

- [ ] **Step 3: Add version-bound acknowledgment endpoints**

```text
POST /transcripts/{id}/limitations/{code}/acknowledgments
GET  /transcripts/{id}/limitations
```

The POST body contains expected transcript/audio/mapping/validator versions, a structured reason enum, and optional note. The server takes therapist user ID/role from authentication and request/audit ID from request context.

- [ ] **Step 4: Replace the attestation contract**

Remove `override_qa_failure` from `AttestationRequest`. Require:

```python
class AttestationRequest(BaseModel):
    expected_transcript_version: int
    expected_speaker_mapping_version: int
    expected_audio_asset_version: int
    expected_normalized_asset_version: int
    expected_qa_rule_version: str
    expected_chat_candidate_verification_id: str
    acknowledgment_ids: list[str]
    reason: str = "Therapist reviewed the current transcript and limitations."
```

Attestation creates an immutable identifier and records every source version,
including the current successful non-downloadable CHAT candidate verification.
Any blocker, unreviewed limitation, stale acknowledgment, candidate-verification
failure, or version mismatch rejects the request.

- [ ] **Step 5: Make debug output non-clinical by construction**

Allow debug override only when both an explicit test/development runtime enum and a process-level test marker are present. Debug runs create a separate `test_only` artifact with a visible marker and audit event; repository methods reject attempts to attest, export, sign, or attach it as the session's report-eligible record. Staging/production configuration validation must reject debug enablement at startup.

- [ ] **Step 6: Invalidate acknowledgments and downstream artifacts**

Transcript content/boundary/timestamp edits, speaker remapping, normalization changes, and validator-version changes mark affected acknowledgments, attestation, CHAT export, features, Findings, and report inputs `stale`. History remains readable.

- [ ] **Step 7: Build the QA limitations UI**

Render blockers separately from acknowledgeable limitations. Each limitation displays code, severity, affected stage/feature, structured reason selector, optional note, validator version, and current/stale state. The attestation action remains disabled until the backend eligibility response is true.

- [ ] **Step 8: Run QA tests**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_qa_policy.py -q

cd ../lingualens-app
npm test -- src/__tests__/qa-limitations-panel.test.tsx
```

Expected: every blocker/limitation/escalation case, stale acknowledgment, successful reviewed-limitations attestation, production debug rejection, and audit completeness test passes.

- [ ] **Step 9: Commit**

```bash
git add apps/api/app/services/qa_policy_service.py apps/api/app/services/qa_rules_v170.py apps/api/app/services/transcript_service.py apps/api/app/api/v1/routes/transcripts.py apps/api/app/schemas/clinical.py apps/api/app/services/feature_service.py apps/api/tests/test_v170_qa_policy.py apps/lingualens-app/src/features/sessions/transcript/qa-limitations-panel.tsx apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts apps/lingualens-app/src/__tests__/qa-limitations-panel.test.tsx
git commit -m "feat: enforce typed transcript QA policy" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 10: Implement the canonical CHAT subset and deterministic round-trip gate

**Files:**

- Create: `apps/api/app/services/chat_subset.py`
- Create: `apps/api/app/services/chat_roundtrip_service.py`
- Modify: `apps/api/app/services/cha_service.py`
- Modify: `apps/api/app/services/transcript_service.py`
- Modify: `apps/api/app/api/v1/routes/transcripts.py`
- Test: `apps/api/tests/test_chat_subset_v170.py`
- Test: `apps/api/tests/test_chat_roundtrip_v170.py`
- Create: `tests/fixtures/chat/v1.7.0/*.cha`
- Create: `tests/fixtures/chat/v1.7.0/expected/*.json`

- [ ] **Step 1: Write golden semantic and mutation tests**

Cover Thai-only, Thai-English, two speakers, more than two speakers, continuation lines, supported dependent tiers, supported annotations, opaque optional metadata, malformed timestamps, swapped speakers, missing participants, Unicode combining marks/NFC, deliberate text/tier/timestamp loss, and repeated deterministic export.

External import tests compare normalized fields and explicitly allow harmless whitespace, line ending, header-order, indentation, wrapping, and equivalent escaping differences.

- [ ] **Step 2: Define one canonical semantic model and normalization profile**

The comparator includes:

```python
class CanonicalChatDocument(BaseModel):
    subset_version: str
    language_codes: tuple[str, ...]
    media_reference: str | None
    participants: tuple[CanonicalParticipant, ...]
    utterances: tuple[CanonicalChatUtterance, ...]
    opaque_extensions: tuple[OpaqueChatExtension, ...]


class CanonicalChatUtterance(BaseModel):
    utterance_id: str
    speaker_code: str
    reviewed_text_nfc: str
    start_ms: int | None
    end_ms: int | None
    dependent_tiers: tuple[CanonicalDependentTier, ...]
    annotations: tuple[CanonicalAnnotation, ...]
    continuation_parts: tuple[str, ...]
```

Normalization pins UTF-8, NFC, `\n`, header order, participant order, timestamp serialization, terminators, escaping, continuation joining, and trailing newline.

- [ ] **Step 3: Preserve or block unknown content explicitly**

Each unknown header/tier/annotation receives:

```python
Literal[
    "preserved_opaque",
    "unsupported_blocking",
    "unsupported_non_blocking",
]
```

Non-blocking is allowed only for content whose omission cannot affect supported transcript meaning, and omission is still recorded. No parser branch may discard unknown content without an action record.

- [ ] **Step 4: Produce structured semantic differences**

Each mismatch returns code, field/tier, utterance/segment ID, expected value, actual value, severity, parser version, and serializer version. Generated timestamps require exact millisecond equality. External conversion tolerance is allowed only when a named import profile in `CHAT_SUBSET_SPEC.md` declares the exact tolerance.

- [ ] **Step 5: Break the QA/attestation/export cycle with a non-downloadable candidate check**

Before attestation, QA serializes the reviewed canonical model and confirmed
speaker mapping into an internal candidate, parses it, compares semantics, and
checks deterministic re-serialization. This candidate is never exposed as a
downloadable or clinical export. Its verification ID/checksum is version-bound
and becomes a blocker when invalid.

After attestation, the export service reruns the same verification against the
attested versions and creates the final artifact:

The export service performs:

```text
canonical source → export A → parse A → canonical B → export B
```

Both passes require semantic equality and
`sha256(export_A) == sha256(export_B)`. Persist transcript version,
speaker-mapping version, candidate verification ID, attestation ID,
subset/parser/serializer versions, canonical checksum, export checksum, export
timestamp, and exporting user/service.

- [ ] **Step 6: Gate the export endpoint**

Add:

```text
POST /transcripts/{id}/chat-exports
GET  /chat-exports/{export_id}
GET  /chat-exports/{export_id}/download
```

`POST` must reject missing/current-version attestation, mapping, QA, or
candidate round-trip state, then generate and verify the final artifact in one
server operation. The existing `GET /transcripts/{id}/export-cha` becomes a
deprecated read of the current verified artifact and must not create a new
record. Never return candidate or unverified bytes as a successful clinical
export.

- [ ] **Step 7: Run CHAT tests**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_chat_subset_v170.py tests/test_chat_roundtrip_v170.py tests/test_cha_service_basic.py tests/test_cha_parser_hardening.py -q
```

Expected: golden semantic equality and deterministic checksums pass; every deliberate mutation fails with the expected structured code.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/services/chat_subset.py apps/api/app/services/chat_roundtrip_service.py apps/api/app/services/cha_service.py apps/api/app/services/transcript_service.py apps/api/app/api/v1/routes/transcripts.py apps/api/tests/test_chat_subset_v170.py apps/api/tests/test_chat_roundtrip_v170.py tests/fixtures/chat/v1.7.0 docs/CHAT_SUBSET_SPEC.md
git commit -m "feat: verify deterministic CHAT round trips" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 11: Select a pinned Thai-aware tokenizer and implement deterministic features

**Files:**

- Create: `apps/api/app/services/tokenizer_service.py`
- Create: `apps/api/app/services/providers/descriptive_v170_provider.py`
- Modify: `apps/api/app/services/providers/registry.py`
- Modify: `apps/api/app/services/providers/base.py`
- Modify: `apps/api/app/services/feature_service.py`
- Modify: `apps/api/app/schemas/clinical.py`
- Create: `scripts/evaluate_v170_tokenizer.py`
- Create: `artifacts/v1.7.0/tokenizer_profile.json`
- Modify: `requirements.txt`
- Test: `apps/api/tests/test_v170_tokenizer.py`
- Test: `apps/api/tests/test_v170_descriptive_features.py`
- Modify: `docs/FEATURE_V1_SPEC.md`

- [ ] **Step 1: Write tokenizer golden tests before choosing an engine**

Use hand-reviewed expected tokens for Thai-only, Thai-English code switching, punctuation/whitespace, filled pauses, repetitions, partial words, unintelligible markers, and custom vocabulary. The evaluator compares feasible pinned PyThaiNLP engines/configurations and writes a candidate report; only a profile with exact golden segmentation may be marked `verified`.

- [ ] **Step 2: Generate an immutable tokenizer profile**

The checked-in profile contains engine, exact package version, segmentation mode, dictionary/model/artifact identifier and SHA-256, NFC rules, punctuation/whitespace/filled-pause/repetition/partial-word/unintelligible-marker/code-switch rules, custom vocabulary version/checksum, fixture manifest checksum, and profile checksum.

Runtime loading must reject any version or checksum mismatch. It returns `TokenizerUnavailable` rather than regex, whitespace, English, browser, unversioned, or alternate-tokenizer fallback.

After evaluation, replace the broad PyThaiNLP requirement with the exact
selected package version and record the installed dictionary/artifact checksum;
the benchmark report preserves rejected engine/profile results.

- [ ] **Step 3: Define exact v1.7.0 feature results**

Each result contains feature ID/version, value/unit, explicit status, numerator/denominator, minimum sample, excluded items, required inputs, transcript/mapping/audio versions, tokenizer profile/checksum when applicable, algorithm/configuration version, generated time, data-quality notes, limitations, and clinical caution.

Non-token formulas:

```text
child/therapist/total utterance count = count of reviewed utterances by confirmed role
turn count = count of contiguous speaker-role runs in canonical utterance order
audio duration = verified normalized asset duration_ms
timestamp coverage = union(valid utterance intervals) / verified audio duration
unexplained gap coverage = union(detected-speech intervals not covered by reviewed intervals) / verified audio duration
intelligibility ratios = reviewed category count / eligible reviewed utterance count
```

Overlap is counted once in interval unions. Intelligibility uses therapist review annotations only, never ASR confidence.

Token formulas:

```text
token count = count of eligible target-speaker tokens after profile exclusions
NDW = count of unique normalized eligible target-speaker tokens
TTR = NDW / token count
MLU-word = eligible target-speaker token count / eligible complete target-speaker utterance count
```

TTR returns `insufficient_data` below 50 eligible target tokens. MLU-word returns `insufficient_data` below 50 complete intelligible or partly intelligible target utterances. These are v1.7.0 engineering stability guards, not normative thresholds, and must be shown with the result.

- [ ] **Step 4: Preserve partial availability correctly**

If the tokenizer is unavailable, non-token metrics remain `available` when their own inputs pass, while token metrics return:

```json
{
  "status": "unavailable",
  "value": null,
  "reason_code": "TOKENIZER_PROFILE_UNAVAILABLE",
  "remediation": "Install and verify the tokenizer profile recorded for this feature schema."
}
```

Never return zero for unavailable/insufficient/failed metrics.

- [ ] **Step 5: Gate extraction and staleness**

Extraction requires current attestation, mapping, exact audio/transcript versions, QA state, and valid CHAT round-trip. Transcript content/boundary/timestamp, speaker mapping, tokenizer profile, or algorithm version changes mark affected results and downstream Findings/Report states `stale`.

- [ ] **Step 6: Keep heuristic cues experimental**

Existing pronoun reversal, echolalia, repetitive phrase, and reciprocal-question rules remain outside the v1.7.0 provider or return `experimental` with supporting utterance IDs. They never block the deterministic bundle and are not promoted to Findings.

- [ ] **Step 7: Run tokenizer and feature tests**

```bash
python scripts/evaluate_v170_tokenizer.py \
  --manifest tests/fixtures/audio/v1.7.0/manifest.json \
  --output artifacts/v1.7.0/tokenizer_profile.json

cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_tokenizer.py tests/test_v170_descriptive_features.py tests/test_feature_provider.py -q
```

Expected: verified tokenizer checksum matches, golden feature numerators/denominators/values pass, unavailable differs from zero, and stale invalidation passes.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/services/tokenizer_service.py apps/api/app/services/providers/descriptive_v170_provider.py apps/api/app/services/providers/registry.py apps/api/app/services/providers/base.py apps/api/app/services/feature_service.py apps/api/app/schemas/clinical.py apps/api/tests/test_v170_tokenizer.py apps/api/tests/test_v170_descriptive_features.py scripts/evaluate_v170_tokenizer.py artifacts/v1.7.0/tokenizer_profile.json requirements.txt docs/FEATURE_V1_SPEC.md
git commit -m "feat: add deterministic Thai-aware features" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 12: Project descriptive Findings with provenance, limitations, and stale-state safety

**Files:**

- Create: `apps/api/app/services/findings_service.py`
- Modify: `apps/api/app/api/v1/routes/features.py`
- Modify: `apps/api/app/services/feature_service.py`
- Create: `apps/lingualens-app/src/features/sessions/findings/descriptive-feature-card.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/findings/session-findings-view.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/findings/session-findings-support.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx`
- Modify: `apps/lingualens-app/src/lib/workflow.ts`
- Test: `apps/api/tests/test_v170_findings.py`
- Test: `apps/lingualens-app/src/__tests__/session-findings-v170.test.tsx`

- [ ] **Step 1: Write Findings contract tests**

Assert every card shows value/status, unit, formula/counting rule, sample size, numerator/denominator, source versions, feature/tokenizer versions, limitations, and unavailable/insufficient reason. Assert the UI never renders normal/abnormal, ASD probability, positive/negative, treatment recommendations, reference ranges, or fallback values.

- [ ] **Step 2: Create an immutable Findings projection**

`POST /sessions/{id}/findings` creates a versioned projection only from current v1.7.0 feature results. Its provenance includes feature-set ID/version, transcript/mapping/audio/normalized/attestation/CHAT export versions, tokenizer and algorithm checksums, acknowledged limitations, generation service version, and timestamp.

- [ ] **Step 3: Remove frontend-generated defaults**

Delete fallback values such as `"3.2"`, `"78"`, `"6%"`, fabricated percentages, and mock summaries from the real Findings path in `workflow.ts`. Missing backend data renders `unavailable`; stale data renders `stale`.

- [ ] **Step 4: Persist limitations downstream**

Acknowledged limitations and feature-specific limitations remain visible in Findings and report inputs. Report generation must not restate unavailable, insufficient, experimental, stale, or failed values as findings. The v1.7.0 vertical slice does not invoke ML or reference-comparison endpoints.

- [ ] **Step 5: Enforce stale propagation**

Any relevant transcript, timestamp, mapping, audio normalization, tokenizer, feature algorithm, CHAT parser/serializer, or QA validator change marks features, Findings, and report inputs stale. The UI removes completed styling, blocks report generation/sign-off/export, and links to the stage requiring regeneration/review.

- [ ] **Step 6: Run backend and frontend Findings tests**

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_findings.py -q

cd ../lingualens-app
npm test -- src/__tests__/session-findings-v170.test.tsx
```

Expected: descriptive-only presentation, provenance, limitation persistence, no fallback values, and stale gating pass.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/services/findings_service.py apps/api/app/api/v1/routes/features.py apps/api/app/services/feature_service.py apps/api/tests/test_v170_findings.py apps/lingualens-app/src/features/sessions/findings/descriptive-feature-card.tsx apps/lingualens-app/src/features/sessions/findings/session-findings-view.tsx apps/lingualens-app/src/features/sessions/findings/session-findings-support.tsx apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx apps/lingualens-app/src/lib/workflow.ts apps/lingualens-app/src/__tests__/session-findings-v170.test.tsx
git commit -m "feat: present auditable descriptive Findings" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 13: Benchmark model, language mode, formats, resources, and derive the runtime profile

**Files:**

- Create: `scripts/benchmark_v170_asr.py`
- Create: `apps/api/tests/test_v170_benchmark_contract.py`
- Create: `artifacts/v1.7.0/asr_benchmark_results.json`
- Create: `artifacts/v1.7.0/asr_runtime_profile.json`
- Create: `docs/benchmarks/V1_7_0_ASR_BASELINE.md`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the benchmark output schema test**

Require:

```python
assert result["fixture_manifest_checksum"]
assert result["machine"]["cpu_model"]
assert result["machine"]["logical_cpu_count"]
assert result["machine"]["memory_bytes"]
assert result["machine"]["os"]
assert result["runtime"]["python_version"]
assert result["runtime"]["faster_whisper_version"]
assert result["runtime"]["ctranslate2_version"]
assert result["runtime"]["decoder_version"]
assert result["measurements"]["elapsed_seconds"]
assert result["measurements"]["cpu_seconds"]
assert result["measurements"]["peak_rss_bytes"]
assert result["quality"]["beginning_covered"] is True
assert result["quality"]["ending_covered"] is True
assert result["quality"]["timestamp_integrity_passed"] is True
assert "segment_completeness" in result["quality"]
assert "thai_character_error_rate" in result["quality"]
assert "mixed_language_correction_operations" in result["quality"]
```

- [ ] **Step 2: Benchmark feasible models and language modes**

Run `base` and `small` for explicit Thai and automatic language detection across 1/5/15-minute Thai and Thai-English fixtures. Run `medium` beyond the one-minute preflight only when its observed peak RSS remains below 70% of physical memory and the machine completes without swapping or resource termination. Record skipped medium cases with measured preflight evidence.

Run at least three cold starts and ten warm runs for each selected 15-minute configuration. Preserve all raw measurements; do not average away failures.

- [ ] **Step 3: Measure complete quality and resource evidence**

For each run record wall time, process CPU time, peak RSS, model-load time, transcription time, media duration, real-time factor, segment count/order, beginning/end anchors, speech-region completeness, unexplained gaps, timestamp ordering/range/overlap, Thai CER, mixed-language correction operations, omissions, insertions, and therapist correction actions against the reviewed gold.

- [ ] **Step 4: Select the model and language behavior deterministically**

Read pass/fail limits from the versioned fixture manifest. A candidate is eligible only if all integrity gates pass on every required fixture and its text/correction limits pass. Among eligible candidates choose the smallest model; choose language mode by the same gate, then lower median correction operations, then lower 15-minute peak RSS, then lower elapsed time. Record every eliminated candidate and deciding metric in `V1_7_0_ASR_BASELINE.md`.

- [ ] **Step 5: Derive timeout from observations**

For the selected profile compute a bootstrap upper 99% confidence bound for the warm-run p95 end-to-end elapsed time and compare it with the maximum observed cold-run elapsed time:

```python
timeout_seconds = math.ceil(
    max(
        bootstrap_upper_99_p95(warm_elapsed_seconds),
        max(cold_elapsed_seconds),
    )
)
```

Write this value, benchmark result checksum, fixture checksum, machine class, selected model/profile checksum, calculation method, and sample counts to `asr_runtime_profile.json`. The application does not load a timeout when these checksums differ.

- [ ] **Step 6: Verify format capability evidence**

Run the decoder/normalizer matrix for WAV and MP3. Run M4A and WebM only through the exact pinned server decoder; enable each format in `supported_audio_formats_csv` only when duration, beginning/end frames, normalized checksum, and repeated conversion stability pass. Otherwise record `unavailable` and leave the UI capability disabled.

- [ ] **Step 7: Run the benchmark and contract tests**

```bash
python scripts/generate_v170_golden_audio.py \
  --manifest tests/fixtures/audio/v1.7.0/manifest.json \
  --output .local/golden-audio/v1.7.0

python scripts/benchmark_v170_asr.py \
  --manifest tests/fixtures/audio/v1.7.0/manifest.json \
  --audio-root .local/golden-audio/v1.7.0 \
  --models base small medium \
  --language-modes th auto \
  --output artifacts/v1.7.0/asr_benchmark_results.json \
  --runtime-profile artifacts/v1.7.0/asr_runtime_profile.json

cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_benchmark_contract.py -q
```

Expected: results validate, one selected profile is justified, and timeout provenance resolves to the benchmark checksum.

- [ ] **Step 8: Commit**

```bash
git add scripts/benchmark_v170_asr.py apps/api/tests/test_v170_benchmark_contract.py artifacts/v1.7.0/asr_benchmark_results.json artifacts/v1.7.0/asr_runtime_profile.json docs/benchmarks/V1_7_0_ASR_BASELINE.md requirements.txt
git commit -m "bench: select v1.7 local ASR profile" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 14: Prove the complete synthetic-audio vertical slice

**Files:**

- Create: `apps/api/tests/test_v170_vertical_slice.py`
- Create: `apps/lingualens-app/e2e/v170-audio-to-findings.spec.ts`
- Modify: `apps/lingualens-app/playwright.config.ts`
- Create: `scripts/check_v170_speech_pipeline.sh`
- Test: `apps/lingualens-app/src/__tests__/browser-audio-recorder.test.tsx`
- Test: `apps/lingualens-app/src/__tests__/experimental-transcription-service.test.ts`

- [ ] **Step 1: Write an API-level vertical-slice test using the real provider**

Mark it `pytest.mark.audio`. The test must:

1. upload a versioned synthetic fixture;
2. complete storage verification;
3. decode, enforce limits, and normalize;
4. create and run `local_faster_whisper`;
5. assert canonical unverified draft provenance;
6. submit reviewed text and timestamps;
7. map temporary speakers and confirm;
8. run QA and acknowledge only typed limitations;
9. attest exact current versions;
10. export and verify `.cha`;
11. extract deterministic features;
12. create Findings;
13. compare every expected checksum, numerator, denominator, value/status, provenance field, and limitation with the fixture manifest.

It must also assert that no mock/manual/cloud provider was called.

- [ ] **Step 2: Write failure-path vertical tests**

Use the just-over-15-minute fixture, missing model, unsupported format, partial ASR output, stale mapping, stale acknowledgment, round-trip mutation, tokenizer unavailable, and transcript edit after Findings. Each test asserts the exact stage that blocks and proves no downstream current artifact exists.

- [ ] **Step 3: Add a Playwright therapist workflow**

The browser test uploads a synthetic file, observes verification/normalization/transcription states, opens the draft, corrects text, reviews every speaker mapping segment, confirms the mapping, resolves blockers, acknowledges a safe limitation, attests, exports CHAT, runs features, and inspects Findings provenance/limitations. It also checks that duration/size/formats appear before upload and all failure messages are actionable.

- [ ] **Step 4: Protect the browser-recording follow-up**

Run the existing recorder and experimental-service unit tests. Add an assertion that the source choice remains visible with experimental/unavailable labeling, cannot unlock the v1.7.0 path, and has not been deleted. Hardcoded mock text must not be reachable from normal audio-file upload.

- [ ] **Step 5: Create one deterministic release-gate script**

`scripts/check_v170_speech_pipeline.sh` must run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_v170_config.py \
  tests/test_speech_pipeline_persistence.py \
  tests/test_audio_media_service.py \
  tests/test_audio_intake_limits.py \
  tests/test_local_faster_whisper_provider.py \
  tests/test_transcription_job_lifecycle.py \
  tests/test_asr_completeness_service.py \
  tests/test_speaker_mapping.py \
  tests/test_v170_qa_policy.py \
  tests/test_chat_subset_v170.py \
  tests/test_chat_roundtrip_v170.py \
  tests/test_v170_tokenizer.py \
  tests/test_v170_descriptive_features.py \
  tests/test_v170_findings.py -q

PYTHONPATH=. ../../.venv/bin/pytest tests/test_v170_vertical_slice.py -q -m audio

cd ../lingualens-app
npm test -- \
  src/__tests__/audio-file-upload-panel.test.tsx \
  src/__tests__/speaker-mapping-panel.test.tsx \
  src/__tests__/qa-limitations-panel.test.tsx \
  src/__tests__/session-findings-v170.test.tsx \
  src/__tests__/browser-audio-recorder.test.tsx \
  src/__tests__/experimental-transcription-service.test.ts
npx playwright test e2e/v170-audio-to-findings.spec.ts
```

The script exits nonzero on any skipped required fixture, stale checksum, missing runtime profile, or missing model artifact. Audio benchmark tests may be scheduled separately, but the selected profile and checksums must be present and valid.

- [ ] **Step 6: Run the complete vertical gate**

```bash
bash scripts/check_v170_speech_pipeline.sh
```

Expected: all required API, audio, frontend, browser-regression, and Playwright checks pass.

- [ ] **Step 7: Commit**

```bash
git add apps/api/tests/test_v170_vertical_slice.py apps/lingualens-app/e2e/v170-audio-to-findings.spec.ts apps/lingualens-app/playwright.config.ts apps/lingualens-app/src/__tests__/browser-audio-recorder.test.tsx apps/lingualens-app/src/__tests__/experimental-transcription-service.test.ts scripts/check_v170_speech_pipeline.sh
git commit -m "test: prove v1.7 audio-to-Findings slice" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 15: Update release truth, handoff evidence, and final verification

**Files:**

- Modify: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Modify: `docs/MVP_VS_EXPERIMENTAL_SCOPE.md`
- Modify: `docs/AUDIO_PIPELINE.md`
- Modify: `README.md`
- Modify: `DEVELOPER_SETUP.md`
- Modify: `CHANGELOG.md`
- Create: `docs/V1_7_0_COMPLETION_AUDIT.md`

- [ ] **Step 1: Update source-of-truth status only from passing evidence**

Record the v1.7.0 vertical slice as complete only after Task 14 passes. State that it is a local/synthetic engineering testbed, not production readiness, clinical validation, Thai norms, diagnosis, or approval for real child audio.

- [ ] **Step 2: Document operational setup**

Add exact model artifact installation/checksum verification, decoder capability check, tokenizer profile verification, fixture generation, backend/frontend startup, worker invocation, retry procedure, benchmark command, artifact locations, and troubleshooting for every structured error.

- [ ] **Step 3: Document scope exclusions**

Keep browser recording, automatic diarization quality, M4A/WebM without decoder evidence, recordings over 15 minutes/100 MB, cloud ASR, production/staging provider selection, ML/reference comparisons, norms, diagnosis, and production rollout outside v1.7.0.

- [ ] **Step 4: Build a requirement-to-evidence audit**

`V1_7_0_COMPLETION_AUDIT.md` must map every user requirement to:

- implementation files;
- test name and exact command;
- fixture/artifact checksum;
- result (`proved`, `contradicted`, `missing`);
- remaining limitation.

No row may be marked `proved` from a planned test or an indirect check.

- [ ] **Step 5: Run full repository verification**

```bash
bash scripts/check_v170_speech_pipeline.sh
bash scripts/check_project.sh
git status --short
git diff --check
```

Expected: both scripts pass, `git diff --check` is clean, no `.next/`, `dist/`, `.local/`, `node_modules/`, or `*.tsbuildinfo` is staged, and unrelated pre-existing worktree changes remain untouched.

- [ ] **Step 6: Commit release documentation**

```bash
git add docs/PROJECT_SOURCE_OF_TRUTH.md docs/MVP_VS_EXPERIMENTAL_SCOPE.md docs/AUDIO_PIPELINE.md docs/V1_7_0_COMPLETION_AUDIT.md README.md DEVELOPER_SETUP.md CHANGELOG.md
git commit -m "docs: record v1.7 speech testbed evidence" -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

## Definition of Done

v1.7.0 is complete only when all statements below are proved by current artifacts:

- [ ] A synthetic WAV or MP3 file follows the real backend upload lifecycle; the UI shows 15-minute/100 MB limits and verified formats before upload.
- [ ] The server computes actual size, decoded duration, format, source checksum, and normalization provenance before creating a transcription job.
- [ ] Exactly 900 seconds is accepted; more than 900 seconds and more than 100 MB are explicitly rejected without truncation, splitting, or partial processing.
- [ ] The original asset remains unchanged and linked to a verified mono deterministic normalized asset.
- [ ] `local_faster_whisper` produces a real canonical draft with pinned model/runtime/decoder/decoding provenance and no silent fallback.
- [ ] Selected model, language mode, format support, timeout, CPU time, memory, and completeness claims are backed by 1/5/15-minute benchmark artifacts.
- [ ] Automatic diarization can be absent without blocking draft generation; raw labels/metadata remain preserved.
- [ ] Therapist-confirmed speaker mapping is current, complete, unambiguous, auditable, and required before role-dependent downstream actions.
- [ ] Transcript QA distinguishes non-overridable integrity blockers from version-bound acknowledged limitations; generic QA override is unavailable.
- [ ] Attestation binds current audio, normalized asset, transcript, mapping, QA validator, and acknowledgment versions.
- [ ] CHAT export passes the documented v1.7.0 subset, semantic round-trip, loss detection, and deterministic re-export checksum.
- [ ] Thai and Thai-English text, Unicode, continuation lines, tiers, annotations, participants, roles, and exact generated timestamps survive the round-trip.
- [ ] Deterministic descriptive feature results expose status, formulas, numerators, denominators, sample safeguards, provenance, limitations, and cautions.
- [ ] Token metrics use only a verified pinned Thai-aware tokenizer; unavailable never becomes zero.
- [ ] Findings contain descriptive backend results only and never add ML, norms, diagnostic labels, reference ranges, or treatment recommendations.
- [ ] Every upstream version/configuration change marks affected features, Findings, and report inputs stale.
- [ ] Browser recording code remains present behind an experimental/unavailable capability and does not block this milestone.
- [ ] The full synthetic vertical-slice gate and project verification pass from a clean supported environment.

## Risks and explicit controls

| Risk | Control |
|---|---|
| Decoder claims format support it cannot reproduce | Capability registry plus fixture checksum and boundary-frame validation |
| Long fixture bloats Git | Commit short synthetic seeds and deterministic frame-exact generator; generated 5/15-minute assets stay under `.local/` |
| ASR model silently changes | Immutable model revision/artifact checksum and profile availability check |
| Provider emits partial but plausible text | Speech-region completeness, beginning/end anchors, timestamp rules, typed partial failure |
| Diarizer invents clinical roles | Neutral temporary IDs and independent therapist-reviewed mapping layer |
| Therapist bypasses structural failure | Non-overridable typed blockers; no generic override boolean |
| CHAT parser drops unfamiliar content | Opaque preservation or explicit blocking/non-blocking classification |
| Thai regex produces false word metrics | Verified tokenizer profile; structured unavailable with no fallback |
| UI invents results | Remove defaults and render only persisted backend feature/Findings contracts |
| A valid old artifact appears current | Source-version graph and repository-wide stale propagation |
| Benchmark produces a machine-specific claim | Record machine class and bind runtime profile to benchmark/checksum; staging provider remains a later decision |

## Execution checkpoints

Use one branch prefixed `codex/` or an isolated worktree created at execution time. Stop for review after Packages B, D, and F because those checkpoints freeze respectively the audio lineage, therapist safety gates, and externally visible Findings contract. Do not combine migration, benchmark artifact, and UI behavior into one commit; the task-level commits above are intended review boundaries.
