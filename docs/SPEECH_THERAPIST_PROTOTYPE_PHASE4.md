# Speech Therapist / Clinician App Phase 4

Phase 4 adds CHAT transcript workflow support to the standalone Speech
Therapist / Clinician App. It remains `MOCK_MODE=True`; transcripts can be
uploaded or mock-generated for review, but real audio-to-CHAT execution is
deferred until real file storage exists.

## Scope

Phase 4 adds:

- `.cha` transcript upload/selection
- mock CHAT transcript generation from audio file metadata
- transcript viewer and correction UI
- transcript QA results using the existing transcript reviewer
- transcript review status updates
- mock feature extraction rerun status after transcript review
- audit events for transcript upload, transcript edit, transcript review, and
  feature rerun

## Transcript QA

The workflow uses the existing rule-based CHAT transcript reviewer. It checks
for required CHAT structure, child speaker tiers, language tag issues,
low-confidence metadata, and likely speaker-label problems. QA results are
decision support for human review; they do not approve a transcript by
themselves.

## Audio-to-CHAT Boundary

Phase 4 does not run Whisper, diarization, or the real audio pipeline because
Phase 3 stores only file metadata. The UI can generate a mock CHAT transcript
from audio metadata to demonstrate the workflow, but this mock transcript is
not derived from real audio content.

## Review Flow

Clinical users can correct transcript text, add interpretation notes, mark the
transcript reviewed, and trigger mock feature extraction status. Feature values
and AI decision-support outputs remain Phase 5.

## Safety Boundary

The persistent disclaimer remains:

> This system is a clinical decision-support prototype. It does not diagnose
> ASD and does not replace qualified clinical judgment.
