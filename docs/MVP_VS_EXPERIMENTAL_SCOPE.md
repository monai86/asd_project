# lingualens MVP vs Experimental Scope

This document separates the stable local manual-first MVP from experimental or pilot-hardening surfaces. It is intentionally conservative: anything that is not verified as part of the manual-first local workflow stays experimental until validated, configured, and governed for a real pilot.

## Stable Manual-First MVP

- Case and session management for non-identifying demo records.
- Manual CHA upload and manual transcript entry.
- Transcript QA, therapist attestation, split/merge/edit support, and CHA export.
- Feature extraction from QA-reviewed and therapist-attested transcripts.
- AI-assisted review support that remains editable or rejectable and is presented only as decision support.
- Report draft, report edit, therapist sign-off, and Markdown/HTML/PDF-fallback export gating.
- Consent withdrawal behavior that blocks new workflow actions and report export.
- Local demo settings, admin-scoped audit review, and privacy operation queue.
- Frontend route coverage for login, Today, Cases, Case detail, Session Workspace, Reports, and Settings/Admin.

## Experimental Or Pilot-Hardening Scope

- Audio upload and audio-to-draft-CHA processing.
- Whisper, Faster Whisper, WhisperX, Batchalign, diarization, and provider-specific ASR dependencies.
- Redis queue mode and durable worker orchestration.
- Production authentication, authorization, and role enforcement.
- Private object storage, signed upload URLs, encryption, deletion verification, and backup/restore procedures.
- PostgreSQL/Supabase deployment hardening, RLS audits, and migration discipline.
- ASR dataset benchmarking beyond local WER/CER/coverage/speaker-label checks.
- Semantic WER, missed entity rate, and Thai ASR validation.
- ML baseline training, model cards, subgroup reliability, and feature importance reporting.
- Thai clinical norms, Thai clinical validation, and clinical deployment governance.
- Desktop packaging such as Tauri or Electron.

## Safety Boundary

- The app is not a diagnostic tool.
- The UI and API must not show ASD probability.
- Review priority is scheduling and review support only.
- Report language must remain therapist-editable and must include limitations.
- AI-assisted review output must never become final report content without therapist review and sign-off.

## Final Verification Table

| Feature | Backend endpoint | Frontend page/component | Test coverage | Current status |
| --- | --- | --- | --- | --- |
| Create/open case | `POST /api/v1/cases`, `GET /api/v1/cases/{case_id}` | `SessionWorkspaceClient`, `CasesPage`, `CaseDetailPage` | `apps/api/tests/test_workflow.py::test_case_session_transcript_feature_report_workflow`, `apps/lingualens-app/src/__tests__/pages.test.tsx` | Stable local MVP |
| Create session | `POST /api/v1/cases/{case_id}/sessions`, `GET /api/v1/sessions/{session_id}` | `SessionWorkspaceClient`, `SessionWorkspacePage` | Backend workflow test, frontend API-backed workflow test | Stable local MVP |
| Upload sample CHA | `POST /api/v1/sessions/{session_id}/transcripts/upload-cha` | `SessionWorkspaceClient`, `TranscriptEditorPanel` | Backend workflow test, frontend API-backed workflow test | Stable local MVP |
| Run transcript QA | `POST /api/v1/transcripts/{transcript_id}/qa` | `SessionWorkspaceClient`, `TranscriptEditorPanel` | Backend workflow test, frontend transcript edit/QA test | Stable local MVP |
| Attest transcript | `POST /api/v1/transcripts/{transcript_id}/attest` | `SessionWorkspaceClient`, `TranscriptEditorPanel` | Backend workflow test, frontend transcript attestation/sign-off gating test | Stable local MVP |
| Extract features | `POST /api/v1/transcripts/{transcript_id}/extract-features`, `GET /api/v1/sessions/{session_id}/features` | `SessionWorkspaceClient` | Backend feature metrics test, frontend API-backed workflow test | Stable local MVP |
| Generate AI-assisted review | `POST /api/v1/sessions/{session_id}/ai-review`, `GET /api/v1/sessions/{session_id}/ai-review`, `PATCH /api/v1/ai-reviews/{ai_review_id}` | `SessionWorkspaceClient`, `CaseDetailPage` | Backend workflow/rejection tests, frontend API-backed workflow test | Stable local MVP decision support |
| Draft report | `POST /api/v1/sessions/{session_id}/reports/draft` | `SessionWorkspaceClient`, `ReportsPage` | Backend workflow test, frontend API-backed workflow test | Stable local MVP |
| Edit report | `PATCH /api/v1/reports/{report_id}` | `SessionWorkspaceClient` | Backend workflow test, frontend API-backed workflow test | Stable local MVP |
| Sign off report | `POST /api/v1/reports/{report_id}/sign-off` | `SessionWorkspaceClient`, `TranscriptEditorPanel`, `ReportsPage` | Backend workflow test, frontend sign-off gating/API-backed workflow tests | Stable local MVP |
| Export report | `GET /api/v1/reports/{report_id}/export?format=markdown` | `SessionWorkspaceClient`, `ReportsPage` | Backend workflow test, frontend API-backed workflow test | Stable local MVP |
| Export reviewed CHA | `GET /api/v1/transcripts/{transcript_id}/export-cha` | `SessionWorkspaceClient` | Backend split/merge/export test, frontend API-backed workflow test | Stable local MVP |
| Consent withdrawal | `POST /api/v1/cases/{case_id}/withdraw-consent` | Settings/Admin privacy copy and backend workflow boundary | Backend consent withdrawal tests | Stable local MVP backend behavior |
| Audio upload/process | `POST /api/v1/sessions/{session_id}/audio/upload`, `POST /api/v1/sessions/{session_id}/audio/process`, `GET /api/v1/jobs/{job_id}` | Session Workspace source intake labels, Settings/Admin runtime controls | Backend audio job tests | Experimental |
| ASR evaluation | `POST /api/v1/evaluation/asr`, `POST /api/v1/evaluation/asr-dataset` | Settings/Admin runtime controls only | Backend ASR evaluation tests and root `tests/test_asr_evaluation.py` | Experimental engineering QA |
| ML dataset/baseline/model card | `POST /api/v1/evaluation/ml-dataset`, `POST /api/v1/evaluation/ml-baseline`, `POST /api/v1/evaluation/model-card` | Settings/Admin runtime controls only | Backend ML path tests | Experimental research support |
| PostgreSQL/Supabase storage | SQL migration docs and repository/storage boundaries | Not a default local UI dependency | SQL contract tests and documented schema/RLS guidance | Pilot hardening |

## Current Completion Statement

The local manual-first MVP is verified as a stable demo workflow. The larger original product vision still contains experimental and pilot-hardening work, especially realtime WebSockets, production identity, private object storage, durable workers, real ASR providers, semantic WER, missed entity rate, desktop packaging, and Thai clinical validation.
