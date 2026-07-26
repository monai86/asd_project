from functools import lru_cache
import os
from pathlib import Path
import warnings

from pydantic import BaseModel


DEFAULT_DATABASE_URL = "postgresql+psycopg://therapist:therapist@localhost/therapist_app_v2"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
JSON_SAFE_INTEGER_MAX = 2**53 - 1
V170_SUPPORTED_AUDIO_FORMATS = frozenset({"wav", "mp3"})
PRODUCTION_STORAGE_MODES = {"private", "supabase_private"}
PRODUCTION_JOB_QUEUE_MODES = {"redis", "celery"}
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
    max_audio_file_size_mb: int = 100
    max_audio_duration_seconds: int = 900
    supported_audio_formats_csv: str = "wav,mp3"
    audio_normalization_sample_rate_hz: int = 16_000
    audio_normalization_channels: int = 1
    audio_normalization_format: str = "wav_pcm_s16le"
    audio_source_min_sample_rate_hz: int = 8_000
    audio_source_max_sample_rate_hz: int = 48_000
    audio_source_max_channels: int = 2
    audio_normalization_max_rational_factor: int = 512
    audio_normalization_max_filter_taps: int = 10_241
    audio_normalization_max_working_bytes: int = 8 * 1024 * 1024
    default_audio_asr_provider: str = "local_faster_whisper"
    asr_runtime_profile_path: str = "artifacts/v1.7.0/asr_runtime_profile.json"
    chat_subset_version: str = "lingualens-chat-v1.7.0"
    chat_parser_version: str = "lingualens-chat-parser-v1.7.0"
    chat_serializer_version: str = "lingualens-chat-serializer-v1.7.0"
    qa_rule_version: str = "speech-qa-v1.7.0"
    feature_schema_version: str = "descriptive-features-v1.7.0"
    tokenizer_profile_path: str = "artifacts/v1.7.0/tokenizer_profile.json"
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

    @property
    def parsed_supported_audio_formats(self) -> tuple[str, ...]:
        return tuple(
            value.strip().lower()
            for value in self.supported_audio_formats_csv.split(",")
            if value.strip()
        )

    def validate_v170_contract(self) -> "Settings":
        if self.max_audio_file_size_mb <= 0:
            raise ValueError("Maximum audio file size must be positive.")
        if self.max_audio_file_size_mb > JSON_SAFE_INTEGER_MAX // (1024 * 1024):
            raise ValueError("Maximum audio file size must serialize as a JSON safe integer.")
        if self.max_audio_duration_seconds <= 0:
            raise ValueError("Maximum audio duration must be positive.")
        if self.max_audio_duration_seconds > JSON_SAFE_INTEGER_MAX:
            raise ValueError("Maximum audio duration must serialize as a JSON safe integer.")

        raw_formats = self.supported_audio_formats_csv.split(",")
        formats = self.parsed_supported_audio_formats
        if (
            not formats
            or any(not item.strip() for item in raw_formats)
            or len(formats) != len(set(formats))
            or not set(formats).issubset(V170_SUPPORTED_AUDIO_FORMATS)
        ):
            raise ValueError(
                "v1.7.0 supported audio formats must be a nonempty, unique subset of wav and mp3."
            )

        if self.audio_normalization_sample_rate_hz <= 0:
            raise ValueError("Audio normalization sample rate must be positive.")
        if self.audio_normalization_sample_rate_hz > JSON_SAFE_INTEGER_MAX:
            raise ValueError("Audio normalization sample rate must serialize as a JSON safe integer.")
        if self.audio_normalization_channels != 1:
            raise ValueError("Audio normalization must use exactly one channel.")
        if self.audio_normalization_format != "wav_pcm_s16le":
            raise ValueError("Unsupported deterministic audio normalization format.")
        if (
            self.audio_source_min_sample_rate_hz < 8_000
            or self.audio_source_min_sample_rate_hz > self.audio_source_max_sample_rate_hz
        ):
            raise ValueError(
                "source sample rate lower bound must be between 8000 Hz and "
                "the configured upper bound."
            )
        if (
            self.audio_source_max_sample_rate_hz
            > 48_000
            or self.audio_source_max_sample_rate_hz
            < self.audio_source_min_sample_rate_hz
        ):
            raise ValueError(
                "source sample rate upper bound must be between the configured "
                "lower bound and 48000 Hz."
            )
        if not 1 <= self.audio_source_max_channels <= 2:
            raise ValueError("source channel limit must be between one and two.")
        if not 1 <= self.audio_normalization_max_rational_factor <= 512:
            raise ValueError(
                "Audio normalization rational factor limit must be between 1 and 512."
            )
        if not 1 <= self.audio_normalization_max_filter_taps <= 10_241:
            raise ValueError(
                "Audio normalization filter tap limit must be between 1 and 10241."
            )
        if not 1 <= self.audio_normalization_max_working_bytes <= 8 * 1024 * 1024:
            raise ValueError(
                "Audio normalization working byte limit must be between 1 and 8388608."
            )
        if not self.default_audio_asr_provider.strip():
            raise ValueError("Default audio ASR provider must be configured.")

        required_identifiers = (
            ("CHAT subset version", self.chat_subset_version),
            ("CHAT parser version", self.chat_parser_version),
            ("CHAT serializer version", self.chat_serializer_version),
            ("QA rule version", self.qa_rule_version),
            ("feature schema version", self.feature_schema_version),
            ("tokenizer profile", self.tokenizer_profile_path),
        )
        for label, value in required_identifiers:
            if not value.strip():
                raise ValueError(f"{label} must be configured.")

        if (
            not self.mock_mode
            and self.default_audio_asr_provider == "local_faster_whisper"
            and not self.asr_runtime_profile_path.strip()
        ):
            raise ValueError("ASR runtime profile must be configured for local_faster_whisper.")
        return self

    def validate_runtime_security(self) -> "Settings":
        self.validate_v170_contract()
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
            max_audio_file_size_mb=int(
                getenv_compat(
                    "LINGUALENS_MAX_AUDIO_FILE_SIZE_MB",
                    "THERAPIST_APP_V2_MAX_AUDIO_FILE_SIZE_MB",
                    "100",
                )
            ),
            max_audio_duration_seconds=int(
                getenv_compat(
                    "LINGUALENS_MAX_AUDIO_DURATION_SECONDS",
                    "THERAPIST_APP_V2_MAX_AUDIO_DURATION_SECONDS",
                    "900",
                )
            ),
            supported_audio_formats_csv=getenv_compat(
                "LINGUALENS_SUPPORTED_AUDIO_FORMATS_CSV",
                "THERAPIST_APP_V2_SUPPORTED_AUDIO_FORMATS_CSV",
                "wav,mp3",
            ),
            audio_normalization_sample_rate_hz=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_NORMALIZATION_SAMPLE_RATE_HZ",
                    "THERAPIST_APP_V2_AUDIO_NORMALIZATION_SAMPLE_RATE_HZ",
                    "16000",
                )
            ),
            audio_normalization_channels=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_NORMALIZATION_CHANNELS",
                    "THERAPIST_APP_V2_AUDIO_NORMALIZATION_CHANNELS",
                    "1",
                )
            ),
            audio_normalization_format=getenv_compat(
                "LINGUALENS_AUDIO_NORMALIZATION_FORMAT",
                "THERAPIST_APP_V2_AUDIO_NORMALIZATION_FORMAT",
                "wav_pcm_s16le",
            ),
            audio_source_min_sample_rate_hz=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_SOURCE_MIN_SAMPLE_RATE_HZ",
                    "THERAPIST_APP_V2_AUDIO_SOURCE_MIN_SAMPLE_RATE_HZ",
                    "8000",
                )
            ),
            audio_source_max_sample_rate_hz=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_SOURCE_MAX_SAMPLE_RATE_HZ",
                    "THERAPIST_APP_V2_AUDIO_SOURCE_MAX_SAMPLE_RATE_HZ",
                    "48000",
                )
            ),
            audio_source_max_channels=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_SOURCE_MAX_CHANNELS",
                    "THERAPIST_APP_V2_AUDIO_SOURCE_MAX_CHANNELS",
                    "2",
                )
            ),
            audio_normalization_max_rational_factor=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_NORMALIZATION_MAX_RATIONAL_FACTOR",
                    "THERAPIST_APP_V2_AUDIO_NORMALIZATION_MAX_RATIONAL_FACTOR",
                    "512",
                )
            ),
            audio_normalization_max_filter_taps=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_NORMALIZATION_MAX_FILTER_TAPS",
                    "THERAPIST_APP_V2_AUDIO_NORMALIZATION_MAX_FILTER_TAPS",
                    "10241",
                )
            ),
            audio_normalization_max_working_bytes=int(
                getenv_compat(
                    "LINGUALENS_AUDIO_NORMALIZATION_MAX_WORKING_BYTES",
                    "THERAPIST_APP_V2_AUDIO_NORMALIZATION_MAX_WORKING_BYTES",
                    str(8 * 1024 * 1024),
                )
            ),
            default_audio_asr_provider=getenv_compat(
                "LINGUALENS_DEFAULT_AUDIO_ASR_PROVIDER",
                "THERAPIST_APP_V2_DEFAULT_AUDIO_ASR_PROVIDER",
                "local_faster_whisper",
            ),
            asr_runtime_profile_path=getenv_compat(
                "LINGUALENS_ASR_RUNTIME_PROFILE_PATH",
                "THERAPIST_APP_V2_ASR_RUNTIME_PROFILE_PATH",
                "artifacts/v1.7.0/asr_runtime_profile.json",
            ),
            chat_subset_version=getenv_compat(
                "LINGUALENS_CHAT_SUBSET_VERSION",
                "THERAPIST_APP_V2_CHAT_SUBSET_VERSION",
                "lingualens-chat-v1.7.0",
            ),
            chat_parser_version=getenv_compat(
                "LINGUALENS_CHAT_PARSER_VERSION",
                "THERAPIST_APP_V2_CHAT_PARSER_VERSION",
                "lingualens-chat-parser-v1.7.0",
            ),
            chat_serializer_version=getenv_compat(
                "LINGUALENS_CHAT_SERIALIZER_VERSION",
                "THERAPIST_APP_V2_CHAT_SERIALIZER_VERSION",
                "lingualens-chat-serializer-v1.7.0",
            ),
            qa_rule_version=getenv_compat(
                "LINGUALENS_QA_RULE_VERSION",
                "THERAPIST_APP_V2_QA_RULE_VERSION",
                "speech-qa-v1.7.0",
            ),
            feature_schema_version=getenv_compat(
                "LINGUALENS_FEATURE_SCHEMA_VERSION",
                "THERAPIST_APP_V2_FEATURE_SCHEMA_VERSION",
                "descriptive-features-v1.7.0",
            ),
            tokenizer_profile_path=getenv_compat(
                "LINGUALENS_TOKENIZER_PROFILE_PATH",
                "THERAPIST_APP_V2_TOKENIZER_PROFILE_PATH",
                "artifacts/v1.7.0/tokenizer_profile.json",
            ),
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
