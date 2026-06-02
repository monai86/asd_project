# Reference Similarity & Storage Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a descriptive scaled Euclidean similarity retrieval engine for peer cohort comparisons and secure the clinician uploads directory with traversal protection.

**Architecture:** A path validation utility resolves paths using `.resolve()` and blocks operations resolving outside `data/uploads`. A similarity engine computes min-max normalized Euclidean distance against matched cohort rows in `english_child_reference_features.csv` to return the top 5 similar cases, exposed via an authenticated FastAPI endpoint and rendered automatically in the therapist app UI.

**Tech Stack:** Python 3 (FastAPI, pytest, pandas), Frontend JS (Vite, vitest, vanilla JS/CSS)

---

### Task 1: Path Traversal Protection Utility

**Files:**
- Create: `src/clinical_workflow/paths.py`
- Test: `tests/test_uploads_security.py`

- [ ] **Step 1: Write the failing test**
  Create `tests/test_uploads_security.py`:
  ```python
  from pathlib import Path
  import pytest
  from src.clinical_workflow.paths import validate_uploads_path

  def test_validate_uploads_path_safe():
      safe_path = Path("data/uploads/session_1/audio.wav")
      resolved = validate_uploads_path(safe_path)
      assert resolved.name == "audio.wav"

  def test_validate_uploads_path_traversal():
      traversal_path = Path("data/uploads/../../raw/talkbank/secret.cha")
      with pytest.raises(ValueError) as exc:
          validate_uploads_path(traversal_path)
      assert "Directory traversal detected" in str(exc.value)
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_uploads_security.py -v`
  Expected: FAIL with `ModuleNotFoundError` for `src.clinical_workflow.paths`.

- [ ] **Step 3: Write minimal implementation**
  Create `src/clinical_workflow/paths.py`:
  ```python
  from pathlib import Path

  PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
  CLINICAL_UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"

  def validate_uploads_path(requested_path: Path) -> Path:
      # Ensure uploads root exists
      CLINICAL_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
      
      # Resolve absolute paths
      resolved_root = CLINICAL_UPLOADS_DIR.resolve()
      resolved_requested = (CLINICAL_UPLOADS_DIR / requested_path).resolve()
      
      if not str(resolved_requested).startswith(str(resolved_root)):
          raise ValueError(f"Directory traversal detected for: {requested_path}")
      return resolved_requested
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_uploads_security.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add src/clinical_workflow/paths.py tests/test_uploads_security.py
  git commit -m "feat(security): add upload path validation and traversal protection"
  ```

---

### Task 2: Hardening the Mock Repository & Intent Endpoints

**Files:**
- Modify: `src/clinical_workflow/mock_repository.py`
- Modify: `src/therapist_backend/app.py`
- Test: `tests/test_uploads_security.py`

- [ ] **Step 1: Write the failing test**
  Append to `tests/test_uploads_security.py`:
  ```python
  from fastapi.testclient import TestClient
  from src.clinical_workflow import MockClinicalRepository
  from src.therapist_backend.app import create_app

  def test_upload_intent_endpoint_blocks_traversal():
      repo = MockClinicalRepository()
      app = create_app(repo)
      client = TestClient(app)
      response = client.post(
          "/api/sessions/SESSION-002/audio/upload-intent",
          headers={"X-User-Id": "user_therapist_001"},
          json={
              "original_filename": "../../raw/talkbank/escape.cha",
              "file_size": 1024,
              "mime_type": "audio/wav",
              "checksum_sha256": "abc123sha",
              "retention_days": 90
          }
      )
      assert response.status_code == 400
      assert "Directory traversal detected" in response.json()["detail"]
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_uploads_security.py -k test_upload_intent_endpoint_blocks_traversal -v`
  Expected: FAIL (returns 201 instead of 400 because paths are not validated).

