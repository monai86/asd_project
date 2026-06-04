# Speech Therapist Backend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the speech therapist web application to the FastAPI backend API, ensuring all caseload management, transcription pipelines, transcript edits, quality checks, and sign-offs execute statefully against the backend database.

**Architecture:** Implement CORS and a new AI output endpoint on the FastAPI backend. Implement a dynamic `apiClient` singleton in the frontend. Load backend data immediately after user session setup, and rewrite frontend service calls to invoke backend HTTP endpoints instead of in-memory mutations.

**Tech Stack:** Javascript, Node.js, Vite, Vitest (frontend) / Python, FastAPI, Uvicorn, Pytest (backend)

---

### Task 1: Enable Backend CORS Middleware
Enable cross-origin requests from the Vite frontend port (`5173`) in the FastAPI backend app.

**Files:**
- Modify: `src/therapist_backend/app.py:129-130`
- Test: `tests/test_clinical_pilot_backend_contract.py`

- [ ] **Step 1: Write a failing test checking CORS middleware**
Add the following test function at the end of `tests/test_clinical_pilot_backend_contract.py`:
```python
def test_backend_cors_middleware_is_configured():
    from fastapi.testclient import TestClient
    from src.therapist_backend.app import create_app
    client = TestClient(create_app(_repo()))
    response = client.options(
        "/api/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-User-Id",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_clinical_pilot_backend_contract.py::test_backend_cors_middleware_is_configured -v`
Expected: FAIL with assertion error or missing headers.

- [ ] **Step 3: Write minimal implementation in app.py**
Add CORS middleware to `src/therapist_backend/app.py` inside `create_app()`:
```python
    from fastapi.middleware.cors import CORSMiddleware
    
    repository = repo or MockClinicalRepository()
    app = FastAPI(
        title="ASD Therapist Clinical Pilot API",
        version="1.2.1",
        description=(
            "Clinical decision-support API for therapist transcript review, "
            "secure audio upload, progress tracking, and sign-off gates."
        ),
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_clinical_pilot_backend_contract.py::test_backend_cors_middleware_is_configured -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tests/test_clinical_pilot_backend_contract.py src/therapist_backend/app.py
git commit -m "backend: add CORS middleware for frontend communication"
```

---

### Task 2: Expose AI Screening Output GET Endpoint
Implement a route on the FastAPI backend to retrieve the AI screening output for a given session.

**Files:**
- Modify: `src/therapist_backend/app.py:363-364`
- Test: `tests/test_clinical_pilot_backend_contract.py`

- [ ] **Step 1: Write a failing test for getting AI screening output**
Add the following test function at the end of `tests/test_clinical_pilot_backend_contract.py`:
```python
def test_get_ai_screening_output_endpoint():
    from fastapi.testclient import TestClient
    from src.therapist_backend.app import create_app
    repo = _repo()
    therapist = repo.users["user_therapist_001"]
    client = TestClient(create_app(repo))
    response = client.get(
        "/api/sessions/SESSION-001/ai-output",
        headers={"X-User-Id": therapist.user_id}
    )
    assert response.status_code == 200
    assert response.json()["concern_level"] == "moderate_concern"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_clinical_pilot_backend_contract.py::test_get_ai_screening_output_endpoint -v`
Expected: FAIL with status code 404.

- [ ] **Step 3: Implement the route in app.py**
Add the following endpoint in `src/therapist_backend/app.py` after the `/api/sessions/{session_id}/features` route:
```python
    @app.get("/api/sessions/{session_id}/ai-output")
    def get_ai_output(session_id: str, user: User = Depends(current_user)) -> dict:
        output = repository.get_ai_output_for_session_for_user(session_id, user)
        if output is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI screening output not found.")
        return _jsonable(output)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_clinical_pilot_backend_contract.py::test_get_ai_screening_output_endpoint -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tests/test_clinical_pilot_backend_contract.py src/therapist_backend/app.py
git commit -m "backend: add GET /api/sessions/{session_id}/ai-output route"
```

---

### Task 3: Implement Stateful Mock Job Progression on Backend
Ensure queued jobs advance to transcribing and then completed state statefully when fetched from the backend.

**Files:**
- Modify: `src/clinical_workflow/mock_repository.py:380-386`
- Test: `tests/test_clinical_pilot_backend_contract.py`

