# asd-Project Surfaces

The project is intentionally split into three user-facing surfaces. They share
the same safety boundary: this is a research/demo system for screening support,
clinical decision support, and progress tracking. It is not an automated ASD
diagnostic system and is not validated for Thai children.

## 1. Public Screening Support Web App

**Audience:** parents, caregivers, students, or general users.

**Purpose:** help users reflect on developmental speech-language concerns and
decide whether to prepare for a conversation with a qualified professional.

**Current implementation:**

- `public-screening/` — bilingual Thai/English Vite web app
- Streamlit page: `Public Screening Demo`

**Boundary:**

- No diagnosis.
- No claim that a child has ASD.
- No real clinical record management.
- No silent data retention.

## 2. Speech Therapist / Clinician App

**Audience:** speech therapists, clinicians, and qualified reviewers.

**Purpose:** support therapist-reviewed workflow for anonymized child cases,
audio/transcript review, speech-language feature inspection, AI-assisted
decision support, and progress tracking over time.

**Current implementation:**

- `therapist-clinician-app/` — standalone Vite/static web app for the therapist/clinician workflow
- `src/clinical_workflow/` — mock login, roles, case ownership, editable
  anonymized cases, session management, therapist notes, metadata-only audio
  file records, CHAT transcript workflow records, 14-feature mock outputs,
  AI decision-support outputs, therapy goal progress, mock progress reports,
  seeded sessions, and audit logs
- Phase 7 hardening adds dashboard quick actions, recent workflow queues, case
  status summaries, session metadata, generated report lists, and an explicit
  phase completion checklist.
- Related Streamlit pages: `AI Therapist Assistant`, `Clinician Workflow`,
  `Audio`, `Transcript QA`, and `Progress`

**Boundary:**

- Therapist/clinician judgment remains required.
- AI outputs are reviewable support, not final diagnosis.
- Progress reports are descriptive tracking artifacts, not ASD diagnoses.
- Current phases use `MOCK_MODE=True`; no real authentication, database, file
  storage, or uploaded clinical record storage is connected.
- Audio/video playback is deferred because the current therapist app stores
  upload metadata only, not playable file bytes.

## 3. Advisor Dashboard / Slide HTML

**Audience:** advisor, classmates, stakeholders, and people who need to
understand the whole project quickly.

**Purpose:** explain the project story, data sources, feature extraction,
classification/progress results, model trust, audio pipeline, safety limits,
and next development steps.

**Current implementation:**

- Streamlit pages: `Project Map`, `Model Trust`, `Reports`, and
  `Advisor Slides`
- `presentation-dashboard/` — React/Vite slide-style dashboard
- `project_dashboard/` — legacy static Project Atlas reference

**Boundary:**

- Presentation surfaces explain and demonstrate; they are not clinical tools.
- Performance claims must be tied to the public TalkBank/ASDBank data and must
  not imply Thai clinical validation.
