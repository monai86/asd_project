# Reference Cohort Clinical Workflow Complete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Reference Cohort Similarity safely stored, audited, gated, and report-controlled inside the therapist clinical workflow.

**Architecture:** Reuse the existing `AIScreeningOutput` and `ModelRun` record shapes, extending them with reference cohort similarity semantics instead of adding a new table. Transcript sign-off remains the clinical source-of-truth gate; reviewed similarity refresh runs after sign-off but must not block sign-off if inference fails.

**Tech Stack:** Python dataclasses, FastAPI, mock clinical repository, existing Supabase-ready model shapes, Vite JavaScript therapist app, Vitest, pytest, scikit-learn/joblib artifact loading.

---

## File Structure

- Modify: `src/clinical_workflow/models.py`
  - Extend `AIScreeningOutput` with output semantics: `output_kind`, `inference_status`, reference cohort probabilities, most-similar cohort, similarity probability, `report_eligible`, and safety warnings.
- Modify: `src/clinical_workflow/mock_repository.py`
  - Add repository methods for preliminary/reviewed similarity generation, unavailable states, model run metadata, and report-eligible lookup.
- Modify: `src/therapist_backend/app.py`
  - Route `/api/sessions/{session_id}/reference-cohort-similarity` through repository methods rather than one-off route logic.
  - Run reviewed similarity refresh after transcript sign-off.
- Modify: `docs/API_CONTRACT.md`
  - Document the similarity route, payload, report eligibility, and failure behavior.
- Modify: `shared/src/services/report-service.js`
  - Include only reviewed + report-eligible similarity output in report markdown.
- Modify: `therapist-clinician-app/src/services/audio-processing-api.js`
  - Preserve preliminary mapping and unavailable state.
- Modify: `therapist-clinician-app/src/views/transcript-view.js`
  - Add loading/error/unavailable states and top feature contribution panel.
- Modify: `therapist-clinician-app/src/views/reports-view.js`
  - Hide preliminary similarity in report preview/export surfaces.
- Test: `tests/test_reference_cohort_similarity_workflow.py`
  - Backend route, sign-off refresh, failure isolation, report eligibility.
- Test: `therapist-clinician-app/src/__tests__/reference-cohort-similarity.test.js`
  - Frontend mapping and preliminary/reviewed UI behavior.
- Test: existing safety tests
  - `therapist-clinician-app/src/__tests__/report.test.js`
  - `therapist-clinician-app/src/__tests__/reports-view.test.js`

---

### Task 1: Extend Output Semantics Without Adding a New Table

**Files:**
- Modify: `src/clinical_workflow/models.py`
- Modify: `src/clinical_workflow/mock_repository.py`
- Test: `tests/test_reference_cohort_similarity_workflow.py`

- [x] **Step 1: Write failing dataclass serialization test**

Create `tests/test_reference_cohort_similarity_workflow.py` with:

```python
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_workflow.models import AIScreeningOutput  # noqa: E402


def test_ai_screening_output_can_represent_reference_cohort_similarity():
    output = AIScreeningOutput(
        output_id="AI-OUTPUT-REF-001",
        session_id="SESSION-001",
        case_id="CASE-001",
        owner_user_id="user_therapist_001",
        concern_level="review_support",
        output_kind="reference_cohort_similarity",
        inference_status="reviewed",
        reference_cohort_probabilities={"ASD": 0.62, "TD": 0.18, "DD": 0.20},
        most_similar_reference_cohort="ASD",
        similarity_probability=0.62,
        report_eligible=True,
        safety_warnings=[],
    )

    payload = output.to_dict()

    assert payload["output_kind"] == "reference_cohort_similarity"
    assert payload["inference_status"] == "reviewed"
    assert payload["most_similar_reference_cohort"] == "ASD"
    assert payload["similarity_probability"] == 0.62
    assert payload["report_eligible"] is True
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py::test_ai_screening_output_can_represent_reference_cohort_similarity -v
```

Expected: FAIL with `TypeError: AIScreeningOutput.__init__() got an unexpected keyword argument 'output_kind'`.

- [x] **Step 3: Extend `AIScreeningOutput`**

