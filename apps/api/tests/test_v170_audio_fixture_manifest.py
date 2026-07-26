from __future__ import annotations

import copy
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import pytest
import soundfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "audio" / "v1.7.0"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
EXPECTED_DURATIONS_MS = {
    "thai_1m": 60_000,
    "thai_english_5m": 300_000,
    "thai_english_15m": 900_000,
    "thai_english_15m_plus_5s": 905_000,
}
REQUIRED_CASES = {
    "thai_1m",
    "thai_english_5m",
    "thai_english_15m",
    "thai_english_15m_plus_5s",
    "two_speakers_correct",
    "swapped_clusters",
    "unknown_speaker",
    "more_than_two_speakers",
    "diarization_unavailable",
    "overlapping_speech",
}
READY_TOKENIZER_PROFILE = {
    "status": "ready",
    "profile_id": "thai-aware-deterministic-v1.7.0",
    "profile_version": 1,
    "engine": "pinned-test-tokenizer",
    "package_version": "1.0.0",
    "segmentation_mode": "deterministic_fixture_mode",
    "artifact_id": "fixture-dictionary-v1",
    "artifact_checksum_sha256": hashlib.sha256(
        b"fixture-dictionary-v1"
    ).hexdigest(),
    "unicode_normalization": "NFC",
    "punctuation_handling": "exclude_punctuation_only_tokens",
    "whitespace_handling": "normalize_without_token_fallback",
    "filled_pause_handling": "exclude",
    "repetition_handling": "exclude_retraced_repetitions",
    "partial_word_handling": "exclude",
    "unintelligibility_marker_handling": "exclude",
    "thai_english_code_switch_handling": "include_profile_segmented_tokens",
    "custom_vocabulary_version": "not_used",
    "custom_vocabulary_checksum_sha256": hashlib.sha256(b"").hexdigest(),
    "golden_fixture_manifest_checksum_sha256": hashlib.sha256(
        json.dumps(
            json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest(),
}
READY_TOKENIZER_PROFILE["profile_checksum_sha256"] = hashlib.sha256(
    json.dumps(
        {
            key: value
            for key, value in READY_TOKENIZER_PROFILE.items()
            if key != "status"
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
READY_FEATURE_PROFILE = {
    "status": "ready",
    "feature_version": "descriptive-features-v1.7.0",
    "algorithm_version": "descriptive-feature-algorithm-v1.7.0",
    "configuration_version": "descriptive-feature-config-v1.7.0",
    "configuration_checksum_sha256": hashlib.sha256(
        b"descriptive-feature-config-v1.7.0"
    ).hexdigest(),
    "tokenizer_profile_id": READY_TOKENIZER_PROFILE["profile_id"],
    "tokenizer_profile_version": READY_TOKENIZER_PROFILE["profile_version"],
    "tokenizer_profile_checksum_sha256": READY_TOKENIZER_PROFILE[
        "profile_checksum_sha256"
    ],
}

sys.path.insert(0, str(REPOSITORY_ROOT))
from scripts.generate_v170_golden_audio import (  # noqa: E402
    FixtureManifestError,
    generate_fixtures,
    load_and_validate_manifest,
    validate_expected_gold,
    validate_manifest,
)


def _load_raw_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _transcript_checksum(transcript: dict) -> str:
    payload = {
        key: value for key, value in transcript.items() if key != "checksum_sha256"
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _canonical_fixture_manifest_checksum(manifest: dict) -> str:
    projection = {
        key: value
        for key, value in manifest.items()
        if key not in {"artifact_profiles", "gold_readiness", "cases"}
    }
    projection["cases"] = {
        case_id: {
            key: value
            for key, value in case.items()
            if key != "expected_artifact_sha256"
        }
        for case_id, case in manifest["cases"].items()
    }
    return hashlib.sha256(
        json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _transition_manifest_profiles_to_ready(manifest: dict) -> None:
    manifest["artifact_profiles"]["chat"]["status"] = "verified"
    manifest["artifact_profiles"]["tokenizer"] = copy.deepcopy(
        READY_TOKENIZER_PROFILE
    )
    manifest["artifact_profiles"]["features"] = copy.deepcopy(
        READY_FEATURE_PROFILE
    )
    manifest["artifact_profiles"]["tokenizer"][
        "golden_fixture_manifest_checksum_sha256"
    ] = _canonical_fixture_manifest_checksum(manifest)
    _refresh_ready_tokenizer_checksum(manifest)


def _refresh_ready_tokenizer_checksum(manifest: dict) -> None:
    tokenizer = manifest["artifact_profiles"]["tokenizer"]
    payload = {
        key: value
        for key, value in tokenizer.items()
        if key not in {"status", "profile_checksum_sha256"}
    }
    tokenizer["profile_checksum_sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    manifest["artifact_profiles"]["features"][
        "tokenizer_profile_checksum_sha256"
    ] = tokenizer["profile_checksum_sha256"]


def _transition_expected_to_ready(expected: dict, *, manifest: dict) -> None:
    expected["gold_status"] = "gold_ready"
    expected["source_transcript"]["status"] = "reviewed"
    expected["source_transcript"]["checksum_sha256"] = _transcript_checksum(
        expected["source_transcript"]
    )
    expected["accepted_timestamp_bounds"]["asr_tolerance_status"] = "verified"
    expected["reviewed_mapping"]["status"] = "confirmed"
    for entry in expected["reviewed_mapping"]["entries"]:
        entry["confirmed_chat_code"] = entry.pop("proposed_chat_code")
        entry["review_status"] = "confirmed"
    expected["attestation"].update(
        {
            "attestation_version": 1,
            "status": "attested",
            "reason_code": "all_gold_gates_satisfied",
        }
    )
    expected["chat_artifact"] = {
        "status": "verified",
        "subset_version": "lingualens-chat-v1.7.0",
        "parser_version": "lingualens-chat-parser-v1.7.0",
        "serializer_version": "lingualens-chat-serializer-v1.7.0",
        "canonical_checksum_sha256": "a" * 64,
        "artifact_checksum_sha256": "b" * 64,
    }
    expected["tokenizer_profile"] = {
        **{
            key: value
            for key, value in manifest["artifact_profiles"]["tokenizer"].items()
            if key != "status"
        },
        "status": "available",
    }
    expected["feature_expectations"] = [
        {
            "feature_id": "total_utterance_count",
            **{
                key: value
                for key, value in manifest["artifact_profiles"]["features"].items()
                if key != "status"
            },
            "status": "available",
            "reason_code": "computed",
            "remediation": "none",
            "numerator": {"value": 13},
            "denominator": {"value": 13},
            "value": {"value": 13, "unit": "utterances"},
            "tolerance": {"absolute": 0},
            "exclusions": [],
        }
    ]
    expected["known_limitations"] = []


def _transition_expected_to_verified_rejection(expected: dict) -> None:
    expected["gold_status"] = "verified_rejection"
    expected["source_transcript"]["status"] = "not_created"
    expected["source_transcript"]["checksum_sha256"] = _transcript_checksum(
        expected["source_transcript"]
    )
    expected["accepted_timestamp_bounds"][
        "asr_tolerance_status"
    ] = "not_applicable_due_to_intake_rejection"
    expected["reviewed_mapping"]["status"] = "not_applicable"
    expected["reviewed_mapping"]["entries"] = []
    expected["attestation"].update(
        {
            "attestation_version": 0,
            "status": "not_created",
            "reason_code": "audio_duration_limit_exceeded",
        }
    )
    for artifact_name in ("chat_artifact", "tokenizer_profile"):
        expected[artifact_name]["status"] = "unavailable"
        expected[artifact_name]["dependency"][
            "reason_code"
        ] = "audio_duration_limit_exceeded"
    for feature in expected["feature_expectations"]:
        feature["status"] = "unavailable"
        feature["reason_code"] = "audio_duration_limit_exceeded"
    expected["known_limitations"] = [
        {
            "code": "audio_duration_limit_exceeded",
            "severity": "integrity_blocker",
            "configured_limit_ms": 900_000,
            "actual_ms": 905_000,
        }
    ]


def _build_strict_ready_manifest(tmp_path: Path) -> tuple[dict, Path]:
    temporary_repository = tmp_path / "repository"
    temporary_fixture_root = (
        temporary_repository / "tests" / "fixtures" / "audio" / "v1.7.0"
    )
    shutil.copytree(FIXTURE_ROOT, temporary_fixture_root)
    temporary_script = (
        temporary_repository / "scripts" / "generate_v170_golden_audio.py"
    )
    temporary_script.parent.mkdir(parents=True)
    shutil.copy2(
        REPOSITORY_ROOT / "scripts" / "generate_v170_golden_audio.py",
        temporary_script,
    )

    manifest_path = temporary_fixture_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["gold_readiness"]["status"] = "gold_ready"
    manifest["gold_readiness"]["blocking_dependencies"] = []
    for seed in manifest["seeds"].values():
        for review_name in ("human_review", "license_review"):
            seed[review_name] = {
                "status": "confirmed",
                "blocking": False,
                "reason_code": "review_complete",
                "reviewed_by": "synthetic-fixture-reviewer",
                "reviewed_at": "2026-07-26T12:00:00+07:00",
            }
    _transition_manifest_profiles_to_ready(manifest)
    for case in manifest["cases"].values():
        expected_path = temporary_fixture_root / case["expected_artifact"]
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        if case.get("intake_expectation") == "audio_duration_limit_exceeded":
            _transition_expected_to_verified_rejection(expected)
        else:
            _transition_expected_to_ready(expected, manifest=manifest)
        expected_path.write_text(
            json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        case["expected_artifact_sha256"] = _sha256(expected_path)
    return manifest, temporary_fixture_root


def test_manifest_has_all_required_versioned_cases_and_expected_artifacts() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)

    assert manifest["schema_version"] == "lingualens-audio-fixture-manifest-v1"
    assert manifest["fixture_version"] == "v1.7.0"
    assert REQUIRED_CASES <= set(manifest["cases"])
    for case_id in REQUIRED_CASES:
        expected_path = FIXTURE_ROOT / manifest["cases"][case_id]["expected_artifact"]
        assert expected_path.is_file()
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert expected["case_id"] == case_id
        assert expected["gold_contract_version"] == "v1.7.0-exact-scaffold-1"
        transcript = expected["source_transcript"]
        assert transcript["version"] == 1
        assert len(transcript["checksum_sha256"]) == 64
        assert transcript["segment_plan"]["sequence"]
        assert all(
            "*" not in json.dumps(component)
            for component in transcript["segment_plan"]["sequence"]
        )
        assert expected["temporary_speaker_labels"]
        assert expected["beginning_anchor"]
        assert expected["ending_anchor"]
        assert expected["accepted_timestamp_bounds"]
        assert expected["reviewed_mapping"]
        assert expected["reviewed_mapping"]["mapping_id"]
        assert expected["reviewed_mapping"]["mapping_version"] == 1
        assert expected["chat_artifact"]["status"] == "unavailable"
        assert expected["tokenizer_profile"]
        assert expected["feature_expectations"]
        assert isinstance(expected["known_limitations"], list)
        if (
            manifest["cases"][case_id].get("intake_expectation")
            == "audio_duration_limit_exceeded"
        ):
            assert expected["gold_status"] == "verified_rejection"
            assert transcript["status"] == "not_created"
            assert expected["reviewed_mapping"]["status"] == "not_applicable"
            assert expected["reviewed_mapping"]["entries"] == []
            assert expected["attestation"]["status"] == "not_created"
            assert (
                expected["chat_artifact"]["dependency"]["reason_code"]
                == "audio_duration_limit_exceeded"
            )
            assert (
                expected["tokenizer_profile"]["dependency"]["reason_code"]
                == "audio_duration_limit_exceeded"
            )
            assert all(
                feature["status"] == "unavailable"
                and feature["reason_code"] == "audio_duration_limit_exceeded"
                for feature in expected["feature_expectations"]
            )
        else:
            assert expected["gold_status"] == "scaffold_pending_external_review"
            assert transcript["status"] == "pending_human_review"
            assert (
                expected["reviewed_mapping"]["status"]
                == "draft_pending_human_review"
            )
            assert expected["attestation"]["status"] == "blocked"


def test_manifest_rejects_identifying_metadata() -> None:
    manifest = _load_raw_manifest()
    manifest["cases"]["thai_1m"]["patient_name"] = "fixture-person"

    with pytest.raises(FixtureManifestError, match="identifying_metadata"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT)


def test_manifest_rejects_missing_seed_provenance() -> None:
    manifest = _load_raw_manifest()
    del manifest["seeds"]["thai_only"]["provenance"]["tool_version"]

    with pytest.raises(FixtureManifestError, match="missing_provenance"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT)


def test_manifest_rejects_incomplete_acoustic_track_provenance() -> None:
    manifest = _load_raw_manifest()
    del manifest["seeds"]["overlap"]["acoustic_tracks"][2]["voice_identifier"]

    with pytest.raises(FixtureManifestError, match="missing_provenance"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT, verify_files=False)


def test_manifest_rejects_unpinned_mp3_decoder_provenance() -> None:
    manifest = _load_raw_manifest()
    del manifest["format_fixtures"]["mp3"]["decoder"]["library_version"]

    with pytest.raises(FixtureManifestError, match="missing_provenance"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT, verify_files=False)


def test_manifest_rejects_incorrect_seed_hash() -> None:
    manifest = _load_raw_manifest()
    manifest["seeds"]["thai_only"]["sha256"] = "0" * 64

    with pytest.raises(FixtureManifestError, match="checksum_mismatch"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT)


def test_manifest_rejects_mutable_fixture_filename() -> None:
    manifest = _load_raw_manifest()
    manifest["seeds"]["thai_only"]["path"] = "seed/latest.wav"

    with pytest.raises(FixtureManifestError, match="mutable_filename"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT)


def test_manifest_rejects_duration_class_mismatch() -> None:
    manifest = _load_raw_manifest()
    manifest["cases"]["thai_english_15m"]["expected_duration_ms"] = 899_999

    with pytest.raises(FixtureManifestError, match="duration_class_mismatch"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT)


def test_seed_wavs_are_frame_exact_and_review_state_is_truthful() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)

    assert set(manifest["seeds"]) == {"thai_only", "thai_english", "overlap"}
    for seed in manifest["seeds"].values():
        seed_path = FIXTURE_ROOT / seed["path"]
        with wave.open(str(seed_path), "rb") as audio:
            assert audio.getnchannels() == seed["pcm"]["channels"] == 1
            assert audio.getsampwidth() * 8 == seed["pcm"]["bits_per_sample"] == 16
            assert audio.getframerate() == seed["pcm"]["sample_rate_hz"] == 16_000
            assert audio.getnframes() == seed["frame_count"]
        assert seed["duration_ms"] == seed["frame_count"] * 1000 // 16_000
        assert _sha256(seed_path) == seed["sha256"]
        assert seed["human_review"]["status"] == "pending"
        assert seed["human_review"]["blocking"] is True
        assert seed["license_review"]["status"] == "pending"
        assert seed["license_review"]["blocking"] is True


def test_exact_long_case_segment_plans_pin_repeat_counts_and_frame_coverage() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    expected_repeats = {
        "thai_1m": 11,
        "thai_english_5m": 56,
        "thai_english_15m": 169,
        "thai_english_15m_plus_5s": 170,
    }

    for case_id, repeat_count in expected_repeats.items():
        case = manifest["cases"][case_id]
        expected = json.loads(
            (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
        )
        sequence = expected["source_transcript"]["segment_plan"]["sequence"]
        repeat = next(component for component in sequence if component["kind"] == "repeat")
        assert repeat["repeat_count"] == repeat_count
        assert sequence[0]["start_frame"] == 0
        assert sequence[-1]["end_frame"] == case["expected_frame_count"]
        assert all(
            earlier["end_frame"] == later["start_frame"]
            for earlier, later in zip(sequence, sequence[1:])
        )


def test_expected_gold_validation_rejects_missing_or_reordered_segment_plan() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    case_id = "thai_1m"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )

    missing = copy.deepcopy(expected)
    del missing["source_transcript"]["segment_plan"]["sequence"][1]
    with pytest.raises(FixtureManifestError, match="segment_plan_coverage"):
        validate_expected_gold(case_id, missing, case=case, manifest=manifest)

    reordered = copy.deepcopy(expected)
    reordered["source_transcript"]["segment_plan"]["sequence"][0:2] = reversed(
        reordered["source_transcript"]["segment_plan"]["sequence"][0:2]
    )
    with pytest.raises(FixtureManifestError, match="segment_plan_order"):
        validate_expected_gold(case_id, reordered, case=case, manifest=manifest)


def test_expected_gold_validation_rejects_unpinned_provenance() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    case_id = "thai_1m"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )
    expected["chat_artifact"]["parser_version"] = "unreviewed-parser"

    with pytest.raises(FixtureManifestError, match="provenance_mismatch"):
        validate_expected_gold(case_id, expected, case=case, manifest=manifest)


def test_expected_gold_accepts_a_fully_populated_ready_transition() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    _transition_manifest_profiles_to_ready(manifest)
    case_id = "thai_1m"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )
    _transition_expected_to_ready(expected, manifest=manifest)

    validate_expected_gold(case_id, expected, case=case, manifest=manifest)


def test_expected_gold_accepts_a_verified_over_limit_rejection() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    case_id = "thai_english_15m_plus_5s"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )
    _transition_expected_to_verified_rejection(expected)

    validate_expected_gold(case_id, expected, case=case, manifest=manifest)


@pytest.mark.parametrize(
    "fabricated_downstream",
    ["transcript", "mapping", "attestation", "chat", "tokenizer", "features"],
)
def test_verified_rejection_rejects_fabricated_downstream_availability(
    fabricated_downstream: str,
) -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    case_id = "thai_english_15m_plus_5s"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )
    _transition_expected_to_verified_rejection(expected)
    if fabricated_downstream == "transcript":
        expected["source_transcript"]["status"] = "reviewed"
        expected["source_transcript"]["checksum_sha256"] = _transcript_checksum(
            expected["source_transcript"]
        )
    elif fabricated_downstream == "mapping":
        expected["reviewed_mapping"]["status"] = "confirmed"
    elif fabricated_downstream == "attestation":
        expected["attestation"]["status"] = "attested"
        expected["attestation"]["attestation_version"] = 1
    elif fabricated_downstream == "chat":
        expected["chat_artifact"]["status"] = "verified"
    elif fabricated_downstream == "tokenizer":
        expected["tokenizer_profile"]["status"] = "available"
    else:
        expected["feature_expectations"][0]["status"] = "available"

    with pytest.raises(FixtureManifestError, match="invalid_rejection_state"):
        validate_expected_gold(case_id, expected, case=case, manifest=manifest)


def test_intake_eligible_case_cannot_claim_verified_rejection() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    case_id = "thai_english_15m"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )
    _transition_expected_to_verified_rejection(expected)

    with pytest.raises(FixtureManifestError, match="invalid_rejection_state"):
        validate_expected_gold(case_id, expected, case=case, manifest=manifest)


def test_strict_manifest_accepts_verified_fully_ready_fixtures(
    tmp_path: Path,
) -> None:
    manifest, temporary_fixture_root = _build_strict_ready_manifest(tmp_path)

    validate_manifest(
        manifest,
        fixture_root=temporary_fixture_root,
        require_gold_ready=True,
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("profile_version", 2),
        ("profile_checksum_sha256", "9" * 64),
        ("engine", "different-tokenizer-engine"),
        ("package_version", "9.9.9"),
        ("segmentation_mode", "different-segmentation-mode"),
        ("artifact_id", "different-artifact"),
        ("artifact_checksum_sha256", "8" * 64),
        ("punctuation_handling", "include_all"),
        ("whitespace_handling", "whitespace_split_fallback"),
        ("filled_pause_handling", "include"),
        ("repetition_handling", "include_all"),
        ("partial_word_handling", "include"),
        ("unintelligibility_marker_handling", "include"),
        ("thai_english_code_switch_handling", "exclude_english"),
        ("custom_vocabulary_version", "synthetic-v2"),
        ("golden_fixture_manifest_checksum_sha256", "7" * 64),
    ],
)
def test_strict_manifest_rejects_tokenizer_profile_provenance_mismatch(
    tmp_path: Path,
    field: str,
    replacement: str | int,
) -> None:
    manifest, temporary_fixture_root = _build_strict_ready_manifest(tmp_path)
    manifest["artifact_profiles"]["tokenizer"][field] = replacement
    if field == "profile_version":
        manifest["artifact_profiles"]["features"][
            "tokenizer_profile_version"
        ] = replacement
    if field != "profile_checksum_sha256":
        _refresh_ready_tokenizer_checksum(manifest)

    expected_error = (
        "checksum_mismatch"
        if field
        in {
            "profile_checksum_sha256",
            "golden_fixture_manifest_checksum_sha256",
        }
        else "provenance_mismatch"
    )
    with pytest.raises(FixtureManifestError, match=expected_error):
        validate_manifest(
            manifest,
            fixture_root=temporary_fixture_root,
            require_gold_ready=True,
        )


