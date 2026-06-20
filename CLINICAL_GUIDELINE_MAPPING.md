# Clinical Guideline Mapping

The Guideline Mapping Catalog links transcript-derived speech-language features to clinical constructs, source references, Thai validation status, and report-use limitations.

Canonical code source: `shared/src/services/guideline-mapping-catalog.js`.

## Advisor-Facing Framing

Use `guideline-linked interpretation` when describing this feature to advisors or in the term paper. The system links observed speech-language features to guideline-backed clinical constructs and review cues; it does not diagnose ASD, identify a single cause, or decide whether a finding is clinically significant.

Avoid describing this feature as automated `correlation with guideline` if that wording implies diagnosis or threshold-based classification. The safer explanation is:

- The system shows which guideline or clinical reference is relevant to each finding.
- The report can list which guideline sources were used for the session.
- The interpretation remains descriptive unless a project-verified norm or threshold is added later.
- The therapist must review the transcript and clinical context before using the finding in a Progress Report.

## Source Use Rules

- Verified open-access sources may support broad construct linkage only.
- Thai/local sources remain `TODO: verify source` unless the exact source and intended use are reviewed.
- No source currently supplies project-verified Thai norms, cutoffs, or diagnostic thresholds.
- Reports must not label feature values as normal, abnormal, elevated, low, delayed, or clinically significant unless a verified threshold is added later.

## Verified Open-Access Sources Currently Used

| Source ID | Title | Use Boundary |
|---|---|---|
| `LSA-METHODOLOGY` | ASHA Spoken Language Disorders / language sample analysis methodology reference | Broad language sample analysis construct linkage only |
| `ASHA-SPOKEN-LANGUAGE` | ASHA Spoken Language Disorders | Speech-language construct linkage only |
| `ASHA-AUTISM` | ASHA Autism and Autism Spectrum Disorder | Social communication review cue context only |
| `ASHA-SOCIAL-COMMUNICATION` | ASHA Social Communication Disorder | Pragmatic/social communication construct linkage only |
| `NICE-CG128` | NICE CG128 Autism spectrum disorder in under 19s | High-level review context only, not diagnostic pathway automation |

## Pending Local Source

| Source ID | Title | Status |
|---|---|---|
| `THAI-DSPM` | Thai DSPM developmental surveillance reference | `TODO: verify source` |

## Feature Mapping Summary

| Feature | Clinical Construct | Report Use |
|---|---|---|
| `mlu`, `mluw` | Expressive language complexity | Descriptive language sample review |
| `ttr` | Lexical diversity | Descriptive lexical diversity review |
| `total_utterances`, `total_words` | Language sample productivity | Sample-size and productivity context |
| `unintelligible_count`, `unintelligible_ratio` | Speech intelligibility and sample quality | Transcript quality and intelligibility cue |
| `echolalia_count`, `echolalia_ratio` | Social communication review | Review cue requiring function and context |
| `pronoun_reversal_count` | Language-specific social communication review | Requires clinician and language-specific interpretation |
| `zero_vocalization_count` | Communication engagement | Contextual review cue |
| `nonverbal_vocalization_count` | Communication mode | Descriptive communication-mode review |
| `question_ratio` | Pragmatic language use | Pragmatic review cue |
| `turn_taking_count` | Conversational reciprocity | Descriptive trend and context review |
| `restricted_interest_words` | Restricted-interest context | Context cue only; word count alone is insufficient |

## Report Limitation

Guideline-linked interpretation in Progress Reports means traceable construct linkage and review cues. It does not mean clinical validation, diagnosis, or automated treatment recommendation.
