# ASD Therapist Clinical Pilot - Developer Setup Guide

Welcome to the development guide for the ASD Speech-Language Screening Support tool. This document explains how to set up, build, test, and run the project's applications.

> [!IMPORTANT]
> **Safety Notice**: This project is a research prototype and educational demo. It is **not a diagnostic tool** and is **not clinically validated** for Thai children. Real child names, surnames, and identifiers are strictly prohibited in the system caseload.

---

## 🛠️ Prerequisites
- **Python**: `3.10` or higher
- **Node.js**: `v18` or higher
- **npm**: `v9` or higher

---

## 🐍 Python and Active API Setup

### 1. Initialize Virtual Environment
From the project root:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r apps/api/requirements.txt
```

### 3. Run the Active Backend API
```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

`src/therapist_backend` is a legacy research compatibility API. Do not use it
as the Therapist App v2 backend or add new product routes there.

### 4. Running Python Unit Tests
We use **pytest** to validate backend services.
- **Run all core tests** (excluding heavy audio/transcription workloads):
  ```bash
  PYTHONPATH=apps/api:src pytest -m "not audio"
  ```
- **Run all tests** (requires installing heavy audio dependencies like `faster-whisper`, `speechbrain`, `librosa`):
  ```bash
  PYTHONPATH=apps/api:src pytest
  ```

---

## 🌐 Frontend Applications Setup

The project includes one Next.js therapist app and two Vite presentation/education apps.

### 1. 🩺 Therapist App (`apps/therapist-app-v2/`)
Enforces the clinical sign-off, consent gates, and caseload review.
```bash
cd apps/therapist-app-v2
npm ci
npm run build
npm test
npm run dev
```
- Default URL: [http://localhost:3000](http://localhost:3000)

### 2. 🏠 Public Screening Support App (`public-screening/`)
Bilingual educational screening tool for parents.
```bash
cd public-screening
npm install
npm run build
npm test
npm run dev
```
- Default URL: [http://localhost:5173](http://localhost:5173) (or next port)

### 3. 📊 Presentation Dashboard (`presentation-dashboard/`)
Dataset insights and model performance visualization.
```bash
cd presentation-dashboard
npm install
npm run build
npm test
npm run dev
```
- Default URL: [http://localhost:5173](http://localhost:5173) (or next port)

---

## ⚙️ Therapist App v2 Runtime Modes

The active app uses `THERAPIST_APP_V2_*` backend settings. The former
`VITE_RUNTIME_MODE` settings belonged to the retired Vite therapist app.

1. **JSON repository** (default):
   - The Therapist App v2 API defaults to durable local JSON persistence,
     which survives API restarts.
   - Memory repository mode is only for isolated tests or intentional demo
     resets.
   - SQL repository mode is PostgreSQL-ready but not pilot-hardened yet.
   - Browser `sessionStorage` is only lightweight workflow/navigation cache,
     never the clinical source of truth.
   - Audio bytes remain memory-only unless the therapist explicitly uploads
     them.
   - Processing is simulated with mock CHAT files.
   - File uploads are metadata-only.
   
2. **Memory repository**:
   - Set `THERAPIST_APP_V2_REPOSITORY_MODE=memory`.
   - Use only for isolated tests or intentional resets.
   
3. **SQL repository**:
   - Set `THERAPIST_APP_V2_REPOSITORY_MODE=sql`.
   - Configure `THERAPIST_APP_V2_DATABASE_URL`.
   - This remains PostgreSQL-ready scaffolding, not a pilot-hardened deployment.

The frontend API base is configured with
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`.
