# ML Reference Evidence Operations

This runbook governs research artifact creation and the opt-in
`reference_evidence_review` provider. The provider is decision-support only and
must fail closed.

## Role separation

| Role | Responsibility |
|---|---|
| Dataset approver | Approves source inventory, provenance exclusions, deduplication audit, and dataset hash. |
| ML evaluator | Runs candidate evaluation and signs the Gate 1 metric report. |
| Clinical content approver | Approves therapist-facing wording and clinician-options rule maps. |
| Privacy reviewer | Approves retention, deletion behavior, audit fields, and telemetry fields. |
| Release approver | Promotes or rolls back only previously approved manifests. |
| Incident owner | Disables the provider and coordinates investigation. |

One person must not approve both the dataset and final release for the same
artifact.

## Build a candidate

Use a secret pseudonymization key of at least 32 bytes. Do not commit the key.

```bash
export ML_REFERENCE_PSEUDONYMIZATION_KEY='replace-with-32-or-more-secret-bytes'
python scripts/build_ml_reference_evidence.py \
  --combined data/combined_features.csv \
  --curated data/curated_group_features.csv \
  --output-dir artifacts/reference_evidence/candidate-v1 \
  --artifact-version candidate-v1 \
  --feature-parity-passed
```

The output directory is immutable. Rebuilding the same version requires a new
version name; do not overwrite or edit an existing artifact.

## Approval and promotion

Record approvals for:

1. source inventory and dataset hash;
2. duplicate/audit exclusions;
3. Gate 1 metrics and failed/passed reasons;
4. therapist-facing wording;
5. privacy and retention; and
6. release manifest and checksums.

Promotion is manual. Point
`LINGUALENS_REFERENCE_ARTIFACT_DIR` to the approved immutable directory,
restart the API, and verify `/api/v1/ml/providers`. The rule-based provider
remains the safe default.

Retain the promoted artifact plus the five most recent candidates.

## Failure and rollback

If a manifest is missing, malformed, incompatible, or fails a checksum:

1. disable the reference provider by removing the configured artifact path;
2. keep therapist transcript, feature, and report workflows available;
3. preserve the failed artifact read-only for investigation;
4. record the artifact version, manifest hash, failure code, application
   version, and timestamp; and
5. never log transcript text, child identifiers, storage keys, or raw feature
   vectors.

Rollback may target only a previously approved artifact:

```bash
export LINGUALENS_REFERENCE_ARTIFACT_DIR=/approved/path/reference-evidence-vN
```

Restart the API and confirm the provider reports available before reopening the
evidence action.

## Incident evidence allowed in logs

Allowed: provider ID/version, artifact version, manifest/checksum status,
feature schema version, availability reason code, latency, result ID, and
review-state action.

Prohibited: transcript text, utterances, names, direct identifiers, audio or
storage keys, and raw feature vectors.
