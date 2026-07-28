from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import multiprocessing
from pathlib import Path
import struct

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.dependencies import get_repository
from app.core.config import Settings
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    AudioProcessRequest,
    ChildCaseCreate,
    TherapySessionCreate,
)
from app.services.storage_service import LocalPrivateStorageAdapter


def _write_sparse_pcm16_wav(
    path: Path,
    *,
    frame_count: int,
    sample_rate_hz: int = 16_000,
    channels: int = 1,
) -> None:
    data_size = frame_count * channels * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate_hz,
        sample_rate_hz * channels * 2,
        channels * 2,
        16,
        b"data",
        data_size,
    )
    with path.open("wb") as destination:
        destination.write(header)
        destination.truncate(len(header) + data_size)


def _repo_with_audio(
    storage_root: Path,
    *,
    source_path: Path,
    claimed_duration_seconds: float | None = None,
    claimed_size_bytes: int | None = None,
    claimed_sample_rate_hz: int | None = None,
    claimed_channels: int | None = None,
) -> tuple[MockRepository, AudioFileMetadata]:
    repo = MockRepository()
    case = repo.create_case(
        ChildCaseCreate(
            child_code="SYNTHETIC-AUDIO-001",
            age_months=48,
            language="Thai",
            consent_status="granted",
        ),
        actor_id="therapist-demo",
    )
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(
            session_date="2026-07-26",
            session_type="synthetic_testbed",
        ),
        actor_id="therapist-demo",
    )
    object_key = "audio/source.wav"
    destination = storage_root / object_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source_path.read_bytes())
    audio_file = AudioFileMetadata(
        audio_file_id="aud_synthetic_001",
        organization_id=session.organization_id,
        session_id=session.session_id,
        case_id=case.case_id,
        original_filename="client-claim.wav",
        content_type="audio/wav",
        size_bytes=(
            claimed_size_bytes
            if claimed_size_bytes is not None
            else source_path.stat().st_size
        ),
        storage_mode="local_private",
        storage_backend_identity_sha256=(
            LocalPrivateStorageAdapter(
                storage_root
            ).storage_backend_identity_sha256
        ),
        object_key=object_key,
        upload_status="uploaded",
        duration_seconds=claimed_duration_seconds,
        sample_rate_hz=claimed_sample_rate_hz,
        channels=claimed_channels,
    )
    repo.audio_files[audio_file.audio_file_id] = audio_file
    return repo, audio_file


def _wav_bytes(
    samples: np.ndarray,
    *,
    sample_rate_hz: int,
) -> bytes:
    destination = BytesIO()
    sf.write(
        destination,
        samples,
        sample_rate_hz,
        format="WAV",
        subtype="PCM_16",
    )
    return destination.getvalue()


def test_actual_905_second_media_rejects_client_claim_of_60_without_job(
    tmp_path: Path,
) -> None:
    from app.services.audio_media_service import (
        AudioIntakeError,
        verify_and_normalize_audio,
    )
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "905.wav"
    _write_sparse_pcm16_wav(source_path, frame_count=14_480_000)
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(
        storage_root,
        source_path=source_path,
        claimed_duration_seconds=60,
    )
    source_before = (storage_root / audio_file.object_key).read_bytes()

    with pytest.raises(AudioIntakeError) as captured:
        verify_and_normalize_audio(
            repo,
            audio_file.audio_file_id,
            storage_adapter=LocalPrivateStorageAdapter(storage_root),
            settings=Settings(),
        )

    assert captured.value.code == "audio_duration_limit_exceeded"
    assert captured.value.details["configured_limit"] == 900_000
    assert captured.value.details["actual_value"] == 905_000
    assert captured.value.details["unit"] == "milliseconds"
    assert captured.value.details["remediation"]
    assert repo.jobs == {}
    assert repo.normalized_audio_assets == {}
    assert (storage_root / audio_file.object_key).read_bytes() == source_before


