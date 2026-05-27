# Speech Therapist / Clinician App Phase 2

Phase 2 extends the standalone Speech Therapist / Clinician App from mock
login and dashboard scaffolding into case and session management. It remains
`MOCK_MODE=True`; no real authentication provider, database, file storage, or
audio pipeline execution is connected.

## Scope

Phase 2 adds:

- editable anonymized child case context
- consent and anonymization status review in case and session views
- session creation for owned child cases
- case-level session timeline
- therapist notes linked to a child case or session
- mock audit events for case updates, session creation, and note creation

Therapist and clinician users can only manage cases they own. Admin users keep
cross-case visibility for testing and demonstration.

## Case Management

Clinical users can update age, sex, external clinical status, consent status,
anonymization status, primary concerns, and internal case notes. Child cases
must continue to use anonymized codes rather than real names or identifiers.

`external_clinical_status` remains therapist-entered context from outside the
system. It is not an AI output and must not be treated as a diagnosis.

## Session Management

Clinical users can create mock sessions for owned child cases. Sessions include
session date, session type, review status, report status, and context notes.
Phase 2 does not store real uploaded files. Audio/video upload and file metadata
workflow remains Phase 3.

## Therapist Notes

Therapist notes can be attached to a child case or linked to a specific session.
Notes are for professional context and review continuity. In mock mode, they
must not include real child identifiers.

## Safety Boundary

The persistent disclaimer remains:

> This system is a clinical decision-support prototype. It does not diagnose
> ASD and does not replace qualified clinical judgment.

Any screening support score, feature summary, session timeline, or note must be
interpreted by a qualified therapist or clinician.
