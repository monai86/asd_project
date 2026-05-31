# Speech Therapist Prototype Phase 8

Phase 8 hardens the prototype for pilot-readiness review. It does not make the
system clinically validated or production-approved.

## Completed Scope

- Visible sample/mock/local development mode banner.
- Case-level privacy operation actions for export, consent withdrawal, and deletion request review.
- Admin-only audit-log access in frontend repository and backend API route.
- SQL schema and RLS guidance for privacy operations and admin-only audit review.
- E2E smoke command covering login, case/session creation, upload metadata, mock processing, transcript review, feature rerun, report generation, and report export.
- Security, privacy, deployment, release, and rollback documentation.

## Acceptance Boundary

- Real clinical data must not be entered while sample mode is visible.
- Therapists and clinicians can access only owned cases and sessions.
- Deletion is an auditable operational request, not immediate hard deletion.
- Reports and AI outputs remain clinical decision support and do not diagnose ASD.