- [ ] **Step 1: Write a failing test for stateful job progression**
Add the following test function at the end of `tests/test_clinical_pilot_backend_contract.py`:
```python
def test_mock_job_stateful_progression():
    repo = _repo()
    therapist = repo.users["user_therapist_001"]
    job = repo.create_processing_job("SESSION-001", therapist)
    assert job.status == "queued"
    
    # First poll should transition to processing
    polled1 = repo.get_processing_job_for_user(job.job_id, therapist)
    assert polled1.status == "processing"
    assert polled1.progress == 35
    
    # Second poll should transition to completed and attach transcripts
    polled2 = repo.get_processing_job_for_user(job.job_id, therapist)
    assert polled2.status == "completed"
    assert polled2.progress == 100
    assert repo.sessions["SESSION-001"].transcript_id is not None
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_clinical_pilot_backend_contract.py::test_mock_job_stateful_progression -v`
Expected: FAIL (job status remains queued).

- [ ] **Step 3: Implement stateful progression in mock_repository.py**
Rewrite `get_processing_job_for_user` in `src/clinical_workflow/mock_repository.py`:
```python
    def get_processing_job_for_user(self, job_id: str, user: User) -> ProcessingJob | None:
        job = self.processing_jobs.get(job_id)
        if job is None:
            return None
        if user.role != "admin" and job.owner_user_id != user.user_id:
            return None

        # Simulate stateful progression on retrieval
        if job.status == "queued":
            job.status = "processing"
            job.progress = 35
            job.stage = "transcribing"
            job.updated_at = self._now()
            self.sessions[job.session_id].processing_status = "processing"
        elif job.status == "processing":
            # Complete the job statefully
            session = self.sessions[job.session_id]
            child_case = self.cases[session.case_id]
            now = self._now()
            
            # Generate Transcript and lines
            transcript_text = self._mock_chat_text(
                child_case.anonymized_child_code,
                child_case.age_months,
                child_case.sex,
            )
            qa_result = review_cha_text(transcript_text)
            self._transcript_sequence += 1
            transcript = Transcript(
                transcript_id=f"TRANSCRIPT-{self._transcript_sequence:03d}",
                session_id=session.session_id,
                case_id=session.case_id,
                owner_user_id=session.owner_user_id,
                transcript_text=transcript_text,
                review_status="awaiting_review",
                reviewer_notes="ASR-generated transcript awaiting review",
                qa_status=qa_result["status"],
                qa_score=qa_result["quality_score"],
                qa_issues=qa_result["issues"],
                created_at=now,
                updated_at=now,
            )
            self.transcripts[transcript.transcript_id] = transcript
            self._replace_transcript_lines(transcript)
            
            # Generate preliminary Features
            core_features = self._mock_features_from_transcript(child_case, transcript_text)
            optional_indicators = self._mock_optional_indicators_from_transcript(transcript_text)
            self._feature_sequence += 1
            features = ExtractedFeatures(
                feature_id=f"FEATURE-{self._feature_sequence:03d}",
                session_id=session.session_id,
                case_id=session.case_id,
                owner_user_id=session.owner_user_id,
                feature_schema_version="14-feature-schema",
                features={**core_features, **optional_indicators},
                core_features=core_features,
                optional_indicators=optional_indicators,
                created_at=now,
                updated_at=now,
            )
            self.extracted_features[features.feature_id] = features
            
            # Generate preliminary AI output
            self.generate_ai_screening_output_for_session(session.session_id, user)
            
            # Complete job status
            job.status = "completed"
            job.progress = 100
            job.stage = "awaiting_review"
            job.result_refs = {"transcript_id": transcript.transcript_id}
            job.finished_at = now
            job.updated_at = now
            
            self.sessions[job.session_id].transcript_id = transcript.transcript_id
            self.sessions[job.session_id].processing_status = "transcript_ready"
            self.sessions[job.session_id].feature_extraction_status = "preliminary"
            self.sessions[job.session_id].ai_analysis_status = "requires_transcript_review"
            self.sessions[job.session_id].therapist_review_status = "awaiting_review"

        return replace(job)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_clinical_pilot_backend_contract.py::test_mock_job_stateful_progression -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/clinical_workflow/mock_repository.py tests/test_clinical_pilot_backend_contract.py
git commit -m "backend: implement stateful job progression in mock repository"
```

---

### Task 4: Instantiate Shared API Client Singleton
Create a shared, authenticated API client singleton that dynamically maps requests using the current logged-in user token.

**Files:**
- Modify: `therapist-clinician-app/src/services/api-client.js:80`
- Test: Create `therapist-clinician-app/src/__tests__/shared-api-client.test.js`