def test_strict_manifest_rejects_non_nfc_tokenizer_profile(
    tmp_path: Path,
) -> None:
    manifest, temporary_fixture_root = _build_strict_ready_manifest(tmp_path)
    manifest["artifact_profiles"]["tokenizer"]["unicode_normalization"] = "NFKC"

    with pytest.raises(FixtureManifestError, match="invalid_ready_profile"):
        validate_manifest(
            manifest,
            fixture_root=temporary_fixture_root,
            require_gold_ready=True,
        )


def test_strict_manifest_rejects_invalid_not_used_custom_vocabulary_checksum(
    tmp_path: Path,
) -> None:
    manifest, temporary_fixture_root = _build_strict_ready_manifest(tmp_path)
    manifest["artifact_profiles"]["tokenizer"][
        "custom_vocabulary_checksum_sha256"
    ] = "6" * 64
    _refresh_ready_tokenizer_checksum(manifest)

    with pytest.raises(FixtureManifestError, match="invalid_ready_profile"):
        validate_manifest(
            manifest,
            fixture_root=temporary_fixture_root,
            require_gold_ready=True,
        )


def test_strict_manifest_rejects_custom_vocabulary_checksum_mismatch(
    tmp_path: Path,
) -> None:
    manifest, temporary_fixture_root = _build_strict_ready_manifest(tmp_path)
    tokenizer = manifest["artifact_profiles"]["tokenizer"]
    tokenizer["custom_vocabulary_version"] = "synthetic-v2"
    tokenizer["custom_vocabulary_checksum_sha256"] = "6" * 64
    _refresh_ready_tokenizer_checksum(manifest)

    with pytest.raises(FixtureManifestError, match="provenance_mismatch"):
        validate_manifest(
            manifest,
            fixture_root=temporary_fixture_root,
            require_gold_ready=True,
        )


