# ML Reference Evidence Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved Version 1 research-first reference evidence workflow: auditable canonical data, supported English reference cells, research Gate 1 validation, and fail-closed therapist evidence cards without probabilities or predicted classes.

**Architecture:** Offline builders create immutable, checksummed reference and research artifacts from traceable public-corpus rows. The existing FastAPI ML provider boundary loads only compatible artifacts and persists evidence through the existing immutable `MLResult` path. Therapist App v2 requests the reference provider explicitly and renders two parallel modules: pattern-review status and independent profile evidence cards.

**Tech Stack:** Python 3, pandas, scikit-learn, Pydantic, FastAPI, pytest, Next.js, React, TypeScript, Vitest, Testing Library

---

## File Structure

### New files

- `packages/ml/reference_contracts.py` — shared labels, support thresholds, artifact manifest types, and safe UI mappings.
- `packages/ml/reference_dataset.py` — canonical CSV merge, provenance audit, deduplication, and participant grouping.
- `packages/ml/reference_artifacts.py` — supported reference-cell construction and immutable artifact output.
- `packages/ml/gate1_validation.py` — grouped/corpus-held-out Gate 1 research evaluation and promotion decision.
- `scripts/build_ml_reference_evidence.py` — CLI orchestrator for dataset, cohorts, manifest, and research report.
- `apps/api/app/services/ml_providers/reference_evidence.py` — fail-closed runtime provider.
- `apps/api/app/services/ml_providers/reference_feature_adapter.py` — exact runtime-to-canonical feature mapping and missing-feature readiness.
- `tests/test_ml_reference_dataset.py` — canonical merge and deduplication tests.
- `tests/test_ml_reference_artifacts.py` — participant/corpus support and manifest tests.
- `tests/test_gate1_validation.py` — grouped evaluation, calibration, and promotion-gate tests.
- `tests/fixtures/reference_feature_parity/english_toyplay.cha` — non-identifying golden CHAT fixture.
- `tests/fixtures/reference_feature_parity/expected.json` — expected canonical feature values and tolerances.
- `tests/test_reference_feature_parity.py` — research/runtime extractor parity test.
- `apps/api/tests/test_reference_evidence_provider.py` — provider availability, evidence, abstention, and checksum tests.
- `docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md` — approval roles, promotion, rollback, incident, and retention runbook.

### Modified files

- `apps/api/app/schemas/clinical.py` — evidence-module and provenance schemas on `MLResult`.
- `apps/api/app/services/ml_providers/base.py` — provider result carries pattern and profile evidence.
- `apps/api/app/services/ml_providers/registry.py` — register the reference provider without replacing the safe default.
- `apps/api/app/services/ml_review_service.py` — persist evidence and artifact provenance through the existing immutable result path.
- `apps/api/app/api/v1/routes/ml_review.py` — existing provider-selectable endpoint remains the public boundary.
- `apps/api/app/core/config.py` — artifact directory and runtime timeout settings.
- `apps/api/app/repositories/mock_repository.py` — no new collection; verify existing `ml_results` snapshot covers new fields.
- `apps/api/app/repositories/sqlalchemy_repository.py` — no new table; verify JSON payload round-trip for new fields.
- `apps/api/tests/test_workflow.py` — provider registry, stale-result, consent, and wording integration tests.
- `apps/therapist-app-v2/src/lib/workflow.ts` — evidence types, request provider ID, and response normalization.
- `apps/therapist-app-v2/src/components/session-workspace-client.tsx` — parallel evidence modules and explicit unavailable states.
- `apps/therapist-app-v2/src/__tests__/pages.test.tsx` — safe rendering, collapsed details, offline, and stale behavior.
- `scripts/build_reference_cohorts.py` — participant key and two-corpus support semantics for legacy descriptive artifacts.
- `tests/test_reference_cohort_builder.py` — regression coverage for participant-based support.
- `src/reference_engine.py` — profile-level abstention and no percentile calculation for unsupported cells.
- `tests/test_reference_engine.py` — independent supported/unsupported profile behavior.
- `docs/ML_DECISION_SUPPORT_MODEL_CARD.md` — Version 1 intended use, artifacts, promotion gate, and limitations.
- `README.md` — builder and validation commands.
- `CHANGELOG.md` — add only when runtime behavior is enabled.

## Task 1: Lock Shared Reference Contracts

**Files:**
- Create: `packages/ml/reference_contracts.py`
- Test: `tests/test_ml_reference_artifacts.py`

- [ ] **Step 1: Write the failing contract tests**

```python
from packages.ml.reference_contracts import (
    MIN_CORPORA_PER_CELL,
    MIN_PARTICIPANTS_PER_CELL,
    original_group,
    presentation_group,
)


def test_other_is_presentation_only():
    assert original_group("SLI") == "STI"
    assert presentation_group("LT") == "OTHER"
    assert presentation_group("STI") == "OTHER"
    assert presentation_group("HL") == "OTHER"
    assert presentation_group("ASD") == "ASD"


def test_reference_support_thresholds_are_preregistered():
    assert MIN_PARTICIPANTS_PER_CELL == 20
    assert MIN_CORPORA_PER_CELL == 2
```

- [ ] **Step 2: Run the tests and verify import failure**

Run:

```bash
pytest tests/test_ml_reference_artifacts.py -q
```

Expected: FAIL because `packages.ml.reference_contracts` does not exist.

- [ ] **Step 3: Implement the shared contracts**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MIN_PARTICIPANTS_PER_CELL = 20
MIN_CORPORA_PER_CELL = 2
SUPPORTED_LANGUAGE = "eng"

OriginalGroup = Literal["TD", "DD", "ASD", "LT", "STI", "HL"]
PresentationGroup = Literal["TD", "DD", "ASD", "OTHER"]

_ALIASES = {
    "TD": "TD",
    "TYP": "TD",
    "CONTROL": "TD",
    "DD": "DD",
    "ASD": "ASD",
    "LT": "LT",
    "SLI": "STI",
    "STI": "STI",
    "DLD": "STI",
    "HL": "HL",
}


def original_group(value: object) -> OriginalGroup:
    normalized = _ALIASES.get(str(value or "").strip().upper())
    if normalized is None:
        raise ValueError(f"Unsupported reference group: {value}")
    return normalized  # type: ignore[return-value]


def presentation_group(value: object) -> PresentationGroup:
    group = original_group(value)
    return "OTHER" if group in {"LT", "STI", "HL"} else group


