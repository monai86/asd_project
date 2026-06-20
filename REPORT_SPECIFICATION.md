# Progress Report Specification

The canonical report artifact is the Progress Report. It is a therapist-facing clinical decision-support artifact, not a diagnostic report.

## Report Eligibility

An Exportable Progress Report requires transcript review sign-off and safety wording. Before sign-off, the app may show a Draft Report Preview, but guideline-linked interpretation must be withheld or clearly marked unavailable.

## Required Sections

- Child profile and anonymized case information.
- Session analyzed and transcript version used.
- Transcript quality / human review status.
- Feature summary.
- Guideline-linked interpretation for report-eligible findings.
- Guideline sources used.
- AI-assisted explanation or reviewed reference cohort similarity when report eligible.
- Limitations and clinical caution.

## Guideline-Linked Findings

Each Evidence-Linked Finding should include:

- feature name
- observed value
- clinical construct
- source title or pending source marker
- Thai validation status
- interpretation boundary

If no project-verified threshold or norm exists, the finding must stay descriptive and must not assign severity.

## AI and Model Output Rules

- Preliminary outputs are not report eligible.
- Reviewed reference cohort similarity may appear only when reviewed and report eligible.
- Screening Support Score may appear in technical detail, but simplified therapist-facing screens should prefer Review Priority or Concern Level.
- Research Model Results belong in research/dashboard documentation, not as clinical validation claims.

## Clinical Caution

Every report must state that the system does not diagnose ASD, does not replace qualified clinical judgment, and has not been validated for Thai children.

