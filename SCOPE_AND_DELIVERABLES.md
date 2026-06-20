# Scope and Deliverables

## Primary Deliverable

The Therapist / Clinician App is the primary project deliverable. It demonstrates a human-reviewed clinical decision-support workflow for anonymized child cases, session artifacts, transcript review, feature summaries, and Progress Report generation.

The advisor-facing v1.6.0 scope should present one main workflow only:

1. Open case
2. Add session
3. Upload file
4. Review transcript
5. Generate Progress Report

The public screening app and presentation dashboard remain useful supporting artifacts, but they should not be introduced as equal primary products for the term-paper deliverable.

## Supplementary Surfaces

The Public Screening App is supplementary and educational only. It should not be presented as the main clinical workflow or as a diagnostic product.

The Presentation Dashboard is supplementary and supports advisor explanation of model performance, dataset limits, feature importance, and Thai validation gaps. It should not duplicate the therapist workflow.

## Research Output

The ML model result is a research result. Model performance metrics may support the term paper discussion, but they are separate from therapist-facing clinical decision support and must not be described as clinical validation.

## Clinical Boundary

This project is suitable as a clinical decision-support prototype and research demonstration. It is not a deployed clinical system, not a diagnostic device, and not clinically validated for Thai children.

The current audio-to-CHAT workflow is experimental. Automated transcript or audio-derived outputs require therapist review before feature interpretation or exportable reporting.

## In Scope for v1.6.0

- Simplify the therapist-facing workflow and labels.
- Keep advanced metrics available behind details or advanced sections.
- Strengthen Progress Reports with transcript review status, guideline-linked findings, and clinical caution.
- Keep guideline mappings traceable without inventing citations or norms.
- Clarify documentation for advisor review.
- Frame ML accuracy and classification results as Chapter 4 research results, separate from therapist-facing Progress Report behavior.

## Out of Scope for v1.6.0

- Clinical diagnosis.
- Production deployment.
- Thai clinical validation claims.
- New large AI features.
- Rebuilding the public screening app or dashboard as primary products.
