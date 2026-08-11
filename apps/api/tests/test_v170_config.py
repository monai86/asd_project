import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.security import get_current_user
from app.main import app


def test_v170_audio_contract_defaults() -> None:
    settings = Settings()

    assert settings.max_audio_file_size_mb == 100
    assert settings.max_audio_duration_seconds == 900
    assert settings.audio_normalization_sample_rate_hz == 16_000
    assert settings.audio_normalization_channels == 1
    assert settings.audio_normalization_format == "wav_pcm_s16le"
    assert settings.audio_source_min_sample_rate_hz == 8_000
    assert settings.audio_source_max_sample_rate_hz == 48_000
    assert settings.audio_source_max_channels == 2
    assert settings.audio_normalization_max_rational_factor == 512
    assert settings.audio_normalization_max_filter_taps == 10_241
    assert settings.audio_normalization_max_working_bytes == 8 * 1024 * 1024
    assert settings.default_audio_asr_provider == "local_faster_whisper"
    assert settings.parsed_supported_audio_formats == ("wav", "mp3")


def test_fastapi_startup_initializes_decoder_registry_and_health_state() -> None:
    from app.services.audio_media_service import get_decoder_capability_registry

    get_decoder_capability_registry.cache_clear()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    audio_decoder = response.json()["audio_decoder"]
    assert audio_decoder["processing_state"] == "available"
    assert audio_decoder["verified_formats"] == ["wav", "mp3"]
    assert audio_decoder["unavailable_reason"] is None
    assert get_decoder_capability_registry.cache_info().currsize == 1


def test_decoder_registry_startup_failure_is_fail_closed_for_health_and_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.audio_media_service as audio_media

    def fail_registry_build(*args, **kwargs):
        raise RuntimeError("synthetic decoder startup failure")

    monkeypatch.setattr(
        audio_media,
        "_fixture_matches",
        fail_registry_build,
    )
    audio_media.get_decoder_capability_registry.cache_clear()
    try:
        with TestClient(app) as client:
            health = client.get("/health")
            capabilities = client.get("/api/v1/audio/capabilities")
    finally:
        audio_media.get_decoder_capability_registry.cache_clear()

    assert health.status_code == 200
    assert health.json()["status"] == "degraded"
    assert (
        health.json()["audio_decoder"]["unavailable_reason"]
        == "decoder_registry_initialization_failed"
    )
    assert capabilities.status_code == 200
    assert capabilities.json()["processing_state"] == "unavailable"
    assert capabilities.json()["supported_formats"] == []
    assert (
        capabilities.json()["unavailable_reason"]
        == "decoder_registry_initialization_failed"
    )


def test_supported_audio_formats_are_normalized() -> None:
    settings = Settings(supported_audio_formats_csv=" WAV, Mp3 ")

    assert settings.parsed_supported_audio_formats == ("wav", "mp3")


@pytest.mark.parametrize(
    "formats_csv",
    [
        "m4a",
        "webm",
        "wav,flac",
        ".wav",
        "wav,,mp3",
        "wav,",
        "wav,wav",
        "mp 3",
    ],
)
def test_v170_format_evidence_rejects_unverified_or_malformed_formats(
    formats_csv: str,
) -> None:
    settings = Settings(supported_audio_formats_csv=formats_csv)

    with pytest.raises(ValueError, match="supported audio format"):
        settings.validate_runtime_security()