@pytest.mark.parametrize("profile_name", ["tokenizer", "features"])
def test_strict_manifest_rejects_ready_profile_with_pending_dependency(
    tmp_path: Path,
    profile_name: str,
) -> None:
    manifest, temporary_fixture_root = _build_strict_ready_manifest(tmp_path)
    manifest["artifact_profiles"][profile_name]["dependency"] = {
        "reason_code": "task_11_artifact_not_resolved",
        "required_artifact": "Task 11 resolved artifact",
        "remediation": "Resolve and pin the artifact.",
    }

    with pytest.raises(FixtureManifestError, match="invalid_ready_profile"):
        validate_manifest(
            manifest,
            fixture_root=temporary_fixture_root,
            require_gold_ready=True,
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("feature_version", "mismatched-feature-version"),
        ("algorithm_version", "mismatched-feature-algorithm"),
        ("configuration_version", "mismatched-feature-config"),
        ("configuration_checksum_sha256", "f" * 64),
    ],
)
def test_strict_manifest_rejects_feature_profile_provenance_mismatch(
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    manifest, temporary_fixture_root = _build_strict_ready_manifest(tmp_path)
    manifest["artifact_profiles"]["features"][field] = replacement

    with pytest.raises(FixtureManifestError, match="provenance_mismatch"):
        validate_manifest(
            manifest,
            fixture_root=temporary_fixture_root,
            require_gold_ready=True,
        )


def test_expected_gold_rejects_ready_status_flips_without_ready_data() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    case_id = "thai_1m"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )
    expected["gold_status"] = "gold_ready"
    expected["source_transcript"]["status"] = "reviewed"
    expected["source_transcript"]["checksum_sha256"] = _transcript_checksum(
        expected["source_transcript"]
    )

    with pytest.raises(FixtureManifestError, match="invalid_ready_state"):
        validate_expected_gold(case_id, expected, case=case, manifest=manifest)


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        ("unknown_reference", "speaker_reference_mismatch"),
        ("duplicate_label", "duplicate_speaker_label"),
        ("duplicate_mapping", "duplicate_mapping_speaker"),
        ("duplicate_chat_code", "ambiguous_chat_code"),
        ("duplicate_required_role", "ambiguous_required_role"),
    ],
)
def test_expected_gold_rejects_speaker_integrity_mutations(
    mutation: str,
    error_code: str,
) -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    case_id = "two_speakers_correct"
    case = manifest["cases"][case_id]
    expected = json.loads(
        (FIXTURE_ROOT / case["expected_artifact"]).read_text(encoding="utf-8")
    )
    if mutation == "unknown_reference":
        expected["source_transcript"]["segment_plan"]["sequence"][0][
            "speaker"
        ] = "SPK_99"
        expected["source_transcript"]["checksum_sha256"] = _transcript_checksum(
            expected["source_transcript"]
        )
    elif mutation == "duplicate_label":
        expected["temporary_speaker_labels"].append("SPK_01")
    elif mutation == "duplicate_mapping":
        expected["reviewed_mapping"]["entries"].append(
            copy.deepcopy(expected["reviewed_mapping"]["entries"][0])
        )
    elif mutation == "duplicate_chat_code":
        expected["reviewed_mapping"]["entries"][1]["proposed_chat_code"] = "TGT"
    else:
        expected["reviewed_mapping"]["entries"][1][
            "participant_role"
        ] = "synthetic_target"

    with pytest.raises(FixtureManifestError, match=error_code):
        validate_expected_gold(case_id, expected, case=case, manifest=manifest)


