# CHA Reference Cohort Pipeline Design

## Intent

Add a CHA-based feature extraction and baseline machine-learning pipeline for
the Speech Therapist Prototype. The pipeline uses existing CHAT transcripts as
structured speech-language data and exposes model-assisted reference cohort
similarity for therapist review.

The system must not diagnose ASD. Labels such as ASD, TD, and DD are Reference
Cohort Labels used for model development and evaluation. User-facing surfaces
must describe outputs as Reference Cohort Similarity.

## Decisions

- Use the existing Canonical Feature Schema as runtime model input.
- Provide Feature Aliases for prompt-facing and therapist-facing names.
- Treat new interaction features as optional indicators until separately
  selected for model input.
- Treat acoustic measurements as Context-Only Acoustic Indicators in this
  iteration.
- Support two inference states:
  - Preliminary Reference Cohort Similarity from unreviewed or ASR-derived
    transcript text.
  - Reviewed Reference Cohort Similarity after transcript line review and
    sign-off.
- Keep `artifacts/screening_model.joblib` as the Runtime Model Artifact.
- Add `models/transcript_classifier.pkl` only as a Compatibility Model Export.
- Use group-based evaluation when participant/session grouping is available.
- Make XGBoost and LightGBM optional benchmark candidates, never required
  dependencies.

## Data Sources

Existing curated corpora keep their current loader-specific label rules.
New external CHA folders use `metadata.csv` with `file_id`, `label`, `age`,
`sex`, `language`, and `notes`.

Dataset validation must fail or warn on:

- missing labels,
- empty transcripts,
- no child utterances,
- insufficient class counts,
- repeated-session leakage risk when no grouping key exists.

## Runtime Output

Inference returns:

- `reference_cohort_probabilities`,
- `most_similar_reference_cohort`,
- `similarity_probability`,
- `inference_status`,
- `top_contributing_features`,
- `safety_warnings`,
- `plain_language_explanation`.

The explanation must use similarity wording and must include clinical
decision-support safety language.

## UI Direction

The therapist app should show the result inside the transcript review workflow,
near transcript QA and feature extraction status. Preliminary output must be
visually distinct from reviewed output and must not be report-ready.

The UI follows the existing Clinical Teal product system: high contrast,
restrained surfaces, clear status badges, no decorative effects, and no
diagnostic wording.

## Non-Goals

- No autonomous ASD diagnosis.
- No Thai clinical validation claim.
- No acoustic classifier input in this iteration.
- No forced dependency on boosted-tree packages.