- [ ] **Step 3: Write minimal implementation**
  In `src/clinical_workflow/mock_repository.py` import `validate_uploads_path` and update `create_audio_file_intent_for_user`:
  ```python
  from src.clinical_workflow.paths import validate_uploads_path
  # in create_audio_file_intent_for_user method, before creating records:
  validate_uploads_path(Path(original_filename))
  ```
  In `src/therapist_backend/app.py` update `create_upload_intent` endpoint:
  ```python
  @app.post("/api/sessions/{session_id}/audio/upload-intent")
  def create_upload_intent(
      session_id: str,
      payload: UploadIntentRequest,
      user: User = Depends(current_user),
  ) -> dict:
      try:
          # Call repository which validates filename path safety
          result = repository.create_audio_file_intent_for_user(
              session_id=session_id,
              user=user,
              original_filename=payload.original_filename,
              file_size=payload.file_size,
              mime_type=payload.mime_type,
              checksum_sha256=payload.checksum_sha256,
              retention_days=payload.retention_days,
          )
          return _jsonable(result)
      except ValueError as exc:
          raise HTTPException(status_code=400, detail=str(exc))
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_uploads_security.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add src/clinical_workflow/mock_repository.py src/therapist_backend/app.py tests/test_uploads_security.py
  git commit -m "security: enforce directory traversal block on upload intents"
  ```

---

### Task 3: Similarity Retrieval Logic

**Files:**
- Modify: `src/reference_engine.py`
- Test: `tests/test_reference_similarity.py`

- [ ] **Step 1: Write the failing test**
  Create `tests/test_reference_similarity.py`:
  ```python
  from src.reference_engine import ReferenceEngine

  def test_similarity_calculation():
      engine = ReferenceEngine()
      # Construct dummy core features
      features = {
          "mlu": 2.5, "mluw": 2.4, "ttr": 0.45, "total_words": 500,
          "unintelligible_count": 0, "unintelligible_ratio": 0.0,
          "zero_vocalization_count": 0, "nonverbal_vocalization_count": 0,
          "question_ratio": 0.1, "echolalia_count": 0, "echolalia_ratio": 0.0,
          "pronoun_reversal_count": 0
      }
      results = engine.retrieve_similar_cases(
          features=features,
          age_months=48,
          task_type="toyplay",
          k=5
      )
      assert len(results) == 5
      assert results[0]["distance"] >= 0.0
      assert "transcript_uid" in results[0]
      assert "group" in results[0]
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_reference_similarity.py -v`
  Expected: FAIL with `AttributeError` for `ReferenceEngine` missing `retrieve_similar_cases`.