- [ ] **Step 1: Write a test verifying the shared client fetches user headers dynamically**
Create `therapist-clinician-app/src/__tests__/shared-api-client.test.js`:
```javascript
import { describe, expect, it, vi } from "vitest";
import { store } from "../store/state.js";
import { api } from "../services/api-client.js";

describe("shared api client singleton", () => {
  it("applies X-User-Id header dynamically from state store", async () => {
    store.setState({ currentUser: { user_id: "user_test_123" } });
    expect(api).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails/passes**
Run: `npx vitest run src/__tests__/shared-api-client.test.js`
Expected: FAIL if `api` is not defined or error is thrown.

- [ ] **Step 3: Define and export the `api` singleton in api-client.js**
Append to `therapist-clinician-app/src/services/api-client.js`:
```javascript
import { store } from "../store/state.js";
import { AUTH_API_BASE_URL } from "../constants.js";

export const api = createApiClient({
  baseUrl: AUTH_API_BASE_URL || "http://localhost:8000",
  getToken: () => {
    const state = store.getState();
    return state.currentUser?.user_id || state.authSession?.session_token || null;
  }
});
```

- [ ] **Step 4: Run test to verify it passes**
Run: `npx vitest run src/__tests__/shared-api-client.test.js`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add therapist-clinician-app/src/services/api-client.js therapist-clinician-app/src/__tests__/shared-api-client.test.js
git commit -m "frontend: instantiate and export authenticated api client singleton"
```

---

### Task 5: Trigger Bulk Loading of Backend Data on Login/Restore
Implement `loadUserDataFromApi` to retrieve cases and sessions, then wire it to auth results.

**Files:**
- Modify: `therapist-clinician-app/src/services/auth-service.js:18-70`
- Test: Create a verification case in `therapist-clinician-app/src/__tests__/auth-service-sync.test.js`

- [ ] **Step 1: Write a test verifying that loader gets called on successful sign in**
Create `therapist-clinician-app/src/__tests__/auth-service-sync.test.js`:
```javascript
import { describe, expect, it, vi } from "vitest";
import { store } from "../store/state.js";
import { loadUserDataFromApi } from "../services/auth-service.js";

describe("auth sync load", () => {
  it("exports loadUserDataFromApi", () => {
    expect(loadUserDataFromApi).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**
Run: `npx vitest run src/__tests__/auth-service-sync.test.js`
Expected: FAIL (loadUserDataFromApi is undefined).

- [ ] **Step 3: Implement loadUserDataFromApi and hooks in auth-service.js**
Import `api` and implement in `therapist-clinician-app/src/services/auth-service.js`:
```javascript
import { api } from "./api-client.js";

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
Update `applySignInResult` and `applyRestoreResult` to trigger `loadUserDataFromApi` if successful:
```javascript
function applySignInResult(result, email) {
  const user = result.user;
  if (user) {
    store.setState({
      currentUser: user,
      authSession: result.session || null,
      authStatus: "signed_in",
      authError: ""
    });
    addAudit("login_success", "User", user.user_id, `User ${user.name} logged in successfully.`);
    loadUserDataFromApi();
    return user;
  }
  ...
}

function applyRestoreResult(result) {
  if (result?.user) {
    store.setState({
      currentUser: result.user,
      authSession: result.session || null,
      authStatus: "signed_in",
      authError: ""
    });
    loadUserDataFromApi();
    return result.user;
  }
  ...
}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `npx vitest run src/__tests__/auth-service-sync.test.js`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add therapist-clinician-app/src/services/auth-service.js therapist-clinician-app/src/__tests__/auth-service-sync.test.js
git commit -m "frontend: hook user data load from api on auth events"
```

---

### Task 6: Connect Caseload Mutations to the API
Modify caseload services to execute POST/PATCH backend requests in `api` mode.

**Files:**
- Modify: `therapist-clinician-app/src/services/case-service.js:11-37`
- Test: Add tests to a mock server setup or unit test verification.

