from functools import lru_cache
import os
from pathlib import Path
import warnings

from pydantic import BaseModel


DEFAULT_DATABASE_URL = "postgresql+psycopg://therapist:therapist@localhost/therapist_app_v2"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
PRODUCTION_STORAGE_MODES = {"private", "supabase_private"}
# Keep this list aligned with implemented queue adapters. Celery is not
# installed or implemented in this repository, so it must not pass production
# configuration validation.
PRODUCTION_JOB_QUEUE_MODES = {"redis"}
PRODUCTION_OBSERVABILITY_PROVIDERS = {"sentry", "cloudwatch", "otlp"}
PRODUCTION_SECRET_STORE_PROVIDERS = {
    "aws_secrets_manager",
    "azure_key_vault",
    "gcp_secret_manager",
    "doppler",
    "infisical",
    "vault",
}


def getenv_compat(new_name: str, legacy_name: str, default: str = "") -> str:
    if new_name in os.environ:
        return os.environ[new_name]
    if legacy_name in os.environ:
        warnings.warn(
            f"{legacy_name} is deprecated; use {new_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return os.environ[legacy_name]
    return default


class Settings(BaseModel):
    app_name: str = "lingualens API"
    api_prefix: str = "/api/v1"
    mock_mode: bool = True
    auth_mode: str = "mock"
    supabase_jwt_verification_mode: str = "hs256_shared_secret"
    supabase_jwt_secret: str = ""
    supabase_jwt_jwks_json: str = ""
    supabase_jwt_jwks_url: str = ""
    supabase_jwt_jwks_cache_ttl_seconds: int = 300
    supabase_jwt_issuer: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_require_mfa: bool = True
    supabase_require_invitation: bool = True
    debug_feature_override: bool = False
    max_audio_file_size_mb: int = 250
    repository_mode: str = "json"
    json_repository_path: str = ".local/lingualens-app-repository.json"
    database_url: str = DEFAULT_DATABASE_URL
    sql_create_schema: bool = True
    run_migrations_on_startup: bool = False
    job_queue_mode: str = "memory"
    redis_url: str = DEFAULT_REDIS_URL
    storage_mode: str = "local_private"
    local_storage_root: str = ".local/storage"
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    csrf_origin_guard_enabled: bool = True
    ai_report_drafting_enabled: bool = False
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    observability_enabled: bool = False
    observability_provider: str = "disabled"
    critical_alert_route: str = ""
    secret_store_provider: str = "local_env"
    credential_rotation_runbook: str = ""
    reference_artifact_dir: str = "artifacts/reference_evidence/current"
    ml_inference_timeout_seconds: float = 2.0

    @property
    def resolved_json_repository_path(self) -> Path:
        return Path(self.json_repository_path)

    @property
    def resolved_local_storage_root(self) -> Path:
        return Path(self.local_storage_root)

    @property
    def parsed_cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def validate_runtime_security(self) -> "Settings":
        origins = self.parsed_cors_allowed_origins
        if not self.mock_mode and (not origins or "*" in origins):
            raise ValueError(
                "CORS allowed origins must be explicit in production; wildcard or empty origins are not allowed."
            )
        if "*" in origins and self.csrf_origin_guard_enabled:
            raise ValueError("CORS allowed origins cannot include wildcard when origin guard is enabled.")
        if not self.mock_mode:
            if self.auth_mode != "supabase":
                raise ValueError("Production auth mode must be supabase.")
            if self.supabase_jwt_verification_mode not in {"hs256_shared_secret", "jwks_json", "jwks_url"}:
                raise ValueError("Production Supabase JWT verification mode is invalid.")
            if not self.supabase_jwt_issuer.strip():
                raise ValueError("Production Supabase JWT issuer must be configured.")
            if self.supabase_jwt_verification_mode == "hs256_shared_secret":
                if not self.supabase_jwt_secret.strip():
                    raise ValueError("Production Supabase JWT secret must be configured for HS256 verification.")
            elif self.supabase_jwt_verification_mode == "jwks_json":
                if not self.supabase_jwt_jwks_json.strip():
                    raise ValueError("Production Supabase JWKS JSON must be configured for asymmetric verification.")
            else:
                if not self.supabase_jwt_jwks_url.strip():
                    raise ValueError("Production Supabase JWKS URL must be configured for remote asymmetric verification.")
                if self.supabase_jwt_jwks_cache_ttl_seconds <= 0:
                    raise ValueError("Production Supabase JWKS cache TTL must be positive.")
            if not self.supabase_require_mfa:
                raise ValueError("Production Supabase auth must require MFA.")
            if not self.supabase_require_invitation:
                raise ValueError("Production Supabase auth must require invitation acceptance.")
            if self.repository_mode != "sql":
                raise ValueError("Production repository mode must be sql.")
            if self.database_url == DEFAULT_DATABASE_URL or "localhost" in self.database_url:
                raise ValueError("Production database URL must come from managed secrets and cannot use demo defaults.")
            if self.storage_mode not in PRODUCTION_STORAGE_MODES:
                raise ValueError("Production storage mode must use private managed storage.")
            if self.job_queue_mode not in PRODUCTION_JOB_QUEUE_MODES:
                raise ValueError("Production job queue mode must use a durable managed queue.")
            if self.redis_url == DEFAULT_REDIS_URL or "localhost" in self.redis_url:
                raise ValueError("Production Redis URL must come from managed secrets and cannot use demo defaults.")
            if not self.observability_enabled or self.observability_provider not in PRODUCTION_OBSERVABILITY_PROVIDERS:
                raise ValueError("Production observability provider must be configured.")
            if not self.critical_alert_route.strip():
                raise ValueError("Production critical alert route must be configured.")
            if self.secret_store_provider not in PRODUCTION_SECRET_STORE_PROVIDERS:
                raise ValueError("Production secrets must use a managed secret store provider.")
            if not self.credential_rotation_runbook.strip():
                raise ValueError("Production credential rotation runbook must be configured.")
            if self.sql_create_schema:
                raise ValueError("Production database schema creation must use Alembic migrations, not automatic create_all.")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mock_mode=getenv_compat("LINGUALENS_MOCK_MODE", "THERAPIST_APP_V2_MOCK_MODE", "true").lower() != "false",
            auth_mode=getenv_compat("LINGUALENS_AUTH_MODE", "THERAPIST_APP_V2_AUTH_MODE", "mock"),
            supabase_jwt_verification_mode=getenv_compat(
                "LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE",
                "THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE",
                "hs256_shared_secret",
            ),
            supabase_jwt_secret=getenv_compat("LINGUALENS_SUPABASE_JWT_SECRET", "THERAPIST_APP_V2_SUPABASE_JWT_SECRET", ""),
            supabase_jwt_jwks_json=getenv_compat(
                "LINGUALENS_SUPABASE_JWT_JWKS_JSON",
                "THERAPIST_APP_V2_SUPABASE_JWT_JWKS_JSON",
                "",
            ),
            supabase_jwt_jwks_url=getenv_compat(
                "LINGUALENS_SUPABASE_JWT_JWKS_URL",
                "THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL",
                "",
            ),
            supabase_jwt_jwks_cache_ttl_seconds=int(
                getenv_compat(
                    "LINGUALENS_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS",
                    "THERAPIST_APP_V2_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS",
                    "300",
                )
            ),
            supabase_jwt_issuer=getenv_compat("LINGUALENS_SUPABASE_JWT_ISSUER", "THERAPIST_APP_V2_SUPABASE_JWT_ISSUER", ""),
            supabase_jwt_audience=getenv_compat(
                "LINGUALENS_SUPABASE_JWT_AUDIENCE",
                "THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE",
                "authenticated",
            ),
            supabase_require_mfa=getenv_compat(
                "LINGUALENS_SUPABASE_REQUIRE_MFA",
                "THERAPIST_APP_V2_SUPABASE_REQUIRE_MFA",
                "true",
            ).lower()
            != "false",
            supabase_require_invitation=getenv_compat(
                "LINGUALENS_SUPABASE_REQUIRE_INVITATION",
                "THERAPIST_APP_V2_SUPABASE_REQUIRE_INVITATION",
                "true",
            ).lower()
            != "false",
            debug_feature_override=getenv_compat(
                "LINGUALENS_DEBUG_FEATURE_OVERRIDE",
                "THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE",
                "false",
            ).lower()
            == "true",
            repository_mode=getenv_compat("LINGUALENS_REPOSITORY_MODE", "THERAPIST_APP_V2_REPOSITORY_MODE", "json"),
            json_repository_path=getenv_compat(
                "LINGUALENS_JSON_REPOSITORY_PATH",
                "THERAPIST_APP_V2_JSON_REPOSITORY_PATH",
                ".local/lingualens-app-repository.json",
            ),
            database_url=getenv_compat("LINGUALENS_DATABASE_URL", "THERAPIST_APP_V2_DATABASE_URL", DEFAULT_DATABASE_URL),
            sql_create_schema=getenv_compat(
                "LINGUALENS_SQL_CREATE_SCHEMA",
                "THERAPIST_APP_V2_SQL_CREATE_SCHEMA",
                "true",
            ).lower()
            != "false",
            run_migrations_on_startup=getenv_compat(
                "LINGUALENS_RUN_MIGRATIONS_ON_STARTUP",
                "THERAPIST_APP_V2_RUN_MIGRATIONS_ON_STARTUP",
                "false",
            ).lower()
            == "true",
            job_queue_mode=getenv_compat("LINGUALENS_JOB_QUEUE_MODE", "THERAPIST_APP_V2_JOB_QUEUE_MODE", "memory"),
            redis_url=os.getenv("REDIS_URL", DEFAULT_REDIS_URL),
            storage_mode=getenv_compat("LINGUALENS_STORAGE_MODE", "THERAPIST_APP_V2_STORAGE_MODE", "local_private"),
            local_storage_root=getenv_compat(
                "LINGUALENS_LOCAL_STORAGE_ROOT",
                "THERAPIST_APP_V2_LOCAL_STORAGE_ROOT",
                ".local/storage",
            ),
            cors_allowed_origins=getenv_compat(
                "LINGUALENS_CORS_ALLOWED_ORIGINS",
                "THERAPIST_APP_V2_CORS_ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ),
            csrf_origin_guard_enabled=getenv_compat(
                "LINGUALENS_CSRF_ORIGIN_GUARD_ENABLED",
                "THERAPIST_APP_V2_CSRF_ORIGIN_GUARD_ENABLED",
                "true",
            ).lower()
            != "false",
            ai_report_drafting_enabled=getenv_compat(
                "LINGUALENS_AI_REPORT_DRAFTING_ENABLED",
                "THERAPIST_APP_V2_AI_REPORT_DRAFTING_ENABLED",
                "false",
            ).lower()
            == "true",
            rate_limit_enabled=getenv_compat(
                "LINGUALENS_RATE_LIMIT_ENABLED",
                "THERAPIST_APP_V2_RATE_LIMIT_ENABLED",
                "false",
            ).lower()
            == "true",
            rate_limit_requests=int(
                getenv_compat("LINGUALENS_RATE_LIMIT_REQUESTS", "THERAPIST_APP_V2_RATE_LIMIT_REQUESTS", "120")
            ),
            rate_limit_window_seconds=int(
                getenv_compat(
                    "LINGUALENS_RATE_LIMIT_WINDOW_SECONDS",
                    "THERAPIST_APP_V2_RATE_LIMIT_WINDOW_SECONDS",
                    "60",
                )
            ),
            observability_enabled=getenv_compat(
                "LINGUALENS_OBSERVABILITY_ENABLED",
                "THERAPIST_APP_V2_OBSERVABILITY_ENABLED",
                "false",
            ).lower()
            == "true",
            observability_provider=getenv_compat(
                "LINGUALENS_OBSERVABILITY_PROVIDER",
                "THERAPIST_APP_V2_OBSERVABILITY_PROVIDER",
                "disabled",
            ),
            critical_alert_route=getenv_compat(
                "LINGUALENS_CRITICAL_ALERT_ROUTE",
                "THERAPIST_APP_V2_CRITICAL_ALERT_ROUTE",
                "",
            ),
            secret_store_provider=getenv_compat(
                "LINGUALENS_SECRET_STORE_PROVIDER",
                "THERAPIST_APP_V2_SECRET_STORE_PROVIDER",
                "local_env",
            ),
            credential_rotation_runbook=getenv_compat(
                "LINGUALENS_CREDENTIAL_ROTATION_RUNBOOK",
                "THERAPIST_APP_V2_CREDENTIAL_ROTATION_RUNBOOK",
                "",
            ),
            reference_artifact_dir=getenv_compat(
                "LINGUALENS_REFERENCE_ARTIFACT_DIR",
                "THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR",
                "artifacts/reference_evidence/current",
            ),
            ml_inference_timeout_seconds=float(
                getenv_compat(
                    "LINGUALENS_ML_INFERENCE_TIMEOUT_SECONDS",
                    "THERAPIST_APP_V2_ML_INFERENCE_TIMEOUT_SECONDS",
                    "2.0",
                )
            ),
        ).validate_runtime_security()


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