@dataclass(frozen=True)
class SupportDecision:
    supported: bool
    participant_count: int
    corpus_count: int
    reason_code: str | None


def evaluate_support(participant_count: int, corpus_count: int) -> SupportDecision:
    if participant_count < MIN_PARTICIPANTS_PER_CELL:
        return SupportDecision(False, participant_count, corpus_count, "insufficient_participants")
    if corpus_count < MIN_CORPORA_PER_CELL:
        return SupportDecision(False, participant_count, corpus_count, "insufficient_corpus_diversity")
    return SupportDecision(True, participant_count, corpus_count, None)
```

- [ ] **Step 4: Run the contract tests**

Run:

```bash
pytest tests/test_ml_reference_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/ml/reference_contracts.py tests/test_ml_reference_artifacts.py
git commit -m "feat(ml): define reference evidence contracts" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 2: Build the Canonical Auditable Dataset

**Files:**
- Create: `packages/ml/reference_dataset.py`
- Create: `tests/test_ml_reference_dataset.py`

- [ ] **Step 1: Write failing merge and deduplication tests**

```python
import pandas as pd

from packages.ml.reference_dataset import build_canonical_reference_rows


def test_canonical_rows_preserve_original_and_presentation_groups():
    combined = pd.DataFrame([{
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "ASD",
        "age_months": 50,
        "total_utterances": 10,
    }])
    curated = pd.DataFrame([{
        "participant_id": "P2",
        "source_path": "data/lt.cha",
        "corpus": "Rescorla",
        "group": "LT",
        "age_months": 48,
        "total_utterances": 12,
    }])

    result = build_canonical_reference_rows(combined, curated)

    assert set(result.rows["original_group"]) == {"ASD", "LT"}
    assert set(result.rows["presentation_group"]) == {"ASD", "OTHER"}
    assert result.rows["participant_key"].nunique() == 2


def test_exact_overlap_is_excluded_and_audited():
    row = {
        "participant_id": "P1",
        "source_path": "data/shared.cha",
        "corpus": "Eigsti",
        "group": "TD",
        "age_months": 42,
        "total_utterances": 10,
    }
    result = build_canonical_reference_rows(pd.DataFrame([row]), pd.DataFrame([row]))

    assert len(result.rows) == 1
    assert "duplicate_source_row" in set(result.audit["reason_code"])
```

- [ ] **Step 2: Run the tests**

Run:

```bash
pytest tests/test_ml_reference_dataset.py -q
```

Expected: FAIL because the dataset builder does not exist.

- [ ] **Step 3: Implement canonical row construction**

Implement `CanonicalDatasetResult(rows, audit, dataset_hash)` and:

```python
CANONICAL_METADATA = [
    "source_dataset",
    "source_path",
    "source_row_hash",
    "corpus",
    "participant_key",
    "session_key",
    "original_group",
    "presentation_group",
    "age_months",
    "language",
    "task_type",
    "extractor_version",
    "feature_schema_version",
]


def _participant_key(row: pd.Series) -> str:
    participant = str(row.get("participant_id") or row.get("child") or row.get("file_id") or "").strip()
    corpus = str(row.get("corpus") or "unknown").strip()
    if not participant:
        raise ValueError("missing_participant_key")
    return f"{corpus}:{participant}"


def _source_row_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
```

The builder must:

- normalize labels with `original_group`;
- derive `presentation_group`;
- keep all 14 canonical features in `src.feature_schema.FEATURES`;
- require traceable participant and corpus values;
- deduplicate source path first, then identical row hash;
- record every exclusion in the audit table;
- sort deterministically before hashing.

- [ ] **Step 4: Add participant-session leakage regression**

```python
def test_repeated_sessions_share_one_participant_key():
    curated = pd.DataFrame([
        {"participant_id": "P1", "source_path": "a.cha", "corpus": "Gillam", "group": "TD"},
        {"participant_id": "P1", "source_path": "b.cha", "corpus": "Gillam", "group": "TD"},
    ])
    result = build_canonical_reference_rows(pd.DataFrame(), curated)
    assert result.rows["participant_key"].nunique() == 1
    assert result.rows["session_key"].nunique() == 2
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_ml_reference_dataset.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/ml/reference_dataset.py tests/test_ml_reference_dataset.py
git commit -m "feat(ml): build auditable canonical reference rows" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 3: Enforce Participant and Corpus Support in Reference Artifacts

**Files:**
- Create: `packages/ml/reference_artifacts.py`
- Modify: `scripts/build_reference_cohorts.py`
- Modify: `tests/test_reference_cohort_builder.py`
- Modify: `tests/test_ml_reference_artifacts.py`

- [ ] **Step 1: Write failing independent-support tests**

```python
from packages.ml.reference_artifacts import build_reference_cells


def test_twenty_sessions_from_one_participant_do_not_support_a_cell(canonical_rows):
    rows = canonical_rows(participants=1, sessions_each=20, corpora=["CorpusA"])
    cells = build_reference_cells(rows)
    cell = cells.iloc[0]
    assert cell["participant_count"] == 1
    assert cell["supported"] is False
    assert cell["reason_code"] == "insufficient_participants"


def test_twenty_participants_from_one_corpus_still_abstain(canonical_rows):
    rows = canonical_rows(participants=20, sessions_each=1, corpora=["CorpusA"])
    cell = build_reference_cells(rows).iloc[0]
    assert cell["participant_count"] == 20
    assert cell["corpus_count"] == 1
    assert cell["reason_code"] == "insufficient_corpus_diversity"