- [ ] **Step 3: Write minimal implementation**
  Add method to `ReferenceEngine` in `src/reference_engine.py`:
  ```python
      def retrieve_similar_cases(
          self,
          *,
          features: dict[str, Any],
          age_months: Any,
          task_type: str,
          language: str = "eng",
          k: int = 5,
      ) -> list[dict[str, Any]]:
          band = age_band_12mo(age_months)
          resolved_task = resolve_task_type(task_type=task_type)
          if not band or not resolved_task:
              return []

          # Filter reference features
          matched = self.reference_features[
              (self.reference_features["language"].astype(str) == language)
              & (self.reference_features["age_band_12mo"].astype(str) == band)
              & (self.reference_features["task_type"].astype(str) == resolved_task)
          ].copy()

          if matched.empty:
              return []

          # Calculate Euclidean distance on min-max scaled features within the cohort
          scaled_matched = matched.copy()
          diffs_sq = []
          for f in FEATURES:
              col_vals = pd.to_numeric(matched[f], errors="coerce").fillna(0.0)
              c_min = float(col_vals.min())
              c_max = float(col_vals.max())
              denom = (c_max - c_min) + 1e-5
              
              val = float(features.get(f, 0.0))
              val_scaled = (val - c_min) / denom
              
              ref_scaled = (col_vals - c_min) / denom
              diffs_sq.append((ref_scaled - val_scaled) ** 2)
          
          matched["distance"] = np.sqrt(sum(diffs_sq))
          top_k = matched.sort_values("distance").head(k)
          
          results = []
          for _, row in top_k.iterrows():
              row_features = {f: float(row[f]) for f in FEATURES if f in row}
              results.append({
                  "transcript_uid": str(row["transcript_uid"]),
                  "corpus": str(row["corpus"]),
                  "group": str(row["group"]),
                  "distance": round(float(row["distance"]), 4),
                  "features": row_features
              })
          return results
  ```
  Note: Import `numpy as np` at the top of `src/reference_engine.py` if not already present.

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_reference_similarity.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add src/reference_engine.py tests/test_reference_similarity.py
  git commit -m "feat(reference): implement scaled Euclidean similarity retrieval engine"
  ```

---

### Task 4: Similarity API Endpoint

**Files:**
- Modify: `src/therapist_backend/app.py`
- Test: `tests/test_reference_similarity.py`

- [ ] **Step 1: Write the failing test**
  Append to `tests/test_reference_similarity.py`:
  ```python
  from fastapi.testclient import TestClient
  from src.therapist_backend.app import create_app
  from src.clinical_workflow import MockClinicalRepository

  def test_similarity_endpoint_auth_required():
      repo = MockClinicalRepository()
      app = create_app(repo)
      client = TestClient(app)
      
      response = client.get("/api/sessions/SESSION-001/reference-similarity")
      assert response.status_code == 401

  def test_similarity_endpoint_payload():
      repo = MockClinicalRepository()
      app = create_app(repo)
      client = TestClient(app)
      
      response = client.get(
          "/api/sessions/SESSION-001/reference-similarity",
          headers={"X-User-Id": "user_therapist_001"}
      )
      assert response.status_code == 200
      payload = response.json()
      assert payload["similarity_term"] == "Reference Similarity Retrieval"
      assert len(payload["results"]) == 5
      # Check safety wording (no diagnostic words)
      text = str(payload).lower()
      assert "diagnostic" not in text
      assert "norm" not in text
      assert "benchmark" not in text
      assert "validation" not in text
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_reference_similarity.py -k "endpoint" -v`
  Expected: FAIL with HTTP `404 Not Found`.

- [ ] **Step 3: Write minimal implementation**
  Add route in `src/therapist_backend/app.py`:
  ```python
      @app.get("/api/sessions/{session_id}/reference-similarity")
      def get_reference_similarity(
          session_id: str,
          user: User = Depends(current_user),
      ) -> dict:
          session = repository.sessions.get(session_id)
          if session is None or (user.role != "admin" and session.owner_user_id != user.user_id):
              raise HTTPException(
                  status_code=status.HTTP_404_NOT_FOUND,
                  detail="Session not found or access denied.",
              )
          
          features_record = repository.extracted_features.get(f"FEATURE-{session_id}")
          if not features_record:
              features_record = repository.extracted_features.get(f"FEATURE-001") # fallback for seed
          
          if not features_record:
              raise HTTPException(
                  status_code=status.HTTP_400_BAD_REQUEST,
                  detail="Extracted features are required before calculating similarity."
              )
              
          results = repository.reference_engine.retrieve_similar_cases(
              features=features_record.features,
              age_months=features_record.features.get("age_months", 48),
              task_type=session.session_type,
              k=5
          )
          
          payload = {
              "status": "ok",
              "similarity_term": "Reference Similarity Retrieval",
              "session_id": session_id,
              "age_band_12mo": age_band_12mo(features_record.features.get("age_months", 48)),
              "task_type": session.session_type,
              "results": results
          }
          # Validate safety wording
          assert_descriptive_wording(payload)
          return payload
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_reference_similarity.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add src/therapist_backend/app.py tests/test_reference_similarity.py
  git commit -m "feat(api): add GET /api/sessions/{session_id}/reference-similarity endpoint"
  ```

---

### Task 5: Frontend Service & Resource Library Integration

**Files:**
- Create: `therapist-clinician-app/src/services/reference-similarity-service.js`
- Modify: `therapist-clinician-app/src/views/transcript-view.js`
- Create: `therapist-clinician-app/src/__tests__/reference-similarity.test.js`

- [ ] **Step 1: Write the failing test**
  Create `therapist-clinician-app/src/__tests__/reference-similarity.test.js`:
  ```javascript
  import { describe, expect, it } from "vitest";
  import { renderReferenceComparisonPanel } from "../views/transcript-view.js";

  describe("Reference Similarity UI", () => {
    it("renders similar descriptive cards without diagnostic terms", () => {
      const comparisonState = {
        status: "ready",
        payload: {
          status: "ok",
          cohorts: []
        },
        similarityPayload: {
          status: "ok",
          results: [
            {
              transcript_uid: "test-uid",
              corpus: "Eigsti",
              group: "ASD",
              distance: 0.12,
              features: { mlu: 2.5 }
            }
          ]
        }
      };

      const html = renderReferenceComparisonPanel({
        session: { session_id: "SESSION-001" },
        transcript: { review_status: "reviewed" },
        features: { extraction_status: "completed" },
        currentUser: { user_id: "therapist" },
        comparisonState
      });

      expect(html).toContain("Similar Reference Cases (Descriptive)");
      expect(html).toContain("Eigsti");
      expect(html).not.toContain("diagnostic");
      expect(html).not.toContain("norm");
    });
  });
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `npm test -- --run` in `therapist-clinician-app`
  Expected: FAIL with `AssertionError` (HTML does not contain "Similar Reference Cases").

