# ML Reference Evidence Review Design

Date: 2026-06-20
Status: Approved design
Scope: Research-first English reference comparison and ML validation for Therapist App v2

## 1. Purpose

This workstream adds cautious, therapist-facing evidence review based on
age-, task-, and language-matched public English CHAT corpora. It is intended
to help speech therapists decide:

- which transcript-derived language patterns warrant closer review;
- whether a longer or better-matched language sample is needed; and
- which clinician-authored assessment or referral options may be relevant for
  professional consideration.

The system remains a research and education prototype. It does not diagnose
ASD, DD, or any other condition, and it does not claim Thai clinical
validation.

## 2. Design Outcome

The approved architecture is a research-first hybrid with two parallel
evidence paths:

1. **Descriptive reference comparison**
   compares reviewed transcript features with independently supported
   TD, DD, ASD, LT, STI, and HL reference cohorts.
2. **Research Gate 1 classifier**
   evaluates the public-corpus proxy task TD versus non-TD with an emphasis on
   sensitivity and calibrated abstention.

These paths run in parallel. A Gate 1 result must never suppress descriptive
cohort evidence.

The original sequential hierarchy is not used in the therapist workflow
because it could propagate Gate 1 errors and resemble a diagnostic decision
tree.

## 3. Version 1 Scope

Version 1 includes:

- canonical data inventory, provenance validation, and deduplication;
- participant- and corpus-aware dataset construction;
- feature parity verification between research and runtime extraction;
- English age/task/language-matched descriptive reference comparison;
- independent profile-level support and abstention;
- research validation of a calibrated TD-versus-non-TD proxy classifier;
- immutable artifact manifests and promotion records;
- therapist-facing evidence cards only for components that pass their
  applicable readiness and promotion gates.

Version 1 excludes:

- a production four-class classifier;
- treating LT, STI, and HL as one homogeneous training label;
- deep learning or sequence-model deployment;
- automated retraining or model promotion;
- Thai or mixed-language cohort inference;
- diagnostic probability, predicted class, winner ranking, or referral orders;
- automatic insertion of ML output into reports.

A four-profile classifier may be evaluated as a research challenger, but it is
not a Version 1 dependency and cannot be therapist-facing without a separate
approved design and promotion review.

## 4. Clinical Safety Boundary

Therapist-facing output must:

- run only after transcript QA and therapist attestation;
- use backend-authoritative feature results;
- remain decision-support evidence rather than a clinical conclusion;
- avoid diagnostic probability, predicted diagnosis, winner labels, and class
  ranking;
- show limitations next to the evidence they qualify;
- abstain when input or reference support is insufficient;
- remain excluded from reports until a therapist explicitly selects and edits
  appropriate wording;
- become unavailable when the current transcript or feature result changes;
- never fall back to browser inference, cached cues, or an older model.

The names TD, DD, ASD, and Other may appear only as public-corpus profile
context. The UI must not state or imply that a child belongs to one of these
groups.

## 5. Data Sources and Canonical Dataset

The initial inputs are:

- `data/combined_features.csv`;
- `data/curated_group_features.csv`; and
- traceable source CHAT files and extraction metadata.

The dataset builder must not describe the 2,301 curated rows as 2,301
independent children. The current table contains repeated sessions and
approximately 168 unique participant identifiers.

Each canonical row must retain:

- source path or non-identifying source reference;
- corpus;
- participant grouping key;
- session key where available;
- original group;
- UI roll-up group;
- age in months and its provenance;
- language;
- task type and its provenance;
- extractor version;
- feature schema version;
- source and row hashes;
- deduplication disposition; and
- exclusion reasons.

### 5.1 Label Mapping

Research labels remain distinct:

- TD;
- DD;
- ASD;
- LT;
- STI; and
- HL.

`Other language profiles` is a presentation roll-up for LT, STI, and HL. It is
not a homogeneous training label. Evaluation must continue to report each
original subgroup separately.

### 5.2 Canonical Features

The first runtime-compatible version uses only the 14 canonical features that
can be reproduced by both research and backend extraction.

The additional interaction features remain research extensions until their
runtime definitions, missingness behavior, and extraction parity are
separately validated.

### 5.3 Deduplication and Independence

Deduplication must consider:

- exact source path;
- source checksum;
- corpus and participant;
- session or recording identifier;
- feature-row checksum; and
- known overlap between combined and curated tables.

