# LinguaLens Current Handoff

Last verified: 2026-08-16  
Handoff base: `main` at `4771ab0b`

เอกสารนี้เป็น snapshot สำหรับส่งต่องาน ไม่ใช่ architecture authority หากข้อมูล
ขัดกัน ให้ยึด `docs/PROJECT_SOURCE_OF_TRUTH.md`, `AGENTS.md` และโค้ดบน `main`
ก่อนเสมอ

## Executive summary

LinguaLens มี canonical therapist product เพียงชุดเดียว:

- Next.js frontend: `apps/lingualens-app/`
- FastAPI workflow and clinical-policy API: `apps/api/`
- Supabase: Auth/PostgreSQL/private Storage target
- Scientific/research code: `packages/` และ `src/`
- Analysis-only transcript boundary: `packages/analysis_contract/` และ
  `packages/cha/`

เว็บและ API deploy และตอบสนองได้ แต่ระบบยังเป็น research/education prototype
ไม่ใช่ diagnostic tool และยังไม่ผ่าน production security/legal/Thai clinical
validation gates

Owner feedback ล่าสุดคือ UI ปัจจุบันเข้าใจยาก ดูยาก และใช้งานยาก ดังนั้นงาน
product ถัดไปควรเริ่มจาก UI/UX audit ของ workflow จริงก่อนแก้หน้าจอ ห้ามเริ่มจาก
การ redesign ทั้งระบบ

## Verified deployed state

- Frontend: `https://lingualens-nu.vercel.app`
  - `/` redirects to `/today`
  - `/today` returned HTTP 200 after merge `4771ab0b`
- API: `https://lingualens-api-staging.onrender.com`
  - `/health` returned `{"status":"ok","mock_mode":false}`
- GitHub workflow `Test and Deploy CI/CD`, run `31907613812`: success on
  merge commit `4771ab0b`
- Local `main` was clean and aligned with `origin/main` at handoff creation

Reachability and smoke tests do not prove tenant isolation, production Auth,
private Storage policy, backup, legal, or clinical readiness

## Recently completed work

| PR | Merge commit | Result |
| --- | --- | --- |
| #4 | `af662c97` | Frontend runtime, CI audits, and security alignment |
| #5 | `e5de62fc` | Extraction Phase 1: deterministic CHAT and reviewed-transcript scientific contracts |
| #6 | `538c0944` | Status/source-of-truth cleanup; Redis/Celery no longer treated as an automatic requirement |
| #7 | `4771ab0b` | Extraction Phase 2: synchronous reviewed-transcript execution seam |

Extraction Phase 2 now builds a versioned request, SHA-256 input checksum,
analysis profile, provenance, and result envelope through
`execute_reviewed_transcript_analysis()`. The serialized envelope does not
contain transcript content

It intentionally adds none of the following:

- FastAPI or frontend route wiring
- result persistence or database migration
- Redis, Celery, or background worker
- new ML model or diagnostic output
- UI changes

## Last verification evidence

After rebasing Phase 2 on the status cleanup:

- Python 3.12 core suite: 770 passed, 3 deselected
- analysis contract targeted suite: 18 passed
- API migration smoke: passed through `0012_report_runtime_fields`, 24 tables
- therapist frontend: 412 tests passed
- frontend typecheck: passed
- frontend lint: passed
- Next.js 16.3.1 production build: passed
- repository consistency and secret scan: passed
- GitHub Linux matrix: Python 3.11, 3.12, and 3.13 passed

Known local environment issue: the macOS Python 3.13 environment can segfault in
the existing `numba/librosa` acoustic test. Python 3.12 and GitHub Linux Python
3.13 pass. No audio implementation was changed to hide this platform-specific
issue

## Current architecture boundary

```text
Browser / Next.js
  -> Supabase Auth session
  -> FastAPI /api/v1 for clinical reads, writes, authorization, consent,
     storage mediation, audit, and workflow transitions
       -> PostgreSQL / Supabase
       -> private Storage through server-mediated signed URLs

packages/analysis_contract + packages/cha
  -> deterministic scientific computation only
  -> no auth, CRUD, storage, queue, report finalization, or product API ownership
```

Do not add product endpoints to `src/therapist_backend/` or
`src/clinical_workflow/`. Do not recreate the removed Vite/Capacitor therapist
app

## Important deployment constraint

