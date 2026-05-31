# Privacy And Consent Operations

The therapist-clinician app treats privacy work as auditable workflow, not as
instant destructive UI behavior.

## Consent Rules

- Real upload and backend processing require granted guardian consent.
- Consent withdrawal updates the case summary status and active consent records.
- After withdrawal, new secure upload and processing should be blocked.
- Existing audit and sign-off records remain available for authorized review.

## Privacy Operation Types

| Type | Purpose | Immediate Effect |
|------|---------|------------------|
| `case_export_request` | Prepare a case-scoped privacy export | Adds queue item and audit event |
| `consent_withdrawal_request` | Record guardian withdrawal | Marks consent withdrawn and audits it |
| `case_deletion_request` | Request deletion/retention review | Adds queue item; no silent hard delete |

## Export Boundary

Exports must be scoped to one owned child case and include only the related
case, sessions, consent records, audio metadata, transcripts, transcript lines,
features, AI support outputs, reports, and clinical sign-offs.

## Deletion Boundary

Deletion requests require admin or privacy-owner review. Required audit logs,
clinical sign-offs, retention records, and incident evidence must not be removed
automatically from the therapist UI.
