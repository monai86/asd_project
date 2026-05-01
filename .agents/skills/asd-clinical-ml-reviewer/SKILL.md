---
name: asd-clinical-ml-reviewer
description: Review ASD clinical machine-learning changes in asd-project for data leakage, evaluation validity, class imbalance, feature definitions, uncertainty handling, explainability, clinical safety, and non-overclaiming language. Use when modifying or reviewing src/classifier.py, src/deep_learning.py, src/data_loader.py, app/dashboard.py prediction logic, reports/metrics, XAI outputs, severity scores, M-CHAT fusion, README claims, or advisor-facing clinical conclusions.
---

# ASD Clinical ML Reviewer

## Purpose

Review ASD screening and progress-tracking work as a clinical ML quality gate. Prioritize validity, transparent limitations, and safe wording over impressive metrics.

## Files To Inspect

- `src/data_loader.py` for cohort labels, feature definitions, leakage risks, and corpus/session handling.
- `src/classifier.py` and `src/deep_learning.py` for train/test split, metrics, baselines, calibration, and model comparison.
- `src/progress_tracking.py` for longitudinal logic and improvement claims.
- `app/dashboard.py` for prediction display, uncertainty band, severity scores, XAI explanations, and clinical wording.
- `data/combined_features.csv`, `data/longitudinal_features.csv`, and `reports/metrics/` for generated outputs.
- `README.md`, `docs/PROJECT_SUMMARY_TH.md`, `docs/DISCUSSION_TH.md`, and `docs/REFERENCES.md` for claims and citations.

## Review Workflow

1. Identify the changed behavior and the claim it supports.
2. Trace the data path from raw `.cha` or audio input to features, model input, prediction, and displayed explanation.
3. Check split integrity. Watch for same child, same corpus-specific artifact, same session family, or derived labels crossing train/test boundaries.
4. Check metric validity. Prefer AUC, sensitivity, specificity, confusion matrix, uncertainty counts, confidence intervals, and clinically meaningful threshold behavior over a single accuracy number.
5. Check class balance and group composition. Call out when ASD/DD/TD proportions or corpus differences could inflate performance.
6. Check calibration and uncertainty handling. Predictions in the 40-60% band should remain indeterminate and recommend further assessment.
7. Check explainability. XAI text must explain feature contribution without implying causal diagnosis.
8. Check clinical wording. Use screening/support language, not diagnosis language.
9. Recommend focused tests or analysis before release.

## Clinical Safety Rules

- Do not describe the app as diagnosing autism. Prefer "screening", "risk estimate", "decision support", or "research prototype".
- Do not present model output as a replacement for clinician judgment.
- State uncertainty clearly when prediction confidence is low or data quality is limited.
- Treat audio/ASR outputs as noisy estimates. Do not overinterpret transcripts or diarization-derived features.
- Keep parent questionnaire fusion as an auxiliary signal, not proof of ASD.

## Common Findings To Look For

- Data leakage from corpus, child/session ID, generated severity labels, or duplicated transcripts.
- Evaluation on generated features after preprocessing learned from all data.
- Metrics reported without test-set size or class composition.
- Thresholds chosen on test data without validation separation.
- SHAP-like explanations computed with inconsistent feature ordering.
- Feature names in dashboard not matching model training columns.
- DD group treated as non-ASD without discussing clinical heterogeneity.
- Longitudinal improvement inferred from too few sessions or inconsistent session spacing.
- README or Thai summary claims exceeding the actual evidence.

## Output Format

Lead with findings ordered by severity. Include file paths and line numbers when possible. Then provide:

- "Clinical wording fix" if user-facing text needs safer phrasing.
- "Validation to run" with the smallest useful check.
- "Release readiness" as Ready, Needs minor fixes, or Blocked.

Read [references/review-checklist.md](references/review-checklist.md) for a compact checklist before finalizing a review.
