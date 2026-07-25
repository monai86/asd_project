# LinguaLens Descriptive Feature Contract v1.7.0

Status: frozen engineering contract for
`descriptive-features-v1.7.0`. It specifies deterministic descriptive output;
it is not a normative, diagnostic, ML, or clinical-validation specification.

## Input eligibility

Extraction requires all of the following to be current and mutually linked:

- therapist-reviewed transcript and exact transcript/content/boundary version;
- confirmed speaker-to-role mapping and mapping version;
- successful `speech-qa-v1.7.0` state with required limitations acknowledged;
- current attestation and successful CHAT candidate round-trip under
  `lingualens-chat-v1.7.0`;
- verified source/normalized audio versions for timing features;
- the exact feature algorithm/configuration version; and
- for token features only, a verified tokenizer profile and checksum.

Ineligible extraction fails explicitly. No browser, regex, whitespace, English,
alternate tokenizer, prior result, or zero-valued fallback is permitted.
Non-token metrics remain independently available when their own inputs pass.

## Result shape and statuses

Every metric records feature ID and schema version, value and unit, status,
numerator, denominator, minimum sample, excluded item counts/reasons, required
inputs, transcript/mapping/source-audio/normalized-audio versions, tokenizer
profile/checksum when applicable, algorithm/configuration version, generation
time, data-quality notes, limitations, and clinical caution.

The only statuses are:

- `available`: formula ran from eligible current inputs;
- `unavailable`: a required capability/input is absent;
- `insufficient_data`: inputs exist but the stated engineering minimum is not
  met;
- `experimental`: a non-core heuristic is shown with evidence and limitations;
- `stale`: an input or algorithm version changed after generation;
- `failed`: execution or integrity checking failed.

Only `available` has a numeric value for the required bundle.
`unavailable`, `insufficient_data`, `stale`, and `failed` have `value: null`,
a reason code, and remediation. `experimental` is visually and structurally
separate and never promoted into descriptive Findings.

## Shared counting rules

Canonical utterance order is the reviewed CHAT order. Confirmed role—not an ASR
cluster label—determines target child, therapist, and other speakers. A
reviewed utterance is eligible for role counts unless deleted or marked
non-utterance by review. Interval union merges overlapping or adjacent
half-open intervals `[start_ms, end_ms)` so overlap is counted once.

An utterance is intelligibility-eligible when the therapist assigned exactly
one of `intelligible`, `partly_intelligible`, or `unintelligible`. ASR
confidence is never used. Counts and ratios report explicit exclusions for
missing/ambiguous review, non-speech-only events, and invalid boundaries.

## Required non-token features

| Feature | Exact value/formula | Numerator / denominator and safeguards |
|---|---|---|
| `child_utterance_count` | Count reviewed utterances mapped to target child | numerator = included child utterances; denominator = all reviewed utterances; no minimum |
| `therapist_utterance_count` | Count reviewed utterances mapped to therapist | numerator = included therapist utterances; denominator = all reviewed utterances; no minimum |
| `total_utterance_count` | Count all eligible reviewed utterances | numerator = included utterances; denominator = reviewed utterances examined; no minimum |
| `turn_count` | Count contiguous speaker-role runs in canonical utterance order | numerator = role-run starts; denominator = eligible reviewed utterances; unavailable when mapping is not confirmed |
| `audio_duration` | Verified normalized asset `duration_ms` | numerator = `duration_ms`; denominator = 1000 for value in seconds; duration must be positive |
| `timestamp_coverage` | `duration(union(valid reviewed utterance intervals)) / verified audio duration` | numerator/denominator in ms; invalid/out-of-range intervals excluded and reported; unavailable without verified duration |
| `unexplained_gap_coverage` | `duration(union(detected-speech intervals) minus union(valid reviewed intervals)) / verified audio duration` | numerator/denominator in ms; unavailable without version-matched detected-speech evidence; overlap counted once |
| `intelligible_utterance_count` | Count eligible utterances reviewed `intelligible` | numerator = category count; denominator = all intelligibility-eligible reviewed utterances |
| `partly_intelligible_utterance_count` | Count eligible utterances reviewed `partly_intelligible` | same denominator/exclusions |
| `unintelligible_utterance_count` | Count eligible utterances reviewed `unintelligible` | same denominator/exclusions |
| `intelligible_utterance_ratio` | intelligible count / intelligibility-eligible count | denominator must be greater than zero or status is `insufficient_data` |
| `partly_intelligible_utterance_ratio` | partly-intelligible count / intelligibility-eligible count | denominator must be greater than zero or status is `insufficient_data` |
| `unintelligible_utterance_ratio` | unintelligible count / intelligibility-eligible count | denominator must be greater than zero or status is `insufficient_data` |

