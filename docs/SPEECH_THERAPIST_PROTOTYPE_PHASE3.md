# Speech Therapist / Clinician App Phase 3

Phase 3 adds metadata-only audio/video upload support to the standalone Speech
Therapist / Clinician App. It remains `MOCK_MODE=True`; selected files are
validated in the UI and represented as metadata records, but file bytes are not
persisted and the real audio pipeline is not executed.

## Scope

Phase 3 adds:

- allowed file type validation for `wav`, `mp3`, `m4a`, `mp4`, and `mov`
- maximum file size validation at 250 MB
- mock `audio_file` metadata records linked to owner, child case, and session
- secure stored filenames based on case/session/audio IDs only
- processing status display for mock upload records
- audit events for metadata-only file upload records

## Metadata-Only Boundary

Audio file metadata records may include original filename, stored filename,
file type, file size, upload time, owner user ID, case ID, session ID, and
processing status. They do not contain the uploaded file content.

The stored filename must use IDs rather than child names or direct identifiers.
For example:

```text
CASE-001_SESSION-004_AUDIO-002.wav
```

## Ownership

Therapist and clinician users can attach file metadata only to sessions that
belong to their owned child cases. Admin users can view all mock metadata for
testing and demonstration.

## Deferred Work

Phase 3 does not add browser preview, local persistence, real file storage,
ASR, diarization, CHAT generation, transcript QA, feature extraction, or report
generation. Those remain later phases.

## Safety Boundary

The persistent disclaimer remains:

> This system is a clinical decision-support prototype. It does not diagnose
> ASD and does not replace qualified clinical judgment.