def test_gold_ready_mode_refuses_pending_external_reviews() -> None:
    with pytest.raises(FixtureManifestError, match="gold_not_ready"):
        load_and_validate_manifest(MANIFEST_PATH, require_gold_ready=True)

    manifest = load_and_validate_manifest(MANIFEST_PATH, require_gold_ready=False)
    assert manifest["gold_readiness"]["status"] == "scaffold_only"
    assert set(manifest["gold_readiness"]["blocking_dependencies"]) == {
        "human_spoken_content_review",
        "redistribution_license_review",
        "chat_gold_task_10",
        "tokenizer_profile_task_11",
        "feature_gold_task_11",
    }


def test_gold_ready_mode_cannot_be_bypassed_by_flipping_manifest_status() -> None:
    manifest = _load_raw_manifest()
    manifest["gold_readiness"]["status"] = "gold_ready"
    manifest["gold_readiness"]["blocking_dependencies"] = []
    for seed in manifest["seeds"].values():
        for review_name in ("human_review", "license_review"):
            seed[review_name] = {
                "status": "confirmed",
                "blocking": False,
                "reason_code": "review_complete",
                "reviewed_by": "synthetic-fixture-reviewer",
                "reviewed_at": "2026-07-26T12:00:00+07:00",
            }

    with pytest.raises(FixtureManifestError, match="gold_not_ready"):
        validate_manifest(
            manifest,
            fixture_root=FIXTURE_ROOT,
            require_gold_ready=True,
        )


