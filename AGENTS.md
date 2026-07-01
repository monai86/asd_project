# Agent Instructions

## Mandatory Source of Truth

- Read `docs/PROJECT_SOURCE_OF_TRUTH.md` before changing architecture,
  runtime paths, ML behavior, deployment, or project status.
- `apps/lingualens-app/` and `apps/api/` are the canonical therapist product.
- `src/therapist_backend/` and `src/clinical_workflow/` are legacy research
  compatibility surfaces. Do not add new product endpoints there.
- Do not recreate the removed `therapist-clinician-app/` Vite/Capacitor app.
- Never commit `.next/`, `dist/`, `.local/`, `node_modules/`, or
  `*.tsbuildinfo`.
- Historical plans and phase documents are context, not current runtime
  instructions.

## Package Managers
- Python uses `venv` + `pip`: `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`.
- Frontend apps use `npm` and committed `package-lock.json` files in each app directory.
- No root Node workspace is configured; run frontend commands inside the target app directory.

## Project Surfaces
- `src/`: Python ML/audio research code and legacy compatibility workflows.
- `apps/lingualens-app/`: the only active therapist frontend; Next.js + React + TypeScript.
- `apps/api/`: FastAPI backend for the lingualens therapist workflow.
- `shared/`: shared JavaScript models/services used by app surfaces.

## Clinical Safety Boundary
- This is a research/education prototype, not a diagnostic tool.
- Do not add text or flows that imply automated ASD diagnosis or Thai clinical validation.
- Keep real child names, surnames, direct identifiers, transcript text, audio bytes, and storage keys out of logs, fixtures, and committed data.
- Secure upload or pilot backend changes must preserve consent gates, signed URLs, role boundaries, audit logs, and private encrypted storage assumptions.

## File-Scoped Commands
| Task | Command |
|------|---------|
| Python test file | `pytest tests/test_name.py -q` |
| Python core tests | `pytest -m "not audio"` |
| Python audio tests | `pytest -m audio` |
| Therapist app test file | `cd apps/lingualens-app && npm test -- src/__tests__/file.test.tsx` |

## Build And Run
- Backend API: `cd apps/api && PYTHONPATH=. uvicorn app.main:app --reload --port 8000`.
- Therapist app: `cd apps/lingualens-app && npm run dev`.
- Full local verification: `bash scripts/check_project.sh`.

## Key Conventions
- Follow `README.md`, `DEVELOPER_SETUP.md`, `docs/DEVELOPMENT.md`, and `docs/SECURITY.md` for workflow and safety rules.
- Update `README.md` when setup, project structure, major dependencies, or user-facing behavior changes.
- Update `CHANGELOG.md` only for real system behavior changes; docs-only edits do not require a version bump.
- Keep Python reference datasets and generated reports auditable; do not silently rewrite raw TalkBank/CHILDES source files.
- Keep frontend changes scoped to the relevant app unless shared behavior in `shared/` is intentionally changed.

## Commit Attribution
AI commits MUST include:
```
Co-Authored-By: (the agent model's name and attribution byline)
```
