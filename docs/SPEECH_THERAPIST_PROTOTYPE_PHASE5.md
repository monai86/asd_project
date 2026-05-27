# Speech Therapist / Clinician App Phase 5

Phase 5 adds mock feature extraction and AI decision-support output to the
standalone Speech Therapist / Clinician App. It remains `MOCK_MODE=True`;
feature values are generated from reviewed mock transcript text and aligned to
the existing 14-feature schema.

## Scope

Phase 5 adds:

- schema-complete extracted feature records using the shared 14-feature schema
- screening support score and concern level display
- top contributing feature list
- evidence review panel for therapist interpretation
- audit events for feature extraction and AI support output generation

## Schema Boundary

The feature output must include exactly the shared schema from
`src.feature_schema.FEATURES`. Phase 5 does not replace the existing
`data_loader.py` pipeline; it provides a mock, database-ready workflow shape for
the therapist prototype.

## Decision-Support Boundary

The AI output is screening support only. It must not say that a child has ASD,
does not diagnose ASD, and must be interpreted with transcript QA, session
context, external clinical context, and therapist judgment.

## Deferred Work

Phase 5 does not add real model inference, calibrated probability claims, Thai
clinical validation, printable reports, or longitudinal report export. Those
remain later phases.