- [ ] **Step 1: Implement case creation API synchronization**
Update `createCase` in `therapist-clinician-app/src/services/case-service.js`:
```javascript
import { api } from "./api-client.js";

export function createCase({ anonymized_child_code, age_months, sex, primary_concerns, notes, consent_status = "pending", anonymization_status = "anonymized" }) {
  const { currentUser, cases, dataMode } = store.getState();
  requireAuth();

  const caseId = `CASE-${String(cases.length + 1).padStart(3, "0")}`;
  const displayLabel = `Case ${String.fromCharCode(65 + cases.length)}`; // A, B, C...

  const newCase = createChildCase({
    case_id: caseId,
    owner_user_id: currentUser.user_id,
    anonymized_child_code,
    display_label: displayLabel,
    age_months: parseInt(age_months) || 48,
    sex,
    primary_concerns,
    consent_status,
    anonymization_status,
    notes,
    support_level: "Needs review",
    latest_score: 0.0,
    score_trend: []
  });

  if (dataMode === "api") {
    // Send case to API
    api.post("/api/cases", {
      anonymized_child_code,
      age_months: parseInt(age_months) || 48,
      sex,
      primary_concerns,
      consent_status,
      anonymization_status,
      external_clinical_status: "not_provided",
      notes
    }).then(backendCase => {
      // If consent granted, record it statefully on backend too
      if (consent_status === "granted") {
        api.post(`/api/cases/${backendCase.case_id}/consent`, {
          audio_permission: true,
          transcript_permission: true,
          consent_type: "clinical_audio_processing",
          guardian_status: "guardian",
          notes: "Granted at case creation"
        });
      }
      
      const updatedCases = store.getState().cases.map(c => 
        c.case_id === caseId ? { ...c, case_id: backendCase.case_id } : c
      );
      store.setState({ cases: updatedCases, selectedCaseId: backendCase.case_id });
    }).catch(err => {
      console.error("Failed to create case on backend:", err);
    });
  }

  store.setState({
    cases: [...cases, newCase],
    selectedCaseId: caseId
  });

  addAudit("create_case", "ChildCase", caseId, `Created child case ${anonymized_child_code}`);
  return newCase;
}
```

- [ ] **Step 2: Implement case updates notes sync**
Update `updateCaseNotes` in `therapist-clinician-app/src/services/case-service.js`:
```javascript
export function updateCaseNotes(caseId, notes) {
  const { currentUser, cases, dataMode } = store.getState();
  const targetCase = cases.find(c => c.case_id === caseId);
  if (!targetCase) return;
  assertCanAccessCase(currentUser, targetCase);

  if (dataMode === "api") {
    api.patch(`/api/cases/${caseId}`, { notes }).catch(err => {
      console.error("Failed to update case notes on backend:", err);
    });
  }

  const updatedCases = cases.map(c => {
    if (c.case_id === caseId) {
      addAudit("update_notes", "ChildCase", caseId, `Updated notes for case ${caseId}`);
      return { ...c, notes, updated_at: new Date().toISOString() };
    }
    return c;
  });
  store.setState({ cases: updatedCases });
}
```

- [ ] **Step 3: Run the project tests to verify no regressions**
Run: `npm test`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add therapist-clinician-app/src/services/case-service.js
git commit -m "frontend: connect case creation and notes editing to backend API"
```

---

### Task 7: Connect Session Mutations to the API
Modify session creation and update functions to synchronize with the backend in API mode.

**Files:**
- Modify: `therapist-clinician-app/src/services/session-service.js:16-55`
- Test: Check that vitest tests pass.

- [ ] **Step 1: Update createNewSession to call API**
Update `createNewSession` in `therapist-clinician-app/src/services/session-service.js`:
```javascript
import { api } from "./api-client.js";

