# Audio Pipeline QA Checklist

## CHAT Validity

- Required headers exist: participant metadata, age, sex, group when available.
- Utterance tiers use valid participant codes.
- Empty or failed ASR output is handled explicitly.
- Generated `.cha` can be parsed by `pylangacq`.

## Diarization

- Backend choice is shown or logged.
- Missing `HF_TOKEN` falls back gracefully when pyannote is unavailable.
- Speaker assignment uncertainty is visible to the user.
- Child-only feature extraction does not accidentally include adult tiers.

## ASR and Features

- Segment timestamps remain ordered.
- Non-speech events and unintelligible tokens are handled consistently.
- Feature columns match the classifier input schema.
- Audio-derived predictions include caveats about ASR and diarization noise.

## Tests

- Add a round-trip formatter test for any CHAT format change.
- Add a dashboard smoke check for upload UI changes.
- Add a fixture or mock for external ASR/diarization when network/model downloads are impractical.