Ratios are in `[0,1]`. Counts never substitute for missing ratios. A zero is
valid only when the denominator is eligible and positive.

## Token eligibility and required token features

Token metrics use target-child utterances only. Eligible tokens are NFC
normalized output from the pinned profile after applying its explicit rules.
Punctuation-only items, pause markers, media bullets, dependent-tier text,
filled pauses, repetitions excluded by the profile, partial words excluded by
the profile, unintelligibility markers, and non-speech events do not count.
Code-switched tokens are included or excluded exactly as the profile declares.
An eligible complete utterance must be child-role, intelligible or partly
intelligible, and not marked abandoned/incomplete by therapist review.

| Feature | Exact value/formula | Minimum |
|---|---|---|
| `target_token_count` | Count eligible target-child tokens after profile exclusions | no minimum; zero is available only with a verified profile and eligible input |
| `number_different_words` (`NDW`) | Count unique profile-normalized eligible target-child token strings | no minimum beyond verified tokenization |
| `type_token_ratio` (`TTR`) | `NDW / target_token_count` | at least 50 eligible target tokens; otherwise `insufficient_data` |
| `mean_length_of_utterance_words` (`MLU-word`) | eligible target-child tokens in eligible complete utterances / eligible complete target-child utterances | at least 50 complete intelligible or partly intelligible target-child utterances; otherwise `insufficient_data` |

Each ratio stores the exact numerator and denominator used. The 50-token and
50-utterance rules are engineering stability safeguards shown alongside the
result; they are not developmental or clinical thresholds.

## Thai-aware tokenizer profile

`artifacts/v1.7.0/tokenizer_profile.json` is immutable and must contain:

- engine, exact package version, and segmentation mode;
- dictionary/model/artifact identifier and SHA-256;
- Unicode NFC behavior;
- punctuation, whitespace, filled-pause, repetition, partial-word,
  unintelligibility-marker, and Thai-English code-switch rules;
- custom vocabulary version and checksum;
- golden fixture manifest checksum; and
- profile checksum over the canonical profile.

Runtime rejects package, artifact, fixture, or profile checksum mismatch. When
the profile is unavailable, every token feature returns `unavailable`,
`value: null`, reason `TOKENIZER_PROFILE_UNAVAILABLE`, and remediation to
install and verify the recorded profile. Non-token metrics are not downgraded
solely because tokenization is unavailable.

## Staleness and provenance

Transcript text, utterance inclusion, boundary/timestamp, intelligibility
review, speaker mapping, source or normalized audio, detected-speech evidence,
attestation, QA rule, CHAT parser/serializer/subset, tokenizer profile/custom
vocabulary, feature formula, or configuration version changes mark affected
results `stale`. Downstream Findings and report inputs become stale too.
History remains readable but cannot be treated as current.

Provenance includes all input record IDs and versions, canonical CHAT/export
checksums, audio normalization profile/checksum, tokenizer profile/checksum,
feature schema/algorithm/configuration versions, numerator/denominator and
exclusion ledger, limitation acknowledgments, generation service identity, and
UTC generation timestamp.

## Findings and experimental cues

Findings may restate only current `available` descriptive metrics. Each card
shows value/status, unit, formula, sample size, numerator/denominator,
exclusions, source versions, profile/algorithm versions, data-quality notes,
limitations, and clinical caution. Missing data stays `unavailable`;
insufficient data stays `insufficient_data`; stale/failed data blocks current
Findings and downstream report actions. Findings never invent a summary,
threshold, interpretation, recommendation, or fallback value.

Pronoun-reversal, echolalia, repetitive-phrase, reciprocal-question, and similar
heuristics are outside the required bundle. If exposed, they are
`experimental`, carry supporting utterance IDs and limitations, never block
the deterministic bundle, and are not promoted to Findings.

The v1.7.0 path prohibits reference-range comparisons, cohort comparisons,
normal/abnormal labels, norms, probabilities, predicted classes, concern
scores, diagnosis, treatment recommendations, ML inference, and
reference-evidence comparison. It remains a research/education prototype and
does not establish Thai clinical validation.