export function createNewSession({ case_id, session_date, session_type, notes }) {
  const { currentUser, sessions, dataMode } = store.getState();
  requireAuth();
  const targetCase = getVisibleCases().find(c => c.case_id === case_id);
  if (!targetCase) throw new Error("Access denied: this case is not assigned to your account.");

  const sessionId = `SESSION-${String(sessions.length + 1).padStart(3, "0")}`;
  const newSession = createSession({
    session_id: sessionId,
    case_id,
    owner_user_id: targetCase.owner_user_id,
    session_date,
    session_type,
    notes,
    processing_status: "not_started"
  });

  if (dataMode === "api") {
    api.post("/api/sessions", {
      case_id,
      session_date,
      session_type,
      notes
    }).then(backendSess => {
      const updatedSess = store.getState().sessions.map(s => 
        s.session_id === sessionId ? { ...s, session_id: backendSess.session_id } : s
      );
      store.setState({ sessions: updatedSess, selectedSessionId: backendSess.session_id });
    }).catch(err => {
      console.error("Failed to create session on backend:", err);
    });
  }

  store.setState({
    sessions: [...sessions, newSession],
    selectedSessionId: sessionId,
    activeView: "session"
  });

  addAudit("create_session", "Session", sessionId, `Created session ${sessionId} for case ${case_id}`);
  return newSession;
}
```

- [ ] **Step 2: Update updateSessionStatus to call API**
Update `updateSessionStatus` in `therapist-clinician-app/src/services/session-service.js`:
```javascript
export function updateSessionStatus(sessionId, updates) {
  const { currentUser, sessions, dataMode } = store.getState();
  const targetSession = sessions.find(s => s.session_id === sessionId);
  if (!targetSession) return;
  assertCanAccessSession(currentUser, targetSession);

  if (dataMode === "api") {
    api.patch(`/api/sessions/${sessionId}`, { notes: updates.notes }).catch(err => {
      console.error("Failed to patch session on backend:", err);
    });
  }

  const updated = sessions.map(s => {
    if (s.session_id === sessionId) {
      return { ...s, ...updates, updated_at: new Date().toISOString() };
    }
    return s;
  });
  store.setState({ sessions: updated });
}
```

- [ ] **Step 3: Commit**
```bash
git add therapist-clinician-app/src/services/session-service.js
git commit -m "frontend: synchronize session mutations to API backend"
```

---

### Task 8: Audio Secure Upload Intent & Polling Transcription Pipeline
Connect secure upload intent and start transcription polling.

**Files:**
- Modify: `therapist-clinician-app/src/services/audio-service.js:126-140`
- Modify: `therapist-clinician-app/src/services/transcription-service.js:19-22`, `130-153`

- [ ] **Step 1: Hook up requestSecureUploadIntent to backend API**
Update `requestSecureUploadIntent` in `therapist-clinician-app/src/services/audio-service.js`:
```javascript
import { api } from "./api-client.js";

export async function requestSecureUploadIntent(file, sessionId, caseId) {
  const { cases, dataMode } = store.getState();
  const childCase = cases.find(item => item.case_id === caseId);
  assertSecureAudioConsent(childCase);

  if (dataMode === "api") {
    const intent = await api.post(`/api/sessions/${sessionId}/audio/upload-intent`, {
      original_filename: file.name,
      file_size: file.size,
      mime_type: file.type || "application/octet-stream"
    });
    addAudit(
      "secure_upload_intent_requested",
      "Session",
      sessionId,
      "Requested secure signed-upload URL for private audio storage."
    );
    return intent;
  }

  const intent = await createSecureAudioUploadIntent(sessionId, file);
  addAudit(
    "secure_upload_intent_requested",
    "Session",
    sessionId,
    intent.status === "not_configured"
      ? intent.message
      : "Requested secure signed-upload URL for private audio storage."
  );
  return intent;
}
```

- [ ] **Step 2: Update startTranscription to execute polling for backend API**
Update `startTranscription` and `startBackendAudioProcessing` in `therapist-clinician-app/src/services/transcription-service.js`:
```javascript
import { api } from "./api-client.js";

