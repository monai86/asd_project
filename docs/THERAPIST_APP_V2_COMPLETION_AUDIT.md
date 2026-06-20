# Therapist App v2 Completion Audit

Current-state audit date: 2026-06-14

This audit maps the attached Phase 0-14 plan to current repository evidence.
It is scoped to the local research/education prototype and does not claim
clinical validation, production readiness, or automated diagnosis.

## Verification Snapshot

Latest verified commands after the 2026-06-14 safety-default update:

- `cd apps/api && PYTHONPATH=. pytest -q` -> 36 passed, 3 skipped
- `pytest tests/test_asr_evaluation.py -q` -> 2 passed
- `cd apps/therapist-app-v2 && npm test` -> 10 passed
- `cd apps/therapist-app-v2 && npm run lint` -> passed
- `cd apps/therapist-app-v2 && npm run build` -> passed
- `cd apps/therapist-app-v2 && npm run typecheck` -> passed
- Runtime route smoke with `npm run dev` + Playwright screenshots -> `/login`,
  `/`, `/record`, `/results`, `/review-transcript`, `/transcript`, `/report-summary`, and
  `/settings?scope=admin` returned HTTP 200 and rendered non-empty pages.

Safety grep currently returns only the product-spec forbidden-wording checklist
line, not product UI/API copy.

Safety-default check: `THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE=false` is now
the default in API settings, `.env.example`, and Docker Compose. Failed-QA or
unattested transcript feature extraction requires explicit engineering opt-in
plus an override reason.

## Phase Evidence

| Phase | Current evidence | Audit status |
| --- | --- | --- |
| 0. Repository audit | `docs/THERAPIST_APP_V2_AUDIT.md` exists and current v2 evidence is summarized in this completion audit. | Complete for local MVP scope. |
| 1. Product principles | `docs/THERAPIST_APP_V2_PRODUCT_SPEC.md` covers case-centered workflow, review gates, no automated diagnostic claim, privacy, and report principles. | Complete for local MVP scope. |
| 2. Therapist App v2 frontend | `apps/therapist-app-v2/` contains Next.js App Router pages for login, today, cases, case detail, session workspace, reports, and settings/admin. Frontend tests cover 10 workflow cases, `npm run build` verifies all app routes compile, and Playwright runtime smoke returned HTTP 200 for key routes. | Complete for local MVP scope. |
| 3. Backend API boundary | `apps/api/app/main.py` wires cases, sessions, goals, transcripts, features, AI review, reports, jobs, privacy, settings, evaluation, and audit routes. | Complete for local MVP scope. |
| 4. Manual CHA/transcript workflow | Transcript services parse/upload/manual-entry/edit/split/merge/export QA and attestation. Tests cover unsupported language, code-switching warning, stale-output invalidation, media header export, and QA gates. | Complete for local MVP scope. |
| 5. Feature extraction | `feature_service.py` extracts core language sample features and review cues with schema/version/warnings. Tests cover MLU, TTR, NDW, unintelligible ratio, unknown speaker ratio, QA blocking, and version capture. | Complete for local MVP scope; acoustic features remain intentionally optional/unavailable unless future audio alignment is configured. |
| 6. Audio-to-draft pipeline | `audio_job_service.py` provides async job status, provider interface, quality checks, draft transcript creation, status history, ASR failure, and diarization warnings. | Complete for experimental scaffold scope. |
| 7. ASR evaluation harness | `asr_evaluation_service.py`, `tests/test_asr_evaluation.py`, and `data/evaluation/` exist and pass. | Complete for local MVP scope. |
| 8. AI assistance module | `ai_review_service.py` stores sanitized, editable/rejectable review support with five assistance areas, provenance, review priority, and therapist review status. | Complete for local MVP scope. |
| 9. ML baseline | `ml_baseline_service.py`, evaluation endpoints, and `artifacts/model_card_v2.md` exist. Tests cover dataset/baseline/model-card paths, and the model card states review-support use, metrics to report, limitations, bias risks, and out-of-scope uses. | Complete for local MVP scope. |
| 10. Reports | `report_service.py` supports draft, patch, sign-off, Markdown/HTML/PDF export fallback, report focus sections, limitations, and export timestamp. Reports UI shows four report types and disables export before sign-off. | Complete for local MVP scope. |
| 11. Consent/privacy/governance | `consent_service.py`, storage adapter, audit route, role checks, privacy operation queue, and consent withdrawal tests exist. Tests block new sessions, session edits, transcript uploads, audio upload/process, feature read/extract, report draft, and export after withdrawal. | Complete for local MVP scope. |
| 12. Tests/gates | Backend, ASR, frontend tests, lint, build, and typecheck pass. Safety grep returns one documented product-spec checklist false positive and no product UI/API hit. | Complete for local MVP scope. |
| 13. Docker/local demo | `docker-compose.yml`, `.env.example`, `README_THERAPIST_APP_V2.md`, `data/demo/sample_session.cha`, `data/demo/sample_report.md`, and `data/demo/demo_manifest.json` exist. Compose statically defines frontend, API, worker, PostgreSQL, and Redis services with debug override disabled. | Complete for local MVP scope. |
| 14. Final deliverables | Major files/directories exist: audit, spec, README, frontend app, API app, transcript workflow, feature service, AI review service, ML baseline, report generation, tests, docker compose, model card, known limitations, and this Phase 14 summary. | Complete for local MVP scope. |

## Endpoint Map

Required Phase 3 API endpoints are present:

- Cases: `GET/POST /api/v1/cases`, `GET/PATCH /api/v1/cases/{case_id}`,
  `GET /api/v1/cases/{case_id}/timeline`.