```

- [ ] **Step 2: Run tests**

Run:

```bash
pytest tests/test_ml_reference_artifacts.py tests/test_reference_cohort_builder.py -q
```

Expected: FAIL because current support uses row count.

- [ ] **Step 3: Implement supported-cell artifacts**

`build_reference_cells()` groups by:

```python
CELL_KEY = ["language", "age_band_12mo", "task_type", "original_group"]
```

For each cell it writes:

```python
{
    "language": language,
    "age_band_12mo": age_band,
    "task_type": task,
    "original_group": group,
    "presentation_group": presentation_group(group),
    "participant_count": participant_count,
    "session_count": len(cell),
    "corpus_count": corpus_count,
    "corpora": ";".join(sorted(cell["corpus"].unique())),
    "supported": support.supported,
    "reason_code": support.reason_code or "",
}
```

Distribution columns are populated only when `supported` is true. Unsupported
cells receive empty distribution values.

- [ ] **Step 4: Update the legacy cohort builder**

Add `participant_key` to `METADATA_COLUMNS`, derive it from corpus plus CHAT
child identity/source path, and replace:

```python
cohort_n = int(len(cohort))
confidence_flag = "ok" if cohort_n >= 20 else "low_n"
```

with:

```python
participant_count = int(cohort["participant_key"].nunique())
corpus_count = int(cohort["corpus"].nunique())
support = evaluate_support(participant_count, corpus_count)
cohort_n = participant_count
confidence_flag = "ok" if support.supported else "low_support"
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_ml_reference_artifacts.py tests/test_reference_cohort_builder.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/ml/reference_artifacts.py scripts/build_reference_cohorts.py tests/test_ml_reference_artifacts.py tests/test_reference_cohort_builder.py
git commit -m "feat(ml): require participant and corpus support" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 4: Add Immutable Artifact Manifests

**Files:**
- Modify: `packages/ml/reference_artifacts.py`
- Create: `scripts/build_ml_reference_evidence.py`
- Modify: `tests/test_ml_reference_artifacts.py`

- [ ] **Step 1: Write the failing manifest test**

```python
import json

from packages.ml.reference_artifacts import write_reference_artifacts


def test_manifest_binds_dataset_schema_cohort_and_checksums(tmp_path, canonical_result):
    paths = write_reference_artifacts(canonical_result, tmp_path)
    manifest = json.loads(paths.manifest.read_text())
    assert manifest["dataset_hash"] == canonical_result.dataset_hash
    assert manifest["feature_schema_version"] == "reference-core-14-v1"
    assert manifest["support_policy"] == {
        "minimum_unique_participants": 20,
        "minimum_corpora": 2,
    }
    assert len(manifest["files"]["cohorts"]["sha256"]) == 64
```

- [ ] **Step 2: Run the test**

Run:

```bash
pytest tests/test_ml_reference_artifacts.py::test_manifest_binds_dataset_schema_cohort_and_checksums -q
```

Expected: FAIL.

- [ ] **Step 3: Implement atomic artifact writes**

Write to a temporary directory, compute SHA-256 for:

- `canonical_rows.csv`;
- `dataset_audit.csv`;
- `reference_cells.csv`; and
- `gate1_validation.json` when present.

Then write `manifest.json` last and atomically rename the candidate directory
to its versioned destination.

The manifest must contain:

```python
{
    "artifact_type": "ml_reference_evidence",
    "artifact_version": artifact_version,
    "dataset_hash": canonical.dataset_hash,
    "extractor_version": extractor_version,
    "feature_schema_version": "reference-core-14-v1",
    "cohort_version": artifact_version,
    "rule_map_version": "clinician-options-v1",
    "supported_language": "eng",
    "support_policy": {
        "minimum_unique_participants": 20,
        "minimum_corpora": 2,
    },
    "files": file_checksums,
}
```

- [ ] **Step 4: Add the CLI**

The CLI loads:

```python
combined = pd.read_csv(project_root / "data/combined_features.csv")
curated = pd.read_csv(project_root / "data/curated_group_features.csv")
canonical = build_canonical_reference_rows(combined, curated)
write_reference_artifacts(canonical, output_dir)
```

Arguments:

```text
--combined
--curated
--output-dir
--artifact-version
```

- [ ] **Step 5: Run tests and a temporary smoke build**

Run:

```bash
pytest tests/test_ml_reference_artifacts.py -q
python scripts/build_ml_reference_evidence.py --output-dir /tmp/asd-reference-evidence-smoke --artifact-version smoke
```

Expected: tests PASS; command writes a manifest and CSV artifacts under the
temporary directory without transcript text or direct identifiers.

- [ ] **Step 6: Commit**

```bash
git add packages/ml/reference_artifacts.py scripts/build_ml_reference_evidence.py tests/test_ml_reference_artifacts.py
git commit -m "feat(ml): write immutable reference evidence artifacts" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 5: Verify Training and Runtime Feature Parity

**Files:**
- Create: `tests/fixtures/reference_feature_parity/english_toyplay.cha`
- Create: `tests/fixtures/reference_feature_parity/expected.json`
- Create: `tests/test_reference_feature_parity.py`
- Modify: `packages/ml/reference_contracts.py`

- [ ] **Step 1: Add a non-identifying golden CHAT fixture**

Use fixed speakers and no real identifiers:

```text
@UTF8
@Begin
@Languages:	eng
@Participants:	CHI DemoChild Target_Child, THER DemoTherapist Investigator
@ID:	eng|Demo|CHI|4;02.00|female|||Target_Child|||
@Types:	cross, toyplay, TD
*THER:	what do you see ?
*CHI:	I see a blue car .
*THER:	what is next ?
*CHI:	car car .
*CHI:	xxx .
@End
```

- [ ] **Step 2: Write the failing parity test**

```python
import json
from pathlib import Path

from packages.features.transcript_features import extract_transcript_features
from src.chat_feature_extractor import extract_chat_features


def test_golden_fixture_matches_research_and_runtime_extractors():
    root = Path("tests/fixtures/reference_feature_parity")
    expected = json.loads((root / "expected.json").read_text())
    research = extract_chat_features(root / "english_toyplay.cha")
    runtime = extract_transcript_features(root / "english_toyplay.cha")["canonical_features"]
    for feature, rule in expected["features"].items():
        assert abs(float(research[feature]) - float(runtime[feature])) <= rule["tolerance"]
        assert abs(float(runtime[feature]) - float(rule["value"])) <= rule["tolerance"]
```

- [ ] **Step 3: Run the parity test**

Run:

```bash
pytest tests/test_reference_feature_parity.py -q
```

Expected: FAIL for any semantic mismatch between extractors.

- [ ] **Step 4: Reconcile canonical extraction**

Move any divergent canonical formula into the shared extraction path used by
both `src.chat_feature_extractor` and
`packages.features.transcript_features`. Do not loosen tolerances to hide a
semantic mismatch.

Define explicit tolerances:

```python
FEATURE_TOLERANCES = {
    feature: 0.0 for feature in FEATURES
}
FEATURE_TOLERANCES.update({
    "age_months": 0.01,
    "mlu": 0.001,
    "mluw": 0.001,
    "ttr": 0.0001,
    "unintelligible_ratio": 0.0001,
    "question_ratio": 0.0001,
    "echolalia_ratio": 0.0001,
})
```

- [ ] **Step 5: Run focused feature tests**

Run:

```bash
pytest tests/test_reference_feature_parity.py tests/test_feature_schema.py apps/api/tests/test_feature_provider.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/reference_feature_parity tests/test_reference_feature_parity.py packages/ml/reference_contracts.py src/chat_feature_extractor.py packages/features/transcript_features.py
git commit -m "test(ml): enforce canonical feature parity" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 6: Implement Research Gate 1 Validation