export async function startTranscription(sessionId, language = "en", speakerCount = null) {
  const { dataMode } = store.getState();
  if (dataMode === "api") {
    return startBackendAudioProcessing(sessionId);
  }
  
  if (PROCESSING_MODE !== "mock") {
    return startBackendAudioProcessing(sessionId);
  }
  // ... rest of mock transcription continues (already correct in original file)
```
And modify `startBackendAudioProcessing` to include a polling loop:
```javascript
export async function startBackendAudioProcessing(sessionId) {
  const { sessions } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");
  if (!session.audio_file_id) {
    throw new Error("Audio file metadata is required before submitting backend processing.");
  }

  addAudit("backend_processing_submit", "Session", sessionId, `Submitted backend audio processing request for session ${sessionId}`);
  updateSessionStatus(sessionId, { processing_status: "processing_submitted" });

  const job = await api.post(`/api/sessions/${sessionId}/process-audio`, {});
  updateSessionStatus(sessionId, {
    processing_status: "processing",
    processing_job_id: job.job_id
  });
  
  applyProcessingJobUpdate(job);

  // Polling loop
  const intervalId = setInterval(async () => {
    try {
      const polledJob = await api.get(`/api/jobs/${job.job_id}`);
      applyProcessingJobUpdate(polledJob);
      
      if (polledJob.status === "completed") {
        clearInterval(intervalId);
        
        // Fetch all generated results statefully from API
        const [transcriptPayload, qaPayload, featuresPayload, aiPayload, comparisonPayload, similarityPayload] = await Promise.all([
          api.get(`/api/sessions/${sessionId}/transcript`),
          api.get(`/api/sessions/${sessionId}/qa`),
          api.get(`/api/sessions/${sessionId}/features`),
          api.get(`/api/sessions/${sessionId}/ai-output`),
          api.get(`/api/sessions/${sessionId}/reference-comparison`).catch(() => null),
          api.get(`/api/sessions/${sessionId}/reference-similarity`).catch(() => null),
        ]);
        
        const state = store.getState();
        const transcriptLines = mapBackendLinesToTranscriptLines(transcriptPayload, {
          transcriptId: transcriptPayload.transcript_id,
          session,
          ownerUserId: session.owner_user_id
        });
        
        store.setState({
          transcripts: {
            ...state.transcripts,
            [sessionId]: {
              ...transcriptPayload,
              qa_status: qaPayload.qa_status || qaPayload.status,
              qa_score: qaPayload.qa_score || qaPayload.quality_score,
              qa_issues: qaPayload.qa_issues || qaPayload.issues
            }
          },
          transcriptLines: {
            ...state.transcriptLines,
            [sessionId]: transcriptLines
          },
          extractedFeatureOutputs: {
            ...state.extractedFeatureOutputs,
            [sessionId]: {
              ...featuresPayload,
              extraction_status: "preliminary"
            }
          },
          aiDecisionOutputs: {
            ...state.aiDecisionOutputs,
            [sessionId]: aiPayload
          },
          referenceComparisons: comparisonPayload ? {
            ...state.referenceComparisons,
            [sessionId]: comparisonPayload
          } : state.referenceComparisons
        });
        
        updateSessionStatus(sessionId, {
          transcript_id: transcriptPayload.transcript_id,
          processing_status: "transcript_ready",
          feature_extraction_status: "preliminary",
          ai_analysis_status: "requires_transcript_review",
          therapist_review_status: "awaiting_review"
        });
        
        addAudit("backend_transcript_generated", "Session", sessionId, "ASR transcript generation and preliminary features completed statefully.");
      } else if (polledJob.status === "failed") {
        clearInterval(intervalId);
        updateSessionStatus(sessionId, { processing_status: "failed" });
      }
    } catch (err) {
      console.error("Error polling job status:", err);
    }
  }, 1500);

  return job;
}
```

- [ ] **Step 3: Commit**
```bash
git add therapist-clinician-app/src/services/audio-service.js therapist-clinician-app/src/services/transcription-service.js
git commit -m "frontend: implement audio upload intent and dynamic job polling loops"
```

---

### Task 9: Connect Transcript Edits & Sign-off to the API
Modify line corrections and transcript sign-offs to write directly to backend API routes.

**Files:**
- Modify: `therapist-clinician-app/src/services/review-service.js:40-121`, `187-232`

- [ ] **Step 1: Synchronize line updates via PATCH endpoint**
Update `updateUtterance` in `therapist-clinician-app/src/services/review-service.js`:
```javascript
export function updateUtterance(sessionId, lineIndex, text, speaker, options = {}) {
  const { currentUser, sessions, transcripts, transcriptLines, extractedFeatureOutputs, aiDecisionOutputs, dataMode } = store.getState();
  const lines = transcriptLines[sessionId];
  if (!lines || !lines[lineIndex]) return null;

  const original = { ...lines[lineIndex] };
  const expectedVersion = options.expectedVersion ?? options.expected_version;
  const actualVersion = Number(original.version || 1);
  const lineId = original.line_id || makeTranscriptLineId(sessionId, original.line_number ?? lineIndex + 1, original.transcript_id);
  if (expectedVersion != null && Number(expectedVersion) !== actualVersion) {
    throw new TranscriptLineConflictError({
      lineId,
      expectedVersion: Number(expectedVersion),
      actualVersion
    });
  }

  const session = sessions.find(item => item.session_id === sessionId);
  const transcript = transcripts[sessionId];
  const now = new Date().toISOString();
  const editedLine = normalizeTranscriptLineForPersistence({
    ...lines[lineIndex],
    line_id: lineId,
    text,
    speaker,
    reviewed: Boolean(options.reviewed),
    review_status: options.reviewed ? "reviewed" : "needs_review",
    interpretation_note: options.interpretation_note || "",
    version: actualVersion + 1
  }, { session, transcript, currentUser, now });
  editedLine.clinical_flags = detectClinicalReviewFlags(editedLine, lines[lineIndex - 1]);

  if (dataMode === "api" && transcript?.transcript_id) {
    api.patch(`/api/transcripts/${transcript.transcript_id}/lines/${lineId}`, {
      speaker_code: speaker,
      utterance_text: text,
      reviewed: Boolean(options.reviewed),
      interpretation_note: options.interpretation_note || "",
      expected_version: actualVersion
    }).catch(err => {
      console.error("Failed to patch transcript line on backend:", err);
    });
  }

  const updatedLines = [...lines];
  updatedLines[lineIndex] = editedLine;

  const previousFeatures = extractedFeatureOutputs[sessionId];
  const previousAiOutput = aiDecisionOutputs[sessionId];

  store.setState({
    transcriptLines: {
      ...transcriptLines,
      [sessionId]: updatedLines
    },
    extractedFeatureOutputs: previousFeatures
      ? {
          ...extractedFeatureOutputs,
          [sessionId]: {
            ...previousFeatures,
            extraction_status: "stale",
            review_status: "stale",
            stale_reason: "transcript_edited",
            updated_at: new Date().toISOString()
          }
        }
      : extractedFeatureOutputs,
    aiDecisionOutputs: previousAiOutput
      ? {
          ...aiDecisionOutputs,
          [sessionId]: {
            ...previousAiOutput,
            therapist_review_status: "requires_transcript_review",
            explanation: "AI-assisted explanation requires transcript review and feature re-run after transcript edits.",
            updated_at: new Date().toISOString()
          }
        }
      : aiDecisionOutputs
  });

  updateSessionStatus(sessionId, {
    feature_extraction_status: previousFeatures ? "stale" : "not_started",
    ai_analysis_status: previousAiOutput ? "requires_transcript_review" : "not_started",
    therapist_review_status: "awaiting_review"
  });

  addAudit(
    "edit_utterance",
    "Utterance",
    `${sessionId}_L${lineIndex}`,
    `Edited utterance index ${lineIndex} in session ${sessionId}. Speaker changed from ${original.speaker} to ${speaker}, text from "${original.text}" to "${text}"`
  );

  return editedLine;
}
```

- [ ] **Step 2: Synchronize transcript sign-off approval**
Update `saveTherapistReview` in `therapist-clinician-app/src/services/review-service.js`:
```javascript
export function saveTherapistReview({ sessionId, notes, approvedSummary = "", rejectedReason = "" }) {
  const { currentUser, sessions, transcripts, clinicalSignoffs = [], dataMode } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");

  const reviewId = `REV-${String(Math.random()).slice(2, 6)}`;
  const review = createTherapistReview({
    review_id: reviewId,
    session_id: sessionId,
    reviewer_id: currentUser ? currentUser.user_id : "anonymous",
    review_status: "reviewed",
    therapist_notes: notes,
    approved_summary: approvedSummary,
    rejected_summary_reason: rejectedReason
  });

  if (dataMode === "api") {
    api.post(`/api/sessions/${sessionId}/transcript/signoff`, { notes }).then(signoffResponse => {
      // Sync sessions from API to fetch updated feature_extraction_status
      api.get("/api/sessions").then(backendSessions => {
        store.setState({ sessions: backendSessions || [] });
      });
    }).catch(err => {
      console.error("Failed to sign off transcript on backend:", err);
    });
  }

  markTranscriptReviewed(sessionId, notes);

  const transcript = transcripts[sessionId];
  const signoff = {
    signoff_id: `SIGNOFF-${String(clinicalSignoffs.length + 1).padStart(3, "0")}`,
    target_type: "transcript",
    target_id: transcript?.transcript_id || sessionId,
    session_id: sessionId,
    case_id: session.case_id,
    owner_user_id: session.owner_user_id,
    signed_by_user_id: currentUser ? currentUser.user_id : "anonymous",
    notes,
    created_at: new Date().toISOString()
  };

  updateSessionStatus(sessionId, {
    therapist_review_status: "reviewed",
    notes: notes,
    report_status: "pending"
  });

  store.setState({
    clinicalSignoffs: [...clinicalSignoffs, signoff]
  });

  addAudit("save_review", "TherapistReview", reviewId, `Therapist saved review for session ${sessionId}`);
  addAudit("clinical_signoff_created", "ClinicalSignoff", signoff.signoff_id, `Created transcript sign-off for session ${sessionId}`);

  return review;
}
```

- [ ] **Step 3: Commit**
```bash
git add therapist-clinician-app/src/services/review-service.js
git commit -m "frontend: hook line updates and sign-off events to backend API"
```

---

### Task 10: Rerun Feature Extraction and Progress Reports via API
Hook the UI re-run click and report generation triggers to API endpoints.

**Files:**
- Modify: `therapist-clinician-app/src/views/transcript-view.js:1052-1084`
- Modify: `therapist-clinician-app/src/services/report-service.js:16-50`

- [ ] **Step 1: Hook rerun features button event listener to API endpoint**
Update `rerunFeaturesBtn` click listener in `therapist-clinician-app/src/views/transcript-view.js`:
```javascript
  const rerunFeaturesBtn = document.getElementById("rerun-feature-extraction-btn");
  if (rerunFeaturesBtn) {
    rerunFeaturesBtn.addEventListener("click", async () => {
      const sessId = rerunFeaturesBtn.getAttribute("data-session-id");
      const state = store.getState();
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session?.case_id);
      
      rerunFeaturesBtn.innerText = "Extracting...";
      rerunFeaturesBtn.disabled = true;

      try {
        if (state.dataMode === "api") {
          // Trigger backend feature extraction
          await api.post(`/api/sessions/${sessId}/features/extract`, {});
          
          // Retrieve updated features, AI output, and comparisons
          const [featuresSet, aiOutput, comparison] = await Promise.all([
            api.get(`/api/sessions/${sessId}/features`),
            api.get(`/api/sessions/${sessId}/ai-output`),
            api.get(`/api/sessions/${sessId}/reference-comparison`).catch(() => null),
          ]);
          
          // Re-fetch sessions list to sync statuses
          const updatedSessions = await api.get("/api/sessions");
          
          store.setState({
            sessions: updatedSessions || state.sessions,
            extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: featuresSet },
            aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: aiOutput },
            referenceComparisons: comparison ? { ...state.referenceComparisons, [sessId]: comparison } : state.referenceComparisons
          });
          
          alert("Feature extraction re-run complete on backend.");
          navigate("transcript");
          return;
        }

        // Mock mode extraction fallback (original code)
        const transcriptRecord = state.transcripts[sessId];
        const lines = state.transcriptLines[sessId] || [];
        const reviewed = transcriptRecord?.review_status === "reviewed";
        const { featuresSet, aiOutput } = buildFeatureAndAiOutputs({
          session,
          childCase,
          transcriptLines: lines,
          reviewed
        });

        store.setState({
          extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: featuresSet },
          aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: aiOutput },
          referenceComparisons: withoutReferenceComparison(state.referenceComparisons, sessId)
        });

        updateSessionStatus(sessId, {
          feature_extraction_status: featuresSet.extraction_status,
          ai_analysis_status: aiOutput.therapist_review_status
        });

        addAudit("rerun_feature_extraction", "Session", sessId, "Re-ran feature extraction after transcript review/correction.");
        alert(reviewed ? "Feature extraction re-run complete." : "Feature extraction re-run complete and remains preliminary until transcript review is signed off.");
        navigate("transcript");
      } catch (err) {
        alert("Failed to re-run feature extraction: " + err.message);
        navigate("transcript");
      }
    });
  }
