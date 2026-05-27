# Deployment Guide

This project has **three web applications**, all deployed as static sites on Cloudflare Pages.

| App | Directory | Tech | Target |
|-----|-----------|------|--------|
| Public Screening Support | `public-screening/` | Vite + HTML/JS | Cloudflare Pages |
| Therapist / Clinician App | `therapist-clinician-app/` | Vite + React/TS | Cloudflare Pages |
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
Runs in `MOCK_MODE=True` — no real data is stored or processed.

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
```

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
