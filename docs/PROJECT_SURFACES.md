# Project Surfaces

The canonical architecture is defined in
[`PROJECT_SOURCE_OF_TRUTH.md`](./PROJECT_SOURCE_OF_TRUTH.md).

## Active user-facing surfaces

### Therapist App v2

- Frontend: `apps/therapist-app-v2/`
- API: `apps/api/`
- Technology: Next.js/React/TypeScript + FastAPI
- Audience: therapists and qualified reviewers
- Purpose: case/session workflow, transcript QA and attestation, descriptive
  features, evidence review, goals, and reviewed reports
- Persistence: backend JSON by default; memory for tests; SQL scaffold optional
- Boundary: backend is authoritative when workflow IDs exist; ML evidence does
  not produce a diagnostic conclusion or enter reports automatically

## Active research/tooling surfaces

- `packages/cha/`: CHAT parser
- `packages/features/`: canonical feature extraction
- `packages/ml/`: training, contracts, Gate 1, and reference artifacts
- `src/audio_pipeline/`: experimental audio-to-CHAT
- `src/clinical_speech/`: clinical speech normalization and feature utilities
- `scripts/`: reproducible research and artifact generation

## Legacy compatibility surfaces

- `src/therapist_backend/`: earlier FastAPI pilot contract retained for
  research tests
- `src/clinical_workflow/`: earlier clinical workflow repository/domain layer
- historical phase/spec/plan documents under `docs/`
- `public-screening/`: retained demo surface, not current-maintained
- `presentation-dashboard/`: retained demo surface, not current-maintained

Do not add new Therapist App v2 product behavior to legacy surfaces.

## Retired surfaces

- `therapist-clinician-app/`: former Vite/Capacitor therapist application,
  removed from Git
- old Streamlit/project-atlas presentation paths referenced by historical docs

Generated local copies of retired surfaces are not source and may be deleted.