def test_gold_ready_mode_rejects_unverified_forged_expected_files(
    tmp_path: Path,
) -> None:
    manifest = _load_raw_manifest()
    manifest["gold_readiness"]["status"] = "gold_ready"
    manifest["gold_readiness"]["blocking_dependencies"] = []
    manifest["artifact_profiles"]["chat"]["status"] = "verified"
    manifest["artifact_profiles"]["tokenizer"]["status"] = "ready"
    manifest["artifact_profiles"]["features"]["status"] = "ready"
    for seed in manifest["seeds"].values():
        for review_name in ("human_review", "license_review"):
            seed[review_name] = {
                "status": "confirmed",
                "blocking": False,
                "reason_code": "forged_review",
                "reviewed_by": "forged-reviewer",
                "reviewed_at": "2026-07-26T12:00:00+07:00",
            }
    for case_id, case in manifest["cases"].items():
        forged = {
            "gold_status": "gold_ready",
            "source_transcript": {"status": "reviewed"},
            "reviewed_mapping": {"status": "confirmed"},
            "attestation": {"status": "attested"},
            "chat_artifact": {"status": "verified"},
            "tokenizer_profile": {"status": "available"},
            "feature_expectations": [{"status": "available"}],
        }
        expected_path = tmp_path / "expected" / f"{case_id}.json"
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(json.dumps(forged), encoding="utf-8")
        case["expected_artifact"] = f"expected/{case_id}.json"
        case["expected_artifact_sha256"] = _sha256(expected_path)

    with pytest.raises(
        FixtureManifestError,
        match="gold_ready_requires_verified_files",
    ):
        validate_manifest(
            manifest,
            fixture_root=tmp_path,
            verify_files=False,
            require_gold_ready=True,
        )