def test_actual_object_over_100_mib_rejects_before_decode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.audio_media_service as media_service
    from app.services.audio_media_service import (
        AudioIntakeError,
        verify_and_normalize_audio,
    )
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "oversize.bin"
    with source_path.open("wb") as source:
        source.truncate(100 * 1024 * 1024 + 1)
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(
        storage_root,
        source_path=source_path,
        claimed_size_bytes=1,
    )

    def unexpected_decode(*args, **kwargs):
        raise AssertionError("decoder must not run for an oversized object")

    monkeypatch.setattr(media_service, "probe_audio", unexpected_decode)

    with pytest.raises(AudioIntakeError) as captured:
        verify_and_normalize_audio(
            repo,
            audio_file.audio_file_id,
            storage_adapter=LocalPrivateStorageAdapter(storage_root),
            settings=Settings(),
        )

    assert captured.value.code == "audio_size_limit_exceeded"
    assert captured.value.details["configured_limit"] == 100 * 1024 * 1024
    assert captured.value.details["actual_value"] == 100 * 1024 * 1024 + 1
    assert captured.value.details["unit"] == "bytes"
    assert repo.jobs == {}
    assert repo.normalized_audio_assets == {}


def test_decoded_exact_duration_limit_is_inclusive_and_one_ms_over_rejects(
    tmp_path: Path,
) -> None:
    from app.services.audio_media_service import (
        AudioIntakeError,
        enforce_audio_limits,
        probe_audio,
    )

    exact = tmp_path / "exact.wav"
    over = tmp_path / "over.wav"
    _write_sparse_pcm16_wav(exact, frame_count=14_400_000)
    _write_sparse_pcm16_wav(over, frame_count=14_400_016)

    with exact.open("rb") as source:
        exact_metadata = probe_audio(source)
    with over.open("rb") as source:
        over_metadata = probe_audio(source)

    assert exact_metadata.duration_ms == 900_000
    assert over_metadata.duration_ms == 900_001
    enforce_audio_limits(
        actual_size_bytes=exact.stat().st_size,
        decoded=exact_metadata,
        settings=Settings(),
    )
    with pytest.raises(AudioIntakeError) as captured:
        enforce_audio_limits(
            actual_size_bytes=over.stat().st_size,
            decoded=over_metadata,
            settings=Settings(),
        )
    assert captured.value.code == "audio_duration_limit_exceeded"


def test_runtime_format_subset_is_enforced_after_actual_decode() -> None:
    from app.services.audio_media_service import (
        AudioIntakeError,
        enforce_audio_limits,
        probe_audio,
    )

    root = Path(__file__).resolve().parents[3]
    mp3_path = root / "tests/fixtures/audio/v1.7.0/formats/verified_sample.mp3"
    with mp3_path.open("rb") as source:
        decoded = probe_audio(source)

    with pytest.raises(AudioIntakeError) as captured:
        enforce_audio_limits(
            actual_size_bytes=mp3_path.stat().st_size,
            decoded=decoded,
            settings=Settings(supported_audio_formats_csv="wav"),
        )

    assert captured.value.code == "audio_format_unavailable"
    assert captured.value.details["actual_value"] == "mp3"
    assert captured.value.details["supported_formats"] == ["wav"]


def test_submillisecond_frame_past_limit_is_not_hidden_by_duration_rounding() -> None:
    from app.services.audio_media_service import (
        AudioIntakeError,
        DecodedAudioMetadata,
        enforce_audio_limits,
    )

    sample_rate_hz = 44_100
    decoded = DecodedAudioMetadata(
        detected_format="wav",
        duration_ms=900_000,
        frame_count=900 * sample_rate_hz + 1,
        sample_rate_hz=sample_rate_hz,
        channels=1,
        decoder_name="soundfile",
        decoder_version="0.14.0",
        decoder_library_name="libsndfile",
        decoder_library_version="1.2.2",
    )

    with pytest.raises(AudioIntakeError) as captured:
        enforce_audio_limits(
            actual_size_bytes=1024,
            decoded=decoded,
            settings=Settings(),
        )

    assert captured.value.code == "audio_duration_limit_exceeded"
    assert captured.value.details["actual_value"] == 900_001


