# Deployment Guide

This project has **three web applications**, all deployed as static sites on Cloudflare Pages.

| App | Directory | Tech | Target |
|-----|-----------|------|--------|
| Public Screening Support | `public-screening/` | Vite + HTML/JS | Cloudflare Pages |
| Therapist / Clinician App | `therapist-clinician-app/` | Vite + ESM JavaScript | Cloudflare Pages |
| Presentation Dashboard | `presentation-dashboard/` | Vite + React/TS | Cloudflare Pages |

---

## 1. Public Screening Support App (`public-screening/`)

A bilingual (Thai/English) parent-facing educational screening support tool.  
Zero data retention — all state lives in `sessionStorage` only.

### Cloudflare Pages settings

| Setting | Value |
|---------|-------|
| Framework preset | Vite (or None) |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `public-screening` |

### Local development

```bash
cd public-screening
npm install
npm run dev        # http://localhost:3000
npm run build      # compiles to dist/
npm run preview    # preview production build locally
```

---

## 2. Therapist / Clinician App (`therapist-clinician-app/`)

A clinical decision-support prototype for speech therapists and clinicians.
The current frontend is a Vite + ESM JavaScript app. Mock mode remains the
default, while the full-product path connects it to Supabase Auth, Postgres
RLS, Storage, and a FastAPI/Python processing backend.

### Mock accounts

| Role | Email | Password |
|------|-------|----------|
| Therapist | `therapist@example.test` | `demo-password` |
| Clinician | `clinician@example.test` | `demo-password` |
| Admin | `admin@example.test` | `demo-password` |

### Cloudflare Pages settings

| Setting | Value |
|---------|-------|
| Framework preset | Vite (or None) |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `therapist-clinician-app` |

### Local development

```bash
cd therapist-clinician-app
npm install
npm run dev        # open the Vite URL shown in terminal
npm run build      # compiles to dist/
npm run test:e2e:smoke
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

Recommended environment variables:

```bash
AUTH_MODE=supabase
DATA_MODE=api
PROCESSING_MODE=backend
FILE_STORAGE_MODE=secure_backend
THERAPIST_API_BASE_URL=https://api.example.org
SUPABASE_URL=https://example.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...   # backend only, never exposed to browser
PRIVATE_AUDIO_BUCKET=clinical-audio
LOG_RETENTION_DAYS=90
BACKUP_RETENTION_DAYS=30
```

Operational requirements:
- Terminate TLS at the edge and enforce HTTPS redirects.
- Keep private storage keys server-side; browsers receive only short-lived signed URLs.
- Run database backups daily and test restore before pilot launch.
- Retain audit logs according to clinic policy; privacy deletion requests must not silently erase audit evidence.
- Route incidents through `docs/SECURITY.md` and rollback through `docs/RELEASE_CHECKLIST.md`.

---

## 3. Presentation Dashboard (`presentation-dashboard/`)

A data visualization dashboard for advisor presentations and project demos.  
Displays model performance, dataset stats, feature importance, and LOCO validation results.

### Cloudflare Pages settings

| Setting | Value |
|---------|-------|
| Framework preset | Vite (or None) |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `presentation-dashboard` |

### Local development

```bash
cd presentation-dashboard
npm install
npm run dev        # open the Vite URL shown in terminal
npm run build      # compiles to dist/
```

---

## Deploying to Cloudflare Pages (General Steps)

1. Log in to the **Cloudflare Dashboard** → **Workers & Pages**.
2. Click **Create Application** → **Pages** → **Connect to Git**.
3. Select your repository.
4. Set the build settings shown for the respective app above.
5. Click **Save and Deploy**.

Future pushes to the `main` branch will trigger automatic redeployments.

---

## Python ML Backend (`src/`)

The Python ML source code in `src/` is research and reference code for the term paper.  
It is **not deployed** — it runs locally for model training, evaluation, and generating report artifacts.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Key commands

```bash
# Run feature extraction and train model
python src/classifier.py

# Run deep learning baselines
python src/deep_learning.py

# Compute fairness and calibration metrics
python scripts/compute_fairness_metrics.py

# Run all tests
pytest tests/
```

### Generated artifacts (committed to repo)

| File | Description |
|------|-------------|
| `data/combined_features.csv` | 122-child cross-corpus feature dataset |
| `data/longitudinal_features.csv` | Longitudinal session features |
| `reports/metrics/*.csv` | All model evaluation metrics |
| `reports/figures/*.png` | All report figures |
| `artifacts/screening_model.joblib` | Trained model bundle |
| `artifacts/model_card.json` | Model card with caveats |
| `artifacts/feature_schema.json` | 14-feature schema definition |
