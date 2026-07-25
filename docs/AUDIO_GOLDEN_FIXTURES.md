# LinguaLens v1.7.0 Synthetic Audio Golden Fixture Contract

Status: fixture and benchmark specification for `v1.7.0-testbed`. The assets,
generator, decoder evidence, and benchmark artifacts described here are future
gates; this document does not claim they already exist or that the real ASR and
storage-normalization pipeline is complete.

## Privacy and content

All audio is synthetic. Scripts use neutral, non-identifying Thai and
Thai-English test phrases plus explicit beginning/end markers. They contain no
real child speech, names, dates of birth, case/session IDs, contact details,
storage keys, copied clinical transcripts, or other direct identifiers.

Committed short seeds record synthetic voice/tool, voice identifier, generation
date, license, source script and checksum, language, PCM properties, exact frame
count/duration, SHA-256, and human confirmation that speech matches the checked
script. Fixtures use immutable versioned filenames.

Required semantic cases are Thai-only, Thai-English code switching, correct two
speakers, swapped clusters, unknown speaker, more than two speakers,
diarization unavailable, and overlapping speech. The first and final spoken
items are unique synthetic `BEGIN_V170` and `END_V170` semantic markers (spoken
in the fixture language, with marker IDs in expected metadata) so truncation is
measurable.

## Duration and size classes

The frame-exact classes are:

| Case | Decoded duration | Expected gate |
|---|---:|---|
| `thai_1m` | 60,000 ms | accepted |
| `thai_english_5m` | 300,000 ms | accepted |
| `thai_english_15m` | 900,000 ms | accepted at the limit |
| `thai_english_15m_plus_5s` | 905,000 ms | rejected before ASR |

Every upload is also subject to a 100 MiB (`104857600` byte) encoded-file
limit. The manifest includes cases at and just above this boundary without
committing oversized blobs. A file that exceeds either the byte limit or 900
decoded seconds is rejected before job creation. There is no 250 MB or
60-minute compatibility class.

Only short seed WAV files and a short MP3 format fixture are committed. Longer
assets are assembled under `.local/golden-audio/v1.7.0/` and are never committed.

## Format evidence matrix

WAV and MP3 are the initial required decoder/normalizer baseline. Each must
pass the exact pinned server decoder for decoded duration, sample count,
beginning/end frame presence, deterministic mono 16 kHz PCM signed-16-bit WAV
normalization, and repeated normalized SHA-256 equality.

M4A and WebM remain `unavailable`, and v1.7.0 configuration rejects them, until
each has a committed short decode fixture and the same evidence under the exact
server decoder/version. Browser claims, extension, MIME type, local media-player
playback, or transitive dependencies are not evidence. Enabling a conditional
format requires a reviewed code/contract allowlist change together with the
fixture manifest, decoder version/checksum evidence, capability tests, and
`LINGUALENS_SUPPORTED_AUDIO_FORMATS_CSV`.

## Manifest and deterministic assembly

`tests/fixtures/audio/v1.7.0/manifest.json` is the source of truth. It records
manifest/schema versions; generator script checksum; every source and generated
checksum; seed/format encoder and decoder provenance; expected frames,
durations, and size class; assembly order; silence frame counts; source
transcript/timing; and artifact/profile versions.

`scripts/generate_v170_golden_audio.py` uses Python `wave` frame reads/writes
for deterministic PCM concatenation and silence insertion. It must not use a
platform player. It verifies frame counts and checksums and refuses to overwrite
an unexpected existing output unless `--rebuild` is explicit.

```bash
python scripts/generate_v170_golden_audio.py \
  --manifest tests/fixtures/audio/v1.7.0/manifest.json \
  --output .local/golden-audio/v1.7.0
```

Regeneration starts from the committed seeds and pinned tool versions. The
command writes generated hashes back only through an explicit reviewed manifest
update; it never silently rewrites raw or gold inputs.

## Expected artifacts

Each `tests/fixtures/audio/v1.7.0/expected/<case>.json` records:

- reviewed source transcript and exact beginning/end markers;
- expected temporary speaker labels, segment order, speech regions, and
  accepted ASR-evaluation timestamp bounds;
- reviewed speaker mapping and ambiguity/diarization outcome;
- expected coverage, unexplained gaps, omissions, insertions, and limitations;
- canonical CHAT semantic fields and checksum;
- tokenizer profile/checksum and expected tokens; and
- feature statuses, numerators, denominators, values, exclusions, and
  provenance versions.

Expected text is gold input, never copied into provider output. Timing
tolerances are for comparing ASR to reviewed gold; generated CHAT timestamps
still require exact millisecond round-trip equality.

## Benchmark protocol

Benchmark feasible local models and explicit-Thai versus automatic language
mode on required 1-, 5-, and 15-minute Thai and Thai-English cases. Each
selected 15-minute configuration runs at least three cold starts and ten warm
runs. Raw failures and skipped cases are retained. A larger model advances past
a one-minute preflight only when peak RSS is below 70% of physical memory and
the machine neither swaps nor terminates it.

Every run records:

- fixture/manifest and model/profile checksums;
- CPU model, logical CPU count, physical memory, OS/architecture;
- Python, faster-whisper, CTranslate2, decoder/normalizer, and dependency
  versions;
- wall elapsed time, process CPU time, peak RSS, model-load and transcription
  times, media duration, and real-time factor;
- segment count/order, beginning/end coverage, speech-region and segment
  completeness;
- timestamp order, bounds, overlap, coverage, and unexplained gaps; and
- Thai character error rate, mixed-language correction operations, omissions,
  insertions, and therapist correction actions.

Model selection is evidence-driven. A candidate must pass integrity,
completeness, timestamp, and manifest quality limits for every required
fixture. Among eligible candidates choose the smallest model; choose language
mode by the same gate, then fewer median correction operations, lower
15-minute peak RSS, and lower elapsed time. The baseline report lists every
rejected/skipped candidate and the deciding measurement.

Timeout is derived, never guessed:

```text
ceil(max(bootstrap upper 99% bound of warm-run p95 elapsed,
         maximum observed cold-run elapsed))
```

The runtime profile records the result checksum, fixture checksum, machine
class, selected model/profile checksum, method, and sample counts. Missing or
mismatched evidence makes the local provider unavailable and fails explicitly;
there is no provider/model/decoder fallback.

```bash
python scripts/benchmark_v170_asr.py \
  --manifest tests/fixtures/audio/v1.7.0/manifest.json \
  --audio-root .local/golden-audio/v1.7.0 \
  --output artifacts/v1.7.0/asr_benchmark_results.json

PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python \
  -m pytest apps/api/tests/test_v170_audio_fixture_manifest.py \
  apps/api/tests/test_v170_benchmark_contract.py -q
```

Benchmark results are local machine-class evidence for a synthetic testbed, not
production SLOs, transcription accuracy claims for children, diagnosis, norms,
or Thai clinical validation.