def test_verified_normalization_persists_complete_lineage_and_keeps_source(
    tmp_path: Path,
) -> None:
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.storage_service import LocalPrivateStorageAdapter

    samples = np.zeros((8_001, 2), dtype=np.float64)
    samples[0] = (0.75, 0.25)
    samples[-1] = (-0.75, -0.25)
    source_path = tmp_path / "stereo-8khz.wav"
    source_path.write_bytes(_wav_bytes(samples, sample_rate_hz=8_000))
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(
        storage_root,
        source_path=source_path,
        claimed_duration_seconds=777,
        claimed_sample_rate_hz=44_100,
        claimed_channels=1,
    )
    source_object = storage_root / audio_file.object_key
    source_before = source_object.read_bytes()
    source_checksum = sha256(source_before).hexdigest()

    normalized = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=LocalPrivateStorageAdapter(storage_root),
        settings=Settings(),
    )

    assert source_object.read_bytes() == source_before
    assert repo.audio_files[audio_file.audio_file_id].checksum_sha256 == source_checksum
    assert normalized.source_checksum_sha256 == source_checksum
    assert normalized.normalized_checksum_sha256 != source_checksum
    assert normalized.object_key != audio_file.object_key
    assert normalized.format == "wav_pcm_s16le"
    assert normalized.sample_rate_hz == 16_000
    assert normalized.channels == 1
    assert normalized.frame_count == 16_002
    assert normalized.verification_status == "verified"
    assert normalized.provenance.source_size_bytes == len(source_before)
    assert normalized.provenance.source_detected_format == "wav"
    assert normalized.provenance.source_duration_ms == 1_000
    assert normalized.provenance.source_frame_count == 8_001
    assert normalized.provenance.source_sample_rate_hz == 8_000
    assert normalized.provenance.source_channels == 2
    assert repo.audio_files[audio_file.audio_file_id].duration_seconds == (
        8_001 / 8_000
    )
    assert repo.audio_files[audio_file.audio_file_id].sample_rate_hz == 8_000
    assert repo.audio_files[audio_file.audio_file_id].channels == 2
    normalized_path = storage_root / normalized.object_key
    assert normalized.provenance.normalized_size_bytes == normalized_path.stat().st_size
    assert normalized.provenance.boundary_frames_verified is True
    assert normalized.provenance.decoder_library_version == "1.2.2"
    assert normalized.provenance.mixer_version == "2.4.4"
    assert normalized.provenance.resampler_version == "1.17.1"
    assert normalized.provenance.writer_version == "0.14.0"
    assert normalized.provenance.profile_checksum_sha256
    info = sf.info(normalized_path)
    assert info.channels == 1
    assert info.samplerate == 16_000
    assert info.subtype == "PCM_16"
    assert (
        repo.get_current_normalized_audio_asset(audio_file.audio_file_id)
        == normalized
    )


def test_repeat_verification_is_idempotent_for_same_source_and_profile(
    tmp_path: Path,
) -> None:
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(storage_root, source_path=source_path)
    storage = LocalPrivateStorageAdapter(storage_root)

    first = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )
    second = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )

    assert second == first
    assert len(repo.normalized_audio_assets) == 1
    assert len(list((storage_root / "normalized").glob("*.wav"))) == 1


def test_runtime_profile_change_creates_new_normalized_asset_version(
    tmp_path: Path,
) -> None:
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(storage_root, source_path=source_path)
    storage = LocalPrivateStorageAdapter(storage_root)
    first = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )
    repo.normalized_audio_assets[
        (audio_file.audio_file_id, first.asset_version)
    ] = first.model_copy(
        update={
            "provenance": first.provenance.model_copy(
                update={"mixer_version": "unexpected-version"}
            )
        }
    )

    second = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )

    assert second.asset_version == first.asset_version + 1
    assert second.provenance.mixer_version == "2.4.4"
    assert len(repo.normalized_audio_assets) == 2