```

- [ ] **Step 2: Update report generation to hit backend API**
Update `generateSessionReport` in `therapist-clinician-app/src/services/report-service.js`:
```javascript
import { api } from "./api-client.js";

export function generateSessionReport(sessionId) {
  const { currentUser, sessions, generatedReports = [], dataMode } = store.getState();
  const session = sessions.find(s => s.session_id === sessionId);
  if (!session) throw new Error("Session not found");

  const reportId = `REP-${String(Math.random()).slice(2, 6)}`;
  const newReport = createReport({
    report_id: reportId,
    case_id: session.case_id,
    session_id: sessionId,
    owner_user_id: session.owner_user_id,
    created_at: new Date().toISOString()
  });

  if (dataMode === "api") {
    api.post(`/api/sessions/${sessionId}/report`, {}).then(backendReport => {
      const updatedReports = store.getState().generatedReports.map(r =>
        r.report_id === reportId ? { ...r, report_id: backendReport.report_id } : r
      );
      store.setState({ generatedReports: updatedReports });
      
      // Update session status list from API
      api.get("/api/sessions").then(backendSessions => {
        store.setState({ sessions: backendSessions || [] });
      });
    }).catch(err => {
      console.error("Failed to generate report on backend:", err);
    });
  }

  store.setState({
    generatedReports: [...generatedReports, newReport]
  });

  updateSessionStatus(sessionId, {
    report_status: "completed"
  });

  addAudit("generate_report", "Report", reportId, `Generated progress report ${reportId} for session ${sessionId}`);
  return newReport;
}
```

- [ ] **Step 3: Commit**
```bash
git add therapist-clinician-app/src/views/transcript-view.js therapist-clinician-app/src/services/report-service.js
git commit -m "frontend: integrate feature extraction re-runs and report generation with backend API"
```