- [ ] **Step 3: Write minimal implementation**
  Create `therapist-clinician-app/src/services/reference-similarity-service.js`:
  ```javascript
  import { AUTH_API_BASE_URL, DATA_MODE } from "../constants.js";

  export async function loadReferenceSimilarity({ sessionId, currentUser, dataMode = DATA_MODE }) {
    if (dataMode === "mock") {
      return {
        status: "ok",
        results: [
          { transcript_uid: "Eigsti:1017", corpus: "Eigsti", group: "ASD", distance: 0.08, features: { mlu: 2.28, ttr: 0.58, total_words: 483 } },
          { transcript_uid: "Nadig:104", corpus: "Nadig", group: "ASD", distance: 0.14, features: { mlu: 2.12, ttr: 0.52, total_words: 395 } }
        ]
      };
    }
    const response = await fetch(`${AUTH_API_BASE_URL}/api/sessions/${sessionId}/reference-similarity`, {
      method: "GET",
      headers: { "X-User-Id": currentUser.user_id }
    });
    return response.json();
  }
  ```
  In `therapist-clinician-app/src/views/transcript-view.js` modify `renderReferenceComparisonPanel`:
  Where the payload is rendered, add the similarity results:
  ```javascript
    if (payload) {
      let similarityHtml = "";
      if (comparisonState?.similarityPayload?.results?.length) {
        similarityHtml = `
          <div style="margin-top: 12px; border-top: 1px dashed var(--line); padding-top: 12px;">
            <strong style="font-size: 0.82rem; color: var(--ink);">Similar Reference Cases (Descriptive)</strong>
            <div style="display: grid; gap: 8px; margin-top: 8px;">
              ${comparisonState.similarityPayload.results.map(res => `
                <div style="padding: 8px; border: 1px solid var(--line); border-radius: 4px; background: var(--shell); font-size: 0.74rem;">
                  <div style="display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 4px;">
                    <span>${escapeHtml(res.corpus)} (${escapeHtml(res.group)})</span>
                    <span style="color: var(--violet);">dist: ${res.distance}</span>
                  </div>
                  <div style="color: var(--muted);">MLU: ${res.features.mlu || "-"} · TTR: ${res.features.ttr || "-"}</div>
                </div>
              `).join("")}
            </div>
          </div>
        `;
      }
  ```
  And in `bindTranscriptReview` modify `loadReferenceComparison` button click handler to also fetch similarity:
  ```javascript
        const similarityResult = await loadReferenceSimilarity({
          sessionId: sessId,
          currentUser: nextState.currentUser
        });
        store.setState({
          referenceComparisons: {
            ...(store.getState().referenceComparisons || {}),
            [sessId]: {
              ...result,
              similarityPayload: similarityResult
            }
          }
        }, { persist: false });
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `npm test -- --run` in `therapist-clinician-app`
  Expected: PASS

- [ ] **Step 5: Commit & Build**
  Run: `npm run build` in `therapist-clinician-app`
  Expected: Successful production build.
  Commit:
  ```bash
  git add therapist-clinician-app/src/services/reference-similarity-service.js therapist-clinician-app/src/views/transcript-view.js therapist-clinician-app/src/__tests__/reference-similarity.test.js
  git commit -m "feat(ui): display descriptive similar reference case cards in Transcript tab"
  ```