**Files:**
- Create: `packages/ml/gate1_validation.py`
- Create: `tests/test_gate1_validation.py`
- Modify: `scripts/build_ml_reference_evidence.py`

- [ ] **Step 1: Write failing split and gate tests**

```python
from packages.ml.gate1_validation import PromotionGate, evaluate_gate1


def test_participant_never_crosses_train_and_test(canonical_rows):
    result = evaluate_gate1(canonical_rows, random_state=42)
    for split in result.split_audit:
        assert set(split.train_participants).isdisjoint(split.test_participants)


def test_failed_sensitivity_lower_bound_keeps_candidate_research_only():
    gate = PromotionGate(
        sensitivity_ci_lower=0.79,
        specificity=0.80,
        ece=0.05,
        brier=0.10,
        baseline_brier=0.20,
        abstention_rate=0.10,
        corpus_holdout_completed=True,
        feature_parity_passed=True,
    )
    assert gate.passed is False
    assert "sensitivity_ci_lower" in gate.failed_reasons
```

- [ ] **Step 2: Run tests**

Run:

```bash
pytest tests/test_gate1_validation.py -q
```

Expected: FAIL.

- [ ] **Step 3: Implement grouped and corpus-held-out evaluation**

Use:

```python
Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("classifier", LogisticRegression(
        class_weight="balanced",
        max_iter=2000,
        random_state=random_state,
    )),
])
```

Requirements:

- label is `original_group != "TD"`;
- use `StratifiedGroupKFold` by participant;
- run leave-one-corpus-out evaluations where both classes are present;
- calibration is fit inside training folds only;
- bootstrap resampling uses participant IDs;
- report sensitivity, specificity, macro-F1, ROC-AUC, PR-AUC, Brier, ECE,
  confidence intervals, abstention, and split audit;
- no model artifact is marked promoted unless the complete gate passes.

- [ ] **Step 4: Encode the preregistered gate**

```python
passed = (
    sensitivity_ci_lower >= 0.80
    and specificity >= 0.60
    and ece <= 0.10
    and brier <= baseline_brier
    and abstention_rate <= 0.40
    and corpus_holdout_completed
    and feature_parity_passed
)
```

Subgroups without adequate evidence use `status="not_evaluable"` and are never
reported as passing.

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_gate1_validation.py -q
```

Expected: PASS.

- [ ] **Step 6: Integrate the research report into the CLI**

The CLI writes `gate1_validation.json` and adds:

```python
manifest["gate1"] = {
    "status": "promoted_candidate" if report.promotion_gate.passed else "research_only",
    "report_sha256": sha256_file(report_path),
}
```

It must not register or activate the runtime provider.

- [ ] **Step 7: Commit**

```bash
git add packages/ml/gate1_validation.py tests/test_gate1_validation.py scripts/build_ml_reference_evidence.py
git commit -m "feat(ml): validate research Gate 1 with promotion gates" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 7: Make the Reference Engine Abstain Per Profile

**Files:**
- Modify: `src/reference_engine.py`
- Modify: `tests/test_reference_engine.py`

- [ ] **Step 1: Write failing profile-level abstention tests**

```python
def test_supported_profile_returns_distribution_while_unsupported_profile_abstains(tmp_path):
    features_path, cohorts_path = _write_reference_csvs_with_support(tmp_path)
    result = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=_missing_clan_path(tmp_path),
    ).compare(features=_feature_payload(21), age_months=50, task_type="toyplay")

    td = next(item for item in result.cohorts if item.group == "TD")
    asd = next(item for item in result.cohorts if item.group == "ASD")
    assert td.status == "comparable_patterns_observed"
    assert td.feature_comparisons
    assert asd.status == "not_available"
    assert asd.feature_comparisons == []
    assert asd.reason_code == "insufficient_participants"
```

- [ ] **Step 2: Run tests**

Run:

```bash
pytest tests/test_reference_engine.py -q
```

Expected: FAIL because unsupported cohorts still return percentiles.

- [ ] **Step 3: Extend cohort output**

Add to `CohortComparison`:

```python
status: str
reason_code: str | None
participant_count: int
corpus_count: int
presentation_group: str
```

Before calculating percentiles:

```python
supported = str(cohort_row.get("supported", "")).lower() == "true"
if not supported:
    cohorts.append(CohortComparison(
        group=group,
        presentation_group=presentation_group(group),
        status="not_available",
        reason_code=str(cohort_row.get("reason_code") or "insufficient_reference_data"),
        participant_count=int(cohort_row.get("participant_count") or 0),
        corpus_count=int(cohort_row.get("corpus_count") or 0),
        cohort_n=int(cohort_row.get("participant_count") or 0),
        confidence_flag="low_support",
        corpora=str(cohort_row.get("corpora", "")),
        design_types=str(cohort_row.get("design_types", "")),
        feature_comparisons=[],
        clan_metric_comparisons=[],
    ))
    continue
```

- [ ] **Step 4: Strengthen prohibited wording**

Extend the wording blocklist with:

```python
{
    "normal range",
    "predicted class",
    "predicted diagnosis",
    "diagnostic confidence",
    "winner",
}
```

- [ ] **Step 5: Run reference tests**

Run:

```bash
pytest tests/test_reference_engine.py tests/test_reference_similarity.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/reference_engine.py tests/test_reference_engine.py tests/test_reference_similarity.py
git commit -m "feat(reference): abstain independently by profile" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 8: Add Evidence Schemas to the Existing ML Result

**Files:**
- Modify: `apps/api/app/schemas/clinical.py`
- Modify: `apps/api/app/services/ml_providers/base.py`
- Modify: `apps/api/app/services/ml_providers/rule_based.py`
- Modify: `apps/api/app/services/ml_review_service.py`
- Modify: `apps/api/tests/test_reference_evidence_provider.py`

- [ ] **Step 1: Write failing schema tests**

```python
from app.schemas.clinical import (
    EvidenceAvailability,
    PatternEvidence,
    ProfileEvidence,
)


