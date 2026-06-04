from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = (ROOT / "docs" / "sql" / "001_initial_clinical_schema.sql").read_text()
RLS_SQL = (ROOT / "docs" / "sql" / "002_indexes_rls.sql").read_text()


def test_child_cases_require_anonymized_code_shape() -> None:
    assert "anonymized_child_code text not null unique check" in SCHEMA_SQL
    assert "^[A-Za-z0-9_-]{3,64}$" in SCHEMA_SQL


def test_supabase_rls_has_owner_admin_boundary_without_audit_log_read_policy() -> None:
    assert "create or replace function public.current_app_role()" in RLS_SQL
    assert "alter table users enable row level security" in RLS_SQL
    assert "public.current_app_role() = 'admin'" in RLS_SQL
    assert "create policy owners_read_child_cases" in RLS_SQL
    assert "create policy owners_read_audit_logs" not in RLS_SQL
    assert "Audit logs are intentionally not exposed through direct client RLS" in RLS_SQL


def test_supabase_private_media_bucket_is_owner_scoped() -> None:
    assert "insert into storage.buckets" in RLS_SQL
    assert "'clinical-media'" in RLS_SQL
    assert "create policy clinical_media_owner_insert" in RLS_SQL
    assert "(storage.foldername(name))[1] = 'private'" in RLS_SQL
    assert "(storage.foldername(name))[2] = auth.uid()::text" in RLS_SQL
