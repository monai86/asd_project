# Development Workflow

Read these files before changing the project:

1. `AGENTS.md`
2. `docs/PROJECT_SOURCE_OF_TRUTH.md`
3. `README.md`
4. the relevant component documentation

## Branch and workspace discipline

- `main` is the integration branch.
- Use a feature branch for multi-session or high-risk work.
- Before editing, run `git status --short` and confirm the active branch.
- Worktrees and subagent branches are temporary. Merge verified work into
  `main`, then delete obsolete local branches/worktrees.
- Never use generated files as the source of truth.

## Canonical paths

- Product frontend: `apps/therapist-app-v2`
- Product API: `apps/api`
- Research ML/audio: `packages`, `src`, `scripts`
- Legacy compatibility only: `src/therapist_backend`,
  `src/clinical_workflow`
- Retained non-current demo surfaces: `public-screening`,
  `presentation-dashboard`

Changing these boundaries requires an ADR and updates to
`docs/PROJECT_SOURCE_OF_TRUTH.md`, `README.md`, and `AGENTS.md`.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r apps/api/requirements.txt
```

Frontend dependencies are installed independently:

```bash
cd apps/therapist-app-v2 && npm ci
```

## Run

```bash
# Terminal 1
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Terminal 2
cd apps/therapist-app-v2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

## Verification

Use the maintained full-project check:

```bash
bash scripts/check_project.sh
```

Targeted checks:

```bash
PYTHONPATH=apps/api:src pytest tests/test_name.py -q
cd apps/api && PYTHONPATH=. pytest tests/test_workflow.py -q
cd apps/therapist-app-v2 && npm test
cd apps/therapist-app-v2 && npm run typecheck && npm run build
```

## Generated and local-only files

Do not commit:

- `.next/`
- `dist/`
- `.local/`
- `node_modules/`
- `*.tsbuildinfo`
- caches, logs, uploaded media, credentials, or private corpus mirrors

Runtime JSON repositories must use anonymized demo records only.

## Documentation and versioning

- Update `README.md` when entry points, setup, architecture, or behavior changes.
- Update `PROJECT_STATUS.md` for maintained status changes.
- Update `CHANGELOG.md` for behavior, dependency, deployment, or meaningful
  maintenance changes.
- Component versions such as ML `v0.9.x` are not the overall project version.
- Use semantic project versions (`v1.6.x`) and Git tags for releases.
- Historical phase/spec/plan documents remain immutable context unless a
  factual correction is required.

## Commit format

Use Conventional Commits:

```text
type(scope): imperative summary
```

AI-authored commits include the required `Co-Authored-By` footer from
`AGENTS.md`.

## Clinical and privacy constraints

- Use anonymized case codes only.
- Do not log transcript/audio content, identifiers, secrets, or storage keys.
- Preserve consent, role, audit, attestation, and report-finalization gates.
- Software verification and Gate 1 results are not clinical validation.
- Thai or mixed-language evidence must fail closed when unsupported.