All sessions for one participant must remain in the same evaluation partition.
When metadata permits, splits must also respect site, corpus, elicitation
protocol, and transcriber boundaries.

Session count must never be used as a substitute for participant count.

## 6. Reference Cohort Construction

Reference matching uses:

- English language only;
- a documented age band;
- a normalized task type; and
- an independently supported profile.

A reference cell is supported only when it contains:

- at least 20 unique participants; and
- participants from at least two corpora.

These are engineering support thresholds, not clinical norm requirements.

If a profile fails the threshold, that profile abstains independently. The
system must not silently widen the age band, merge tasks, pool languages, or
use repeated sessions to satisfy the threshold.

For supported cells, the service may return descriptive distribution
statistics and empirical positions. It must use the term `reference
distribution`, not `normal range`, `clinical norm`, or `validated benchmark`.

## 7. Research Gate 1

Gate 1 is a public-corpus proxy experiment:

- negative research label: TD;
- positive research label: non-TD public-corpus groups;
- primary baseline: calibrated Logistic Regression;
- challenger: Random Forest;
- primary objective: sensitivity with controlled specificity, calibration,
  and abstention.

The labels do not mean that a child is clinically typical or requires a
specific referral. Therapist-facing text must therefore use:

- `No additional pattern cue`; or
- `Additional evidence review suggested`.

The terms `TD-like` and `Needs further review` may appear in research analysis
only when their proxy meaning is stated explicitly.

## 8. Evaluation Design

Evaluation must include:

- participant-grouped cross-validation;
- corpus-held-out evaluation;
- preprocessing fit only within training folds;
- bootstrap confidence intervals resampled at participant level;
- sensitivity and specificity;
- macro F1;
- ROC-AUC and PR-AUC where statistically meaningful;
- Brier score;
- expected calibration error;
- calibration plots;
- confusion matrices;
- abstention coverage;
- subgroup reports for age, sex, corpus, and LT/STI/HL;
- leave-one-corpus-out stress tests; and
- feature stability analysis across folds.

Subgroups with inadequate sample size or excessively wide confidence
intervals must be marked `not evaluable`. They must not be counted as passing.

Research metrics must not be presented as evidence of clinical generalization
to Thai children or to a new clinic.

## 9. Feature Parity and Input Readiness

Schema names, versions, and hashes are necessary but not sufficient.

Golden reviewed CHAT fixtures must be processed through both the research and
runtime extractors. Each canonical feature must have a preregistered numeric
tolerance. A parity failure blocks model promotion.

Inference abstains when any of the following applies:

- transcript QA has blocking errors;
- therapist attestation is absent;
- required features are missing;
- extractor or schema compatibility is unknown;
- language or task is unsupported;
- age is outside reference coverage;
- the language-coverage rule identifies unsupported code-switching;
- the input is out of the supported feature distribution; or
- the artifact manifest or checksum is invalid.

## 10. Preregistered Promotion Gate

Before final candidate evaluation, the following candidate engineering gate is
recorded:

- Gate 1 sensitivity: lower bound of the participant-bootstrap 95% confidence
  interval is at least 0.80;
- specificity point estimate is at least 0.60;
- expected calibration error is at most 0.10;
- Brier score is no worse than the preregistered baseline;
- overall abstention rate is at most 40%;
- corpus-held-out evaluation completes without a material unsupported
  generalization claim;
- feature parity passes; and
- required subgroup analyses are either acceptable or explicitly
  `not evaluable`.

Passing this gate permits only limited feature-flag evaluation. It does not
establish clinical validity.

Failure of any mandatory gate keeps the classifier research-only. Descriptive
reference comparison may still be available for independently supported cells.

## 11. Therapist Experience

The active Evidence Review Panel contains two parallel modules:

1. **Pattern review cue**
   shows either no additional cue, additional evidence review suggested, or a
   precise unavailable state.
2. **Reference evidence**
   shows one independent card per supported public-corpus profile.

The interface must not show:

- model probabilities;
- a ranked list;
- a winning profile;
- a predicted class;
- a combined concern score; or
- a diagnostic decision tree.

Each profile card uses one of:

- `Comparable patterns observed`;
- `Limited comparison`; or
- `Not available`.

The initial view shows no more than three high-priority evidence cues.
Distribution details and methodology remain behind an explicit
`View supporting evidence` action.

### 11.1 Evidence Wording

Use:

- `associated feature evidence`;
- `reference distribution`;
- `public-corpus profile`;
- `reviewed transcript`;
- `limitations`; and
- `options for clinician consideration`.

