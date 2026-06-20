# Therapist Simple Workflow

Therapist Simple Mode is the default presentation of the existing therapist app workflow. It does not create a separate app, route, or reduced clinical workflow.

## Five-Step Demo Flow

1. Open case
2. Add session
3. Upload file
4. Review transcript
5. Generate Progress Report

## Default Screen Principles

- Show one clear next action per workflow step.
- Use therapist-facing labels such as `Review Priority`, `Concern Level`, `Review transcript`, and `Generate Progress Report`.
- Keep model details, reference comparison, feature schema, acoustic/prosody metrics, and technical QA behind `View details` or `Advanced` controls.
- Show workflow status as Upload -> Processing -> Transcript Review -> Report Ready.
- Keep mock/demo mode reliable and clearly labeled.

## Screen Simplification Targets

### Cases

- Primary: active child cases, consent/review readiness, and `Open case`.
- Secondary: detailed demographics, audit metadata, storage mode, and repository details behind `View details`.

### Session

- Primary: `Add session`, `Upload file`, processing status, and next required action.
- Secondary: pipeline logs, acoustic/prosody metrics, API payload details, and storage implementation details behind `Advanced`.

### Transcript Review

- Primary: transcript quality status, unresolved review items, therapist sign-off action, and whether the report is eligible.
- Secondary: line-level technical QA, feature extraction diagnostics, and raw ASR/diarization metadata behind `View details`.

### Progress Report

- Primary: reviewed session, feature summary, guideline-linked findings, clinical caution, and export action.
- Secondary: model coefficients, reference cohort similarity, feature schema, and exploratory metrics behind `Advanced`.

## Required Human Review

Transcript Sign-Off is the whole-transcript checkpoint that controls report eligibility. Line-level review can support QA, but an Exportable Progress Report requires whole-transcript sign-off.

## Avoided Labels

- Avoid `AI diagnosis`.
- Avoid `ASD probability`.
- Avoid `diagnostic result`.
- Avoid `production-ready clinical system`.