def test_manifest_uses_frozen_contract_versions_and_task_dependencies() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)

    assert manifest["artifact_profiles"]["chat"] == {
        "subset_version": "lingualens-chat-v1.7.0",
        "parser_version": "lingualens-chat-parser-v1.7.0",
        "serializer_version": "lingualens-chat-serializer-v1.7.0",
        "status": "pending_task_10",
    }
    assert manifest["artifact_profiles"]["tokenizer"]["status"] == "pending_task_11"
    assert manifest["artifact_profiles"]["features"][
        "feature_version"
    ] == "descriptive-features-v1.7.0"
    assert manifest["artifact_profiles"]["features"]["status"] == "pending_task_11"
    assert manifest["gold_readiness"]["blocking_dependencies"] == [
        "human_spoken_content_review",
        "redistribution_license_review",
        "chat_gold_task_10",
        "tokenizer_profile_task_11",
        "feature_gold_task_11",
    ]


def test_gold_ready_cli_refuses_cleanly_without_a_traceback() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "scripts" / "generate_v170_golden_audio.py"),
            "--manifest",
            str(MANIFEST_PATH),
            "--output",
            str(REPOSITORY_ROOT / ".local" / "golden-audio" / "v1.7.0"),
            "--require-gold-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "gold_not_ready" in result.stderr
    assert "Traceback" not in result.stderr