@pytest.mark.parametrize(
    "tamper_kind",
    [
        "delete_object",
        "replace_object",
        "conversion_profile",
        "provenance_profile",
        "normalized_checksum",
    ],
)
def test_current_normalized_asset_is_reused_only_after_byte_and_profile_verification(
    tmp_path: Path,
    tamper_kind: str,
) -> None:
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(storage_root, source_path=source_path)
    storage = LocalPrivateStorageAdapter(storage_root)
    first = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )
    key = (audio_file.audio_file_id, first.asset_version)
    if tamper_kind == "delete_object":
        (storage_root / first.object_key).unlink()
    elif tamper_kind == "replace_object":
        (storage_root / first.object_key).write_bytes(b"not-a-wave")
    elif tamper_kind == "conversion_profile":
        repo.normalized_audio_assets[key] = first.model_copy(
            update={"conversion_command_profile": "tampered-profile"}
        )
    elif tamper_kind == "provenance_profile":
        repo.normalized_audio_assets[key] = first.model_copy(
            update={
                "provenance": first.provenance.model_copy(
                    update={"normalization_profile": "tampered-profile"}
                )
            }
        )
    else:
        repo.normalized_audio_assets[key] = first.model_copy(
            update={"normalized_checksum_sha256": "0" * 64}
        )

    second = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )

    assert second.asset_version == first.asset_version + 1
    assert second.verification_status == "verified"
    assert second.normalized_checksum_sha256 != "0" * 64
    assert (storage_root / second.object_key).is_file()
    assert repo.normalized_audio_assets[key].status.value == "stale"


def test_verified_normalized_asset_requires_complete_consistent_provenance(
    tmp_path: Path,
) -> None:
    from app.schemas.speech_pipeline import NormalizedAudioAsset
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(storage_root, source_path=source_path)
    verified = verify_and_normalize_audio(
        repo,
        audio_file.audio_file_id,
        storage_adapter=LocalPrivateStorageAdapter(storage_root),
        settings=Settings(),
    )
    payload = verified.model_dump(mode="json")
    payload["provenance"] = None

    with pytest.raises(ValidationError, match="provenance"):
        NormalizedAudioAsset.model_validate(payload)

    inconsistent = verified.model_dump(mode="json")
    inconsistent["conversion_command_profile"] = "tampered-profile"
    with pytest.raises(ValidationError, match="profile"):
        NormalizedAudioAsset.model_validate(inconsistent)


def test_lineage_records_without_task4_verification_default_unverified() -> None:
    from app.schemas.speech_pipeline import NormalizedAudioAsset

    assert (
        NormalizedAudioAsset.model_fields["verification_status"].default
        == "unverified"
    )


def test_persistence_failure_removes_only_new_normalized_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(storage_root, source_path=source_path)
    source_object = storage_root / audio_file.object_key
    source_before = source_object.read_bytes()

    def reject_record(record):
        raise RuntimeError("synthetic repository failure")

    monkeypatch.setattr(repo, "create_normalized_audio_asset", reject_record)

    with pytest.raises(RuntimeError, match="repository failure"):
        verify_and_normalize_audio(
            repo,
            audio_file.audio_file_id,
            storage_adapter=LocalPrivateStorageAdapter(storage_root),
            settings=Settings(),
        )

    assert source_object.read_bytes() == source_before
    assert not list((storage_root / "normalized").glob("*.wav"))
    assert repo.audio_files[audio_file.audio_file_id].checksum_sha256 is None