- Sessions: `POST /api/v1/cases/{case_id}/sessions`,
  `GET/PATCH /api/v1/sessions/{session_id}`,
  `GET /api/v1/sessions/{session_id}/status`.
- Transcript: upload CHA, manual transcript, read transcript, patch transcript,
  split, merge, export CHA, QA, and attest endpoints.
- Audio/jobs: metadata-only signed upload intent, upload completion, async
  process job, and job status endpoints.
- Features: transcript feature extraction and session feature retrieval.
- AI Review: create, read, and therapist patch endpoints.
- Reports: draft, list, patch, sign off, read, and export endpoints.
- Consent/governance: consent withdrawal, audit logs, therapy goals, privacy
  operation request queue, settings, ASR evaluation, ML dataset, baseline, and
  model-card endpoints.

## Test Evidence

Backend `apps/api/tests/test_workflow.py` covers the core case/session/manual
CHA workflow, QA blocking, therapist attestation, feature extraction, AI review
schema, report generation/sign-off, transcript split/merge/export, stale output
invalidation, unsupported language warning, code-switching warning, metadata
audio upload, async audio job states, ASR failure, diarization warning, consent
withdrawal, queued job cancellation, local storage object deletion, privacy
operation queue, SQL repository table coverage, ML dataset/baseline/model-card
paths, JSON repository persistence, and runtime settings.

Root `tests/test_asr_evaluation.py` covers ASR single-pair metrics and dataset
JSON/Markdown report output.

Frontend `apps/therapist-app-v2/src/__tests__/pages.test.tsx` covers mock
therapist/admin login routing without browser storage, Today / Work Queue,
Cases, Case Detail progress/timeline/goals, Session Workspace stepper and
transcript editor, API-backed feature summary and AI review status, QA warning
display, attestation/sign-off gating, all four report types, export gating, and
therapist/admin settings scope.

## Demo And Deployment Evidence

- `docker-compose.yml` defines API, worker, frontend, PostgreSQL, and Redis
  services. The API/worker run with debug feature override disabled by default.
- `.env.example` documents API URL, frontend API base URL, mock mode, repository
  modes, SQL URL, queue mode, Redis URL, metadata storage mode, and local
  storage root.
- `README_THERAPIST_APP_V2.md` documents install, backend run, frontend run,
  worker run, tests, case/session creation, CHA upload, transcript edit/export,
  report generation/export, audio-to-draft workflow, ASR evaluation, ML
  baseline/model card, Docker Compose, local demo persistence, audit/roles,
  PostgreSQL-ready schema, professor demo path, and known limitations.
- `data/demo/demo_manifest.json`, `data/demo/sample_session.cha`, and
  `data/demo/sample_report.md` provide non-identifying local demo assets.

## Phase 14 Summary

Changed:

- Added a parallel Next.js Therapist App v2 in `apps/therapist-app-v2/`.
- Added a mock-first, PostgreSQL-ready FastAPI boundary in `apps/api/`.
- Added manual CHA/transcript workflow, QA, transcript editing/export,
  feature extraction, structured AI-assisted review support, report generation,
  privacy operations, consent withdrawal behavior, async audio draft jobs, ASR
  evaluation, ML baseline scaffolding, Docker/local demo files, and v2 docs.

Reused:

- Existing project language around human-in-the-loop review, review priority,
  transcript sign-off, report eligibility, privacy/consent boundaries, CHA/CHAT
  conventions, language-sample features, and decision-support safety wording.
- Existing repository structure remains intact, including the legacy Vite
  clinician app, public screening app, presentation dashboard, shared services,
  Python speech/audio modules, and prior documentation.

Deprecated for v2 therapist workflow:

- Dashboard-first navigation and scattered technical/research pages are kept out
  of the main v2 therapist navigation.
- Audio automation, ASR placeholders, debug override, model diagnostics, and raw
  research outputs are not MVP dependencies for ordinary therapist workflow.
- Raw probabilities, diagnostic wording, and binary child-label categories are
  excluded from therapist-facing v2 UI/API output.

Still needing real validation or pilot hardening:

- Thai clinical validation, clinical norms, production authentication, signed
  private object storage, encryption, backup/restore procedures, operational
  audit review, real ASR provider dependencies, durable worker orchestration,
  PDF packaging guarantees, and deployment-specific external-AI compliance.

Professor demo path:

1. Open `/login`, show mock therapist/admin role selection, and note local demo
   mode.
2. Open Today / Work Queue and Cases, then case `C-1024`.
3. Show consent, session timeline, therapy goals, progress comparison, and the
   seven-step Session Workspace.
4. Demonstrate CHA upload/manual transcript review, QA warnings, therapist
   attestation, feature summary, AI-assisted review support, report draft, and
   report sign-off/export gating.
5. Open `data/demo/demo_manifest.json`, `data/demo/sample_session.cha`, and
   `data/demo/sample_report.md` to show the non-identifying demo package.

Pilot continuation path:

- Replace mock role headers with real identity and authorization.
- Configure private signed object storage and deletion verification.
- Move queue/worker state to durable infrastructure.
- Expand ASR gold datasets before enabling real audio automation in pilot use.
- Add clinical governance review for report templates, retention policy, audit
  review, and external-AI deployment configuration.
- Run therapist usability testing and document validation limits before any
  real clinical workflow.

## Current Conclusion

The Phase 0-14 local MVP plan is implemented and verified for the repository's
research/education prototype scope. Remaining work is explicitly pilot
hardening and clinical validation, not missing local MVP deliverables.