def test_v170_settings_load_from_lingualens_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    overrides = {
        "LINGUALENS_MAX_AUDIO_FILE_SIZE_MB": "42",
        "LINGUALENS_MAX_AUDIO_DURATION_SECONDS": "321",
        "LINGUALENS_SUPPORTED_AUDIO_FORMATS_CSV": "mp3, WAV",
        "LINGUALENS_AUDIO_NORMALIZATION_SAMPLE_RATE_HZ": "8000",
        "LINGUALENS_AUDIO_NORMALIZATION_CHANNELS": "1",
        "LINGUALENS_AUDIO_NORMALIZATION_FORMAT": "wav_pcm_s16le",
        "LINGUALENS_AUDIO_SOURCE_MIN_SAMPLE_RATE_HZ": "9000",
        "LINGUALENS_AUDIO_SOURCE_MAX_SAMPLE_RATE_HZ": "44100",
        "LINGUALENS_AUDIO_SOURCE_MAX_CHANNELS": "1",
        "LINGUALENS_AUDIO_NORMALIZATION_MAX_RATIONAL_FACTOR": "500",
        "LINGUALENS_AUDIO_NORMALIZATION_MAX_FILTER_TAPS": "10001",
        "LINGUALENS_AUDIO_NORMALIZATION_MAX_WORKING_BYTES": "4194304",
        "LINGUALENS_DEFAULT_AUDIO_ASR_PROVIDER": "fixture_asr",
        "LINGUALENS_ASR_RUNTIME_PROFILE_PATH": "artifacts/test/runtime.json",
        "LINGUALENS_CHAT_SUBSET_VERSION": "subset-test",
        "LINGUALENS_CHAT_PARSER_VERSION": "parser-test",
        "LINGUALENS_CHAT_SERIALIZER_VERSION": "serializer-test",
        "LINGUALENS_QA_RULE_VERSION": "qa-test",
        "LINGUALENS_FEATURE_SCHEMA_VERSION": "features-test",
        "LINGUALENS_TOKENIZER_PROFILE_PATH": "artifacts/test/tokenizer.json",
    }
    for name, value in overrides.items():
        monkeypatch.setenv(name, value)

    settings = Settings.from_env()

    assert settings.max_audio_file_size_mb == 42
    assert settings.max_audio_duration_seconds == 321
    assert settings.parsed_supported_audio_formats == ("mp3", "wav")
    assert settings.audio_normalization_sample_rate_hz == 8000
    assert settings.audio_normalization_channels == 1
    assert settings.audio_source_min_sample_rate_hz == 9_000
    assert settings.audio_source_max_sample_rate_hz == 44_100
    assert settings.audio_source_max_channels == 1
    assert settings.audio_normalization_max_rational_factor == 500
    assert settings.audio_normalization_max_filter_taps == 10_001
    assert settings.audio_normalization_max_working_bytes == 4 * 1024 * 1024
    assert settings.default_audio_asr_provider == "fixture_asr"
    assert settings.asr_runtime_profile_path == "artifacts/test/runtime.json"
    assert settings.chat_subset_version == "subset-test"
    assert settings.chat_parser_version == "parser-test"
    assert settings.chat_serializer_version == "serializer-test"
    assert settings.qa_rule_version == "qa-test"
    assert settings.feature_schema_version == "features-test"
    assert settings.tokenizer_profile_path == "artifacts/test/tokenizer.json"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("max_audio_file_size_mb", 0, "file size"),
        ("max_audio_duration_seconds", -1, "duration"),
        ("audio_normalization_sample_rate_hz", 0, "sample rate"),
        ("audio_normalization_channels", 2, "exactly one channel"),
        ("audio_normalization_format", "flac", "normalization format"),
        ("audio_source_min_sample_rate_hz", 7_999, "source sample rate"),
        ("audio_source_max_sample_rate_hz", 48_001, "source sample rate"),
        ("audio_source_max_channels", 3, "source channel"),
        (
            "audio_normalization_max_rational_factor",
            513,
            "rational factor",
        ),
        ("audio_normalization_max_filter_taps", 10_242, "filter tap"),
        (
            "audio_normalization_max_working_bytes",
            8 * 1024 * 1024 + 1,
            "working byte",
        ),
        ("supported_audio_formats_csv", " , ", "supported audio format"),
        ("default_audio_asr_provider", " ", "ASR provider"),
        ("chat_subset_version", "", "CHAT subset version"),
        ("chat_parser_version", "", "CHAT parser version"),
        ("chat_serializer_version", "", "CHAT serializer version"),
        ("qa_rule_version", "", "QA rule version"),
        ("feature_schema_version", "", "feature schema version"),
        ("tokenizer_profile_path", "", "tokenizer profile"),
    ],
)
def test_v170_contract_validation_rejects_invalid_values(
    field: str,
    value: object,
    message: str,
) -> None:
    settings = Settings(**{field: value})

    with pytest.raises(ValueError, match=message):
        settings.validate_runtime_security()


def test_local_faster_whisper_requires_runtime_profile_outside_mock_mode() -> None:
    settings = Settings(
        mock_mode=False,
        default_audio_asr_provider="local_faster_whisper",
        asr_runtime_profile_path="",
    )

    with pytest.raises(ValueError, match="ASR runtime profile"):
        settings.validate_runtime_security()


def test_mock_only_configuration_can_omit_local_asr_runtime_profile() -> None:
    settings = Settings(mock_mode=True, asr_runtime_profile_path="")

    assert settings.validate_runtime_security() is settings


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_audio_file_size_mb", (2**53 - 1) // (1024 * 1024) + 1),
        ("max_audio_duration_seconds", 2**53),
        ("audio_normalization_sample_rate_hz", 2**53),
    ],
)
def test_capability_integers_must_serialize_safely_for_json_clients(
    field: str,
    value: int,
) -> None:
    settings = Settings(**{field: value})

    with pytest.raises(ValueError, match="JSON safe integer"):
        settings.validate_runtime_security()