@pytest.mark.parametrize("backend", ["json", "sql"])
@pytest.mark.parametrize("wrong_backend", [False, True])
def test_normalized_persistence_orphan_has_durable_exact_key_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
    wrong_backend: bool,
) -> None:
    from app.repositories.mock_repository import JsonFileRepository
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.consent_service import recover_audio_upload_cleanup
    from app.services.storage_service import LocalPrivateStorageAdapter

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    template, audio_file = _repo_with_audio(
        storage_root,
        source_path=source_path,
    )
    template.audio_files[
        audio_file.audio_file_id
    ].checksum_sha256 = sha256(source_path.read_bytes()).hexdigest()
    audio_file = template.audio_files[audio_file.audio_file_id]
    if backend == "json":
        repository_path = tmp_path / "repository.json"
        repo = JsonFileRepository(repository_path)
        reopen = lambda: JsonFileRepository(repository_path)
    else:
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import (
            SqlAlchemyRepository,
        )

        database_url = f"sqlite:///{tmp_path / 'repository.db'}"
        repo = SqlAlchemyRepository(database_url)
        reopen = lambda: SqlAlchemyRepository(database_url)
    repo.cases = repo.clone(template.cases)
    repo.sessions = repo.clone(template.sessions)
    repo.audio_files = repo.clone(template.audio_files)
    repo.save()

    class DeleteOutageStorage(LocalPrivateStorageAdapter):
        def delete_object(self, object_key):
            raise OSError("synthetic normalized delete outage")

    def reject_record_once(record):
        raise RuntimeError("synthetic repository failure")

    monkeypatch.setattr(
        repo,
        "create_normalized_audio_asset",
        reject_record_once,
    )
    with pytest.raises(RuntimeError, match="repository failure"):
        verify_and_normalize_audio(
            repo,
            audio_file.audio_file_id,
            storage_adapter=DeleteOutageStorage(storage_root),
            settings=Settings(),
        )

    durable = reopen()
    durable_audio = durable.audio_files[audio_file.audio_file_id]
    remediation = durable_audio.upload_cleanup_remediation
    assert remediation is not None
    assert len(remediation.additional_object_keys) == 1
    normalized_key = remediation.additional_object_keys[0]
    normalized_path = storage_root / normalized_key
    assert normalized_path.is_file()
    assert not durable.normalized_audio_assets

    recovery_storage = LocalPrivateStorageAdapter(
        tmp_path / "wrong-private"
        if wrong_backend
        else storage_root
    )
    recovered = recover_audio_upload_cleanup(
        durable,
        audio_file.audio_file_id,
        storage_adapter=recovery_storage,
        actor_id="normalization-recovery-test",
    )
    after = reopen().audio_files[audio_file.audio_file_id]
    if wrong_backend:
        assert recovered is False
        assert after.upload_cleanup_remediation is not None
        assert after.upload_cleanup_remediation.state == "escalated"
        assert after.upload_cleanup_remediation.error_code == (
            "storage_receipt_backend_mismatch"
        )
        assert normalized_path.is_file()
    else:
        assert recovered is True
        assert after.upload_cleanup_remediation is None
        assert not normalized_path.exists()


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_normalized_reservation_before_upload_recovers_missing_object(
    tmp_path: Path,
    backend: str,
) -> None:
    from app.repositories.mock_repository import JsonFileRepository
    from app.services.consent_service import recover_audio_upload_cleanup

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    template, audio_file = _repo_with_audio(
        storage_root,
        source_path=source_path,
    )
    if backend == "json":
        repository_path = tmp_path / "repository.json"
        repo = JsonFileRepository(repository_path)
        reopen = lambda: JsonFileRepository(repository_path)
    else:
        from app.repositories.sqlalchemy_repository import (
            SqlAlchemyRepository,
        )

        database_url = f"sqlite:///{tmp_path / 'repository.db'}"
        repo = SqlAlchemyRepository(database_url)
        reopen = lambda: SqlAlchemyRepository(database_url)
    repo.cases = repo.clone(template.cases)
    repo.sessions = repo.clone(template.sessions)
    repo.audio_files = repo.clone(template.audio_files)
    repo.save()
    object_key = "normalized/reserved-before-upload.wav"
    repo.reserve_normalized_audio_cleanup(
        audio_file.audio_file_id,
        expected_source_asset_version=audio_file.source_asset_version,
        object_key=object_key,
        storage_backend_identity_sha256=(
            audio_file.storage_backend_identity_sha256
        ),
        actor_id="normalization-crash-test",
    )

    restarted = reopen()
    assert recover_audio_upload_cleanup(
        restarted,
        audio_file.audio_file_id,
        storage_adapter=LocalPrivateStorageAdapter(storage_root),
        actor_id="normalization-recovery-test",
    )
    after = reopen().audio_files[audio_file.audio_file_id]
    assert after.upload_cleanup_remediation is None
    assert not (storage_root / object_key).exists()


