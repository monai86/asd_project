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

## 🐍 Backend Python Setup

### 1. Initialize Virtual Environment
From the project root:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Backend API Server
```bash
uvicorn src.therapist_backend.app:app --reload --port 8000
```
API Documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Running Python Unit Tests
We use **pytest** to validate backend services.
- **Run all core tests** (excluding heavy audio/transcription workloads):
  ```bash
  pytest -m "not audio"
  ```
- **Run all tests** (requires installing heavy audio dependencies like `faster-whisper`, `speechbrain`, `librosa`):
  ```bash
  pytest
  ```

---

## 🌐 Frontend Applications Setup

The project consists of three distinct web applications, each running on **Vite**.

### 1. 🩺 Therapist & Clinician App (`therapist-clinician-app/`)
Enforces the clinical sign-off, consent gates, and caseload review.
```bash
cd therapist-clinician-app
npm install
npm run build
npm test
npm run dev
```
- Default URL: [http://localhost:5173](http://localhost:5173)

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

## ⚙️ Configuration & Runtime Modes

The therapist app can run in three distinct high-level modes. Configure the environment by setting the `VITE_RUNTIME_MODE` variable (or in `constants.js`):

1. **`mock`** (Default):
   - Fully mocked in-memory database and localStorage records.
   - Processing is simulated with mock CHAT files.
   - File uploads are metadata-only.
   
2. **`local_dev`**:
   - Routes API requests to a local FastAPI backend running the `MockClinicalRepository`.
   - File uploads remain metadata-only.
   - Processing is simulated.
   
3. **`pilot_backend`**:
   - Connected to a real backend containing real Postgres/Supabase DB adapters and Supabase private object storage.
   - Requires real authentication.
   - Storage uses AES256 server-side encryption with signed upload intent URLs.

To prevent leaks, **case validation strictly blocks spaces or real child names** in `mock` and `local_dev` modes.
