# Project Status

Current advisor-readiness target: `v1.6.0`.

This project is an AI-assisted speech-language clinical decision-support prototype for therapist review, language sample analysis, transcript QA, guideline-linked interpretation, and Progress Report generation. It is not a diagnostic device and has not been clinically validated for Thai children.

## Current Deliverable Status

- Therapist / Clinician App: primary deliverable and main demo surface.
- Public Screening App: supplementary educational demo surface.
- Presentation Dashboard: supplementary advisor/research explanation surface.
- Python ML and audio pipeline: research and prototype support code, not a deployed clinical system.

## Current Strengths

- Human-in-the-loop transcript review and sign-off workflow.
- Mock/demo mode with seeded therapist cases and sessions.
- Reviewed-only report eligibility boundary for decision-support outputs.
- Shared Guideline Mapping Catalog for feature-to-construct mapping.
- Safety wording that separates research model results from clinical decision support.

## Current Limitations

- The system does not diagnose ASD and cannot confirm or rule out ASD.
- The model was evaluated on public English-language datasets, not validated as a clinical model for Thai children.
- The audio-to-CHAT pipeline is experimental and requires therapist transcript review.
- Guideline-linked findings provide construct linkage and review cues only; no project-verified Thai thresholds or norms are applied.
- Acoustic/prosody features are exploratory/display-only unless separately validated.

## Advisor Demo Priority

The recommended demo path is the Therapist Five-Step Workflow:

1. Open case
2. Add session
3. Upload file
4. Review transcript
5. Generate Progress Report