def test_normalized_hard_kill_mid_local_write_recovers_all_private_bytes(
    tmp_path: Path,
) -> None:
    from app.repositories.mock_repository import JsonFileRepository
    from app.services.consent_service import recover_audio_upload_cleanup

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    template, audio_file = _repo_with_audio(
        storage_root,
        source_path=source_path,
    )
    repository_path = tmp_path / "repository.json"
    repo = JsonFileRepository(repository_path)
    repo.cases = repo.clone(template.cases)
    repo.sessions = repo.clone(template.sessions)
    repo.audio_files = repo.clone(template.audio_files)
    repo.save()

    object_key = "normalized/hard-kill-partial.wav"
    repo.reserve_normalized_audio_cleanup(
        audio_file.audio_file_id,
        expected_source_asset_version=audio_file.source_asset_version,
        object_key=object_key,
        storage_backend_identity_sha256=(
            audio_file.storage_backend_identity_sha256
        ),
        actor_id="normalization-hard-kill-test",
    )

    context = multiprocessing.get_context("fork")
    write_reached_fsync = context.Event()
    keep_child_blocked = context.Event()

    def persist_until_killed() -> None:
        import app.services.storage_service as storage_module

        real_fsync = storage_module.os.fsync

        def block_at_first_fsync(file_descriptor: int) -> None:
            write_reached_fsync.set()
            keep_child_blocked.wait(timeout=30)
            real_fsync(file_descriptor)

        storage_module.os.fsync = block_at_first_fsync
        LocalPrivateStorageAdapter(storage_root).persist_normalized_asset(
            audio_file,
            BytesIO(b"x" * (2 * 1024 * 1024)),
            content_type="audio/wav",
            object_key=object_key,
        )

    process = context.Process(target=persist_until_killed)
    process.start()
    try:
        assert write_reached_fsync.wait(timeout=10)
    finally:
        process.terminate()
        process.join(timeout=10)
        if process.is_alive():
            process.kill()
            process.join(timeout=10)
    assert process.exitcode is not None
    assert process.exitcode != 0

    restarted = JsonFileRepository(repository_path)
    assert recover_audio_upload_cleanup(
        restarted,
        audio_file.audio_file_id,
        storage_adapter=LocalPrivateStorageAdapter(storage_root),
        actor_id="normalization-hard-kill-recovery-test",
    )

    after = JsonFileRepository(repository_path)
    assert (
        after.audio_files[
            audio_file.audio_file_id
        ].upload_cleanup_remediation
        is None
    )
    assert not (storage_root / object_key).exists()
    assert not list((storage_root / "normalized").iterdir())


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_normalized_record_before_reservation_clear_preserves_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
) -> None:
    from app.repositories.mock_repository import JsonFileRepository
    from app.services.audio_media_service import verify_and_normalize_audio
    from app.services.consent_service import recover_audio_upload_cleanup

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    template, audio_file = _repo_with_audio(
        storage_root,
        source_path=source_path,
    )
    template.audio_files[
        audio_file.audio_file_id
    ].checksum_sha256 = sha256(source_path.read_bytes()).hexdigest()
    audio_file = template.audio_files[audio_file.audio_file_id]
    if backend == "json":
        repository_path = tmp_path / "repository.json"
        repo = JsonFileRepository(repository_path)
        reopen = lambda: JsonFileRepository(repository_path)
    else:
        from app.repositories.sqlalchemy_repository import (
            SqlAlchemyRepository,
        )

        database_url = f"sqlite:///{tmp_path / 'repository.db'}"
        repo = SqlAlchemyRepository(database_url)
        reopen = lambda: SqlAlchemyRepository(database_url)
    repo.cases = repo.clone(template.cases)
    repo.sessions = repo.clone(template.sessions)
    repo.audio_files = repo.clone(template.audio_files)
    repo.save()

    def interrupted_clear(*args, **kwargs):
        raise RuntimeError("synthetic reservation clear interruption")

    monkeypatch.setattr(
        repo,
        "clear_normalized_audio_cleanup",
        interrupted_clear,
    )
    with pytest.raises(RuntimeError, match="clear interruption"):
        verify_and_normalize_audio(
            repo,
            audio_file.audio_file_id,
            storage_adapter=LocalPrivateStorageAdapter(storage_root),
            settings=Settings(),
        )

    restarted = reopen()
    remediation = restarted.audio_files[
        audio_file.audio_file_id
    ].upload_cleanup_remediation
    assert remediation is not None
    assert len(restarted.normalized_audio_assets) == 1
    object_key = remediation.additional_object_keys[0]
    assert (storage_root / object_key).is_file()
    assert recover_audio_upload_cleanup(
        restarted,
        audio_file.audio_file_id,
        storage_adapter=LocalPrivateStorageAdapter(storage_root),
        actor_id="normalization-recovery-test",
    )
    after = reopen()
    assert (
        after.audio_files[
            audio_file.audio_file_id
        ].upload_cleanup_remediation
        is None
    )
    assert (storage_root / object_key).is_file()
    assert len(after.normalized_audio_assets) == 1


