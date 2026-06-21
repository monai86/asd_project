# ML Decision-Support Model Card

Project version: v1.6.3
Component status: current maintained runtime

## Intended use

The ML layer provides two independent therapist-review surfaces:

- transparent feature-based review cues from the default rule provider; and
- descriptive public-corpus profile evidence from the optional
  `reference_evidence_review` provider.

## Not intended use

It must not diagnose ASD or another developmental condition, produce
probabilities, rank profiles, name a winner, output a predicted class, replace
professional interpretation, automate report conclusions, or claim Thai
clinical validation.

## Inputs and outputs

- Input: backend-persisted `BasicFeatureProvider` results with a known schema.
- Input feature schema: `features-basic-v1`; incompatible or unknown schemas
  are blocked from ML review.
- Core values: child utterance count, adult utterance count, and total child
  word count.
- Output: immutable `MLResult` records with cues, supporting values,
  limitations, provider metadata, and input provenance.
- Reference output: independently abstaining TD, DD, ASD, LT, STI, and HL
  profile cards. LT, STI, and HL may be rolled up to `OTHER` for presentation,
  but their research labels remain distinct in artifacts and results.

Review cues contain a code, review-attention severity, explanation, supporting
feature values, limitations, and a recommended next review step. They never
contain ASD positive/negative output.

## Provider and validation

`RuleBasedReviewCueProvider` is the default. Its thresholds are engineering
review thresholds, not clinical norms. The experimental classifier remains
unavailable until label provenance and runtime schema compatibility are
verified. This research prototype has no established diagnostic performance.

`ReferenceEvidenceProvider` is opt-in and local-only. It verifies the artifact
manifest, feature schema, supported language, and every declared SHA-256
checksum before loading reference cells. It fails closed and never silently
falls back to a different provider.

## Dataset limitations

Reference artifacts use public English-language corpora. A profile cell is
supported only with at least 20 unique verified participants from at least two
corpora. Unsupported cells retain support metadata but contain no feature
distribution. Thai and mixed-language samples are outside the current
reference scope.

Gate 1 uses the proxy label `original_group != "TD"` for research evaluation
only. Evaluation is participant-grouped, includes corpus-held-out checks,
participant bootstrap confidence intervals, calibration metrics, and the
following preregistered promotion gate:

- sensitivity lower 95% CI at least 0.80;
- specificity at least 0.60;
- ECE at most 0.10;
- Brier score no worse than the baseline;
- abstention at most 0.40;
- corpus holdout completed; and
- feature parity passed.

The latest committed Gate 1 artifact is `promoted_candidate`:

- sensitivity: `0.8862`;
- sensitivity lower 95% CI: `0.8091`;
- specificity: `0.6124`;
- ECE: `0.0332`;
- Brier score: `0.1877`; and
- abstention rate: `0.3166`.

This means the candidate passed the preregistered engineering gate on the
current proxy-label/public-corpus evaluation. It does not establish diagnostic
performance, clinical validity, Thai validity, or permission to expose
probabilities/predicted classes. The therapist workflow remains evidence-only,
fail-closed, human-reviewed, and report-excluded by default.

## Validation status and known limitations

The implementation is verified by software tests for readiness gates,
participant/corpus support, feature parity, artifact integrity, persistence,
provider metadata, stale-result handling, consent withdrawal, and safety
wording. This is engineering verification only, not clinical validation.
Transcript quality, sample length, speaker attribution, language background,
age, task, and session context can affect feature values and evidence
availability.

## Human oversight

Transcript attestation is required. Therapists interpret every cue; review
state is audited separately from immutable provider output. “Reviewed” records
that the evidence was read, not endorsed. “Disagreement” requires a therapist
note and preserves the original evidence. Evidence is not inserted into reports
automatically. Consent withdrawal deletes derived ML results.

This system is decision-support only and not diagnostic. It makes no clinical
validation claim.