In `src/clinical_workflow/models.py`, update the dataclass:

```python
@dataclass
class AIScreeningOutput:
    output_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    concern_level: str
    model_version: str = "screening-support-v0.2.0"
    screening_support_score: float | None = None
    confidence_interval: dict[str, float | str] | None = None
    explanation: str = ""
    plain_language_explanation: str = ""
    top_contributing_features: list[str] = field(default_factory=list)
    evidence_items: list[dict] = field(default_factory=list)
    therapist_review_status: ReviewStatus = "awaiting_review"
    differential_probabilities: dict[str, float] | None = None
    output_kind: str = "screening_support"
    inference_status: str = "preliminary"
    reference_cohort_probabilities: dict[str, float] = field(default_factory=dict)
    most_similar_reference_cohort: str | None = None
    similarity_probability: float | None = None
    report_eligible: bool = False
    safety_warnings: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)
```

- [x] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py::test_ai_screening_output_can_represent_reference_cohort_similarity -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clinical_workflow/models.py tests/test_reference_cohort_similarity_workflow.py
git commit -m "feat: extend AI output for reference cohort similarity"
```

---

### Task 2: Persist Preliminary and Reviewed Similarity Outputs Through Repository Methods

**Files:**
- Modify: `src/clinical_workflow/mock_repository.py`
- Modify: `src/therapist_backend/app.py`
- Test: `tests/test_reference_cohort_similarity_workflow.py`

- [x] **Step 1: Write failing repository test for preliminary output**

Append to `tests/test_reference_cohort_similarity_workflow.py`:

```python
from src.clinical_workflow import MockClinicalRepository  # noqa: E402


def test_repository_generates_preliminary_reference_cohort_similarity():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    output = repo.generate_reference_cohort_similarity_for_session(
        "SESSION-001",
        therapist,
        inference_status="preliminary",
    )

    assert output.output_kind == "reference_cohort_similarity"
    assert output.inference_status == "preliminary"
    assert output.report_eligible is False
    assert output.reference_cohort_probabilities
    assert output.most_similar_reference_cohort in output.reference_cohort_probabilities
    assert any(run.session_id == "SESSION-001" for run in repo.model_runs.values())
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py::test_repository_generates_preliminary_reference_cohort_similarity -v
```

Expected: FAIL with `AttributeError: 'MockClinicalRepository' object has no attribute 'generate_reference_cohort_similarity_for_session'`.

- [x] **Step 3: Implement repository method**

In `src/clinical_workflow/mock_repository.py`, import the predictor:

```python
from packages.ml.predict import predict_reference_cohort_similarity
```

Add method near `generate_ai_screening_output_for_session`:

```python
    def generate_reference_cohort_similarity_for_session(
        self,
        session_id: str,
        user: User,
        *,
        inference_status: str = "preliminary",
    ) -> AIScreeningOutput:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if user.role != "admin" and session.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only generate similarity for owned sessions.")

        feature_row = self.get_features_for_session_for_user(session_id, user)
        if feature_row is None:
            feature_row = self.extract_features_for_session(session_id, user)

        now = self._now()
        try:
            result = predict_reference_cohort_similarity(
                feature_row.core_features or feature_row.features,
                inference_status=inference_status,
            )
            report_eligible = inference_status == "reviewed"
            status = "reviewed" if report_eligible else "awaiting_review"
        except Exception as exc:  # noqa: BLE001
            result = {
                "model_version": "unavailable",
                "reference_cohort_probabilities": {},
                "most_similar_reference_cohort": None,
                "similarity_probability": None,
                "top_contributing_features": [],
                "plain_language_explanation": "Reference cohort similarity is unavailable for this transcript.",
                "safety_warnings": [{"code": "SIMILARITY_UNAVAILABLE", "message": str(exc)}],
            }
            report_eligible = False
            status = "needs_correction"

        self._ai_output_sequence += 1
        output = AIScreeningOutput(
            output_id=f"AI-OUTPUT-{self._ai_output_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            concern_level="review_support",
            model_version=result["model_version"],
            output_kind="reference_cohort_similarity",
            inference_status=inference_status,
            reference_cohort_probabilities=result["reference_cohort_probabilities"],
            most_similar_reference_cohort=result["most_similar_reference_cohort"],
            similarity_probability=result["similarity_probability"],
            report_eligible=report_eligible,
            safety_warnings=result.get("safety_warnings", []),
            plain_language_explanation=result["plain_language_explanation"],
            top_contributing_features=[
                item["feature_key"] if isinstance(item, dict) else str(item)
                for item in result.get("top_contributing_features", [])
            ],
            evidence_items=result.get("top_contributing_features", []),
            therapist_review_status=status,
            differential_probabilities=result["reference_cohort_probabilities"],
            screening_support_score=result["similarity_probability"],
            created_at=now,
        )
        self.ai_screening_outputs[output.output_id] = output

        self._model_run_sequence += 1
        self.model_runs[f"MODEL-RUN-{self._model_run_sequence:03d}"] = ModelRun(
            model_run_id=f"MODEL-RUN-{self._model_run_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            model_card_version=result["model_version"],
            feature_schema_version=feature_row.feature_schema_version,
            thresholds={"report_eligible": float(report_eligible)},
            calibration_metadata={
                "output_kind": "reference_cohort_similarity",
                "inference_status": inference_status,
                "report_eligible": int(report_eligible),
            },
            created_at=now,
        )
        self._audit(
            "reference_cohort_similarity_generated",
            actor_user_id=user.user_id,
            target_type="ai_screening_output",
            target_id=output.output_id,
            message=f"Generated {inference_status} reference cohort similarity for {session_id}.",
        )
        return replace(output)