def test_verify_route_returns_structured_limit_error_and_creates_no_job(
    tmp_path: Path,
) -> None:
    from app.core.config import get_settings
    from app.services.storage_service import (
        LocalPrivateStorageAdapter,
        get_storage_adapter,
    )

    source_path = tmp_path / "1001ms.wav"
    _write_sparse_pcm16_wav(source_path, frame_count=16_016)
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(storage_root, source_path=source_path)
    test_settings = Settings(max_audio_duration_seconds=1)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_storage_adapter] = lambda: LocalPrivateStorageAdapter(
        storage_root
    )
    try:
        response = TestClient(app).post(
            f"/api/v1/audio/{audio_file.audio_file_id}/verify-and-normalize",
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error_code": "audio_duration_limit_exceeded",
        "actual_value": 1_001,
        "configured_limit": 1_000,
        "unit": "milliseconds",
        "supported_formats": ["wav", "mp3"],
        "remediation": (
            "Upload one complete language-sample file no longer than 0 minutes; "
            "the server will not truncate or split it."
        ),
    }
    assert repo.jobs == {}


def test_real_provider_job_requires_verified_normalized_asset(
    tmp_path: Path,
) -> None:
    from app.services.audio_job_service import create_audio_processing_job
    from app.services.audio_media_service import AudioIntakeError

    source_path = tmp_path / "short.wav"
    source_path.write_bytes(
        _wav_bytes(np.zeros(1_600, dtype=np.float64), sample_rate_hz=16_000)
    )
    storage_root = tmp_path / "private"
    repo, audio_file = _repo_with_audio(storage_root, source_path=source_path)
    audio_file.checksum_sha256 = sha256(source_path.read_bytes()).hexdigest()

    with pytest.raises(AudioIntakeError) as captured:
        create_audio_processing_job(
            repo,
            audio_file.session_id,
            AudioProcessRequest(
                provider="local_faster_whisper",
                duration_seconds=0.1,
            ),
        )

    assert captured.value.code == "audio_normalization_required"
    assert repo.jobs == {}


def test_local_storage_rejects_escape_and_cleans_partial_atomic_write(
    tmp_path: Path,
) -> None:
    from app.services.storage_service import (
        LocalPrivateStorageAdapter,
        StorageProcessingError,
    )

    storage_root = tmp_path / "private"
    storage = LocalPrivateStorageAdapter(storage_root)
    escaped = AudioFileMetadata(
        audio_file_id="aud_escape",
        session_id="session_escape",
        case_id="case_escape",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=4,
        storage_mode="local_private",
        storage_backend_identity_sha256=(
            storage.storage_backend_identity_sha256
        ),
        object_key="../outside.wav",
        upload_status="uploaded",
    )
    with pytest.raises(StorageProcessingError) as invalid_key:
        storage.open_source_for_processing(escaped)
    assert invalid_key.value.code == "storage_object_key_invalid"

    valid = escaped.model_copy(
        update={
            "audio_file_id": "aud_atomic",
            "object_key": "audio/source.wav",
        }
    )

    class FailingSource(BytesIO):
        calls = 0

        def read(self, size: int = -1) -> bytes:
            self.calls += 1
            if self.calls > 1:
                raise OSError("synthetic interrupted read")
            return b"x" * (1024 * 1024)

    with pytest.raises(StorageProcessingError) as captured:
        storage.persist_normalized_asset(
            valid,
            FailingSource(),
            content_type="audio/wav",
        )
    assert captured.value.code == "storage_write_failed"
    assert not list(storage_root.rglob("*.part"))
    assert not list((storage_root / "normalized").glob("*.wav"))


