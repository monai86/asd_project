# Project Status

Current maintained version: `v1.6.2`.

This project is an AI-assisted speech-language clinical decision-support prototype for therapist review, language sample analysis, transcript QA, guideline-linked interpretation, and Progress Report generation. It is not a diagnostic device and has not been clinically validated for Thai children.

## Current Deliverable Status

- Therapist App v2 (`apps/therapist-app-v2` + `apps/api`): primary deliverable
  and main demo surface.
- Public Screening App: supplementary educational demo surface.
- Presentation Dashboard: supplementary advisor/research explanation surface.
- Python ML and audio pipeline: research and prototype support code, not a
  deployed clinical system.
- Legacy Vite/Capacitor therapist app: removed from Git.
- Legacy `src/therapist_backend`: retained only for research compatibility and
  its existing tests.

## Current Strengths

- Human-in-the-loop transcript review and sign-off workflow.
- Mock/demo mode with seeded therapist cases and sessions.
- Reviewed-only report eligibility boundary for decision-support outputs.
- Shared Guideline Mapping Catalog for feature-to-construct mapping.
- Safety wording that separates research model results from clinical decision support.
- One documented runtime source of truth shared across Codex and Antigravity.
- Gate 1 reference-evidence candidate passes the engineering promotion gate,
  while clinical and diagnostic claims remain explicitly blocked.

## Current Limitations

- The system does not diagnose ASD and cannot confirm or rule out ASD.
- The model was evaluated on public English-language datasets, not validated as a clinical model for Thai children.
- The audio-to-CHAT pipeline is experimental and requires therapist transcript review.
- Guideline-linked findings provide construct linkage and review cues only; no project-verified Thai thresholds or norms are applied.
- Acoustic/prosody features are exploratory/display-only unless separately validated.
- SQL persistence, production authentication, durable workers, monitoring, and
  private object storage still require pilot hardening.
- Gate 1 is an engineering validation on proxy labels and public English
  corpora, not clinical validation.
- Therapist App v2 currently uses Next.js 14.2.35. Production dependency audit
  reports high/moderate advisories whose automated fix requires a breaking
  Next.js major upgrade; this must be resolved before public production
  deployment.

## Canonical Demo Path

The recommended demo path is the Therapist Five-Step Workflow:

1. Open case
2. Add session
3. Upload file
4. Review transcript
5. Generate Progress Report

See `docs/PROJECT_SOURCE_OF_TRUTH.md` for the exact active/legacy boundaries.