def test_diarization_cases_have_two_and_three_real_acoustic_voice_sources() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    thai_english_tracks = manifest["seeds"]["thai_english"]["acoustic_tracks"]
    overlap_tracks = manifest["seeds"]["overlap"]["acoustic_tracks"]

    assert len({track["voice_identifier"] for track in thai_english_tracks}) == 2
    assert len({track["voice_identifier"] for track in overlap_tracks}) == 3
    assert manifest["cases"]["two_speakers_correct"]["source_seed_id"] == "thai_english"
    assert manifest["cases"]["more_than_two_speakers"]["source_seed_id"] == "overlap"
    expected = json.loads(
        (
            FIXTURE_ROOT
            / manifest["cases"]["more_than_two_speakers"]["expected_artifact"]
        ).read_text(encoding="utf-8")
    )
    assert expected["temporary_speaker_labels"] == ["SPK_01", "SPK_02", "SPK_03"]


def test_manifest_rejects_generated_filename_path_traversal() -> None:
    manifest = _load_raw_manifest()
    manifest["cases"]["thai_1m"]["generated_filename"] = "../victim.wav"

    with pytest.raises(FixtureManifestError, match="unsafe_generated_filename"):
        validate_manifest(manifest, fixture_root=FIXTURE_ROOT, verify_files=False)


