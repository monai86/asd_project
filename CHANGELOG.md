# Changelog

> **โปรเจกต์:** AI-Assisted Clinical Assessment of Autism (Term Paper)  
> **รูปแบบ:** Semantic Versioning (MAJOR.MINOR.PATCH)  
> **วันที่ update ล่าสุด:** 31 พฤษภาคม 2026

## [v1.2.1] - 2026-05-31

### Hardened (Clinical Pilot & Reproducibility)
- **Environment & Build Reproducibility** — Confirmed clean `npm install`, `npm test`, and `npm run build` setups for `therapist-clinician-app`, `public-screening`, and `presentation-dashboard`.
- **Database Repository Interface** — Added `ClinicalRepository` abstract class base interface in `src/clinical_workflow/repository_interface.py` defining all domain actions and made `MockClinicalRepository` implement it.
- **PostgreSQL / Supabase Adapter Placeholder** — Built `PostgresSupabaseRepository` placeholder database adapter mapping all 20+ interface methods with clear query planning and SQL TODO boundaries.
- **Python Test Infrastructure** — Restructured requirements to include test dependencies and isolated heavy audio tests with `@pytest.mark.audio` markers so core validations run fast.
- **Explicit Runtime Modes** — Centralized three modes (`mock`, `local_dev`, `pilot_backend`) in the frontend constants and upgraded the environment banner design in the therapist app to prevent accidental real data input.
- **Anonymization Enforcement** — Enforced child code validations in both frontend input and backend repository paths to block any spaces or real child names.
- **FastAPI API Contract** — Documented all FastAPI endpoints (`docs/API_CONTRACT.md`) with explicit request/response examples and decision-support disclaimers.
- **CI-style Script** — Added `scripts/check_project.sh` validating Python imports, running pytest core suite, and building/testing all 3 frontend applications.

## [v1.2.0] - 2026-05-31

### Added (Therapist Clinical Pilot Backend & Secure Workflow)
- **FastAPI Pilot Boundary** — Added `src/therapist_backend/` with routes for auth, cases, sessions, secure audio upload intent, processing jobs, transcript sign-off, feature extraction, reports, and audit logs.
- **Secure Clinical Workflow Models** — Added consent records, private file objects, processing jobs, clinical sign-offs, and model run metadata to the clinical workflow layer.
- **Secure Upload Gate** — Added consent-gated secure backend upload mode for therapist audio/video workflows, using signed upload intent semantics instead of exposing permanent storage paths.
- **Clinical Safety Tests** — Added backend contract tests for consent, private storage metadata, processing job transitions, transcript sign-off, and non-diagnostic model run metadata.

### Added (Phase 8 Privacy & Release Readiness)
- **Visible Environment Mode Banner** — Added explicit sample/mock/local development mode status to reduce accidental real-data entry during demos.
- **Privacy Operations Workflow** — Added auditable case export, consent withdrawal, and deletion-review request actions.
- **Admin Audit Review** — Added admin-only audit-log access boundaries in the frontend repository, backend API, and SQL/RLS guidance.
- **Release Readiness Docs** — Added security, privacy/consent, release checklist, rollback, ADR, and SQL migration draft documentation.
- **E2E Smoke Coverage** — Added a smoke test command covering login, case/session creation, upload metadata, mock processing, transcript review, feature rerun, report generation, and export.