Render currently uses `apps/api` as its service root, while the scientific
packages live at repository root under `packages/`. Directly importing the new
analysis execution seam from a FastAPI route is therefore not deployment-safe
until the packaging/PYTHONPATH boundary is deliberately resolved and verified
on Render

Do not add a `sys.path` hack or duplicate the scientific code inside
`apps/api`. When product wiring is actually required, choose one small explicit
packaging/deployment change and verify API startup on Render before merge

## Recommended next work

### Priority 1: UI/UX audit

Inspect the maintained app and document the real therapist workflow before
editing components:

1. Sign in and walk through Today -> Cases -> consent -> Session -> transcript
   -> findings -> report
2. Record where the user cannot tell the current state, next action, or reason
   an action is blocked
3. Review navigation, terminology, hierarchy, empty/loading/error states,
   mobile behavior, accessibility, and duplicated information
4. Rank findings Critical/High/Medium/Low
5. Propose small independently testable UI phases
6. Stop for owner approval before implementing the UI plan

Preserve the clinical safety wording, consent gates, human review, abstention,
provenance, and backend authority. Do not turn this into a generic dashboard
redesign

### Priority 2: analysis product adapter, only when needed

After the deployment import boundary is resolved, the smallest next step is an
authorized, consent-gated, therapist-attestation-gated synchronous adapter. It
should not persist results or introduce a queue in its first iteration

Measure runtime before choosing asynchronous execution. If synchronous work is
too slow, use the existing database-backed job model and one worker before
considering a dedicated queue

### Deferred by owner: Supabase security evidence

The owner explicitly deferred this while UI usability is assessed. It remains
required before real clinical production use:

- real-claim two-organization RLS verification
- JWT/JWKS and custom-claim verification
- invitation and TOTP MFA lifecycle verification
- private Storage, signed URL expiry, completion, and retention verification
- secret rotation, backup/restore, observability, privacy/legal/vendor approval

Follow `docs/PHASE1_EXTERNAL_BLOCKERS.md` and
`docs/STAGING_TENANT_SAFETY_VERIFICATION.md` when this work resumes

## Do not do next

- Do not merge `codex/v1.7.0-speech-to-chat` wholesale
- Do not drop the recovery stash without explicit owner approval
- Do not add Redis/Celery because it appears in historical deployment docs
- Do not add realtime, GraphQL, Kubernetes, vector databases, LLM/RAG, or new ML
- Do not move ordinary CRUD or clinical workflow policy into the analysis layer
- Do not weaken non-diagnostic wording or therapist review gates for UI clarity

## Preserved recovery state

- Worktree: `.worktrees/v1.7.0-speech-to-chat`
- Branch: `codex/v1.7.0-speech-to-chat`
- Recovery stash: `stash@{0}: phase1-recovery-2026-08-15-before-main-cleanup`

The old speech-to-CHAT branch is large and contains over-scoped product/queue
work. Reuse only reviewed pieces through small extractions; do not merge the
branch as a unit

## Environment and secret handling

Expected frontend variable names include:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SITE_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Backend configuration uses the `LINGUALENS_*` names documented in
`apps/api/README.md` and the deployment runbooks. Never place values, bearer
tokens, service-role keys, database passwords, child identifiers, transcript
text, audio content, storage keys, or raw clinical URLs in commits, fixtures,
handoff notes, logs, or issue trackers

## Commands for the next engineer

```bash
# Confirm the starting point
git switch main
git pull --ff-only origin main
git status --short --branch

# Read current authority and boundaries
sed -n '1,260p' docs/PROJECT_SOURCE_OF_TRUTH.md
sed -n '1,240p' docs/CURRENT_HANDOFF.md

# Full local verification; Python 3.12 is recommended
LINGUALENS_PYTHON=/absolute/path/to/python3.12 bash scripts/check_project.sh

# Active API
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Active frontend
cd apps/lingualens-app
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

## Copy/paste continuation brief

```text
Read AGENTS.md, docs/PROJECT_SOURCE_OF_TRUTH.md, and docs/CURRENT_HANDOFF.md.
Start with a read-only UI/UX audit of the maintained Next.js therapist app.
Use the live workflow and current code, rank usability problems, propose the
smallest reviewable phases, and stop for approval before changing UI code.
Do not modify the deferred Supabase security configuration, scientific
analysis behavior, legacy research surfaces, or clinical safety gates.
```
