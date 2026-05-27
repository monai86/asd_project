# Speech Therapist / Clinician App Phase 1

The Speech Therapist / Clinician App adds mock multi-user workflow support for
therapist and clinician demos. It is a standalone web app in
`therapist-clinician-app/`, separate from the Pastel dashboard and advisor
slides. It remains a research prototype and demo. It is not a
diagnostic tool, is not validated for Thai children, and requires
human-in-the-loop review by qualified professionals.

## Login

Phase 1 uses `MOCK_MODE=True` and deterministic mock accounts only. The login
form is intentionally shaped like real email/password authentication so it can
be replaced later by a real auth provider, but no real auth provider or database
is connected in this phase.

Sample accounts are shown in the UI:

| Role | Email | Password |
|---|---|---|
| therapist | `therapist@example.test` | `demo-password` |
| clinician | `clinician@example.test` | `demo-password` |
| admin | `admin@example.test` | `demo-password` |

Therapist and clinician are equivalent case-owning clinical users. Admin can
view all mock cases and the full mock audit log for testing and demo purposes.

## Case Ownership

Each mock child case has one `owner_user_id`. Therapist and clinician users see
only their own cases and seeded sessions. Admin users can view all seeded and
newly created mock cases.

The prototype uses anonymized child codes such as `CHI-A01`; it does not use
real child names or wrap TalkBank/ASDBank corpus child labels as clinical cases.

## Creating a Case

Phase 1 supports only minimal case creation:

- anonymized child code
- age in months
- sex
- primary concerns
- consent status
- anonymization status
- external clinical status
- notes

`external_clinical_status` is therapist-entered context from outside the
system. It is not an AI output and must not be treated as a system-generated
diagnosis.

The standalone app includes a case detail view, mock session creation, upload
metadata validation, transcript correction UI, mock feature-rerun status, and
mock report generation. These are UI/data-model scaffolds only; real file
storage, real authentication, and real pipeline execution are deferred.

## Mock Sessions and Dashboard Counts

Seeded mock sessions power Phase 1 dashboard counts for transcript review,
report queues, and review-priority cases. Newly created sessions store metadata
only and do not persist uploaded files.

## Audit Logs

The mock repository records audit events for login and case creation. Admin
users can view the audit table in the Speech Therapist / Clinician App. Therapist and
clinician users do not see the admin-wide audit table.

## Safety Boundary

The prototype displays this persistent disclaimer:

> This system is a clinical decision-support prototype. It does not diagnose
> ASD and does not replace qualified clinical judgment.

Mock data must not be mixed silently with real uploaded data. Future phases that
add real storage, audio upload, transcript correction, feature extraction, or
report generation should keep this boundary visible in the UI and tests.
