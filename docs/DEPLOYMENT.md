# Deployment Guide

This project currently maintains the therapist application path only.

The complete runtime boundary is documented in
[`docs/ARCHITECTURE_BOUNDARIES.md`](./ARCHITECTURE_BOUNDARIES.md). In
particular, the Python research layer is not deployed as a collection of
microservices, and heavy scientific work must not be placed in a Vercel or
Cloudflare edge function.

| App | Directory | Tech | Target |
|-----|-----------|------|--------|
| Therapist App | `apps/lingualens-app/` | Next.js + React + TypeScript | Vercel (standard Next.js build); Cloudflare Workers for staging |

---

## 1. Therapist / Clinician App (`apps/lingualens-app/`)

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
cd apps/lingualens-app
npm ci
npm run dev
npm test
npm run typecheck
npm run build
```

### Vercel deployment

Vercel is the simplest production target for the maintained Next.js app. No
Vercel-specific adapter, CLI, or `vercel.json` is required; use the standard
Next.js build that CI verifies.

Configure the Vercel project as follows:

| Setting | Value |
|---------|-------|
| Root Directory | `apps/lingualens-app` |
| Framework Preset | Next.js (auto-detected) |
| Install Command | `npm ci` (or Vercel's default lockfile-aware install) |
| Build Command | `npm run build` |
| Output Directory | Default (`.next`) |
| Node.js Version | `22.x` |

Set these public browser variables in the Vercel project for each environment;
the values belong in Vercel's Environment Variables UI, not in the repository:

```text
NEXT_PUBLIC_API_BASE_URL=https://<app-api-host>/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-publishable-key>
NEXT_PUBLIC_SITE_URL=https://<therapist-app-host>
```

The FastAPI API, Redis worker, private Supabase Storage credentials, and Python
analysis code remain outside Vercel. After adding a Vercel preview or
production origin, add that exact HTTPS origin to the API CORS allowlist and
the Supabase Auth redirect/allowed-site settings before testing browser auth.
The GitHub workflow validates this same standard build; it does not trigger a
Vercel deployment, so deployment previews and production promotion stay under
the Vercel project's normal Git integration.

### Cloudflare Workers deployment

The maintained frontend can deploy through OpenNext for Cloudflare:

```bash
cd apps/lingualens-app
npm ci
npm run build:cf
npm run deploy:cf
```

Current Cloudflare staging worker:

```text
https://lingualens-web.monai-yut.workers.dev
```

The Cloudflare build reads public runtime values from the deploy environment.
Set these in the Cloudflare/CI environment before running `npm run build:cf`;
do not hardcode staging or production project values in `package.json` or
`wrangler.jsonc`.

```text
NEXT_PUBLIC_API_BASE_URL=<api-base-url>/api/v1
NEXT_PUBLIC_SUPABASE_URL=<supabase-project-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-publishable-key>
```

After changing the frontend host, update the Render backend CORS origin:

```text
THERAPIST_APP_V2_CORS_ALLOWED_ORIGINS=https://lingualens-web.monai-yut.workers.dev
```

If keeping the older Render frontend active too, include both origins as a
comma-separated list.

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
LINGUALENS_REPOSITORY_MODE=sql
LINGUALENS_DATABASE_URL=postgresql+psycopg://...
LINGUALENS_JOB_QUEUE_MODE=redis
# Use a managed TLS Redis endpoint in production.
REDIS_URL=rediss://...
LINGUALENS_STORAGE_MODE=supabase_private
LINGUALENS_SUPABASE_STORAGE_URL=https://<project-ref>.supabase.co
LINGUALENS_SUPABASE_STORAGE_SERVICE_ROLE_KEY=<managed-secret>
LINGUALENS_SUPABASE_STORAGE_BUCKET=clinical-audio
LINGUALENS_REFERENCE_ARTIFACT_DIR=artifacts/reference_evidence/reference-core-14-v1
```

Legacy v2 env names remain supported temporarily for backward compatibility.

When `LINGUALENS_MOCK_MODE=false`, the API validates runtime security at
startup and rejects demo/default database URLs, localhost Redis URLs, non-SQL
repositories, local storage, and in-memory job queues. Production secrets must
come from the deployment platform's managed secret store, not from committed
files. Production must set `LINGUALENS_SECRET_STORE_PROVIDER` to an
approved managed secret store and `LINGUALENS_CREDENTIAL_ROTATION_RUNBOOK`
to the active rotation runbook.

Production authentication, provider credentials, retention, storage, and audit
settings remain deployment-specific and must stay server-side.

Operational requirements:
- Terminate TLS at the edge and enforce HTTPS redirects.
- Keep private storage keys server-side; browsers receive only short-lived signed URLs.
- Run database backups daily and test restore before pilot launch.
- Run `PYTHONPATH=apps/api:src python scripts/check_api_migrations.py` before
  promotion and follow `docs/BACKUP_RESTORE_RUNBOOK.md` for restore drills.
- Retain audit logs according to clinic policy; privacy deletion requests must not silently erase audit evidence.
- Route incidents through `docs/SECURITY.md` and
  `docs/INCIDENT_RESPONSE_RUNBOOK.md`; rollback through
  `docs/RELEASE_CHECKLIST.md`.

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
