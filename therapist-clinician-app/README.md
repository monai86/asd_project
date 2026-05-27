# Speech Therapist / Clinician Prototype App

This is the standalone web app for project surface 2: the workflow used by
speech therapists and clinicians. It is intentionally separate from:

- `public-screening/` — public/general-user screening support web app
- `app/dashboard_unified.py` and `presentation-dashboard/` — project dashboard
  and advisor presentation surfaces

## Scope

The app currently runs in `MOCK_MODE=True` and includes:

- mock email/password login for therapist, clinician, and admin users
- role-aware case filtering
- anonymized child case creation
- anonymized child case editing
- seeded clinical sessions and review queues
- owned-case session creation and session timelines
- therapist notes linked to cases or sessions
- audio/video upload metadata validation and linked metadata records, without storing files
- `.cha` transcript upload/selection, QA, and editable mock transcript review
- mock 14-feature extraction/rerun status
- AI decision-support output with screening support score and evidence review
- progress monitoring with score timeline, feature trends, therapy goal
  progress, before/after radar comparison, and exportable Markdown reports
- final hardening views for quick actions, recent queues, case workflow
  status, generated reports, and session metadata
- admin audit log

## Safety Boundary

This app is a clinical decision-support prototype. It does not diagnose ASD and
does not replace qualified clinical judgment. AI-assisted outputs must be
reviewed by a therapist or clinician before use.

Phase 3 stores upload metadata only. It does not persist selected file bytes,
create browser previews, or run the real audio pipeline.

Phase 4 can upload/select CHAT `.cha` transcript text or generate a mock CHAT
transcript from audio metadata. Real audio-to-CHAT execution remains deferred
until real file storage exists.

Phase 5 adds mock 14-feature schema output and AI decision-support panels. The
screening support score is not a diagnosis and requires therapist review.

Phase 6 adds descriptive progress tracking and printable/exportable Markdown
reports. Reports summarize reviewed sessions, feature trends, therapy goal
progress, transcript status, and safety wording; they are not ASD diagnoses.

Phase 7 closes the `Therapist-Prototype.md` acceptance checklist. It adds
dashboard quick actions, recent cases/sessions, high review-priority cases,
case-level AI/report/status summaries, session metadata, and explicit wording
that audio/video playback remains deferred because this app stores metadata
only.

## Run Locally

```bash
cd therapist-clinician-app
npm install
npm run dev
```

Open the Vite URL shown in the terminal.

## Mock Accounts

| Role | Email | Password |
|---|---|---|
| therapist | `therapist@example.test` | `demo-password` |
| clinician | `clinician@example.test` | `demo-password` |
| admin | `admin@example.test` | `demo-password` |