def test_evidence_models_do_not_require_scores():
    profile = ProfileEvidence(
        profile_code="ASD",
        presentation_group="ASD",
        status="not_available",
        availability=EvidenceAvailability(
            state="insufficient_reference_data",
            reason_code="insufficient_participants",
            message="This public-corpus profile does not have enough independent participants.",
            workflow_can_continue=True,
        ),
        participant_count=17,
        corpus_count=1,
    )
    assert profile.model_dump().get("probability") is None
```

- [ ] **Step 2: Run tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py -q
```

Expected: FAIL.

- [ ] **Step 3: Add safe evidence schemas**

```python
EvidenceState = Literal[
    "available",
    "input_action_required",
    "unsupported_scope",
    "insufficient_reference_data",
    "system_unavailable",
]


class EvidenceAvailability(BaseModel):
    state: EvidenceState
    reason_code: str | None = None
    message: str
    workflow_can_continue: bool
    next_step: str | None = None


class AssociatedFeatureEvidence(BaseModel):
    feature_name: str
    observed_value: float | int | None
    position: Literal["below_iqr", "within_iqr", "above_iqr", "missing"]
    q1: float | None = None
    median: float | None = None
    q3: float | None = None
    caveat: str


class ProfileEvidence(BaseModel):
    profile_code: Literal["TD", "DD", "ASD", "LT", "STI", "HL"]
    presentation_group: Literal["TD", "DD", "ASD", "OTHER"]
    status: Literal["comparable_patterns_observed", "limited_comparison", "not_available"]
    availability: EvidenceAvailability
    participant_count: int
    corpus_count: int
    associated_features: list[AssociatedFeatureEvidence] = Field(default_factory=list)
    review_state: EvidenceReviewState = Field(default_factory=EvidenceReviewState)


class PatternEvidence(BaseModel):
    status: Literal["no_additional_pattern_cue", "additional_evidence_review_suggested", "not_available"]
    availability: EvidenceAvailability
    associated_features: list[AssociatedFeatureEvidence] = Field(default_factory=list)
    review_state: EvidenceReviewState = Field(default_factory=EvidenceReviewState)


class EvidenceReviewState(BaseModel):
    status: Literal["unreviewed", "reviewed", "disagreement"] = "unreviewed"
    therapist_note: str = ""
    reviewed_by: str | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None


class EvidenceReviewPatch(BaseModel):
    status: Literal["reviewed", "disagreement"]
    therapist_note: str = ""

    @model_validator(mode="after")
    def require_disagreement_note(self):
        if self.status == "disagreement" and not self.therapist_note.strip():
            raise ValueError("A therapist note is required when recording disagreement.")
        return self
```

Extend `MLResult` with:

```python
pattern_evidence: PatternEvidence | None = None
profile_evidence: list[ProfileEvidence] = Field(default_factory=list)
artifact_provenance: dict[str, str] = Field(default_factory=dict)
```

Do not populate `scores` for this provider.

- [ ] **Step 4: Extend provider result**

Add matching optional fields to `MLProviderResult`, preserving defaults so the
existing rule provider remains compatible.

Add a context object so providers do not infer clinical metadata from feature
names:

```python
@dataclass(frozen=True)
class MLProviderContext:
    case_id: str
    session_id: str
    transcript_id: str
    age_months: int | None
    language: str
    session_type: str
    task_type: str | None
```

Change the interface to:

```python
def predict(
    self,
    features: FeatureSet,
    context: MLProviderContext,
    config: dict | None = None,
) -> MLProviderResult: ...
```

Update `RuleBasedReviewCueProvider.predict()` to accept and ignore `context`.
`create_ml_review()` constructs context from the persisted case, session, and
transcript rather than from browser input.

- [ ] **Step 5: Run schema and workflow tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py tests/test_workflow.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/schemas/clinical.py apps/api/app/services/ml_providers/base.py apps/api/app/services/ml_providers/rule_based.py apps/api/app/services/ml_review_service.py apps/api/tests/test_reference_evidence_provider.py
git commit -m "feat(api): add safe reference evidence schemas" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 9: Implement the Fail-Closed Runtime Provider

**Files:**
- Create: `apps/api/app/services/ml_providers/reference_evidence.py`
- Create: `apps/api/app/services/ml_providers/reference_feature_adapter.py`
- Modify: `apps/api/app/services/ml_providers/registry.py`
- Modify: `apps/api/app/core/config.py`
- Modify: `apps/api/app/services/ml_review_service.py`
- Modify: `apps/api/tests/test_reference_evidence_provider.py`

- [ ] **Step 1: Write failing availability and checksum tests**

```python
import time

import numpy


def test_provider_is_unavailable_when_manifest_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR", str(tmp_path))
    provider = ReferenceEvidenceProvider()
    availability = provider.check_availability()
    assert availability.available is False
    assert "manifest" in availability.reason.lower()


def test_provider_rejects_checksum_mismatch(reference_artifact_dir):
    (reference_artifact_dir / "reference_cells.csv").write_text("tampered")
    provider = ReferenceEvidenceProvider(reference_artifact_dir)
    assert provider.check_availability().available is False


def test_local_provider_p95_latency_is_within_budget(reference_provider, feature_sets, provider_context):
    durations = []
    for feature_set in feature_sets[:100]:
        started = time.perf_counter()
        reference_provider.predict(feature_set, provider_context)
        durations.append((time.perf_counter() - started) * 1000)
    assert numpy.percentile(durations, 95) <= 500
```

