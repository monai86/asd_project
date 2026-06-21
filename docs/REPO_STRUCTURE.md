# Repository Structure

Use [`PROJECT_SOURCE_OF_TRUTH.md`](./PROJECT_SOURCE_OF_TRUTH.md) as the
authoritative runtime boundary. This file is the quick structural map for the
current repository layout.

## Active product surfaces

- `apps/therapist-app-v2/` — canonical therapist frontend (Next.js)
- `apps/api/` — canonical therapist workflow API (FastAPI)

## Shared and research libraries

- `shared/` — shared frontend-safe JavaScript models/services used by the Vite
  surfaces
- `packages/cha/` — CHAT parser
- `packages/features/` — canonical transcript feature extraction
- `packages/ml/` — reference-evidence ML contracts, artifacts, and inference
- `src/audio_pipeline/` — experimental audio-to-CHAT pipeline
- `src/clinical_speech/` — normalization and clinical speech utilities
- `src/` top-level scripts — active research entrypoints that remain outside
  the maintained product runtime

## Legacy compatibility surfaces

- `src/therapist_backend/` — legacy pilot API retained for research tests
- `src/clinical_workflow/` — legacy repository/domain layer retained for
  compatibility

Do not add new product behavior to these legacy paths.

## Removed non-current surfaces

- `public-screening/` — removed educational demo
- `presentation-dashboard/` — removed advisor/demo dashboard
- `src/classifier.py`, `src/deep_learning.py` — removed legacy benchmark pipelines

## Data and artifacts

- `data/` — corpora, curated/reference data, evaluation inputs, and local demo
  uploads
- `artifacts/` — promoted or candidate model/reference artifacts
- `reports/` — generated figures, metrics, and progress-report outputs

## Documentation and operations

- `docs/` — maintained product, architecture, safety, and research docs
- `scripts/` — verification, artifact generation, and reproducible research
  helpers
- `tests/` — research/runtime regression tests
- `apps/api/tests/` — API-focused tests for the active therapist backend

## Generated and local-only files

These may exist locally but are not source:

- `.next/`
- `dist/`
- `.local/`
- `node_modules/`
- `__pycache__/`
- `.pytest_cache/`
- `*.tsbuildinfo`
