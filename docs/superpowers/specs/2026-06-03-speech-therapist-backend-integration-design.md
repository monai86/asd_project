# REST API Integration Design - Speech Therapist Prototype

## 1. Overview
The goal of this design is to connect the Speech Therapist web application with the FastAPI backend in `api` data mode (active when `VITE_RUNTIME_MODE = "local_dev"`). It ensures all interactive features—such as case/session creation, audio uploads, transcription pipeline execution, transcript QA review, feature re-runs, and report generation—directly communicate with the running FastAPI backend endpoints instead of staying mock/in-memory in the browser.

---

## 2. Architecture & Backend Changes

### 2.1. CORS Middleware
FastAPI will be updated in [src/therapist_backend/app.py](file:///Users/porschecaa/Desktop/asd-project/src/therapist_backend/app.py) to enable CORS requests from the Vite dev server origins:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2.2. Expose AI Screening Output Endpoint
Expose the `get_ai_output_for_session_for_user` method under a new route in [src/therapist_backend/app.py](file:///Users/porschecaa/Desktop/asd-project/src/therapist_backend/app.py):
```python
@app.get("/api/sessions/{session_id}/ai-output")
def get_ai_output(session_id: str, user: User = Depends(current_user)) -> dict:
    row = repository.get_ai_output_for_session_for_user(session_id, user)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI screening output not found."
        )
    return _jsonable(row)
```

### 2.3. Stateful Mock Job Progression
In [src/clinical_workflow/mock_repository.py](file:///Users/porschecaa/Desktop/asd-project/src/clinical_workflow/mock_repository.py), `get_processing_job_for_user` will be modified to simulate ASR pipeline progression statefully upon subsequent polls:
- **State Transition 1 (queued -> transcribing)**:
  If a job's current status is `"queued"`, update it to `"processing"`, progress `35%`, and stage `"transcribing"`.
- **State Transition 2 (transcribing -> completed)**:
  If the status is `"processing"`, transition it to `"completed"`, progress `100%`, and stage `"awaiting_review"`. Generate:
  - Mock CHAT text transcript and line records in `self.transcripts` and `self.transcript_lines`.
  - Extracted speech-language feature records (preliminary status) in `self.extracted_features`.
  - Preliminary AI decision-support output in `self.ai_screening_outputs`.
  - Link the transcript to the session and update the session's processing status to `"transcript_ready"`.

---

## 3. Frontend Client & Service Integration

### 3.1. Authenticated API Client Singleton
Create and export a shared API client `api` in [api-client.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/api-client.js) that extracts the active `user_id` on each request to authenticate requests automatically:
```javascript
import { AUTH_API_BASE_URL } from "../constants.js";
import { store } from "../store/state.js";

export const api = createApiClient({
  baseUrl: AUTH_API_BASE_URL || "http://localhost:8000",
  getToken: () => {
    const state = store.getState();
    return state.currentUser?.user_id || state.authSession?.session_token || null;
  }
});
```

### 3.2. User Data Loader Hook
Update [auth-service.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/auth-service.js) to trigger an async bulk fetch of cases, sessions, and audit logs immediately after sign-in or session restoration:
```javascript
export async function loadUserDataFromApi() {
  const state = store.getState();
  if (state.dataMode !== "api") return;
  try {
    const [cases, sessions] = await Promise.all([
      api.get("/api/cases"),
      api.get("/api/sessions")
    ]);
    let auditLogs = [];
    if (state.currentUser?.role === "admin") {
      auditLogs = await api.get("/api/audit-logs").catch(() => []);
    }
    store.setState({
      cases: cases || [],
      sessions: sessions || [],
      auditLogs: auditLogs || []
    });
  } catch (error) {
    console.error("Failed to load user data from API:", error);
  }
}
```

### 3.3. Service Mutations Sync
1. **[case-service.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/case-service.js)**:
   - `createCase`: Call `POST /api/cases`. If consent status is granted, call `POST /api/cases/{case_id}/consent`. Commit returned record to store.
   - `updateCaseNotes`: Call `PATCH /api/cases/{case_id}` to save notes on the backend.
2. **[session-service.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/session-service.js)**:
   - `createNewSession`: Call `POST /api/sessions`. Commit to store.
   - `updateSessionStatus`: Call `PATCH /api/sessions/{session_id}` to update session metadata.

### 3.4. Audio & Transcription Pipeline Sync
- **[audio-service.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/audio-service.js)**:
  - Register secure upload intent with `POST /api/sessions/{session_id}/audio/upload-intent`.
- **[transcription-service.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/transcription-service.js)**:
  - In `startBackendAudioProcessing`, call `POST /api/sessions/{session_id}/process-audio`.
  - Start an async polling loop (`setInterval` every 1.5 seconds) checking `GET /api/jobs/{job_id}`.
  - Upon job completion, clear the timer and bulk-fetch:
    - `/api/sessions/{session_id}/transcript`
    - `/api/sessions/{session_id}/qa`
    - `/api/sessions/{session_id}/features`
    - `/api/sessions/{session_id}/ai-output`
    - `/api/sessions/{session_id}/reference-comparison`
    - `/api/sessions/{session_id}/reference-similarity`
  - Merge the resulting payloads into the reactive store and navigate to the transcript review.

### 3.5. Live Review & Sign-off Sync
- **[review-service.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/review-service.js)**:
  - `updateUtterance`: Call `PATCH /api/transcripts/{transcript_id}/lines/{line_id}` to save spelling/speaker corrections.
  - `saveTherapistReview`: Call `POST /api/sessions/{session_id}/transcript/signoff` to log the clinical gate record.
- **[transcript-view.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/views/transcript-view.js)**:
  - "Re-run feature extraction" click handler: call `POST /api/sessions/{session_id}/features/extract` to recalculate feature rows on the backend, then fetch `/api/sessions/{session_id}/ai-output` and `/api/sessions/{session_id}/reference-comparison` to update the store state.
- **[report-service.js](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app/src/services/report-service.js)**:
  - "Generate Report" click handler: call `POST /api/sessions/{session_id}/report` to generate and persist the descriptive report.

---

## 4. Verification Plan

### 4.1. Automated Tests
- Run backend unit tests: `pytest`
- Run E2E smoke tests: `npm run test:e2e:smoke` (confirming login, case creation, transcription, review, feature rerun, and report generation execute successfully against API mock boundaries).

### 4.2. Manual Verification
- Start backend: `uvicorn src.therapist_backend.app:app --port 8000`
- Start frontend: `npm run dev` in `therapist-clinician-app`
- Log in with `therapist@example.test`, create a case, add a session, register audio, start the transcription pipeline, and verify the UI updates correctly from the backend responses.