- [ ] **Step 2: Run tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py -q
```

Expected: FAIL.

- [ ] **Step 3: Implement manifest validation**

`ReferenceEvidenceProvider`:

- provider ID: `reference_evidence_review`;
- reads `manifest.json`;
- verifies artifact type, supported language, feature schema compatibility,
  and every declared checksum;
- loads reference cells once after successful validation;
- has no network calls;
- returns unavailable rather than falling back.

Add settings:

```python
reference_artifact_dir: str = "artifacts/reference_evidence/current"
ml_inference_timeout_seconds: float = 2.0
```

- [ ] **Step 4: Implement exact runtime feature adaptation**

`reference_feature_adapter.py` maps backend feature names to canonical
semantics only when their formulas match:

```python
RUNTIME_TO_CANONICAL = {
    "child_utterance_count": "total_utterances",
    "total_word_count": "total_words",
    "type_token_ratio": "ttr",
    "mean_length_of_utterance_words": "mluw",
    "unintelligible_ratio": "unintelligible_ratio",
    "question_ratio": "question_ratio",
    "echolalia_cue_count": "echolalia_count",
    "pronoun_reversal_cue_count": "pronoun_reversal_count",
}
```

Age comes from `MLProviderContext`, not a feature value. Features without exact
semantic parity remain missing. The adapter returns:

```python
CanonicalRuntimeFeatures(
    values=canonical_values,
    missing_required=sorted(missing),
    schema_version=features.schema_version,
)
```

Provider readiness blocks activation until the artifact manifest declares a
feature subset compatible with the exact mapped values. It must not substitute
zeros for missing canonical features.

- [ ] **Step 5: Implement descriptive profile evidence**

For each original profile:

- resolve age band, task, and language from case/session/feature context;
- select the matching cell;
- return `not_available` for an unsupported cell;
- compute associated feature evidence only for supported cells;
- select at most three strongest absolute IQR deviations;
- never return a probability, rank, winner, or predicted class.

When Gate 1 is research-only or missing, return pattern evidence with
`state="system_unavailable"` while profile evidence remains independently
available.

- [ ] **Step 6: Persist evidence through `MLResult`**

In `create_ml_review()` copy:

```python
pattern_evidence=provider_result.pattern_evidence,
profile_evidence=provider_result.profile_evidence,
artifact_provenance=provider_result.artifact_provenance,
scores=None,
confidence=None,
```

The existing input feature hash continues to bind transcript, feature values,
and provider configuration.

- [ ] **Step 7: Register without changing the safe default**

```python
ml_provider_registry.register(RuleBasedReviewCueProvider())
ml_provider_registry.register(ReferenceEvidenceProvider())
ml_provider_registry.register(BaselineResearchClassifierProvider())
ml_provider_registry.register(FutureMLProvider())
```

`rule_based_review_cue` remains the default. The frontend must request
`reference_evidence_review` explicitly.

- [ ] **Step 8: Run provider tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py tests/test_workflow.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/api/app/services/ml_providers/reference_evidence.py apps/api/app/services/ml_providers/reference_feature_adapter.py apps/api/app/services/ml_providers/registry.py apps/api/app/core/config.py apps/api/app/services/ml_review_service.py apps/api/tests/test_reference_evidence_provider.py apps/api/tests/test_workflow.py
git commit -m "feat(api): add fail-closed reference evidence provider" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 10: Enforce Language, Task, Age, Stale, and Consent Boundaries

**Files:**
- Modify: `apps/api/app/services/ml_review_service.py`
- Modify: `apps/api/app/services/consent_service.py`
- Modify: `apps/api/tests/test_reference_evidence_provider.py`
- Modify: `apps/api/tests/test_workflow.py`

- [ ] **Step 1: Write failing boundary tests**

```python
def test_thai_sample_returns_unsupported_scope_without_profile_evidence(client, reviewed_thai_transcript):
    response = client.post(
        f"/api/v1/transcripts/{reviewed_thai_transcript}/ml-review",
        json={"provider_id": "reference_evidence_review"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_evidence"] == []
    assert payload["pattern_evidence"]["availability"]["state"] == "unsupported_scope"


def test_transcript_edit_makes_evidence_non_current_and_non_exportable(client, evidence_result):
    client.patch(
        f"/api/v1/transcripts/{evidence_result['transcript_id']}",
        json={"utterances": [{"speaker": "CHI", "text": "changed"}]},
    )
    current = client.get(f"/api/v1/sessions/{evidence_result['session_id']}/ml-review")
    assert current.status_code == 404
```

- [ ] **Step 2: Run tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py tests/test_workflow.py -q
```

Expected: FAIL.

- [ ] **Step 3: Add explicit readiness codes**

Add readiness codes:

```text
unsupported_language
unsupported_code_switching
missing_age_band
age_outside_reference_coverage
missing_task_type
unsupported_task_type
feature_schema_incompatible
artifact_manifest_invalid
```

Input-action errors remain HTTP 409 readiness conflicts. Supported requests
whose matched profile cells are insufficient return HTTP 200 with profile-level
abstention.

- [ ] **Step 4: Verify staleness behavior**

Any transcript edit or feature refresh must clear `session.ml_result_id`.
Historical results remain in repository storage for restricted audit only and
`is_current` returns false when fetched by ID.

- [ ] **Step 5: Verify consent withdrawal**

Consent withdrawal must remove all `ml_results` for affected sessions and
clear `session.ml_result_id`. Audit messages must not contain transcript text
or feature values.

- [ ] **Step 6: Run tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py tests/test_workflow.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/services/ml_review_service.py apps/api/app/services/consent_service.py apps/api/tests/test_reference_evidence_provider.py apps/api/tests/test_workflow.py
git commit -m "feat(api): enforce reference evidence safety boundaries" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 11: Render Parallel Evidence Modules in Therapist App v2

**Files:**
- Modify: `apps/therapist-app-v2/src/lib/workflow.ts`
- Modify: `apps/therapist-app-v2/src/components/session-workspace-client.tsx`
- Modify: `apps/therapist-app-v2/src/__tests__/pages.test.tsx`

- [ ] **Step 1: Write failing rendering tests**

```tsx
it("renders independent pattern and reference evidence without scores or ranking", async () => {
  // Mock reference_evidence_review response with one supported TD card,
  // one unsupported ASD card, and research-only pattern evidence.
  render(<ResultsPage />);
  fireEvent.click(screen.getByRole("button", { name: "Generate evidence review" }));

  expect(await screen.findByRole("heading", { name: "Evidence Review" })).toBeInTheDocument();
  expect(screen.getByText("Pattern review")).toBeInTheDocument();
  expect(screen.getByText("Public-corpus profile evidence")).toBeInTheDocument();
  expect(screen.getByText("Comparable patterns observed")).toBeInTheDocument();
  expect(screen.getByText("Insufficient reference data")).toBeInTheDocument();
  expect(screen.queryByText(/probability|predicted class|winner/i)).not.toBeInTheDocument();
});


it("shows no more than three evidence cues before details are expanded", async () => {
  render(<ResultsPage />);
  expect(await screen.findAllByTestId("evidence-cue")).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));
  expect(screen.getAllByTestId("evidence-detail").length).toBeGreaterThan(3);
});
```

- [ ] **Step 2: Run tests**

Run:

```bash
cd apps/therapist-app-v2 && npm test -- src/__tests__/pages.test.tsx
```

Expected: FAIL.

- [ ] **Step 3: Add TypeScript evidence types**

Add:

```typescript
type EvidenceState =
  | "available"
  | "input_action_required"
  | "unsupported_scope"
  | "insufficient_reference_data"
  | "system_unavailable";

type EvidenceAvailability = {
  state: EvidenceState;
  reasonCode?: string;
  message: string;
  workflowCanContinue: boolean;
  nextStep?: string;
};

type ProfileEvidence = {
  profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL";
  presentationGroup: "TD" | "DD" | "ASD" | "OTHER";
  status: "comparable_patterns_observed" | "limited_comparison" | "not_available";
  availability: EvidenceAvailability;
  participantCount: number;
  corpusCount: number;
  associatedFeatures: AssociatedFeatureEvidence[];
};
```

Update generation to send:

```typescript
body: JSON.stringify({ provider_id: "reference_evidence_review" })
```

- [ ] **Step 4: Replace the single ML cue card with parallel modules**

The first module displays:

- `No additional pattern cue`;
- `Additional evidence review suggested`; or
- a precise unavailable state.

The second module renders independent cards. It must not sort cards by model
score. It shows participant/corpus support and at most three associated feature
evidence items in the initial view.

Use `reference distribution` and `associated feature evidence`; do not use
`normal range`, `contribution`, or `diagnostic confidence`.

- [ ] **Step 5: Add explicit unavailable state copy**

Map:

```typescript
const evidenceStateTitle = {
  input_action_required: "Input action required",
  unsupported_scope: "Outside the supported evidence scope",
  insufficient_reference_data: "Insufficient reference data",
  system_unavailable: "Evidence service unavailable",
  available: "Evidence available"
};
```

Every card states whether feature/report workflow can continue.

- [ ] **Step 6: Run frontend tests**

Run:

```bash
cd apps/therapist-app-v2 && npm test -- src/__tests__/pages.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/therapist-app-v2/src/lib/workflow.ts apps/therapist-app-v2/src/components/session-workspace-client.tsx apps/therapist-app-v2/src/__tests__/pages.test.tsx
git commit -m "feat(therapist-app): show parallel evidence review modules" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 12: Add Reviewed and Record Disagreement Actions

**Files:**
- Modify: `apps/api/app/schemas/clinical.py`
- Modify: `apps/api/app/services/ml_review_service.py`
- Modify: `apps/api/app/api/v1/routes/ml_review.py`
- Modify: `apps/api/tests/test_reference_evidence_provider.py`
- Modify: `apps/therapist-app-v2/src/lib/workflow.ts`
- Modify: `apps/therapist-app-v2/src/components/session-workspace-client.tsx`
- Modify: `apps/therapist-app-v2/src/__tests__/pages.test.tsx`

- [ ] **Step 1: Write failing audit-semantics tests**

```python
def test_reviewed_means_read_not_endorsed(client, evidence_result):
    response = client.patch(
        f"/api/v1/ml-results/{evidence_result['result_id']}/profiles/TD/review-state",
        json={"status": "reviewed", "therapist_note": ""},
    )
    td = next(item for item in response.json()["profile_evidence"] if item["profile_code"] == "TD")
    assert td["review_state"]["status"] == "reviewed"


def test_disagreement_requires_a_note(client, evidence_result):
    response = client.patch(
        f"/api/v1/ml-results/{evidence_result['result_id']}/profiles/TD/review-state",
        json={"status": "disagreement", "therapist_note": ""},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Implement profile-specific review state**

Add:

```python
def patch_profile_evidence_state(
    repo: MockRepository,
    result_id: str,
    profile_code: str,
    patch: EvidenceReviewPatch,
    user: CurrentUser,
) -> MLResult:
    result = repo.ml_results[result_id]
    profile = next(
        (item for item in result.profile_evidence if item.profile_code == profile_code),
        None,
    )
    if profile is None:
        raise KeyError("Profile evidence not found.")
    profile.review_state = EvidenceReviewState(
        status=patch.status,
        therapist_note=patch.therapist_note,
        reviewed_by=user.user_id,
        reviewed_by_name=user.display_name,
        reviewed_at=utc_now(),
    )
    repo.add_audit(
        "ml_review.profile_state",
        result_id,
        f"Profile {profile_code} marked {patch.status} by {user.user_id}.",
    )
    return _with_current(repo, result)
```

Expose:

```python
@router.patch(
    "/ml-results/{result_id}/profiles/{profile_code}/review-state",
    response_model=MLResult,
)
```

The existing cue endpoint and acknowledged/dismissed semantics remain unchanged
for the rule-based provider.

- [ ] **Step 3: Add frontend actions**

Buttons:

```text
Reviewed
Record disagreement
```

The disagreement flow requires a note and explains that the action records
clinical disagreement rather than deleting provider output.

Add the API function:

```typescript
export async function updateProfileEvidenceReview(
  resultId: string,
  profileCode: ProfileEvidence["profileCode"],
  status: "reviewed" | "disagreement",
  therapistNote = ""
): Promise<MlDecisionSupport> {
  const result = await apiFetch<BackendMlDecisionSupport>(
    `/v1/ml-results/${resultId}/profiles/${profileCode}/review-state`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status,
        therapist_note: therapistNote
      })
    }
  );
  return normalizeMlResult(result);
}
```

After a successful patch, replace `state.mlDecisionSupport` with the returned
immutable-provider/result-plus-review-state payload.

- [ ] **Step 4: Run backend and frontend tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py tests/test_workflow.py -q
cd ../therapist-app-v2 && npm test -- src/__tests__/pages.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/schemas/clinical.py apps/api/app/services/ml_review_service.py apps/api/app/api/v1/routes/ml_review.py apps/api/tests/test_reference_evidence_provider.py apps/therapist-app-v2/src/lib/workflow.ts apps/therapist-app-v2/src/components/session-workspace-client.tsx apps/therapist-app-v2/src/__tests__/pages.test.tsx
git commit -m "feat: clarify therapist evidence review disposition" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 13: Verify Persistence, Privacy, and No Report Auto-Inclusion

**Files:**
- Modify: `apps/api/tests/test_reference_evidence_provider.py`
- Modify: `apps/api/tests/test_workflow.py`
- Modify: `apps/api/app/services/report_service.py` only if a test proves evidence is currently auto-included.

- [ ] **Step 1: Add JSON and SQL round-trip tests**

```python
def test_evidence_result_round_trips_through_json_repository(tmp_path, evidence_result_model):
    repo = JsonFileRepository(tmp_path / "repo.json")
    repo.ml_results[evidence_result_model.result_id] = evidence_result_model
    repo.save()
    loaded = JsonFileRepository(tmp_path / "repo.json")
    assert loaded.ml_results[evidence_result_model.result_id] == evidence_result_model
```

Add the equivalent SQLite-backed `SqlAlchemyRepository` test.

- [ ] **Step 2: Add privacy-log test**

```python
def test_evidence_audit_log_contains_no_transcript_or_raw_features(repo, evidence_result):
    serialized = json.dumps(repo.audit_log).lower()
    assert "blue car" not in serialized
    assert "total_word_count" not in serialized
```

- [ ] **Step 3: Add report exclusion test**

```python
def test_report_draft_does_not_include_reference_evidence_automatically(client, evidence_result):
    report = client.post(f"/api/v1/sessions/{evidence_result['session_id']}/reports/draft").json()
    text = report["markdown"].lower()
    assert "comparable patterns observed" not in text
    assert "public-corpus profile" not in text
```

- [ ] **Step 4: Run tests**

Run:

```bash
cd apps/api && pytest tests/test_reference_evidence_provider.py tests/test_workflow.py -q
```

Expected: PASS. Modify `report_service.py` only if the new test fails because
evidence is being inserted automatically.

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_reference_evidence_provider.py apps/api/tests/test_workflow.py apps/api/app/services/report_service.py
git commit -m "test(api): enforce evidence privacy and report boundaries" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Task 14: Documentation and Full Verification

**Files:**
- Modify: `docs/ML_DECISION_SUPPORT_MODEL_CARD.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md`

- [ ] **Step 1: Update the model card**

Document:

- public English corpus scope;
- participant and corpus support rules;
- Other as presentation roll-up only;
- Gate 1 proxy labels;
- preregistered promotion thresholds;
- current research-only/promoted status from the generated manifest;
- profile-level abstention;
- Thai and mixed-language unsupported scope;
- no probability, ranking, predicted class, or automatic report inclusion.

- [ ] **Step 2: Update setup and research commands**

Add:

```bash
python scripts/build_ml_reference_evidence.py \
  --combined data/combined_features.csv \
  --curated data/curated_group_features.csv \
  --output-dir artifacts/reference_evidence/candidate-v1 \
  --artifact-version candidate-v1
```

Explain that artifact promotion is manual and approval-recorded.

- [ ] **Step 3: Update changelog**

Add a behavior entry only after the reference provider and therapist evidence
panel are enabled. Do not claim clinical validation.

- [ ] **Step 4: Write the operations and approval runbook**

Define a role matrix with distinct named responsibilities:

```text
Dataset approver — approves source inventory, provenance exclusions, and dataset hash.
ML evaluator — runs candidate evaluation and signs the metric report.
Clinical content approver — approves clinician-options rule-map wording.
Privacy reviewer — approves retention, deletion, and telemetry fields.
Release approver — promotes or rolls back only previously approved manifests.
Incident owner — disables the provider and coordinates investigation.
```

Document:

- candidate artifact retention count: promoted artifact plus the five most
  recent candidates;
- failed/tampered artifact response: disable provider and fail closed;
- rollback command and requirement for a prior promoted manifest;
- incident evidence that may be logged;
- prohibition on transcript text, identifiers, and raw feature vectors in
  telemetry.

- [ ] **Step 5: Run focused verification**

Run:

```bash
pytest tests/test_ml_reference_dataset.py tests/test_ml_reference_artifacts.py tests/test_gate1_validation.py tests/test_reference_feature_parity.py tests/test_reference_engine.py -q
cd apps/api && pytest tests/test_reference_evidence_provider.py tests/test_workflow.py tests/test_feature_provider.py -q
cd ../therapist-app-v2 && npm test -- src/__tests__/pages.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Run typecheck and builds**

Run:

```bash
cd apps/therapist-app-v2 && npm run typecheck && npm run build
```

Expected: PASS.

- [ ] **Step 7: Run full project verification**

Run:

```bash
bash scripts/check_project.sh
```

Expected: PASS with no new safety wording or artifact integrity failures.

- [ ] **Step 8: Run final safety and privacy scans**

Run:

```bash
rg -n -i "asd probability|dd probability|predicted diagnosis|predicted class|diagnostic confidence|normal range|winner" \
  apps/api apps/therapist-app-v2/src packages/ml src/reference_engine.py \
  -g '!**/__tests__/**' -g '!**/tests/**'

rg -n "raw_text|utterances|storage_key|object_key" artifacts/reference_evidence
```

Expected:

- no prohibited therapist-facing wording;
- no transcript text, raw utterances, or storage keys in generated artifacts.

- [ ] **Step 9: Commit**

```bash
git add docs/ML_DECISION_SUPPORT_MODEL_CARD.md docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md README.md CHANGELOG.md
git commit -m "docs: document reference evidence review boundaries" \
  -m "Co-Authored-By: OpenAI Codex <codex@openai.com>"
```

## Completion Audit

Before declaring implementation complete, verify every design requirement:

- canonical dataset rows are auditable and participant-grouped;
- `Other` is presentation-only;
- support uses at least 20 unique participants and two corpora;
- unsupported cells do not calculate distributions;
- English/task/age readiness fails closed;
- golden fixture parity passes;
- Gate 1 report uses participant and corpus-aware evaluation;
- promotion gate is preregistered and enforced;
- runtime provider verifies manifest and checksums;
- no probability, ranking, winner, or predicted class reaches Therapist App;
- pattern and profile modules run independently;
- unavailable states are distinct and actionable;
- stale and withdrawn results are excluded from active workflow;
- evidence is not inserted into reports automatically;
- telemetry/audit output has no transcript text, direct identifiers, or raw
  feature vectors;
- persistence round-trips through JSON and SQL repository modes;
- focused tests, frontend tests, typecheck, builds, and
  `scripts/check_project.sh` pass.
