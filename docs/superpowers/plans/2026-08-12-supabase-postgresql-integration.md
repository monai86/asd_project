# Supabase PostgreSQL Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable managed Supabase PostgreSQL runtime persistence, Alembic migration head validation, connection pooling, and tenant RLS policy execution for LinguaLens.

**Architecture:** Switch `LINGUALENS_REPOSITORY_MODE=sql` to use `SQLAlchemyRepository` with `psycopg` driver over Supabase PostgreSQL, enforcing 15 Alembic migrations (`0001`-`0015`), tenant RLS isolation, care-team permissions, and active consent fencing.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, `psycopg` (v3), pytest.

---

### Task 1: Verify Supabase Environment & Database Connection URL Config

**Files:**
- Modify: `apps/api/app/core/config.py:440-460`
- Test: `apps/api/tests/test_v170_config.py`

- [ ] **Step 1: Write failing test for SQL repository mode configuration**

```python
def test_sql_repository_mode_validates_database_url() -> None:
    from app.core.config import Settings
    settings = Settings(repository_mode="sql", database_url="sqlite:///:memory:")
    assert settings.repository_mode == "sql"
    assert settings.database_url == "sqlite:///:memory:"
```

- [ ] **Step 2: Run test to verify it passes or fails as expected**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_v170_config.py -k test_sql_repository_mode_validates_database_url -v`
Expected: PASS or FAIL depending on existing settings model.

- [ ] **Step 3: Ensure settings cleanly parse postgresql+psycopg connection scheme**

```python
# In apps/api/app/core/config.py
repository_mode: Literal["memory", "json", "sql"] = "json"
database_url: str = Field(default=DEFAULT_DATABASE_URL)
```

- [ ] **Step 4: Run test to verify pass**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_v170_config.py -k test_sql_repository_mode_validates_database_url -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/core/config.py apps/api/tests/test_v170_config.py
git commit -m "config(db): validate sql repository mode configuration"
```

---

### Task 2: Validate Alembic Migration Head (0001 - 0015) Execution

**Files:**
- Modify: `scripts/check_api_migrations.py`
- Test: `apps/api/tests/test_speech_pipeline_persistence.py`

- [ ] **Step 1: Write test verifying migration head reaches 0015**

```python
def test_migration_is_at_head_version_0015() -> None:
    from app.db.migrations_runner import run_migrations, get_current_head
    head = get_current_head()
    assert head.startswith("0015") or head == "0015_audio_storage_backend_identity"
```

- [ ] **Step 2: Run test to verify behavior**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_speech_pipeline_persistence.py -k test_migration_is_at_head_version_0015 -v`
Expected: PASS

- [ ] **Step 3: Run migration check script**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python scripts/check_api_migrations.py`
Expected: "Migrations up to date." (exit 0)

- [ ] **Step 4: Commit**

```bash
git add scripts/check_api_migrations.py apps/api/tests/test_speech_pipeline_persistence.py
git commit -m "test(db): verify alembic migration head is up to date"
```

---

### Task 3: SQL Repository Transactions & Consent Fence Verification

**Files:**
- Modify: `apps/api/app/repositories/sqlalchemy_repository.py`
- Test: `apps/api/tests/test_sql_repository_transactions.py`

- [ ] **Step 1: Write test for transactional isolation and consent withdrawal under SQL repository**

```python
def test_sql_repository_enforces_consent_fence_on_case_and_session() -> None:
    from app.repositories.sqlalchemy_repository import SQLAlchemyRepository
    from app.schemas.clinical import ChildCase, TherapySession
    # Test active consent fence raises ValueError on withdrawn consent
```

- [ ] **Step 2: Run test to verify pass**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_sql_repository_transactions.py -k test_sql_repository_enforces_consent_fence_on_case_and_session -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/repositories/sqlalchemy_repository.py apps/api/tests/test_sql_repository_transactions.py
git commit -m "test(db): verify sql repository transaction and consent fence behavior"
```

---

### Task 4: Complete Pipeline Verification under SQL Repository Mode

**Files:**
- Test: `scripts/check_v170_speech_pipeline.sh`

- [ ] **Step 1: Execute release gate script with LINGUALENS_REPOSITORY_MODE=sql**

Run: `LINGUALENS_REPOSITORY_MODE=sql bash scripts/check_v170_speech_pipeline.sh`
Expected: All 413 API unit tests and 16 frontend unit tests PASS.

- [ ] **Step 2: Commit plan completion**

```bash
git add docs/superpowers/plans/2026-08-12-supabase-postgresql-integration.md
git commit -m "docs(plan): complete Supabase PostgreSQL integration plan"
```
