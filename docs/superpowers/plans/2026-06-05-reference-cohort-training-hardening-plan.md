# Reference Cohort Training Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the training pipeline from baseline functionality to research-grade, repeatable model evaluation.

**Architecture:** Keep runtime inference stable while improving offline training and evaluation artifacts. Training changes must not alter the clinical workflow unless a new runtime artifact is explicitly generated and reviewed.

**Tech Stack:** Python, pandas, scikit-learn, optional XGBoost/LightGBM, joblib, pytest.

---

## Safety Boundary

- Training targets are Reference Cohort Labels, not diagnoses.
- Acoustic features remain context-only indicators and must not be classifier inputs in this phase.
- Runtime model replacement requires explicit artifact review, model card update, and compatibility export regeneration.

## Task 1: Add Repeatable Training CLI

- [ ] Add CLI arguments to `packages/ml/train_model.py` for dataset folder, metadata CSV, output directory, random seed, minimum class count, model allowlist, and compatibility export toggle.
- [ ] Add `--dry-run` validation that builds `features.csv` and reports label/sample issues without training.
- [ ] Add tests for missing metadata, missing labels, unsupported labels, and insufficient samples.

## Task 2: Add Group-Based Evaluation

- [ ] Accept `child_id` or `participant_id` from metadata when present.
- [ ] Use `GroupKFold` or group-aware train/test split when group IDs are available.
- [ ] Fall back to stratified split only when no participant grouping exists, and record this in the evaluation report.
- [ ] Add tests proving all sessions from one participant stay on one side of the split.

## Task 3: Add Bootstrap Confidence Intervals

- [ ] Bootstrap accuracy, macro F1, sensitivity, specificity, and AUC where class support allows.
- [ ] Report unavailable CIs explicitly when sample counts are too low.
- [ ] Store CI method, bootstrap count, and random seed in `artifacts/model_card.json`.

## Task 4: Add Calibration Report

- [ ] Generate calibration metrics for the selected runtime candidate.
- [ ] Store reliability summary and class probability caveats in the evaluation report.
- [ ] Prefer Logistic Regression when AUC is within the configured tie-breaker margin of more complex candidates.

## Task 5: Add Dataset Card

- [ ] Generate a dataset card with corpus counts, label distribution, age/sex/language coverage, rejected files, and metadata completeness.
- [ ] Include a data-leakage note describing whether group-based splitting was used.
- [ ] Include a clinical-safety note that labels represent reference cohort group membership, not diagnosis assignment for new children.

## Task 6: Regenerate Compatibility Exports

- [ ] Save the canonical runtime artifact to `artifacts/screening_model.joblib`.
- [ ] Save the compatibility export to `models/transcript_classifier.pkl`.
- [ ] Save feature schema and model card alongside the runtime artifact.
- [ ] Add a documented command for reproducing all artifacts from the same dataset snapshot.

## Verification

```bash
pytest tests/test_cha_reference_cohort_pipeline.py tests/test_reference_cohort_similarity_workflow.py -q
python packages/ml/train_model.py --help
python packages/ml/train_model.py --dataset data/example-cha --metadata data/metadata.example.csv --dry-run
```

Expected:

- CLI help is available,
- dry-run validation produces deterministic feature/schema checks,
- group leakage tests pass,
- compatibility export is created only when explicitly requested.
