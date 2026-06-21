# Deployment Guide

This project currently maintains the therapist application path only.

| App | Directory | Tech | Target |
|-----|-----------|------|--------|
| Therapist App | `apps/therapist-app-v2/` | Next.js + React + TypeScript | Vercel or Node hosting |

---

## 1. Therapist / Clinician App (`apps/therapist-app-v2/`)

A clinical decision-support prototype for speech therapists and clinicians.
This is the only active therapist frontend. It uses the local FastAPI workflow
boundary in `apps/api/` and keeps browser recordings memory-only until explicit
upload.

### Mock accounts

| Role | Email | Password |
|------|-------|----------|
| Therapist | `therapist@example.test` | `demo-password` |
| Clinician | `clinician@example.test` | `demo-password` |
| Admin | `admin@example.test` | `demo-password` |

### Local development

```bash
cd apps/therapist-app-v2
npm ci
npm run dev
npm test
npm run typecheck
npm run build
```

### Production readiness controls

Do not deploy the therapist-clinician app with real clinical data until these
runtime boundaries are configured and verified:

| Boundary | Required production setting |
|----------|-----------------------------|
| Auth | Provider-backed auth, role claims, session expiry, no mock sample accounts |
| API | HTTPS-only FastAPI deployment with authenticated requests and case-owner checks |
| Database | Postgres/Supabase schema from `docs/sql/`, RLS reviewed, backups enabled |
| Storage | Private encrypted bucket, signed upload/download URLs, retention policy |
| Processing | Backend worker queue for audio pipeline; no browser-side PHI processing |
| Monitoring | API error rate, worker failures, storage failures, auth failures, queue latency |
| Logs | Structured logs without transcript/audio content or child identifiers |
| Privacy | Export, consent withdrawal, and deletion requests routed to admin review |

Canonical API environment variables:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.example.org/api/v1
THERAPIST_APP_V2_REPOSITORY_MODE=sql
THERAPIST_APP_V2_DATABASE_URL=postgresql+psycopg://...
THERAPIST_APP_V2_JOB_QUEUE_MODE=redis
REDIS_URL=redis://...
THERAPIST_APP_V2_STORAGE_MODE=private
THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR=artifacts/reference_evidence/current
```

Production authentication, provider credentials, retention, storage, and audit
settings remain deployment-specific and must stay server-side.

Operational requirements:
- Terminate TLS at the edge and enforce HTTPS redirects.
- Keep private storage keys server-side; browsers receive only short-lived signed URLs.
- Run database backups daily and test restore before pilot launch.
- Retain audit logs according to clinic policy; privacy deletion requests must not silently erase audit evidence.
- Route incidents through `docs/SECURITY.md` and rollback through `docs/RELEASE_CHECKLIST.md`.

## Deploying to Cloudflare Pages (General Steps)

1. Log in to the **Cloudflare Dashboard** → **Workers & Pages**.
2. Click **Create Application** → **Pages** → **Connect to Git**.
3. Select your repository.
4. Set the build settings shown for the respective app above.
5. Click **Save and Deploy**.

Future pushes to the `main` branch will trigger automatic redeployments.

---

## Python ML Backend (`packages/` + `src/`)

The Python ML source code is research and reference code for the term paper.
It is **not deployed**. The maintained ML workflow is the reference-evidence
pipeline in `packages/ml/`, with supporting feature/audio code under `src/`.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Key commands

```bash
# Build or refresh reference-evidence artifacts
python -m packages.ml.train_model --features-csv data/combined_features.csv

# Run all tests
pytest tests/
```

### Generated artifacts (committed to repo)

| File | Description |
|------|-------------|
| `data/combined_features.csv` | 122-child cross-corpus feature dataset |
| `data/longitudinal_features.csv` | Longitudinal session features |
| `reports/metrics/reference_cohort_classification_results.csv` | Current reference-cohort evaluation metrics |
| `reports/metrics/calibration_report.json` | Current reference-cohort calibration output |
| `artifacts/screening_model.joblib` | Current runtime model bundle |
| `artifacts/model_card.json` | Model card with caveats |
| `artifacts/feature_schema.json` | 14-feature schema definition |
