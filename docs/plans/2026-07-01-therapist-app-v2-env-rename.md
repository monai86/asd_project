# THERAPIST_APP_V2 Env Rename Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce `LINGUALENS_*` environment variables as the new canonical runtime contract while keeping `THERAPIST_APP_V2_*` fully supported during a staged migration.

**Architecture:** The migration should be additive first. `apps/api` reads `LINGUALENS_*` first and falls back to `THERAPIST_APP_V2_*`, while tests and docs prove that both names work. Only after the compatibility window and deployment rollout should the old prefix become deprecated and then removable.

**Tech Stack:** FastAPI, Python, pytest, Next.js, Playwright, shell scripts, Markdown runbooks

---

### Task 1: Add dual-prefix env resolution helpers in API config

**Files:**
- Modify: `apps/api/app/core/config.py`
- Test: `apps/api/tests/test_workflow.py`

**Step 1: Write the failing tests**

Add tests in `apps/api/tests/test_workflow.py` that verify:

```python
def test_settings_prefers_lingualens_repository_mode(monkeypatch):
    monkeypatch.setenv("LINGUALENS_REPOSITORY_MODE", "sql")
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    from app.core.config import Settings
    assert Settings.from_env().repository_mode == "sql"


def test_settings_falls_back_to_therapist_prefix(monkeypatch):
    monkeypatch.delenv("LINGUALENS_REPOSITORY_MODE", raising=False)
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    from app.core.config import Settings
    assert Settings.from_env().repository_mode == "memory"
```

Repeat the same pattern for one auth variable and one debug/operational variable:
- `LINGUALENS_AUTH_MODE`
- `LINGUALENS_DEBUG_FEATURE_OVERRIDE`

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py -k "lingualens_repository_mode or lingualens_auth_mode or lingualens_debug_feature_override" -q
```

Expected: FAIL because `Settings.from_env()` does not yet read `LINGUALENS_*`.

**Step 3: Write minimal implementation**

In `apps/api/app/core/config.py`:
- Add helper functions near the top of the file:

```python
def env_name_pairs() -> dict[str, tuple[str, str]]:
    return {
        "mock_mode": ("LINGUALENS_MOCK_MODE", "THERAPIST_APP_V2_MOCK_MODE"),
        "auth_mode": ("LINGUALENS_AUTH_MODE", "THERAPIST_APP_V2_AUTH_MODE"),
        "repository_mode": ("LINGUALENS_REPOSITORY_MODE", "THERAPIST_APP_V2_REPOSITORY_MODE"),
    }


def getenv_compat(new_name: str, legacy_name: str, default: str = "") -> str:
    if new_name in os.environ:
        return os.environ[new_name]
    if legacy_name in os.environ:
        return os.environ[legacy_name]
    return default
```

- Expand this pattern to every `THERAPIST_APP_V2_*` config read in `Settings.from_env()`
- Keep current behavior unchanged when only legacy variables are present
- Do not remove the existing defaults

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py -k "lingualens_repository_mode or lingualens_auth_mode or lingualens_debug_feature_override" -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add apps/api/app/core/config.py apps/api/tests/test_workflow.py
git commit -m "feat: add lingualens env compatibility layer"
```

### Task 2: Cover the full compatibility matrix for critical runtime variables

**Files:**
- Modify: `apps/api/tests/test_workflow.py`
- Modify: `apps/api/tests/test_supabase_auth_scaffold.py`
- Modify: `apps/api/tests/test_cors_security.py`

**Step 1: Write the failing tests**

Add tests for these critical variables:
- `LINGUALENS_MOCK_MODE`
- `LINGUALENS_AUTH_MODE`
- `LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE`
- `LINGUALENS_SUPABASE_JWT_ISSUER`
- `LINGUALENS_REPOSITORY_MODE`
- `LINGUALENS_DATABASE_URL`
- `LINGUALENS_STORAGE_MODE`
- `LINGUALENS_CORS_ALLOWED_ORIGINS`

Test cases:
- new prefix only
- legacy prefix only
- both set, new prefix wins
- production validation still fails closed for unsafe values

**Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py apps/api/tests/test_supabase_auth_scaffold.py apps/api/tests/test_cors_security.py -q
```

Expected: FAIL until all compatibility reads are wired and validated.

**Step 3: Write minimal implementation**

In `apps/api/app/core/config.py`:
- Replace every direct `os.getenv("THERAPIST_APP_V2_...")` call with the compatibility helper
- Keep `REDIS_URL` unchanged unless there is a separate rename decision
- Keep `DEFAULT_DATABASE_URL` value unchanged for now

**Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py apps/api/tests/test_supabase_auth_scaffold.py apps/api/tests/test_cors_security.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add apps/api/app/core/config.py apps/api/tests/test_workflow.py apps/api/tests/test_supabase_auth_scaffold.py apps/api/tests/test_cors_security.py
git commit -m "test: cover lingualens env compatibility"
```

### Task 3: Add explicit deprecation warnings for legacy prefix usage

**Files:**
- Modify: `apps/api/app/core/config.py`
- Test: `apps/api/tests/test_workflow.py`

**Step 1: Write the failing test**

Add a test that captures warnings:

```python
def test_legacy_therapist_env_emits_deprecation_warning(monkeypatch):
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    with pytest.warns(DeprecationWarning, match="THERAPIST_APP_V2_REPOSITORY_MODE"):
        Settings.from_env()
```

Also add one test that confirms no warning is emitted when only `LINGUALENS_*` is used.

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py -k "deprecation_warning" -q
```

Expected: FAIL because no warnings are emitted yet.

**Step 3: Write minimal implementation**

In `apps/api/app/core/config.py`:
- Use `warnings.warn(..., DeprecationWarning, stacklevel=2)` inside the compatibility helper when:
  - legacy variable is present
  - new variable is absent
- Warn once per process using `warnings.simplefilter` behavior or a module-level cache
- Make warning text concrete:

```python
"THERAPIST_APP_V2_REPOSITORY_MODE is deprecated; use LINGUALENS_REPOSITORY_MODE instead."
```

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py -k "deprecation_warning" -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add apps/api/app/core/config.py apps/api/tests/test_workflow.py
git commit -m "feat: warn on legacy therapist env usage"
```

### Task 4: Migrate maintained docs and scripts to the new prefix

**Files:**
- Modify: `apps/api/README.md`
- Modify: `DEVELOPER_SETUP.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/PRODUCTION_DEPLOYMENT.md`
- Modify: `docs/SUPABASE_AUTH_CONTRACT.md`
- Modify: `docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md`
- Modify: `docs/STAGING_EXECUTION_RUNBOOK.md`
- Modify: `docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md`
- Modify: `docs/ONE_DAY_PILOT_RUNBOOK.md`
- Modify: `scripts/create_supabase_runtime_env_snippets.sh`
- Modify: `apps/lingualens-app/playwright.config.ts`
- Test: `apps/api/tests/test_workflow.py`

**Step 1: Write the failing tests**

Add or update tests that inspect generated env examples and script output so they expect `LINGUALENS_*` in maintained docs/examples. Preserve acceptance of legacy variables in runtime behavior tests.

Minimum concrete test:

```python
def test_env_example_uses_lingualens_prefix():
    env_example = Path("apps/api/.env.example").read_text()
    assert "LINGUALENS_REPOSITORY_MODE=json" in env_example
```

If `.env.example` does not exist, create it in Task 4 as part of the maintained contract.

**Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py -q
```

Expected: FAIL until examples/docs/scripts are updated.

**Step 3: Write minimal implementation**

- Change maintained documentation to present `LINGUALENS_*` as canonical
- Add a short note in each key document:
  - "`THERAPIST_APP_V2_*` remains supported temporarily for backward compatibility"
- Update `scripts/create_supabase_runtime_env_snippets.sh` to emit `LINGUALENS_*`
- Update `apps/lingualens-app/playwright.config.ts` to use the new prefix in local test startup
- If needed, add `apps/api/.env.example` as the single maintained env contract example

Do not rewrite:
- `docs/release_artifacts/*`
- `docs/THERAPIST_APP_V2_*`
- ADR history files

**Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_workflow.py -q
cd apps/lingualens-app && npm test -- --runInBand
```

Expected: PASS

**Step 5: Commit**

```bash
git add apps/api/README.md DEVELOPER_SETUP.md docs/DEPLOYMENT.md docs/PRODUCTION_DEPLOYMENT.md docs/SUPABASE_AUTH_CONTRACT.md docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md docs/STAGING_EXECUTION_RUNBOOK.md docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md docs/ONE_DAY_PILOT_RUNBOOK.md scripts/create_supabase_runtime_env_snippets.sh apps/lingualens-app/playwright.config.ts apps/api/tests/test_workflow.py
git commit -m "docs: make lingualens env prefix canonical"
```

### Task 5: Rename logger and package metadata after compatibility layer is stable

**Files:**
- Modify: `apps/api/app/core/logging.py`
- Modify: `apps/api/tests/test_logging.py`
- Modify: `apps/lingualens-app/package.json`
- Modify: `apps/lingualens-app/package-lock.json`

**Step 1: Write the failing tests**

Update logging tests to expect `lingualens.request`:

```python
def test_request_logs_use_lingualens_logger(caplog):
    caplog.set_level(logging.INFO, logger="lingualens.request")
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_logging.py -q
```

Expected: FAIL because the logger name is still `therapist_app_v2.request`.

**Step 3: Write minimal implementation**

- Rename logger namespace to `lingualens.request`
- Update tests accordingly
- Rename package metadata from `therapist-app-v2` to `lingualens-app`
- Regenerate `package-lock.json` from `apps/lingualens-app/package.json`

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests/test_logging.py -q
cd apps/lingualens-app && npm install --package-lock-only
```

Expected: PASS and lockfile metadata updated

**Step 5: Commit**

```bash
git add apps/api/app/core/logging.py apps/api/tests/test_logging.py apps/lingualens-app/package.json apps/lingualens-app/package-lock.json
git commit -m "chore: rename lingualens package and logger metadata"
```

### Task 6: Full verification and deprecation follow-up

**Files:**
- Modify: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Modify: `docs/THERAPIST_APP_V2_RENAME_AUDIT.md`
- Modify: `CHANGELOG.md` if behavior changed

**Step 1: Write the failing verification checklist**

Create a short checklist in `docs/THERAPIST_APP_V2_RENAME_AUDIT.md` for:
- local legacy env smoke
- local new env smoke
- docs updated
- deploy scripts updated
- warnings observed for legacy-only env usage

**Step 2: Run verification commands**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests -q
cd apps/lingualens-app && npm test
cd /Users/porschecaa/lingualens && bash scripts/check_project.sh
```

Expected: PASS, or any existing unrelated failures are documented explicitly.

**Step 3: Write minimal implementation**

- Update `docs/PROJECT_SOURCE_OF_TRUTH.md` only after compatibility support exists and maintained docs have switched prefixes
- Document the deprecation window:
  - `LINGUALENS_*` is canonical as of this change
  - `THERAPIST_APP_V2_*` remains supported until a future removal milestone
- Add exact removal prerequisites to the audit doc:
  - all maintained docs switched
  - staging/prod env updated
  - no legacy warnings during rollout window

**Step 4: Re-run verification**

Run:

```bash
cd /Users/porschecaa/lingualens
PYTHONPATH=apps/api:src pytest apps/api/tests -q
cd apps/lingualens-app && npm run build
cd /Users/porschecaa/lingualens && bash scripts/check_project.sh
```

Expected: PASS

**Step 5: Commit**

```bash
git add docs/PROJECT_SOURCE_OF_TRUTH.md docs/THERAPIST_APP_V2_RENAME_AUDIT.md CHANGELOG.md
git commit -m "docs: record lingualens env migration state"
```

## Non-goals

- Do not rewrite historical evidence under `docs/release_artifacts/`
- Do not rename ADR files or historical `docs/THERAPIST_APP_V2_*` filenames
- Do not change database names or SQL identifiers just to match the new env prefix
- Do not remove legacy env support in the same rollout that introduces `LINGUALENS_*`

## Rollout Notes

- Recommended compatibility window: at least one full staging cycle and one production deployment cycle
- During the compatibility window, deployment configs may contain both prefixes, but each logical setting should converge on the `LINGUALENS_*` value
- If both prefixes are present with different values, API behavior must follow `LINGUALENS_*` and emit a warning only if the legacy value is the only one being consumed

## Suggested commit order

1. `feat: add lingualens env compatibility layer`
2. `test: cover lingualens env compatibility`
3. `feat: warn on legacy therapist env usage`
4. `docs: make lingualens env prefix canonical`
5. `chore: rename lingualens package and logger metadata`
6. `docs: record lingualens env migration state`
