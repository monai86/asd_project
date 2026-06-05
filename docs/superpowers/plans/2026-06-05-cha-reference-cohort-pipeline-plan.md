# CHA Reference Cohort Pipeline Plan

## Scope

Implement CHA parsing, transcript feature aliases, dataset building, model
training, inference, safety wording, and therapist app integration for
Reference Cohort Similarity.

## Steps

1. Add `packages/cha/parser.py`
   - Parse CHAT main speaker tiers for CHI, MOT, FAT, INV, CLI, and other
     speaker codes.
   - Preserve raw text, normalized text, cleaned tokens, speaker role, and
     timestamps from media bullets or `%tim` tiers.

2. Add `packages/features/transcript_features.py`
   - Reuse the canonical feature schema.
   - Add aliases required by the CHA prompt.
   - Add extended interaction indicators.
   - Keep acoustic features context-only.

3. Add `packages/ml/train_model.py`
   - Build datasets from curated corpus mode or metadata CSV mode.
   - Train Logistic Regression and Random Forest.
   - Add optional XGBoost/LightGBM candidates if installed.
   - Evaluate with stratified splits and group-aware splits when possible.
   - Save runtime artifacts to `artifacts/` and compatibility export to
     `models/`.

4. Add `packages/ml/predict.py`
   - Load the runtime model bundle.
   - Extract features from a new CHA transcript or feature dict.
   - Return Reference Cohort Similarity output, feature contributions, and
     quality warnings.

5. Integrate backend and frontend
   - Add a backend inference endpoint or route through existing AI output
     generation.
   - Map backend probabilities to similarity wording in the frontend.
   - Show preliminary and reviewed state labels in the transcript workflow.

6. Add deliverables and tests
   - `data/metadata.example.csv`
   - `models/README.md`
   - Unit tests for parser and feature aliases.
   - Integration test from CHA to prediction output.
   - Validation tests for missing labels, empty transcripts, and short
     transcripts.

## Verification

- Run focused Python tests for parser/features/predict.
- Run existing clinical speech tests touched by the integration.
- Run focused frontend tests for audio processing and transcript workflow if
  frontend mapping changes.

## Safety Checks

- No user-facing diagnosis language.
- Preliminary outputs are not report-ready.
- Reviewed outputs use reviewed transcript lines when available.
- Acoustic values remain optional indicators, not classifier inputs.