def test_audio_capabilities_publish_exact_public_contract_without_auth() -> None:
    def fail_auth():
        raise AssertionError("Public capability endpoint must not resolve authentication")

    missing = object()
    previous_override = app.dependency_overrides.get(get_current_user, missing)
    app.dependency_overrides[get_current_user] = fail_auth
    try:
        response = TestClient(app).get("/api/v1/audio/capabilities")
    finally:
        if previous_override is missing:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_override

    assert response.status_code == 200
    assert response.json() == {
        "milestone": "v1.7.0-testbed",
        "max_size_bytes": 104_857_600,
        "max_duration_seconds": 900,
        "supported_formats": ["wav", "mp3"],
        "processing_state": "available",
        "unavailable_reason": None,
        "normalization": {
            "channels": 1,
            "sample_rate_hz": 16_000,
            "format": "wav_pcm_s16le",
            "source_min_sample_rate_hz": 8_000,
            "source_max_sample_rate_hz": 48_000,
            "source_max_channels": 2,
            "max_rational_factor": 512,
            "max_filter_taps": 10_241,
            "max_working_bytes": 8_388_608,
        },
        "browser_recording": {
            "state": "experimental_unavailable",
            "blocks_milestone": False,
        },
    }


def test_audio_capabilities_openapi_uses_allowlisted_concrete_schema() -> None:
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    response_schema = document["paths"]["/api/v1/audio/capabilities"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert response_schema == {
        "$ref": "#/components/schemas/AudioCapabilitiesResponse"
    }

    component = document["components"]["schemas"]["AudioCapabilitiesResponse"]
    assert set(component["properties"]) == {
        "milestone",
        "max_size_bytes",
        "max_duration_seconds",
        "supported_formats",
        "processing_state",
        "unavailable_reason",
        "normalization",
        "browser_recording",
    }
    assert "secret" not in str(component).lower()
    assert "supabase" not in str(component).lower()
    assert component["properties"]["milestone"]["const"] == "v1.7.0-testbed"
    assert component["properties"]["supported_formats"]["items"]["enum"] == [
        "wav",
        "mp3",
    ]

    normalization = document["components"]["schemas"][
        "AudioNormalizationCapabilities"
    ]
    assert normalization["properties"]["channels"]["const"] == 1
    assert normalization["properties"]["format"]["const"] == "wav_pcm_s16le"
    assert set(normalization["properties"]) == {
        "channels",
        "sample_rate_hz",
        "format",
        "source_min_sample_rate_hz",
        "source_max_sample_rate_hz",
        "source_max_channels",
        "max_rational_factor",
        "max_filter_taps",
        "max_working_bytes",
    }

    browser_recording = document["components"]["schemas"][
        "BrowserRecordingCapabilities"
    ]
    assert (
        browser_recording["properties"]["state"]["const"]
        == "experimental_unavailable"
    )
    assert browser_recording["properties"]["blocks_milestone"]["const"] is False


def test_audio_capabilities_follow_environment_overrides_without_secret_leakage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGUALENS_MAX_AUDIO_FILE_SIZE_MB", "12")
    monkeypatch.setenv("LINGUALENS_MAX_AUDIO_DURATION_SECONDS", "75")
    monkeypatch.setenv("LINGUALENS_SUPPORTED_AUDIO_FORMATS_CSV", "MP3")
    monkeypatch.setenv("LINGUALENS_AUDIO_NORMALIZATION_SAMPLE_RATE_HZ", "8000")
    monkeypatch.setenv("LINGUALENS_SUPABASE_JWT_SECRET", "must-not-leak")
    get_settings.cache_clear()
    try:
        response = TestClient(app).get("/api/v1/audio/capabilities")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["max_size_bytes"] == 12 * 1024 * 1024
    assert payload["max_duration_seconds"] == 75
    assert payload["supported_formats"] == ["mp3"]
    assert payload["normalization"]["sample_rate_hz"] == 8000
    assert "must-not-leak" not in response.text
    assert set(payload) == {
        "milestone",
        "max_size_bytes",
        "max_duration_seconds",
        "supported_formats",
        "processing_state",
        "unavailable_reason",
        "normalization",
        "browser_recording",
    }


def test_sql_repository_mode_validates_database_url() -> None:
    psycopg_url = "postgresql+psycopg://therapist:therapist@localhost:5432/therapist_app_v2"
    settings = Settings(repository_mode="sql", database_url=psycopg_url)
    assert settings.validate_runtime_security().database_url == psycopg_url

    postgres_url = "postgresql://therapist:therapist@localhost:5432/therapist_app_v2"
    settings_pg = Settings(repository_mode="sql", database_url=postgres_url)
    assert settings_pg.validate_runtime_security().database_url == postgres_url

    with pytest.raises(ValueError, match="Unsupported repository mode"):
        Settings(repository_mode="invalid_repo_mode").validate_runtime_security()

    with pytest.raises(ValueError, match="SQL repository mode requires"):
        Settings(repository_mode="sql", database_url="").validate_runtime_security()

    with pytest.raises(ValueError, match="SQL repository mode requires"):
        Settings(
            repository_mode="sql",
            database_url="mysql://user:pass@localhost/db",
        ).validate_runtime_security()

