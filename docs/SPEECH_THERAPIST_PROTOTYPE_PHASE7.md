# Speech Therapist / Clinician Product Phase 7

Phase 7 follows `deep-research-report.md`: canonical feature extraction, AI
decision-support contract, progress monitoring, and report generation. The
older mock-hardening checklist remains useful as historical coverage, but the
active Phase 7 product direction is to separate the fixed core feature set from
optional indicators and make backend/report contracts traceable.

## Active Phase 7 Contract

- The **Core Feature Set** remains the fixed 14-feature schema.
- **Optional Indicators** are stored separately and may include
  `turn_taking_count`, `response_latency_avg`, `pause_ratio`,
  `therapist_utterances`, `caregiver_utterances`, and
  `restricted_interest_words`.
- AI decision-support outputs include `model_version`,
  nullable `confidence_interval`, `top_contributing_features`,
  structured `evidence_items`, and plain-language not-a-diagnosis wording.
- Progress views can be derived from repository/backend snapshots, not only
  ephemeral UI state.
- Markdown progress reports must render structured evidence and safety wording
  reliably.

## Phase Completion / MD Checklist

Phase coverage: Phase 1 auth/ownership, Phase 2 case/session management,
Phase 3 upload metadata, Phase 4 transcript review, Phase 5 feature and AI
support, Phase 6 progress/report generation, and Phase 7 final hardening.

| MD area | Status | Notes |
|---|---|---|
| 1. Authentication and user accounts | Complete in mock mode | Therapist, clinician, and admin demo accounts are present. |
| 2. Case ownership and data separation | Complete in mock mode | Therapist/clinician users see owned cases only; admin can see all. |
| 3. Database-ready data model | Complete as typed shells | Models cover users, cases, sessions, transcripts, audio metadata, features, AI outputs, goals, notes, reports, and audit logs. |
| 4. Audio upload and processing workflow | Mock boundary complete | New Session creates metadata and shows processing status; real processing is deferred. |
| 5. File storage design | Metadata-only complete | Stored filenames use IDs and no child names; no file bytes are stored. |
| 6. Transcript review and correction | Mock transcript workflow complete | `.cha` upload/selection, QA, correction, review, and rerun status are present. |
| 7. Therapist dashboard after login | Hardened in Phase 7 | Dashboard now includes metrics, recent cases/sessions, high review-priority cases, and quick actions. |
| 8. Case detail page | Hardened in Phase 7 | Case detail shows profile, timeline, trends, AI history, goals, notes, generated reports, uploads, and transcript status. |
| 9. Session detail page | Hardened in Phase 7 | Session view shows metadata, transcript QA, feature summary, AI output, notes, and report action. |
| 10. Privacy and safety | Complete for mock mode | Persistent disclaimer, anonymized IDs, consent/anonymization status, and audit events are covered. |
| 11. Mock mode vs real mode | Complete for prototype | UI and docs state no real auth, database, file storage, localStorage persistence, or real audio pipeline. |
| 12. Integration with existing project | Complete for mock phase | Reuses transcript reviewer, feature schema, and therapist report metric direction/safe wording. |
| 13. Tests and documentation | Complete for Phase 7 | Contract tests, workflow tests, and phase docs cover the implemented boundary. |

## Deferred by Design

- Real authentication and database persistence.
- Real file storage and audio/video playback.
- Real audio-to-CHAT execution through `audio_pipeline`.
- Clinical validation or Thai validation claims.

These are intentionally out of scope because the current prototype does not
store real clinical records or uploaded media.

## Safety Checks

- The app must keep the persistent clinical decision-support disclaimer visible.
- Reports and AI outputs must avoid diagnostic language such as “diagnosed with”.
- Mock upload wording must state that no file bytes are persisted.
- The app must not use `localStorage` persistence in this mock clinical flow.
- Pastel dashboard files remain untouched by this phase.

## Verification

```bash
python -m pytest tests/test_clinical_workflow.py tests/test_therapist_clinician_app.py tests/test_therapist_report.py -q
python -m py_compile src/clinical_workflow/models.py src/clinical_workflow/mock_repository.py
node --check therapist-clinician-app/src/app.js
git diff -- app/dashboard_unified.py
```