Do not use:

- causal contribution;
- normal or abnormal;
- diagnostic confidence;
- ASD/DD probability;
- predicted diagnosis;
- clinical norm; or
- the model recommends referral.

### 11.2 Clinician-Authored Options

Assessment and referral options are selected from a versioned,
clinician-authored rule map based on observed evidence and limitations. They
are not outputs learned by the classifier.

The section title is `Options for clinician consideration`. The therapist
remains responsible for deciding whether any option applies.

### 11.3 Review Actions

The available actions are:

- `Reviewed`: confirms the therapist read the evidence; it does not endorse
  its correctness.
- `Record disagreement`: stores a therapist note explaining why the evidence
  is not useful or conflicts with clinical judgment.

Provider output is immutable. Review disposition is stored separately.

## 12. Unavailable and Abstention States

The UI and API distinguish:

- **Input action required**: the therapist can correct QA, attestation,
  metadata, or sample-length issues.
- **Unsupported scope**: the language, age, task, or code-switching pattern is
  outside the validated engineering scope.
- **Insufficient reference data**: one or more matched public-corpus profiles
  fail participant or corpus support.
- **System unavailable**: an artifact, provider, checksum, or backend
  dependency failed.

Every state must say:

- why evidence is unavailable;
- whether descriptive feature review can continue;
- whether report work can continue; and
- the next user action, if one exists.

Offline mode must not create or display cached ML cues. It must state that
backend verification is currently unavailable rather than implying that saved
results were deleted.

## 13. Provenance, Versioning, and Integrity

Every result must retain:

- transcript identifier and version;
- feature result identifier and hash;
- dataset snapshot version and hash;
- extractor and feature-schema versions;
- cohort build version;
- model and threshold versions;
- clinician rule-map version;
- provider configuration;
- artifact checksums;
- generation timestamp; and
- current/stale status.

An immutable artifact manifest binds these versions. Promotion requires an
approval record. Rollback may use only a previously promoted artifact.

Training jobs cannot promote themselves.

## 14. Privacy and Consent

Child-level derived features and evidence results follow the same protection
boundary as case data:

- role-scoped access;
- encrypted private storage;
- consent linkage;
- documented retention;
- deletion behavior; and
- audited access and disposition events.

Consent withdrawal removes active derived ML results according to the existing
case deletion workflow.

Audit records may preserve event type, actor, timestamp, artifact version, and
disposition. They must not contain transcript text, direct identifiers, raw
audio, storage keys, or raw child-level feature vectors.

Research datasets and artifacts must not contain direct identifiers or
transcript text. Monitoring and reports must suppress small subgroup cells.

## 15. Staleness and Report Boundary

If the transcript, transcript version, feature set, or compatible artifact
changes:

- the prior result becomes stale;
- it is removed from the active workflow;
- it cannot be copied, exported, or included in reports; and
- it remains accessible only through restricted audit history where required.

No evidence text enters a report automatically. A therapist must select,
rewrite, and attest any report wording.

## 16. Runtime and Failure Behavior

Runtime inference is local to the backend service and has no network
dependency.

Engineering budgets:

- p95 inference latency: at most 500 ms;
- request timeout: 2 seconds;
- failure mode: fail closed; and
- browser fallback: prohibited.

If one module fails, its output becomes unavailable without fabricating a
replacement. Other independently valid descriptive workflow sections may
continue.

## 17. Monitoring and Operations

Version 1 monitoring is engineering monitoring only:

- request and inference counts;
- latency;
- provider failures;
- abstention reasons;
- dataset, cohort, model, and rule-map versions; and
- promotion and rollback events.

Telemetry must not include transcript text, direct identifiers, raw audio,
storage keys, or raw child-level feature vectors.

Delayed research labels may be used for controlled retrospective evaluation,
but they must not be treated as complete production performance monitoring.

Heavy bootstrap, subgroup, and corpus stress evaluations run offline for each
versioned candidate, not during inference.

Artifact and experiment retention must be bounded. The promoted artifact and a
documented number of recent candidate runs are retained; obsolete candidates
are removed according to the research retention policy.

## 18. Roles and Approval Boundaries

The implementation plan must assign named responsibilities for:

- dataset snapshot approval;
- feature-schema and extractor compatibility approval;
- threshold and model promotion;
- clinician rule-map approval;
- privacy and consent review;
- rollback authorization; and
- incident response.

No single automated job may build, approve, and promote an artifact.