def test_upload_route_rejects_actual_oversize_atomically(
    tmp_path: Path,
) -> None:
    from app.core.config import get_settings
    from app.services.storage_service import (
        LocalPrivateStorageAdapter,
        get_storage_adapter,
    )

    storage_root = tmp_path / "private"
    repo = MockRepository()
    case = repo.create_case(
        ChildCaseCreate(
            child_code="SYNTHETIC-UPLOAD-001",
            age_months=48,
            language="Thai",
            consent_status="granted",
        ),
        actor_id="therapist-demo",
    )
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(
            session_date="2026-07-26",
            session_type="synthetic_testbed",
        ),
        actor_id="therapist-demo",
    )
    audio_file = AudioFileMetadata(
        audio_file_id="aud_atomic_upload",
        organization_id=session.organization_id,
        session_id=session.session_id,
        case_id=case.case_id,
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=1024 * 1024 + 1,
        storage_mode="local_private",
        object_key="audio/atomic-source.wav",
        upload_status="pending",
    )
    repo.audio_files[audio_file.audio_file_id] = audio_file
    settings = Settings(max_audio_file_size_mb=1)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_storage_adapter] = lambda: LocalPrivateStorageAdapter(
        storage_root
    )
    try:
        response = TestClient(app).put(
            f"/api/v1/audio/{audio_file.audio_file_id}/upload-file",
            content=b"x" * (1024 * 1024 + 1),
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "audio_size_limit_exceeded"
    assert response.json()["detail"]["actual_value"] == 1024 * 1024 + 1
    assert not (storage_root / audio_file.object_key).exists()
    assert not list(storage_root.rglob("*.part"))
    assert repo.audio_files[audio_file.audio_file_id].upload_status == "pending"


def test_upload_intent_uses_typed_100_mib_and_verified_format_allowlist() -> None:
    from app.services.audio_job_service import validate_audio_upload
    from app.services.audio_media_service import AudioIntakeError
    from app.schemas.clinical import AudioUploadRequest

    validate_audio_upload(
        AudioUploadRequest(
            filename="synthetic.wav",
            content_type="audio/wav",
            size_bytes=100 * 1024 * 1024,
        ),
        settings=Settings(),
    )
    with pytest.raises(AudioIntakeError) as oversized:
        validate_audio_upload(
            AudioUploadRequest(
                filename="synthetic.wav",
                content_type="audio/wav",
                size_bytes=100 * 1024 * 1024 + 1,
            ),
            settings=Settings(),
        )
    assert oversized.value.code == "audio_size_limit_exceeded"

    for filename, content_type in (
        ("synthetic.m4a", "audio/mp4"),
        ("synthetic.webm", "audio/webm"),
    ):
        with pytest.raises(AudioIntakeError) as unavailable:
            validate_audio_upload(
                AudioUploadRequest(
                    filename=filename,
                    content_type=content_type,
                    size_bytes=1024,
                ),
                settings=Settings(),
            )
        assert unavailable.value.code == "audio_format_unavailable"
        assert unavailable.value.details["supported_formats"] == ["wav", "mp3"]


def test_capabilities_and_upload_fail_closed_when_decoder_runtime_is_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.api.v1.routes.jobs as jobs_route
    import app.services.audio_job_service as audio_jobs
    from app.schemas.clinical import AudioUploadRequest
    from app.services.audio_media_service import (
        AudioIntakeError,
        DecoderCapability,
        DecoderCapabilityRegistry,
        DecoderRuntime,
    )

    unavailable_registry = DecoderCapabilityRegistry(
        runtime=DecoderRuntime(
            decoder_name="soundfile",
            soundfile_version="unexpected",
            library_name="libsndfile",
            libsndfile_version="unexpected",
        ),
        capabilities={
            format_id: DecoderCapability(
                format_id=format_id,
                available=False,
                fixture_verified=False,
                reason_code="decoder_runtime_version_mismatch",
            )
            for format_id in ("wav", "mp3", "m4a", "webm")
        },
    )
    monkeypatch.setattr(
        jobs_route,
        "get_decoder_capability_registry",
        lambda: unavailable_registry,
        raising=False,
    )
    monkeypatch.setattr(
        audio_jobs,
        "get_decoder_capability_registry",
        lambda: unavailable_registry,
        raising=False,
    )

    capabilities = jobs_route.get_audio_capabilities(Settings())
    assert capabilities.supported_formats == []
    assert capabilities.processing_state == "unavailable"
    assert capabilities.unavailable_reason == "decoder_runtime_unavailable"

    with pytest.raises(AudioIntakeError) as captured:
        audio_jobs.validate_audio_upload(
            AudioUploadRequest(
                filename="synthetic.wav",
                content_type="audio/wav",
                size_bytes=1024,
            ),
            settings=Settings(),
        )
    assert captured.value.code == "decoder_capability_unavailable"
    assert captured.value.details["supported_formats"] == []