def test_generator_rebuild_rejects_symlink_target_without_touching_victim(
    tmp_path: Path,
) -> None:
    victim = tmp_path / "victim.txt"
    victim.write_bytes(b"do-not-touch")
    target = tmp_path / "thai_1m-v1.7.0.wav"
    target.symlink_to(victim)

    with pytest.raises(FixtureManifestError, match="unsafe_output_target"):
        generate_fixtures(
            manifest_path=MANIFEST_PATH,
            output_dir=tmp_path,
            rebuild=True,
        )

    assert victim.read_bytes() == b"do-not-touch"
    assert target.is_symlink()


def test_generator_rejects_symlink_output_directory(tmp_path: Path) -> None:
    real_output = tmp_path / "real-output"
    real_output.mkdir()
    linked_output = tmp_path / "linked-output"
    linked_output.symlink_to(real_output, target_is_directory=True)

    with pytest.raises(FixtureManifestError, match="unsafe_output_directory"):
        generate_fixtures(
            manifest_path=MANIFEST_PATH,
            output_dir=linked_output,
            rebuild=False,
        )

    assert list(real_output.iterdir()) == []


def test_declared_soundfile_and_runtime_provenance_matches_test_environment() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    requirements = (REPOSITORY_ROOT / "requirements.txt").read_text(encoding="utf-8")
    runtime_matrix = manifest["generator"]["verified_runtime_matrix"]

    assert "soundfile==0.14.0" in requirements
    assert manifest["format_fixtures"]["mp3"]["decoder"] == {
        "package": "soundfile",
        "package_version": "0.14.0",
        "library": "libsndfile",
        "library_version": "1.2.2",
    }
    assert any(
        runtime["python_version"] == platform.python_version()
        and "manifest_validation_tests" in runtime["verified_roles"]
        and "long_fixture_generation" in runtime["verified_roles"]
        for runtime in runtime_matrix
    )


def test_mp3_fixture_is_verified_by_the_pinned_decoder() -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)
    fixture = manifest["format_fixtures"]["mp3"]
    fixture_path = FIXTURE_ROOT / fixture["path"]

    assert soundfile.__version__ == fixture["decoder"]["package_version"]
    assert soundfile.__libsndfile_version__ == fixture["decoder"]["library_version"]
    assert "MP3" in soundfile.available_formats()
    with soundfile.SoundFile(fixture_path) as decoded:
        assert decoded.frames == fixture["decoded"]["frame_count"]
        assert decoded.samplerate == fixture["decoded"]["sample_rate_hz"]
        assert decoded.channels == fixture["decoded"]["channels"]
        assert decoded.frames * 1000 // decoded.samplerate == fixture["decoded"]["duration_ms"]
    assert _sha256(fixture_path) == fixture["sha256"]
    assert fixture["source_seed_sha256"] == manifest["seeds"]["thai_only"]["sha256"]


def test_generator_writes_exact_duration_and_checksum_without_mutating_manifest(
    tmp_path: Path,
) -> None:
    before = MANIFEST_PATH.read_bytes()

    generated = generate_fixtures(
        manifest_path=MANIFEST_PATH,
        output_dir=tmp_path,
        rebuild=False,
    )

    assert MANIFEST_PATH.read_bytes() == before
    assert set(generated) == set(EXPECTED_DURATIONS_MS)
    manifest = _load_raw_manifest()
    for case_id, duration_ms in EXPECTED_DURATIONS_MS.items():
        output = generated[case_id]
        with wave.open(str(output), "rb") as audio:
            assert audio.getframerate() == 16_000
            assert audio.getnchannels() == 1
            assert audio.getsampwidth() == 2
            assert audio.getnframes() * 1000 // audio.getframerate() == duration_ms
        assert _sha256(output) == manifest["cases"][case_id]["generated_sha256"]


def test_generator_refuses_to_overwrite_unexpected_file_without_rebuild(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(
        manifest_path=MANIFEST_PATH,
        output_dir=tmp_path,
        rebuild=False,
    )
    target = generated["thai_1m"]
    target.write_bytes(b"unexpected")

    with pytest.raises(FixtureManifestError, match="unexpected_existing_checksum"):
        generate_fixtures(
            manifest_path=MANIFEST_PATH,
            output_dir=tmp_path,
            rebuild=False,
        )

    regenerated = generate_fixtures(
        manifest_path=MANIFEST_PATH,
        output_dir=tmp_path,
        rebuild=True,
    )
    assert _sha256(regenerated["thai_1m"]) == _load_raw_manifest()["cases"]["thai_1m"][
        "generated_sha256"
    ]