### Added (Public Screening App Refactor & SPA Migration)
- **Single Page Application (SPA) Migration** — Refactored the entire Public Screening Web App from a multi-page site into a single cohesive SPA shell (`index.html`) using client-side hash routing (`#home`, `#screening`, `#results`, `#education`, etc.).
- **Session State Persistence** — Resolved state fragmentation by ensuring form progress, session inputs, child profiles, theme settings, and language choices persist perfectly across view transitions.
- **Mockup UI Redesign** — Transformed the Public Screening Web App's layout and design to match a modern light-lavender visual mockup.
- **Top Header & Bottom Tab Navigation** — Replaced the fixed left-sidebar layout on desktop with a fixed horizontal top-header and implemented a mobile bottom tab navigation bar for better responsive usability.
- **Simplified Results Layout** — Designed clean risk-assessment cards (Low, Moderate, High Concern) and clear checklists of next-step recommendations.
- **Collapsible Detailed Results** — Hidden the detailed gauge, breakdown graphs, and diagnostic charts behind a toggle button ("ดูรายละเอียดผลการคัดกรอง") to preserve clean visuals by default.
- **Improved Thai Typography** — Styled variables to prioritize Prompt and Sarabun font stacks, with HSL colors optimized for lavender/purple primary styling (#6C5DD3).

### Changed
- **Therapist App Storage UX** — Added secure storage messaging and guardian-consent upload locking for backend/private storage modes.
- **Therapist Schema Docs** — Expanded database/API documentation for PostgreSQL-ready clinical pilot entities and FastAPI routes.
- **Sticky Sidebar Offset** — Adjusted `.screening-left` panel positioning to `100px` to prevent overlapping with the fixed desktop horizontal header during scroll.
- **Action Buttons Visibility** — Relocated the results screen action buttons (PDF download, restart, learn more) to be always visible at the bottom of the results content rather than hidden inside the detailed report toggle.

## [v1.1.0] - 2026-05-27

### Added (Centralized Integration & Demo Hardening)
- **Centralized Shared Services** — Unified developmental concern scoring (`scoring-service.js`) and client-side transcript observation scanning (`speech-analysis-service.js`) under `@shared/services/`.
- **Cross-App Path Alias Mapping** — Configured `@shared/*` path resolution alias mapping across all three active web applications: `public-screening/`, `therapist-clinician-app/`, and `presentation-dashboard/`.
- **TypeScript Compliance** — Integrated `"ignoreDeprecations": "6.0"` in `presentation-dashboard/tsconfig.app.json` to resolve `baseUrl` compiler deprecation warnings.
- **Clinical Workflow User Documentation** — Authored a comprehensive [Speech Therapist & Clinician App User Guide](file:///Users/porschecaa/Desktop/asd-project/docs/THERAPIST_APP_USER_GUIDE.md) explaining pre-seeded therapist/clinician accounts, caseload boundaries, case/session creation, audio/transcript review workflows, feature extraction, AI decision-support, and progress reporting.
- **Walkthrough Demo Script** — Formulated a high-fidelity [Demo Script](file:///Users/porschecaa/Desktop/asd-project/docs/DEMO_SCRIPT.md) outlining a step-by-step presentation scenario for speech therapists (Login -> Dashboard -> Create Case -> Add Session -> Upload Audio -> Review Transcript -> Extract Features -> Inspect AI support -> Add notes -> Check Trends -> Export PDF/Markdown).
- **Evidence Flag Detection Testing** — Extended Python pytest suite with explicit test coverage for `test_evidence_flag_detection` mapping feature-level contributions to clinical meanings.
- **Rigorous Test Validation** — Fully verified the integrity of 116 Python unit tests (pytest) and 64 Frontend JavaScript unit tests (Vitest).

### Changed
- **Removed Code Duplication** — Deleted duplicate local copies of `scoring.js` and `speech-analysis.js` from `public-screening/src/js/` and redirected all forms to resolve `@shared/services/` instead.
- **Safety Labeling & Clinical Boundary Guardrails** — Hardened all user-facing documentation and scripts to emphasize mock-mode prototype status. Ensured absolute avoidance of diagnostic terms (e.g., "diagnosis result"), instead using "screening support", "concern level", "review priority", "clinician review support", and "AI-assisted explanations".

### Fixed
- **Vite Bundler Resolution** — Resolved relative path resolution bugs in `therapist-clinician-app/src/app.js` and `utterance-editor.js` following directory modularization.

### Known Limitations
- **No Real Database or Storage** — The application operates under `MOCK_MODE=True`. No real user database, media file storage, or server-side state is active.
- **Audio Upload Privacy Guardrail** — Media file uploads are strictly tracked as metadata-only records; raw voice recordings are never stored.
- **No Local Clinical Validation** — Model weights and screening rules are trained on English corpora and have not been validated for Thai children.
- **Review Pre-requisite** — Screening priority results require prior clinician verification and review of transcript tier formatting.

---

## [v1.0.0] - 2026-05-27

### Added (Major Refactoring & Modular Pipeline)
- **Refactored Monolithic UI into Modular ES Modules** — Split the 2,034-line `app.js` into clean, testable architectural layers: `src/models/`, `src/store/`, `src/providers/`, `src/services/`, `src/views/`, and `src/components/`.
- **Implemented 10 Canonical Data Models** — Standardized `User`, `ChildCase`, `Session`, `AudioFile`, `Transcript`, `Utterance`, `WordAlignment`, `LinguisticFeatureSet`, `TherapistReview`, and `AIReport` classes matching the Python backend.
- **ASR Engine Provider Abstraction** — Standardized transcription interfaces using a base `ASRProvider` class, implementing an interactive `MockASRProvider` and an offline `WhisperProvider` placeholder.
- **Complete Clinical Transcript Processing Pipeline** — Supported a complete audio-to-analysis workflow inspired by TalkBank/Batchalign2:
  - **Audio Upload (Module 1):** File format validation (`.wav`, `.mp3`, `.m4a`, `.mp4`, `.mov`; limits: 250MB) and metadata-only tracking.
  - **ASR Transcription Queue (Module 2):** Asynchronous transcription pipeline execution with simulated interactive latency.
  - **Utterance Segmentation (Module 3):** Automated speaker mapping (CHILD, THERAPIST, CAREGIVER) and sentence boundaries segmentation.
  - **Timing Alignment Layer (Module 6):** Word-level and utterance-level timestamp synchronization.
  - **Linguistic Feature Extraction (Module 7):** Extracted Core 14-feature schema (with optional interaction/acoustic-derived indicators such as pause count, turn-taking, and response latency).
  - **QA Quality Assessment (Module 8):** Assessed transcript files for CHAT headers (`@Begin`/`@End`) and flagged low-confidence transcription segments.
  - **Interactive Transcript Editor (Module 4):** Inline correction of speaker tags and text utterances with confidence badges.
  - **Therapist Clinical Review Sign-off (Module 9):** Logged clinician review notes, compliance audit trails, and status flags.
  - **Document Exporters (Module 5):** Supported downloading transcripts as CHAT-like `.cha` files or exporting full structured session JSON datasets.
  - **Printable Progress Reports (Module 14):** Automated generation of Markdown/PDF progress trends with caseload goal tracking and safety disclaimers.
- **Integrated Unit Testing Suite (Module 15)** — Added 7 Vitest test suites (12 tests) verifying segmentation, feature counts, pronoun reversals, safety boundaries, and exporting.

---

## [v0.23.0] - 2026-05-27

### Changed (Cleanup)
- **Project surfaces consolidated** — reduced from 5 surfaces to 3 active web apps: `public-screening/`, `therapist-clinician-app/`, and `presentation-dashboard/`
- **Deleted obsolete files:**
  - `app/dashboard_unified.py` — Pastel Streamlit dashboard (no longer used)
  - `app.py` — HF Spaces / Streamlit entry point
  - `project_dashboard/` — legacy static Project Atlas
  - `Dockerfile` + `.dockerignore` — Docker deployment no longer needed
  - `packages.txt` — Docker system deps
  - `.streamlit/config.toml` — Streamlit config
  - `DEPLOYMENT_NOTE.md` — HF Spaces-specific notes
  - `dist/` (root) — old Project Atlas build artifacts
  - `.wrangler/` (root) — stale Wrangler state cache
  - `scripts/build_public_atlas.sh` — Atlas build script
  - `scripts/export_dashboard_data.py` — Streamlit data export script
- **Rewrote `README.md`** — now reflects 3 web apps, Python ML backend, and clean project structure; removed all Streamlit/Docker/HF references
- **Rewrote `docs/DEPLOYMENT.md`** — now covers Cloudflare Pages setup for all 3 web apps and Python ML backend local usage only
- **Cleaned `.gitignore`** — removed Docker/Streamlit-specific patterns

### Kept
- `src/` Python ML backend — reference code for term paper
- `tests/` — full pytest suite
- `scripts/compute_fairness_metrics.py`, `scripts/paper_scout.py`, `scripts/build_zotero_import.py` — still used
- `docs/SPEECH_THERAPIST_PROTOTYPE_PHASE1-7.md` — development history docs
- `docs/VERSION_UPDATE_CHECKLIST.md` — update workflow reference
- All literature files (`docs/literature/`) — paper research

---

## [v0.22.0] - 2026-05-27

### Added
- **Public Screening Support Web App** — Added a brand new, fully bilingual (Thai/English) client-side static web application built with Vite and Vanilla HTML/CSS/JS (`public-screening/` directory). Features include:
  - **Landing Page**: Explains educational purpose, lists clear disclaimers, and details what the tool does and does not do.
  - **Screening Form**: Includes a 14-question Likert-scale questionnaire (speech-language, social communication, and repetitive behavior concerns) with programmatic input validation (red outline on blank fields) and an optional observation notes text area.
  - **Results Page**: Incorporates an interactive concern level gauge with an animated physical needle that shifts between -90deg and 90deg dynamically based on overall score (0–100), category score breakdown cards, detailed question-by-question accordion reviews, and actionable recommendations.
  - **Education Page**: A dedicated page containing collapsible FAQ accordions for parents and caregivers.
  - **Bilingual Support (i18n)**: Centralized ES module dictionary translating all UI copy, error warnings, concern explanation text, and questions in place dynamically without reloading.
  - **Print / PDF Summary**: Uses CSS media print styles to generate clean, print-optimized reports from the browser with zero external library overhead (with a plain-text fallback).
  - **Zero Data Retention**: Stores temporary responses and final scores in local `sessionStorage` and cleans all traces upon clicking "Start Over".
- **Deployment Guidelines**: Documented Cloudflare Pages integration configuration parameters (Build command, Root directory, output directory) for Vite app hosting.

---

## [v0.21.1] - 2026-05-27

### Fixed
- **Dashboard Text Overlaps & Layout Squeezing** — Resolved text crowding across table columns and horizontal bar charts in the presentation dashboard. Specifically:
  - Enforced `whitespace-nowrap` on header and cell rows for all tables (Dataset, Model Comparison, LOCO, and Cohort Explorer) to prevent text wrapping.
  - Wrapped tables with horizontal scroll overflow boxes and applied minimum widths (`min-w-[960px]` / `min-w-[1024px]`) to maintain clean tabular spacing on small screens.
  - Implemented `CustomYAxisTick` for horizontal bar charts (Feature Importance and Linear Model Contributions) to stack Thai labels and English abbreviations onto two separate lines, with custom bolding and opacity.
  - Increased the vertical height of the Linear Model Contributions chart from `h-80` to `h-[460px]` to provide adequate spacing for stacked labels.

---

## [v0.21.0] - 2026-05-27

### Added
- **Advisor-ready glossary** — added `CONTEXT.md` with canonical project terms for screening risk estimates, clinical decision support, human-in-the-loop review, Thai validation, acoustic profile, and research-gap support
- **Pronoun reversal feature** — added conservative `pronoun_reversal_count` / `pronoun_reversal_ratio` extraction and promoted `pronoun_reversal_count` into the shared 14-feature model schema
- **Model Trust confidence intervals** — added bootstrap 95% confidence intervals for AUC, sensitivity, specificity, PPV, NPV, and Brier score in `reports/metrics/classification_ci.csv`
- **Subgroup reliability flags** — added `reports/metrics/subgroup_reliability.csv` with `insufficient_n` flags for small or single-class subgroup rows
- **Uploaded-audio acoustic profile** — added descriptive acoustic profile extraction for uploaded audio, including duration, voiced ratio, median F0, F0 IQR, pause ratio, and child speech rate
- **Human review gate** — added dashboard checklist gating before uploaded-audio screening risk estimates are interpreted or exported

### Changed
- **Screening model artifacts** — regenerated feature CSVs, model bundle, model card, schema artifact, figures, and metrics for the 14-feature schema; LogReg binary ROC-AUC is now `0.9352`
- **Dashboard wording** — replaced diagnosis-like prediction language in the main flow with screening-risk-estimate language and added descriptive-only acoustic-profile caveats
- **Advisor docs** — updated README, Thai project summary, next-steps roadmap, Thai validation readiness notes, audio pipeline docs, and presenter guide for the advisor-ready development cycle

### Tests
- Added tests for pronoun reversal extraction, acoustic profile extraction, bootstrap confidence intervals, and subgroup reliability flags

---

## [v0.20.1] - 2026-05-24

### Changed
- **Thai project status docs** — refreshed `docs/PROJECT_SUMMARY_TH.md`, `docs/NEXT_STEPS_TH.md`, and `docs/SUMMARY_TH.md` to reflect the current v0.20.x state, clarify that paper/literature tooling is research-gap support rather than a core project feature, and prioritize Thai validation, demo QA, and evidence wording as next steps

---

## [v0.20.0] - 2026-05-23

### Added
- **Research-gap paper scout support** — added `scripts/paper_scout.py` for manual ASD/AI paper discovery, Semantic Scholar/OpenAlex metadata search, seed-list deduplication, tag inference including `video`, screening decisions, and optional Markdown report saving
- **Paper scout guide** — added `docs/literature/PAPER_SCOUT.md` with commands, supported tags, screening rules, and clinical safety boundaries for research review
- **Zotero import support** — added `scripts/build_zotero_import.py` to generate collection-specific RIS files, keyword tags, and an import summary from the literature seed list, scout report, and curated PubMed/Scholar/IEEE additions

### Changed
- **README research support docs** — documented the paper scout as a supporting research-gap workflow and its focused test command

### Tests
- Added `tests/test_paper_scout.py` for query selection, tag inference, screening decisions, and duplicate filtering

---

## [v0.19.0] - 2026-05-20

### Added
- **Thai-aware Transcript QA** — AI Transcript Reviewer now flags Thai utterance text when `@Languages` does not include `tha`, summarizes optional ASR/diarization confidence metadata, and warns when average confidence is below the demo threshold
- **Fairness and calibration metrics** — added `src/fairness_metrics.py` and `scripts/compute_fairness_metrics.py` to compute ECE, Brier score, TPR/FPR differences, and demographic parity differences without adding Thai child data
- **Metric exports** — generated `reports/metrics/fairness_metrics.csv` and `reports/metrics/calibration_summary.csv` for dashboard review
- **Therapist report PDF export** — progress reports can now be saved as Markdown or PDF, with a clear dependency fallback path for demo use
- **Clinician Workflow Simulator** — added a Streamlit page that combines transcript QA, screening-pattern interpretation, and progress case brief generation in a compact human-in-the-loop workflow

### Changed
- **Pastel dashboard as primary surface** — switched `app.py` and Docker to launch `app/dashboard_unified.py`, making the Pastel Streamlit dashboard the only recommended public dashboard
- **Deployment docs** — removed Cloudflare Pages / static Project Atlas from the recommended public flow and updated guides to use Streamlit/Hugging Face/Docker for Pastel
- **Streamlit dashboard** — added Model Trust & Fairness tables plus PDF/Markdown export selection on Transcript QA & Reports
- **Project Atlas** — Model Trust now displays calibration summary values and a fairness audit table alongside existing trust views
- **Clinical readiness docs** — README, NEXT_STEPS_TH, DISCUSSION_TH, and Thai validation readiness docs now describe v0.19.0 as decision-support readiness work that still requires external Thai validation

### Tests
- Added `tests/test_fairness_metrics.py`
- Extended transcript reviewer tests for Thai language-tag mismatch and low ASR confidence
- Extended therapist report tests for PDF export and invalid format handling

---

## [v0.18.0] - 2026-05-20

### Added
- **AI Speech Therapist Assistant** — added `src/speech_therapist_assistant.py` for rule-based/template-based therapist-facing interpretation of transcript QA, speech-language patterns, screening risk estimates, progress trends, and Markdown case briefs
- **Assistant Streamlit page** — added an `AI Speech Therapist Assistant` route with transcript QA interpretation, feature-row/manual screening interpretation, progress trend summary, and downloadable therapist-facing case brief
- **Assistant Project Atlas content** — expanded Clinical Readiness cards with assistant capabilities, boundaries, and workflow
- **AI Transcript Reviewer** — added `src/transcript_reviewer.py` for rule-based CHAT `.cha` review, including structure checks, speaker-tier checks, utterance quality warnings, marker counts, quality score/status output, and optional `pylangacq` parse validation
- **Therapist Progress Report** — added `src/therapist_report.py` plus generated sample Markdown reports for Roger and Mark under `reports/progress_reports/`
- **Transcript QA & Reports Streamlit page** — added upload-based `.cha` review, issue table, marker counts, Thai safe-use explanation, child selection, report rendering, and Markdown download
- **Thai Validation Readiness documentation** — added `docs/THAI_VALIDATION_READINESS_TH.md` covering current status, readiness assets, requirements for Thai deployment, pilot design, safe wording, and what the demo does/does not prove
- **Clinical Readiness Project Atlas section** — added cards for prototype status, Thai clinical prerequisites, transcript QA workflow, therapist report workflow, and safe-use boundary
- **Clinical readiness model card fields** — updated `artifacts/model_card.json` with `thai_validation_status: "not_yet_validated"`, missing validation items, safety controls, and recommended next steps

### Changed
- **Safe-use wording** — README, NEXT_STEPS_TH, DISCUSSION_TH, Thai validation docs, Streamlit, and Project Atlas now more clearly state that the project is screening support / risk estimate / decision support / progress tracking only, requires human-in-the-loop review, and is not validated for Thai children
- **Project documentation** — README now documents the Transcript QA & Reports workflow, new test commands, generated reports, and Thai validation readiness file

### Tests
- Added `tests/test_transcript_reviewer.py`, `tests/test_therapist_report.py`, and `tests/test_speech_therapist_assistant.py` for the QA, report, and assistant APIs

---

## [v0.17.2] - 2026-05-17

### Added
- **Unified dashboard foundation** — added `app/dashboard_unified.py` with
  Streamlit-adapted Project Atlas styling, session-state navigation for the
  first 10 dashboard sections, working Overview/Dataset/Features/EDA/
  Screening/Audio/Model Trust/Progress/Research/Presentation pages, real model
  inference, XAI/severity scoring, trust metrics, longitudinal tracking, and
  advisor-demo narrative mode

### Changed
- **README dashboard commands** — documented the optional unified dashboard
  entrypoint alongside the existing Streamlit dashboard

### Fixed
- **Unified dashboard cleanup** — removed stale placeholder routing, added
  CSV-missing guards for generated feature files, and split cached model
  artifact loading from runtime training so `st.cache_resource` no longer
  receives a DataFrame argument

---

## [v0.17.1] - 2026-05-17

### Added
- **Public access links** — README now surfaces the Hugging Face public app,
  GitHub Pages Project Atlas, and a short presenter guide so the project can
  be shared without digging through local setup instructions
- **Presenter guide** — added `docs/PRESENTER_GUIDE_TH.md` for a
  3-5 minute project walkthrough covering what the system does, what to show,
  and which claims to avoid

### Changed
- **Project entrypoint documentation** — README now highlights the public
  access path first, making the repository easier to demo for parents,
  advisors, and first-time viewers

---

## [v0.17.0] - 2026-05-17

### Added
- **Parent public demo** — เพิ่มหน้า Streamlit สำหรับผู้ปกครองแบบ Thai-first,
  no-data-retention, safe wording, parent concern checklist, optional audio
  privacy gate และ downloadable parent summary โดยไม่อ้างว่าเป็น diagnosis
- **Shared feature schema** — เพิ่ม `src/feature_schema.py` เป็น source of
  truth เดียวสำหรับ 13 features, positive/marker feature groups และ
  uncertainty thresholds เพื่อกัน feature order mismatch ระหว่าง training,
  dashboard และ model bundle
- **Model Trust metrics** — `src/classifier.py` สร้างไฟล์ใหม่สำหรับ dashboard:
  `binary_oof_predictions.csv`, `threshold_metrics.csv`,
  `calibration_bins.csv`, `decision_curve.csv`,
  `subgroup_performance.csv`, `leave_one_corpus_out.csv`
- **Model artifacts** — เพิ่ม `artifacts/screening_model.joblib`,
  `artifacts/model_card.json` และ `artifacts/feature_schema.json` สำหรับ
  versioned model loading, model card, data hash, thresholds และ caveats
- **Feature schema test** — เพิ่ม `tests/test_feature_schema.py` เพื่อตรวจว่า
  CSV, schema artifact และ feature order ของโมเดลตรงกัน
- **Project Atlas + Model Trust dashboard** — ยกระดับ `project_dashboard/`
  ด้วย Model Trust section, threshold playground, calibration view,
  decision curve, uncertainty zone, subgroup robustness, leave-one-corpus-out,
  model card, data inventory, corpus explorer, research evidence, glossary
  และ presentation mode
- **Static public Atlas build** — เพิ่ม `scripts/build_public_atlas.sh` และ
  `netlify.toml` เพื่อสร้าง bundle สำหรับ deploy dashboard presentation โดย
  ไม่ copy raw `.cha`, uploaded audio หรือ executable `.joblib` model

### Changed
- **Classifier schema** — sklearn classifier ใช้ 13 features รวม echolalia
  แล้ว; LogReg binary ROC-AUC ใหม่ = **0.9312**, sensitivity = **0.8462**,
  specificity = **0.9123**, PPV = **0.9167**, NPV = **0.8387**,
  Brier score = **0.0983**
- **Deep learning baselines** — rerun PyTorch baselines บน 13-feature schema:
  TabularMLP ROC-AUC = **0.9320**, accuracy/F1 = **0.8525**;
  UtteranceLSTM ROC-AUC = **0.7193**, accuracy/F1 = **0.6311**
- **Dashboard model loading** — Streamlit dashboard พยายามโหลด versioned
  model bundle ก่อน และ fallback ไป train runtime เฉพาะเมื่อ artifact ไม่มี
- **Audio privacy control** — หน้า Audio Assessment เพิ่มปุ่มลบ temp
  audio/transcript cache ของ session หลังตรวจ segment เสร็จ
- **README / dashboard docs** — อัปเดตวิธีรัน, output metrics, artifacts,
  Project Atlas และ Model Trust ให้ตรงกับ v0.17.0
- **Deployment readiness** — อัปเดต `docs/DEPLOYMENT.md` สำหรับ Streamlit
  Cloud, Hugging Face Spaces, Netlify/Cloudflare Pages และ Docker; ปรับ
  Streamlit CORS config ให้ไม่ถูก override ตอน startup

### Fixed
- **Multi-class CV stability** — แปลง label เป็น numpy string array เพื่อแก้
  `cross_val_predict` กับ pandas/pyarrow indexing ใน Python 3.13
- **Docker healthcheck** — เพิ่ม `curl` ใน production image เพราะ
  `HEALTHCHECK` เรียก `/_stcore/health`

## [v0.16.0] - 2026-05-07

### Added
- **Interactive project dashboard** — เพิ่ม `project_dashboard/`
  เป็น modern dashboard สำหรับรวบรวมเนื้อหาทั้งโปรเจกต์ โดยดึงข้อมูลจาก
  `data/` และ `reports/` มาให้เลือก filter/compare ได้ ครอบคลุม overview,
  dataset, feature reference, EDA workspace, screening controls, parent concern checklist,
  audio workflow, segment QA preview, model results, report figures,
  progress tracking, first-vs-last comparison, clinical safety และ next steps
- **Next steps roadmap** — เพิ่ม `docs/NEXT_STEPS_TH.md` เพื่อสรุปแผนพัฒนา
  AI transcript reviewer, therapist progress report, Thai validation,
  และการใช้ project skills ทั้งหมดใน workflow ถัดไป

### Changed
- **Project dashboard parity** — ปรับหน้า dashboard ใหม่ให้ใกล้เคียง
  Streamlit เดิมมากขึ้น โดยเพิ่ม scatter, distribution, correlation heatmap,
  raw data preview, realtime-style project signal, feature documentation
  ครบ 13 ตัว และ progress trajectory
- **README.md** — เพิ่มวิธีรัน interactive project dashboard และอัปเดต
  project structure ให้รวม dashboard ใหม่กับ roadmap ใหม่
- **Project docs** — อัปเดต `docs/PROJECT_SUMMARY_TH.md` และ
  `docs/DISCUSSION_TH.md` ให้ชี้ไปยัง dashboard ใหม่และ roadmap ใหม่

### Fixed
- **Dashboard responsive layout** — แก้การ์ด metric, feature reference,
  correlation heatmap และ first-vs-last table ที่ข้อความ/ตารางล้นกรอบใน
  browser viewport แคบ

---

## [v0.15.2] - 2026-05-02

### Added
- **ASD-specific AI review skills** — เพิ่ม `asd-clinical-ml-reviewer`,
  `asd-audio-pipeline-qa`, และ `asd-advisor-report-writer` ใน `.agents/skills/`
  เพื่อช่วยตรวจ clinical ML validity, audio pipeline QA, และเอกสารสำหรับคุยอาจารย์
- **Project-scoped general workflow skills** — เพิ่ม `personal-data-analyst`,
  `personal-code-quality`, `personal-security-auditor`, `personal-researcher`,
  และ `personal-devops-deployer` เพื่อให้ agent มี workflow ที่เหมาะกับข้อมูล,
  code quality, security/privacy, research, และ deployment ของโปรเจกต์นี้

### Changed
- **README.md** — อัปเดต project structure ให้แสดง project-level skills ใหม่ทั้งหมด

---

## [v0.15.1] - 2026-05-01

### Added
- **Project-level AI workflow skill** — เพิ่ม `.agents/skills/project-update-workflow/`
  เพื่อให้ AI agents ใช้ workflow อัปเดต `README.md`, `CHANGELOG.md`, docs,
  commit message, GitHub push, และ release tag อย่างเป็นระบบ
- **Windsurf bridge rule** — เพิ่ม `.windsurf/rules/project-update-workflow.md`
  เพื่อให้ Windsurf ใช้ workflow เดียวกันได้แม้ไม่ได้อ่าน Agent Skills โดยตรง

### Changed
- **README.md** — อัปเดต project structure ให้รวม `.agents/` และ `.windsurf/` สำหรับ AI/project workflow
- **.gitignore** — อนุญาตให้ track Windsurf project rule โดยยัง ignore
  scratch files อื่นใน `.windsurf/`

---

## [v0.15.0] - 2026-04-26

### Added — Audio pipeline overhaul (production-grade)
- **TH+EN code-switching ASR** ใน `src/audio_pipeline/whisper_transcribe.py`
  - เพิ่ม `LanguageStrategy`: `auto` / `english` / `thai` / `dual_pass` / `thai_specialized`
  - Initial prompt 2 ภาษาสำหรับ child-therapy domain (toys, family, fillers)
  - Hallucination filter: drop segments ที่ `no_speech_prob>0.7`, `avg_logprob<-1.0`, repeated n-grams
  - Temperature fallback chain `[0.0, 0.2, 0.4, 0.6]` + `condition_on_previous_text=False`
  - Per-segment language tag บน `WordSegment` และ `UtteranceSegment`
  - Lazy-load `biodatlab/whisper-th-medium-combined` (Thai-fine-tuned, no HF token)
  - Default model: `base` → **`small`** (ดีกว่ามากบน child speech และ Thai)
- **Speaker diarization ที่ไม่ต้อง HF token** — `EmbeddingDiarizer`
  - ใช้ `speechbrain/spkrec-ecapa-voxceleb` (192-dim ECAPA-TDNN embeddings)
  - `sklearn.AgglomerativeClustering` (cosine, distance_threshold=0.5, max_speakers=4)
  - Age-aware F0 thresholds: 300/260/220/180 Hz ตามช่วงอายุ
  - Cluster scoring: weighted F0 + duration + (optional) enrollment cosine
  - Fallback ลง pitch heuristic เมื่อ utterance สั้นเกินจะ embed
  - Speaker enrollment: รับ reference clip 5-10 วินาที
- **silero-VAD** (`src/audio_pipeline/vad.py`) — VAD cleaner กว่า Whisper-internal
- **Re-segmentation** (`src/audio_pipeline/segmentation.py`) — `clean_segments`,
  `filter_to_speech_regions` (drop <0.2s, split ที่ silence ยาว, merge same-speaker
  ที่ห่าง <0.3s)
- **CHAT formatter ตรง TalkBank spec** — เขียนใหม่หมด (`src/audio_pipeline/chat_formatter.py`)
  - `@Languages` auto-detects single (eng/tha) vs code-switching
  - `@Participants` / `@ID` (10 pipe-separated fields) / `@Date` / `@Coder` / `@Activities` / `@Time Duration` / `@Media`
  - Word-level codes: `xxx`, `&-um`/`&-uh`/`&-เอ่อ`/`&-อืม` fillers,
    `[/]` repetition, `(.)`/`(..)`/`(...)` pauses
  - **Inline language switch markers** `[- eng]` / `[- tha]` สำหรับ code-switching
  - Sentence terminators `. ? !` preserved; auto-added when missing
  - 0-vocalization markers (`*CHI: 0 .`) สำหรับช่วงเด็กเงียบยาว (capped 3)
  - `&=vocalization` สำหรับ non-verbal long segments
- **CHATTER validator integration** (`src/audio_pipeline/chatter_validator.py`)
  - Java subprocess wrapper รอบ TalkBank's `chatter` JAR
  - Auto-fix safe issues (trailing whitespace, missing terminators) — idempotent
  - Graceful skip ถ้า Java/JAR ไม่มี (validation marked as skipped)
  - Parse output เป็น `ValidationReport(errors, warnings, fixed_count)`
- **Post-edit UI ใน dashboard** — Segments tab เปลี่ยนเป็น `st.data_editor`:
  - Editable columns: delete checkbox, speaker dropdown, lang, text, min_conf
  - **Re-export .cha** button — ใช้ edited utterances ไป regenerate + revalidate
  - Pipeline result cached ใน `st.session_state` เพื่อรอด rerun ที่ data_editor trigger

### Tests
- เพิ่ม `tests/test_audio_pipeline_v015.py` — **25 unit tests** ครอบคลุม:
  hallucination filter, dual-pass merge, age-aware F0, segmentation,
  CHAT formatter (TH+EN code-switching, fillers, repetition, pauses,
  zero-vocalization, terminators), CHATTER auto_fix idempotency

### Docs
- เพิ่ม `docs/AUDIO_PIPELINE.md` — full architecture, language strategies,
  diarizer tuning, CHATTER setup, optional pyannote upgrade with HF_TOKEN
  explainer, troubleshooting matrix

### Dependencies
- `requirements.txt`: เพิ่ม `speechbrain>=1.0.0`, `torchaudio>=2.0`
  (silero-VAD ดาวน์โหลดผ่าน `torch.hub` ตอน runtime)
- `pyannote.audio` ยังเป็น **optional** (commented) — ต้องการ HF_TOKEN

### Notes
- **ไม่ต้อง HF_TOKEN** สำหรับ pipeline หลัก — ทุก model ใช้ open weights
- รองรับ **Thai + English code-switching** ตามคำขอ
- Backward-compatible: `audio_to_cha` API เดิมยัง work — แค่มี kwargs
  ใหม่ (`strategy`, `enrollment_audio_path`, `activities`, `validate`)
  เป็น optional

---

## [v0.14.1] - 2026-04-26

### Fixed
- **Streamlit deprecation warnings** — แก้ `use_container_width=True` → `width='stretch'` ใน dashboard.py
- **Documentation consistency** — อัปเดต PROJECT_SUMMARY_TH.md และ DISCUSSION_TH.md ให้ตรงกับ features ปัจจุบัน

### Changed
- **Project overview tags** — เพิ่ม new feature tags ใน Screening Tool และ Audio Assessment pages
- **Feature count** — อัปเดตจาก 11 เป็น 13 features (รวม echolalia)

---

## [v0.14.0] - 2026-04-26

### Added
- **Multi-modal input** — เพิ่ม project-authored parent concern checklist
  (not M-CHAT-R/F) ใน Screening Tool form ทำให้ system รับ input จาก 2 modalities:
  1. **Speech features** (CHAT-derived, 13 features)
  2. **Parent report** (project-authored concern checklist, 10 yes/no items)
- เพิ่มฟังก์ชัน:
  - parent concern item list (10 items + concerning direction)
  - concern severity helper (count concerning answers → 0-10 score)
  - `fuse_severity()` (late-fusion of two modalities)
- แสดง 3 score cards ใหม่: Speech-only · Parent concern · **Combined**
- ทำงานเฉพาะเมื่อตอบ ≥5 ข้อ ไม่ตอบเลยก็ใช้ speech-only ปกติ

### Rationale
อ้างอิง **Abbas et al. (2020)** Multi-modular AI สำหรับ ASD diagnosis ที่
รวม questionnaire + video + clinician input ได้ AUC สูงกว่า single
modality, และ **Megerian et al. (2022)** FDA-cleared device ที่ใช้
3 modalities (caregiver questionnaire + home video + HCP questionnaire).

Parent screening tools เช่น M-CHAT-R/F เป็น established external tools
ที่ต้องตรวจ permission/licensing ก่อน electronic หรือ commercial use;
โปรเจกต์นี้ใช้ checklist ที่เขียนเองสำหรับ demo/research เท่านั้น เพราะ:
- ไม่ต้องการ training data เพิ่ม (rule-based scoring)
- Parent-friendly (ไม่ต้องการ expert)
- Complementary signal (พฤติกรรมที่ไม่อยู่ใน speech transcript)

---

## [v0.13.0] - 2026-04-26

### Added
- **Graded severity scoring (0–10)** ใน Screening Tool — แสดง 3 score
  ที่ map จาก z-score ผ่าน sigmoid:
  1. **ASD severity** — sigmoid(logit) × 10 (สอดคล้องกับ P(ASD))
  2. **Communication strength** — score รวมของ positive features
     (MLU, TTR, words, utterances, questions)
  3. **ASD-marker burden** — score รวมของ negative features
     (echolalia, unintelligible, zero/non-verbal vocalization)
- เพิ่ม `compute_severity()` helper, `POSITIVE_FEATURES`, `MARKER_FEATURES`
- Score cards พร้อม traffic-light colour coding (green/amber/red)

### Rationale
อ้างอิง Eni et al. (2025) **ASDSpeech** — paper แสดงว่า speech-based AI
สามารถ quantify *ระดับความรุนแรง* ของ social communication symptoms ได้
แม่นยำกว่าการบอกแค่ binary yes/no, ตรงกับ ADOS-2 scale.

Graded score มีประโยชน์สำหรับ:
- Speech therapist: วางแผน intervention ตาม sub-scores
- Progress tracking: ดู trajectory ของ score แต่ละมิติ
- Communication: อธิบายผลให้ผู้ปกครองเข้าใจง่ายกว่า binary

---

## [v0.12.0] - 2026-04-26

### Added
- **Uncertainty band (40–60%)** ใน Screening Tool และ Audio Assessment —
  ถ้า P(ASD) อยู่ระหว่าง [0.40, 0.60) ระบบจะรายงานว่า
  *UNCERTAIN — recommend further assessment* แทน HIGH/LOW risk
- เพิ่มค่าคงที่ `UNCERTAIN_LOW`, `UNCERTAIN_HIGH` และฟังก์ชัน `classify_risk()`
  ใน `app/dashboard.py` ใช้ร่วมกันทั้ง 2 หน้า
- Gauge bands ใน Screening Tool ปรับให้สอดคล้องกับ uncertainty zone
  (เขียว → เหลือง 40-60% → แดง)

### Rationale
อ้างอิง Megerian et al. (2022) — FDA-cleared CADx device สำหรับ ASD diagnosis
มี output 3 ทาง (positive / negative / **indeterminate**) ลด over-confident
prediction เมื่อข้อมูลไม่เพียงพอ ปลอดภัยกว่าใน clinical setting

---

## [v0.11.0] - 2026-04-26

### Added
- **Echolalia detection (`echolalia_count`, `echolalia_ratio`)** — feature
  ใหม่ใน `src/data_loader.py` ที่ตรวจจับ utterance ของ CHI ที่
  *ซ้ำคำพูด verbatim* (≥2 content tokens) ของ utterance ใด ๆ
  ภายใน 5 ประโยคก่อนหน้า (รวม self-repetition)
- เพิ่ม column ใน `data/combined_features.csv` (122 rows) และ
  `data/longitudinal_features.csv` (87 rows)
- Screening Tool dashboard ตอนนี้รับ input echolalia ผ่าน form
- Feature reference page อธิบาย echolalia ทาง clinical

### Changed
- `FEATURES` list ใน `app/dashboard.py` เพิ่มจาก 11 → **13 features**
- Re-trained Logistic Regression classifier ด้วย 13 features

### Empirical findings (เบื้องต้น)
จาก dataset ของเรา (122 children):
- **ASD:** echolalia_ratio mean = 0.028, max = 0.169
- **DD:**  echolalia_ratio mean = 0.014, max = 0.096
- **TD:**  echolalia_ratio mean = 0.014, max = 0.054

ASD มี echolalia สูงกว่า TD/DD ~2 เท่า ตรงกับ clinical literature

### Rationale
Prizant (1983) "Echolalia in autism" — echolalia เป็น core ASD marker
ที่ Kanner (1943) ระบุไว้ในนิยามแรกของ autism. การเพิ่ม feature นี้
ปิดช่องว่างใหญ่ของ feature set เดิมที่ไม่มี repetition-based marker

---

## [v0.10.0] - 2026-04-26

### Added
- **Per-prediction explainability (SHAP-equivalent)** — ใน Screening Tool page เพิ่ม
  visualization อธิบายว่าแต่ละ feature ส่งผลต่อ prediction ของเด็กคนนั้น ๆ
  อย่างไร (contribution to log-odds = `coef × standardised value`) ช่วยให้
  speech therapist เข้าใจและไว้ใจผลของ AI มากขึ้น
- แสดง breakdown: `intercept + sum(contributions) = logit → P(ASD)`

### Rationale
อ้างอิงจาก Jeon et al. (2024) "Reliable ASD Diagnosis for Pediatrics Using
Machine Learning and Explainable AI" — XAI ช่วยให้ clinician trust model มากขึ้น

---

## [v0.9.0] - 2026-04-26

### Added
- **CHANGELOG.md** — บันทึก version history ของโปรเจกต์ทั้งหมด เพื่อติดตามการพัฒนา
- **REFERENCES.md** — รวบรวม bibliography ทั้งหมด (37+ รายการ) พร้อมคำอธิบายว่าทำไมใช้อ้างอิงแต่ละตัว

---

## [v0.8.0] - 2026-04-25

### Changed
- **Removed HuggingFace Spaces** — ลบส่วน HF Spaces ออกจาก project ทั้งหมด (DEPLOYMENT.md, Dockerfile)
- **Reverted Dockerfile port** — กลับมาใช้ port 8501 (standard Streamlit) แทน 7860
- **Removed HF-specific comments** — ลบ comment ที่เกี่ยวกับ HF Spaces ออกจาก Dockerfile
- **Updated DEPLOYMENT.md** — ลบ section HuggingFace Spaces ออก เหลือแค่ Streamlit Community Cloud + Self-host Docker

### Added
- **REFERENCES.md** — Full bibliography สำหรับ term paper (clinical linguistics, ASD criteria, tools, methods)

### Removed
- **Git branches** `hf-clean`, `hf-deploy` — ลบ local branches ที่ใช้ทดสอบ HF Spaces

---

## [v0.7.0] - 2026-04-24

### Changed
- **Dockerfile port** — เปลี่ยนจาก 8501 เป็น 7860 (HuggingFace Spaces requirement)
- **Dockerfile comments** — เพิ่ม comment อธิบายว่าเป็น HF-specific
- **README.md** — เพิ่ม YAML header สำหรับ HuggingFace Spaces

### Added
- **Graceful data handling** — dashboard จัดการ missing data files (FileNotFoundError) และ empty DataFrames อย่างสงบ
- **Empty DataFrame guards** — เพิ่ม `if df.empty: return` ใน page_overview, page_eda, page_screening, page_progress

### Fixed
- **HF Spaces binary file rejection** — ใช้ orphan branch + commit squashing เพื่อเอา binary files ออก
- **HF Spaces YAML metadata warning** — เพิ่ม YAML header ใน README.md

---

## [v0.6.0] - 2026-04-23

### Added
- **PROJECT_SUMMARY_TH.md** — สรุปสิ่งที่ทำไปแล้วทั้งหมด (dataset, features, ผลลัพธ์, โครงสร้างระบบ, วิธีรัน)
- **DISCUSSION_TH.md** — ส่วนคุยกับอาจารย์ (3 scenarios, roadmap, จริยธรรม, 11 คำถาม)
- **SUMMARY_TH.md (updated)** — เปลี่ยนเป็น index ที่ชี้ไปสองไฟล์ข้างต้น + เก็บเนื้อหาเดิมไว้ด้านล่าง

### Changed
- **Documentation structure** — แยก project summary และ discussion points ออกจากกันเพื่อให้อ่านง่ายขึ้น

---

## [v0.5.0] - 2026-04-22

### Added
- **DEPLOYMENT.md** — Deployment guide สำหรับ Streamlit Community Cloud + HuggingFace Spaces + Docker
- **Dockerfile** — Production container สำหรับ deployment
- **.dockerignore** — Exclude large corpora จาก Docker image
- **.streamlit/config.toml** — Streamlit configuration (maxUploadSize = 500 MB, theme)
- **packages.txt** — System dependencies สำหรับ Docker (ffmpeg, libsndfile1)
- **Updated README.md** — เพิ่ม pipeline commands, data sources table, audio pipeline section
- **Updated SUMMARY_TH.md** — เพิ่ม deployment options, Docker/Streamlit Cloud

---

## [v0.4.0] - 2026-04-21

### Added
- **Audio upload page** (🎤 Audio assessment) — ใน Streamlit dashboard อัปโหลด `.wav`/`.mp3` → Whisper ASR → diarization → CHAT → features → prediction
- **Audio pipeline CLI** — `python -m src.audio_pipeline.pipeline recording.wav` สร้าง `.cha` จาก audio
- **Smoke test** — `tests/test_audio_pipeline_smoke.py` ทดสอบ CHAT formatter round-trip ผ่าน pylangacq
- **ASR evaluation script** — `src/evaluate_asr.py` คำนวณ WER กับ TalkBank ground-truth

### Changed
- **Dashboard** — เพิ่ม page ที่ 6 (Audio assessment) เข้าไปใน navigation

---

## [v0.3.0] - 2026-04-20

### Added
- **Streamlit dashboard** (`app/dashboard.py`) — 6 pages interactive:
  1. Overview — hero + summary stats
  2. Feature reference — อธิบาย 11 features พร้อม clinical meaning
  3. EDA — interactive boxplots, correlation heatmap, pairplot
  4. Screening — Logistic Regression prediction + feature importance
  5. Progress tracker — longitudinal trajectories + composite score
  6. Audio assessment — upload audio → end-to-end prediction
- **Custom CSS** — polished UI ด้วย gradient backgrounds, cards, metric cards, hero sections
- **Feature documentation** — FEATURE_DOCS dictionary อธิบายแต่ละ feature พร้อม icon, clinical meaning, direction

---

## [v0.2.0] - 2026-04-19

### Added
- **Audio pipeline** (`src/audio_pipeline/`) — end-to-end .wav → .cha:
  - `whisper_transcribe.py` — faster-whisper wrapper (word-level segments + confidence)
  - `diarization.py` — PitchHeuristicDiarizer (F0-based) + PyannoteDiarizer (SOTA)
  - `chat_formatter.py` — Convert utterances → valid CHAT format (@Begin, @ID, *CHI:, %tim:)
  - `pipeline.py` — Wire all 3 components together
- **requirements.txt** — Updated ด้วย faster-whisper, librosa, soundfile, jiwer
- **11 features** — Full feature extraction จาก CHAT (mlu, ttr, unintelligible, zero_vocalization, etc.)

---

## [v0.1.0] - 2026-04-18

### Added
- **Data loader** (`src/data_loader.py`) — Read CHAT files จาก 5 corpora:
  - Eigsti (ASD 16 / DD 16 / TD 16)
  - Nadig (ASD 13 / TD 25)
  - NYU-Emerson (ASD 30)
  - Flusberg (ASD 6, longitudinal)
  - Rollins (5 เด็ก, 21 sessions)
  - QuigleyMcNally (ASD 10 / TD 9)
- **Feature extraction** — 11 features ต่อไฟล์ (mlu, ttr, unintelligible, zero_vocalization, question_ratio, etc.)
- **Combined dataset** — `data/combined_features.csv` (122 children)
- **Longitudinal dataset** — `data/longitudinal_features.csv` (87 sessions, 12 children)

### Added
- **Classifier** (`src/classifier.py`) — Logistic Regression, SVM, Random Forest:
  - Binary: ASD vs non-ASD (AUC 0.93)
  - Multi-class: ASD / DD / TD
  - Stratified 5-fold CV
- **Deep learning** (`src/deep_learning.py`) — TabularMLP + Bi-LSTM:
  - MLP on hand-engineered features
  - Bi-LSTM on utterance sequences

### Added
- **EDA** (`src/eda.py`) — Summary stats + plots:
  - Group counts, age distribution
  - Feature boxplots by group
  - Correlation heatmap
  - Feature pairplot

### Added
- **Progress tracking** (`src/progress_tracking.py`) — Longitudinal analysis:
  - Linear regression per child-feature
  - Composite score (z-score aggregation)
  - 9/12 เด็กแสดง IMPROVING pattern

---

## Versioning Policy

- **MAJOR** — เปลี่ยนโครงสร้างใหญ่, breaking changes, ลบ features ที่สำคัญ
- **MINOR** — เพิ่ม features ใหม่, backward compatible
- **PATCH** — Bug fixes, small improvements, documentation updates

---

## Future Roadmap

### v0.10.0 (Planned)
- [ ] เพิ่ม echolalia ratio feature
- [ ] เพิ่ม pronoun reversal detection
- [ ] เพิ่ม turn-taking latency
- [ ] Thai Whisper fine-tuning (ถ้ามีข้อมูลไทย)

### v1.0.0 (Target)
- [ ] External validation กับ dataset ไทย
- [ ] Mobile app MVP
- [ ] IRB approval + pilot study