```

- [x] **Step 4: Route FastAPI through repository**

In `src/therapist_backend/app.py`, change `/reference-cohort-similarity` to call:

```python
        try:
            result = repository.generate_reference_cohort_similarity_for_session(
                session_id,
                user,
                inference_status=inference_status,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return _jsonable(result)
```

- [x] **Step 5: Run repository and route tests**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py::test_repository_generates_preliminary_reference_cohort_similarity -v
pytest tests/test_clinical_pilot_backend_contract.py -q
```

Expected: PASS.

- [x] **Step 5a: Repair repository contract drift and preliminary status handling**

The mock repository also needed implementations for `list_processing_jobs_for_session_for_user`,
`list_clinical_speech_artifacts_for_session_for_user`, and `update_feature_review_disposition`
so it still satisfies `ClinicalRepository`. Preliminary safety warnings must leave
`ai_analysis_status` as `completed`; only a `SIMILARITY_UNAVAILABLE` warning marks analysis failed.

- [ ] **Step 6: Commit**

```bash
git add src/clinical_workflow/mock_repository.py src/therapist_backend/app.py tests/test_reference_cohort_similarity_workflow.py
git commit -m "feat: persist reference cohort similarity outputs"
```

---

### Task 3: Add Reviewed Similarity Refresh After Transcript Sign-Off

**Files:**
- Modify: `src/clinical_workflow/mock_repository.py`
- Modify: `src/therapist_backend/app.py`
- Test: `tests/test_reference_cohort_similarity_workflow.py`

- [x] **Step 1: Write failing sign-off refresh test**

Append:

```python
def test_transcript_signoff_runs_reviewed_similarity_refresh_without_auto_report():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    signed = repo.signoff_transcript_for_session("SESSION-001", therapist, "Reviewed for similarity refresh.")

    outputs = [
        output for output in repo.ai_screening_outputs.values()
        if output.session_id == "SESSION-001"
        and output.output_kind == "reference_cohort_similarity"
        and output.inference_status == "reviewed"
    ]

    assert signed.target_type == "transcript"
    assert outputs
    assert outputs[-1].report_eligible is True
    assert repo.sessions["SESSION-001"].report_status == "pending"
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py::test_transcript_signoff_runs_reviewed_similarity_refresh_without_auto_report -v
```

Expected: FAIL because sign-off does not generate reviewed similarity yet.

- [x] **Step 3: Update sign-off workflow**

In `src/clinical_workflow/mock_repository.py`, inside `signoff_transcript_for_session`, after transcript review state is saved, call:

```python
        try:
            self.extract_features_for_session(session_id, user)
            self.generate_reference_cohort_similarity_for_session(
                session_id,
                user,
                inference_status="reviewed",
            )
        except Exception as exc:  # noqa: BLE001
            self._audit(
                "reviewed_similarity_refresh_failed",
                actor_user_id=user.user_id,
                target_type="session",
                target_id=session_id,
                message=f"Transcript sign-off succeeded, but reviewed similarity refresh failed: {exc}",
            )
```

Keep transcript sign-off success independent from the similarity refresh failure.

- [x] **Step 4: Write failure isolation test**

Append:

```python
def test_similarity_failure_does_not_block_transcript_signoff(monkeypatch):
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    def fail_similarity(*_args, **_kwargs):
        raise RuntimeError("model artifact missing")

    monkeypatch.setattr(repo, "generate_reference_cohort_similarity_for_session", fail_similarity)

    signed = repo.signoff_transcript_for_session("SESSION-001", therapist, "Reviewed despite model issue.")

    assert signed.target_type == "transcript"
    assert any(
        log.action == "reviewed_similarity_refresh_failed"
        for log in repo.audit_logs
    )
```

- [x] **Step 5: Run tests**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py -q
pytest tests/test_clinical_speech_pipeline.py -q
```

Expected: PASS.

- [x] **Step 5a: Update backend contract tests for post-signoff refresh**

`tests/test_clinical_pilot_backend_contract.py` now expects transcript sign-off to complete
feature extraction and create a reviewed, report-eligible reference cohort similarity output.
The screening-support model run assertion now filters for `prototype-screening-support-v1`
instead of relying on insertion order because sign-off may create a similarity model run first.

- [ ] **Step 6: Commit**

```bash
git add src/clinical_workflow/mock_repository.py tests/test_reference_cohort_similarity_workflow.py
git commit -m "feat: refresh reviewed similarity after transcript signoff"
```

---

### Task 4: Enforce Reviewed-Only Report Output

**Files:**
- Modify: `src/clinical_workflow/mock_repository.py`
- Modify: `shared/src/services/report-service.js`
- Modify: `therapist-clinician-app/src/views/reports-view.js`
- Test: `tests/test_reference_cohort_similarity_workflow.py`
- Test: `therapist-clinician-app/src/__tests__/report.test.js`
- Test: `therapist-clinician-app/src/__tests__/reports-view.test.js`

- [x] **Step 1: Write backend report eligibility lookup test**

Append:

```python
def test_repository_returns_only_latest_reviewed_report_eligible_similarity():
    repo = MockClinicalRepository()
    therapist = repo.users["user_therapist_001"]

    preliminary = repo.generate_reference_cohort_similarity_for_session(
        "SESSION-001",
        therapist,
        inference_status="preliminary",
    )
    reviewed = repo.signoff_transcript_for_session("SESSION-001", therapist, "Reviewed.")
    output = repo.get_report_eligible_similarity_for_session("SESSION-001", therapist)

    assert preliminary.report_eligible is False
    assert reviewed.target_type == "transcript"
    assert output is not None
    assert output.inference_status == "reviewed"
    assert output.report_eligible is True
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py::test_repository_returns_only_latest_reviewed_report_eligible_similarity -v
```

Expected: FAIL with missing `get_report_eligible_similarity_for_session`.

- [x] **Step 3: Implement lookup**

In `src/clinical_workflow/mock_repository.py`, add:

```python
    def get_report_eligible_similarity_for_session(self, session_id: str, user: User) -> AIScreeningOutput | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if user.role != "admin" and session.owner_user_id != user.user_id:
            return None
        rows = [
            output for output in self.ai_screening_outputs.values()
            if output.session_id == session_id
            and output.output_kind == "reference_cohort_similarity"
            and output.inference_status == "reviewed"
            and output.report_eligible
        ]
        if not rows:
            return None
        return replace(max(rows, key=lambda output: output.created_at))
```

- [x] **Step 4: Update report service contract**

In `shared/src/services/report-service.js`, when reading AI outputs for reports, require:

```javascript
function isReportEligibleSimilarity(ai = {}) {
  return ai.output_kind === "reference_cohort_similarity"
    ? ai.inference_status === "reviewed" && ai.report_eligible === true
    : true;
}
```

Before adding the AI section:

```javascript
const ai = aiOutputs[s.session_id];
if (ai && !isReportEligibleSimilarity(ai)) {
  markdown += `- **Reference Cohort Similarity:** Not report-ready. Reviewed transcript similarity is required before export.\n`;
  return;
}
```

- [x] **Step 5: Add frontend report test**

In `therapist-clinician-app/src/__tests__/report.test.js`, add:

```javascript
it("does not include preliminary reference cohort similarity in exported report", () => {
  const markdown = buildProgressReportMarkdown(
    { display_label: "Child A", anonymized_child_code: "A001" },
    [{ session_id: "SESSION-PRELIM", session_date: "2026-06-05" }],
    { "SESSION-PRELIM": { features: { mlu: 2.1, ttr: 0.4 } } },
    {
      "SESSION-PRELIM": {
        output_kind: "reference_cohort_similarity",
        inference_status: "preliminary",
        report_eligible: false,
        most_similar_reference_cohort: "ASD",
        similarity_probability: 0.7
      }
    }
  );

  expect(markdown).toContain("Not report-ready");
  expect(markdown).not.toContain("ASD · 70%");
});
```

- [x] **Step 6: Run tests**

Run:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py -q
npm run test -- src/__tests__/report.test.js src/__tests__/reports-view.test.js
```

Expected: PASS.

- [x] **Step 6a: Enforce the same filter in backend report summary and printable preview**

`progress_summary_for_case` now ignores preliminary/non-report-eligible reference cohort outputs,
and `reports-view.js` uses a reportable AI-output filter so printable previews do not show
preliminary reference cohort text or fallback scores.

- [ ] **Step 7: Commit**

```bash
git add src/clinical_workflow/mock_repository.py shared/src/services/report-service.js therapist-clinician-app/src/views/reports-view.js tests/test_reference_cohort_similarity_workflow.py therapist-clinician-app/src/__tests__/report.test.js
git commit -m "feat: enforce reviewed-only similarity reports"
```

---

### Task 5: Finish Frontend Similarity States

**Files:**
- Modify: `therapist-clinician-app/src/services/audio-processing-api.js`
- Modify: `therapist-clinician-app/src/views/transcript-view.js`
- Create or modify: `therapist-clinician-app/src/__tests__/reference-cohort-similarity.test.js`

- [x] **Step 1: Write frontend mapping tests**

Create `therapist-clinician-app/src/__tests__/reference-cohort-similarity.test.js`:

```javascript
import { describe, expect, it } from "vitest";
import { mapBackendProcessingResultToFrontend } from "../services/audio-processing-api.js";

describe("reference cohort similarity frontend mapping", () => {
  it("maps preliminary similarity and safety warnings from backend output", () => {
    const result = mapBackendProcessingResultToFrontend(
      {
        transcript: { transcript_id: "TRANSCRIPT-REF", transcript_text: "@Begin\n@End\n" },
        transcript_lines: [],
        qa: { status: "needs_review", quality_score: 80, issues: [] },
        features: { feature_schema_version: "14-feature-schema", features: {}, extraction_status: "preliminary" },
        reference_cohort_similarity: {
          output_kind: "reference_cohort_similarity",
          inference_status: "preliminary",
          report_eligible: false,
          reference_cohort_probabilities: { ASD: 0.6, TD: 0.2, DD: 0.2 },
          most_similar_reference_cohort: "ASD",
          similarity_probability: 0.6,
          safety_warnings: [{ code: "PRELIMINARY_TRANSCRIPT", message: "Review required." }],
          plain_language_explanation: "This transcript has feature patterns most similar to the ASD reference cohort. It is not a diagnosis."
        }
      },
      {
        session: { session_id: "SESSION-REF", case_id: "CASE-REF", owner_user_id: "user_therapist_001" },
        childCase: { case_id: "CASE-REF" },
        currentUser: { user_id: "user_therapist_001" },
        transcriptCount: 1
      }
    );

    expect(result.aiOutput.output_kind).toBe("reference_cohort_similarity");
    expect(result.aiOutput.inference_status).toBe("preliminary");
    expect(result.aiOutput.report_eligible).toBe(false);
    expect(result.aiOutput.safety_warnings[0].code).toBe("PRELIMINARY_TRANSCRIPT");
  });
});
```

- [x] **Step 2: Run test**

Run:

```bash
npm run test -- src/__tests__/reference-cohort-similarity.test.js
```

Expected: PASS if mapping already works; otherwise FAIL with missing mapped fields.

- [x] **Step 3: Patch mapping if needed**

In `therapist-clinician-app/src/services/audio-processing-api.js`, ensure `aiPayload` is spread before defaults:

```javascript
const aiOutput = aiPayload
  ? {
      ...aiPayload,
      session_id: session.session_id,
      case_id: session.case_id,
      owner_user_id: ownerUserId,
      output_kind: aiPayload.output_kind || "reference_cohort_similarity",
      inference_status: aiPayload.inference_status || "preliminary",
      report_eligible: Boolean(aiPayload.report_eligible),
      safety_warnings: aiPayload.safety_warnings || [],
      reference_cohort_probabilities:
        aiPayload.reference_cohort_probabilities || aiPayload.differential_probabilities || {},
      most_similar_reference_cohort: aiPayload.most_similar_reference_cohort || null,
      similarity_probability: aiPayload.similarity_probability ?? aiPayload.screening_support_score ?? null,
      model_version: aiPayload.model_version || "screening-support-v0.2.0",
      confidence_interval: aiPayload.confidence_interval ?? null,
      evidence_items: aiPayload.evidence_items || [],
      top_contributing_features: aiPayload.top_contributing_features || [],
      plain_language_explanation:
        aiPayload.plain_language_explanation ||
        "This output highlights reference cohort similarity for clinical review. It is not a diagnosis.",
      therapist_review_status: aiPayload.therapist_review_status || "requires_transcript_review",
      explanation:
        aiPayload.explanation ||
        "AI-assisted explanation requires transcript review before clinical interpretation. It is not a diagnosis.",
      created_at: aiPayload.created_at || now
    }
  : null;
```

- [x] **Step 4: Improve transcript panel states**

In `therapist-clinician-app/src/views/transcript-view.js`, update the similarity panel to display:

```javascript
const isUnavailable = aiOutput.status === "unavailable" || aiOutput.safety_warnings?.some(w => w.code === "SIMILARITY_UNAVAILABLE");
const panelTitle = isUnavailable ? "Reference Cohort Similarity Unavailable" : "Reference Cohort Similarity";
```

Use the existing warning block for unavailable messages and keep the same Clinical Teal styling.

- [x] **Step 5: Run frontend tests and build**

Run:

```bash
npm run test -- src/__tests__/reference-cohort-similarity.test.js src/__tests__/audio-processing-api.test.js src/__tests__/transcript-workflow.test.js
npm run build
```

Expected: PASS and production build succeeds.

- [x] **Step 6: Browser smoke**

Run the existing local app and verify:

```bash
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`, sign in as `therapist@example.test`, navigate to Transcripts, and confirm:

- panel title says `Reference Cohort Similarity`,
- preliminary badge appears before review,
- no text says `ASD Risk Probability`,
- unavailable output shows recovery wording.

- [ ] **Step 7: Commit**

```bash
git add therapist-clinician-app/src/services/audio-processing-api.js therapist-clinician-app/src/views/transcript-view.js therapist-clinician-app/src/__tests__/reference-cohort-similarity.test.js
git commit -m "feat: complete reference similarity UI states"
```

---

### Task 6: Update API Contract and Safety Regression Coverage

**Files:**
- Modify: `docs/API_CONTRACT.md`
- Modify: `therapist-clinician-app/src/__tests__/safety-guardrails.test.js`
- Test: `tests/test_clinical_pilot_backend_contract.py`

- [x] **Step 1: Add API contract section**

In `docs/API_CONTRACT.md`, add:

```markdown
## Reference Cohort Similarity

`POST /api/sessions/{session_id}/reference-cohort-similarity`

Generates or returns a Reference Cohort Similarity Output for therapist review.
This endpoint does not diagnose ASD.

Response fields:

- `output_kind`: `reference_cohort_similarity`
- `inference_status`: `preliminary` or `reviewed`
- `reference_cohort_probabilities`: internal cohort probability map
- `most_similar_reference_cohort`: label with the highest similarity
- `similarity_probability`: probability for the most similar reference cohort
- `report_eligible`: `true` only for reviewed output that may appear in reports
- `safety_warnings`: quality or availability warnings
- `plain_language_explanation`: user-facing similarity wording

Preliminary output may support review prioritization but must not be exported as
a reviewed clinical result.
```

- [x] **Step 2: Add safety regression test**

In `therapist-clinician-app/src/__tests__/safety-guardrails.test.js`, add:

```javascript
it("does not expose diagnostic probability wording in reference similarity UI", () => {
  const forbidden = [
    "ASD Risk Probability",
    "probability of ASD",
    "diagnosis probability",
    "predicted diagnosis"
  ];
  const files = [
    "src/views/transcript-view.js",
    "src/views/reports-view.js",
    "../shared/src/services/report-service.js"
  ];
  for (const file of files) {
    const body = fs.readFileSync(path.join(root, "therapist-clinician-app", file), "utf8");
    for (const phrase of forbidden) {
      expect(body).not.toContain(phrase);
    }
  }
});
```

If the existing test file defines a different `root`, adapt the `path.join` base to match that file's current pattern.

- [x] **Step 3: Run contract and safety tests**

Run:

```bash
pytest tests/test_clinical_pilot_backend_contract.py -q
npm run test -- src/__tests__/safety-guardrails.test.js
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/API_CONTRACT.md therapist-clinician-app/src/__tests__/safety-guardrails.test.js
git commit -m "docs: document reference cohort similarity contract"
```

---

### Task 7: Research-Grade Training Follow-Up Plan

**Files:**
- Create: `docs/superpowers/plans/YYYY-MM-DD-reference-cohort-training-hardening-plan.md`

- [x] **Step 1: Create follow-up plan stub with concrete scope**

Create a separate plan for:

- CLI arguments for `packages/ml/train_model.py`,
- group-based cross-validation,
- bootstrap confidence intervals,
- calibration report,
- dataset card generation,
- compatibility export regeneration command,
- no acoustic classifier inputs.

Use this header:

```markdown
# Reference Cohort Training Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the training pipeline from baseline functionality to research-grade, repeatable model evaluation.

**Architecture:** Keep runtime inference stable while improving offline training and evaluation artifacts. Training changes must not alter the clinical workflow unless a new runtime artifact is explicitly generated and reviewed.

**Tech Stack:** Python, pandas, scikit-learn, optional XGBoost/LightGBM, joblib, pytest.

---
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/plans/*reference-cohort-training-hardening-plan.md
git commit -m "docs: plan reference cohort training hardening"
```

---

## Verification Summary

After all tasks:

```bash
pytest tests/test_reference_cohort_similarity_workflow.py tests/test_clinical_speech_pipeline.py tests/test_clinical_pilot_backend_contract.py -q
cd therapist-clinician-app
npm run test -- src/__tests__/reference-cohort-similarity.test.js src/__tests__/audio-processing-api.test.js src/__tests__/transcript-workflow.test.js src/__tests__/report.test.js src/__tests__/reports-view.test.js src/__tests__/safety-guardrails.test.js
npm run build
```

Expected:

- all tests pass,
- production build succeeds,
- preliminary similarity never appears as report-ready,
- reviewed transcript sign-off succeeds even if similarity refresh fails,
- reviewed + report-eligible similarity is the only similarity output allowed in reports,
- no user-facing diagnostic probability wording appears in transcript or report surfaces.

## Self-Review

- Spec coverage: persistence, reviewed gate, failure isolation, report eligibility, frontend states, contract docs, and training follow-up are covered.
- Placeholder check: no unresolved placeholders or unspecified edge handling remains in the tasks.
- Type consistency: tasks consistently use `output_kind`, `inference_status`, `reference_cohort_probabilities`, `most_similar_reference_cohort`, `similarity_probability`, `report_eligible`, and `safety_warnings`.
