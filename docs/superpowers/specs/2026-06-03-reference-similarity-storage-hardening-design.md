# Reference Similarity Engine & Storage Hardening Design Spec

This document details the architectural design for the descriptive **Reference Similarity Retrieval** feature (Option C) and the directory traversal protection/isolation of the **Clinical Uploads Namespace** (Option B).

---

## 1. Clinical Uploads Namespace (Option B)

### Objective
Ensure that client-uploaded session recording files and transcripts are strictly partitioned from the TalkBank Raw Mirror and other system files, preventing any directory traversal attacks (`..` manipulation).

### Backend Hardening Design
1. **Clinical Uploads Root**: Define `CLINICAL_UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"`.
2. **Path Resolution Validation**:
   - Create a path sanitization utility `validate_uploads_path(requested_path: Path) -> Path` that resolves the path using `.resolve()`.
   - Verify that the resolved absolute path starts exactly with `CLINICAL_UPLOADS_DIR.resolve()`.
   - If a client-supplied filename or path attempts to point outside `CLINICAL_UPLOADS_DIR` (e.g., directory traversal `../`), raise an HTTP `400 Bad Request` or `403 Forbidden` exception.
3. **Mocks Integration**: Enhance `MockClinicalRepository` to validate storage path boundaries when generating mock file intents.

---

## 2. Reference Similarity Retrieval (Option C)

### Objective
Allow speech therapists to query the top 5 most similar reference case feature profiles within their session's matched descriptive cohort slice. This serves as additional clinical decision support without making diagnostic claims or screening risk determinations.

### Mathematical Formulation
1. **Cohort Slice Filtering**: Given the session child's age band (e.g., `36-47`) and task type (e.g., `toyplay`), filter the reference feature database `english_child_reference_features.csv` to rows matching these variables.
2. **Min-Max Scaling**: Scale the Core 14 features *only* within this matched cohort slice to equalize feature weights:
   $$x_{\text{scaled}} = \frac{x - \min_{\text{cohort}}}{\max_{\text{cohort}} - \min_{\text{cohort}} + 1e-5}$$
3. **Euclidean Distance**: Compute the distance between the target child's scaled feature vector $\vec{x}$ and each reference case's scaled feature vector $\vec{r}$:
   $$d = \sqrt{\sum_{i=1}^{14} (x_{i, \text{scaled}} - r_{i, \text{scaled}})^2}$$
4. **Ranking**: Sort matched reference cases in ascending order of $d$ and return the top 5 records.

### API Endpoint Contract
* **Route**: `GET /api/sessions/{session_id}/reference-similarity`
* **Headers**: `X-User-Id` (authenticated)
* **Response Payload (200 OK)**:
  ```json
  {
    "status": "ok",
    "similarity_term": "Reference Similarity Retrieval",
    "session_id": "SESSION-001",
    "age_band_12mo": "48-59",
    "task_type": "toyplay",
    "results": [
      {
        "transcript_uid": "Eigsti:1017:77815150f338",
        "corpus": "Eigsti",
        "group": "ASD",
        "distance": 0.12,
        "features": {
          "mlu": 2.28,
          "ttr": 0.58,
          "echolalia_ratio": 0.03,
          "total_words": 483
          // other Core 14 features
        }
      }
    ]
  }
  ```
* **Read-only Safety**: This endpoint does not write clinical audits or mutate state. Prohibited diagnostic terminology (`norm`, `diagnostic`, `validation`, `benchmark`) is validated and blocked.

### Frontend UI Integration
1. **Service**: Implement `loadReferenceSimilarityForSession` mapping the endpoint and handling API/mock data modes.
2. **Transcript tab render**: Add a *"Similar Reference Cases (Descriptive)"* list at the bottom of the Reference Comparison panel.
3. Automatically render the top 5 similar case cards detailing corpus, group, and key features side-by-side with target child metrics.

---

## 3. Verification Plan

### Automated Python Tests
- Test path resolution utility with traversal strings (e.g. `../../raw/talkbank`) and ensure it raises correct exceptions.
- Mock reference feature database matches and verify that min-max Euclidean calculation returns correct rankings.
- Test `GET /api/sessions/{session_id}/reference-similarity` endpoint authentication and safety wording checks.

### Automated Frontend Tests
- Test similarity service requests, headers, and UI card rendering structure.
- Ensure restricted safety language checks pass cleanly.