## 19. Testing Strategy

Required tests include:

- duplicate and overlap detection across source tables;
- participant, corpus, and protocol grouping;
- label and UI roll-up mapping;
- leakage detection;
- golden-fixture feature parity;
- deterministic dataset and artifact hashing;
- unsupported language, task, age, and code-switching behavior;
- profile-level support and abstention;
- calibration and promotion-gate evaluation;
- immutable provenance and checksum verification;
- timeout and provider failure behavior;
- stale-result blocking;
- consent withdrawal;
- role and audit boundaries;
- offline behavior;
- `Reviewed` and `Record disagreement` semantics;
- report-exclusion behavior;
- safety wording scans; and
- end-to-end reviewed transcript to Evidence Review Panel flow.

## 20. Success Criteria

Version 1 is successful when:

- the canonical dataset is auditable and leakage controls are enforced;
- each reference result reports participant and corpus support;
- unsupported profile cells abstain without silent pooling;
- training and runtime canonical features pass golden-fixture parity;
- the Gate 1 research report uses preregistered metrics and thresholds;
- failed promotion gates keep the classifier unavailable;
- supported therapist evidence contains no probability, ranking, predicted
  class, or diagnostic wording;
- users can distinguish input, scope, reference-data, and system failures;
- stale and withdrawn results cannot enter active reports; and
- all required tests and project verification pass.

## 21. Decision Log

### Decision 1: Use a hybrid architecture

- **Alternatives:** descriptive similarity only; direct four-class model;
  sequential hierarchical model.
- **Objection:** a sequential gate could propagate errors and resemble a
  diagnostic decision tree.
- **Resolution:** Gate 1 and descriptive profile comparison run in parallel.
  Gate 2 classification is a research challenger only.

### Decision 2: Preserve original research groups

- **Alternatives:** train one `Other` class; exclude LT/STI/HL.
- **Objection:** LT, STI, and HL are heterogeneous and may encode corpus
  artifacts.
- **Resolution:** keep them distinct in data and evaluation. Use `Other
  language profiles` only as a UI roll-up.

### Decision 3: Retain named public-corpus profiles without classification

- **Alternative:** hide all group names.
- **Objection:** ASD/DD similarity may be read as diagnostic probability.
- **Resolution:** show no probability, rank, winner, or predicted class.
  Present independent evidence cards only when each profile has adequate
  participant and corpus support.

### Decision 4: Fail closed

- **Alternatives:** widen age bands; merge tasks; use English reference data
  for Thai samples with a warning.
- **Objection:** silent pooling would overstate reliability.
- **Resolution:** abstain per profile and explain the precise reason.

### Decision 5: Research validation precedes therapist activation

- **Alternative:** enable the classifier immediately for demonstration.
- **Objection:** current label provenance, feature parity, calibration, and
  generalization evidence are insufficient.
- **Resolution:** keep the classifier unavailable until preregistered
  engineering gates pass. Descriptive comparison is promoted independently.

### Decision 6: English-only cohort evidence

- **Alternative:** cross-language comparison with caveats.
- **Objection:** English public corpora do not establish Thai reference
  validity.
- **Resolution:** Thai and unsupported mixed-language samples receive
  descriptive features only in the Therapist App.

### Decision 7: Reduce Version 1 scope

- **Alternative:** implement the full hierarchical ensemble, deep learning,
  monitoring, and retraining in one release.
- **Objection:** the scope exceeds the available independent participants and
  creates unnecessary operational risk.
- **Resolution:** Version 1 is limited to data audit, descriptive comparison,
  and Gate 1 research validation.

### Decision 8: Separate ML evidence from clinical actions

- **Alternative:** derive referral recommendations from classifier outputs.
- **Objection:** cohort classification does not estimate the benefit of an
  assessment or referral.
- **Resolution:** show only versioned clinician-authored options for
  consideration, separate from model evidence.

## 22. Structured Review Disposition

The design was reviewed sequentially by:

- Skeptic / Challenger;
- Constraint Guardian;
- User Advocate; and
- Integrator / Arbiter.

Critical and high-severity objections concerning label validity, gate
semantics, diagnostic interpretation, cohort support, confounding, numerical
promotion criteria, privacy, runtime reliability, and cognitive load were
accepted and incorporated.

Final multi-agent disposition: **APPROVED** for written specification and
implementation planning within the reduced Version 1 scope. This approval is
not clinical validation and does not permit bypassing promotion gates.
