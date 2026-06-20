# Agent Instructions

## Package Managers
- Python uses `venv` + `pip`: `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`.
- Frontend apps use `npm` and committed `package-lock.json` files in each app directory.
- No root Node workspace is configured; run frontend commands inside the target app directory.

## Project Surfaces
- `src/`: Python ML, audio pipeline, clinical workflow, and FastAPI pilot backend.
- `apps/therapist-app-v2/`: the only active therapist frontend; Next.js + React + TypeScript.
- `apps/api/`: FastAPI backend for the Therapist App v2 local workflow.
- `public-screening/`: Vite parent-facing educational screening app.
- `presentation-dashboard/`: React/Vite advisor presentation dashboard.
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
| Therapist app test file | `cd apps/therapist-app-v2 && npm test -- src/__tests__/file.test.tsx` |
| Public screening test file | `cd public-screening && npm test -- src/__tests__/file.test.js` |
| Presentation dashboard test file | `cd presentation-dashboard && npm test -- src/__tests__/file.test.ts` |
| Presentation dashboard lint | `cd presentation-dashboard && npm run lint -- src/App.tsx` |

## Build And Run
- Backend API: `cd apps/api && PYTHONPATH=. uvicorn app.main:app --reload --port 8000`.
- Therapist app: `cd apps/therapist-app-v2 && npm run dev`.
- Public screening app: `cd public-screening && npm run dev`.
- Presentation dashboard: `cd presentation-dashboard && npm run dev`.
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
