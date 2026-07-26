#!/usr/bin/env python3
"""Validate and assemble the LinguaLens v1.7.0 synthetic audio fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any


SAMPLE_RATE_HZ = 16_000
SAMPLE_WIDTH_BYTES = 2
CHANNELS = 1
EXPECTED_DURATIONS_MS = {
    "thai_1m": 60_000,
    "thai_english_5m": 300_000,
    "thai_english_15m": 900_000,
    "thai_english_15m_plus_5s": 905_000,
}
REQUIRED_CASES = {
    *EXPECTED_DURATIONS_MS,
    "two_speakers_correct",
    "swapped_clusters",
    "unknown_speaker",
    "more_than_two_speakers",
    "diarization_unavailable",
    "overlapping_speech",
}
FORBIDDEN_METADATA_KEYS = {
    "patient_name",
    "child_name",
    "first_name",
    "last_name",
    "date_of_birth",
    "dob",
    "email",
    "phone",
    "address",
    "storage_key",
}
DIRECT_IDENTIFIER_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:\+?66|0)\d{8,9}\b"),
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class FixtureManifestError(ValueError):
    """Raised when a fixture or its manifest violates the frozen contract."""


def _fail(code: str, detail: str) -> None:
    raise FixtureManifestError(f"{code}: {detail}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_sha256(value: Any, field: str) -> None:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        _fail("invalid_checksum", field)


def _walk_for_identifiers(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.casefold() in FORBIDDEN_METADATA_KEYS:
                _fail("identifying_metadata", f"{path}.{key}")
            _walk_for_identifiers(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _walk_for_identifiers(nested, path=f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in DIRECT_IDENTIFIER_PATTERNS:
            if pattern.search(value):
                _fail("identifying_metadata", path)


def _resolve_fixture_path(fixture_root: Path, relative_path: str) -> Path:
    if (
        not relative_path
        or Path(relative_path).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(relative_path).parts)
    ):
        _fail("unsafe_fixture_path", relative_path)
    if any(token in Path(relative_path).name.casefold() for token in ("latest", "current")):
        _fail("mutable_filename", relative_path)
    resolved = (fixture_root / relative_path).resolve()
    try:
        resolved.relative_to(fixture_root.resolve())
    except ValueError:
        _fail("unsafe_fixture_path", relative_path)
    return resolved


def _require_fields(record: dict[str, Any], fields: set[str], context: str) -> None:
    missing = sorted(field for field in fields if record.get(field) in (None, ""))
    if missing:
        _fail("missing_provenance", f"{context}: {', '.join(missing)}")


def _validate_review_state(review: dict[str, Any], context: str) -> None:
    status = review.get("status")
    if status == "pending":
        if review.get("blocking") is not True:
            _fail("invalid_review_state", f"{context} pending review must block")
        if review.get("reviewed_by") or review.get("reviewed_at"):
            _fail("invalid_review_state", f"{context} pending review cannot name a reviewer")
        return
    if status == "confirmed":
        if review.get("blocking") is not False:
            _fail("invalid_review_state", f"{context} confirmed review cannot block")
        _require_fields(review, {"reviewed_by", "reviewed_at"}, context)
        return
    _fail("invalid_review_state", f"{context}: {status!r}")


def _validate_seed(
    seed_id: str,
    seed: dict[str, Any],
    *,
    fixture_root: Path,
    verify_files: bool,
) -> None:
    _require_fields(
        seed,
        {
            "path",
            "language",
            "source_script",
            "script_sha256",
            "sha256",
            "frame_count",
            "duration_ms",
            "pcm",
            "provenance",
            "human_review",
            "license_review",
        },
        f"seed {seed_id}",
    )
    provenance = seed["provenance"]
    _require_fields(
        provenance,
        {
            "tool",
            "tool_version",
            "voice_identifier",
            "generation_date",
            "license",
        },
        f"seed {seed_id} provenance",
    )
    _assert_sha256(seed["script_sha256"], f"seed {seed_id} script_sha256")
    _assert_sha256(seed["sha256"], f"seed {seed_id} sha256")
    script_bytes = seed["source_script"].encode("utf-8")
    if _sha256_bytes(script_bytes) != seed["script_sha256"]:
        _fail("checksum_mismatch", f"seed {seed_id} source script")
    pcm = seed["pcm"]
    if pcm != {
        "format": "wav_pcm_s16le",
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "channels": CHANNELS,
        "bits_per_sample": SAMPLE_WIDTH_BYTES * 8,
    }:
        _fail("pcm_mismatch", seed_id)
    if seed["duration_ms"] != seed["frame_count"] * 1000 // SAMPLE_RATE_HZ:
        _fail("duration_class_mismatch", f"seed {seed_id}")
    _validate_review_state(seed["human_review"], f"seed {seed_id} human_review")
    _validate_review_state(seed["license_review"], f"seed {seed_id} license_review")
    acoustic_tracks = seed.get("acoustic_tracks")
    if not isinstance(acoustic_tracks, list) or not acoustic_tracks:
        _fail("missing_provenance", f"seed {seed_id} acoustic_tracks")
    track_ids: set[str] = set()
    for track in acoustic_tracks:
        _require_fields(
            track,
            {
                "track_id",
                "voice_identifier",
                "start_frame",
                "end_frame",
                "script_role",
            },
            f"seed {seed_id} acoustic track",
        )
        if track["track_id"] in track_ids:
            _fail("duplicate_acoustic_track", f"{seed_id}.{track['track_id']}")
        track_ids.add(track["track_id"])
        if not (
            isinstance(track["start_frame"], int)
            and isinstance(track["end_frame"], int)
            and 0 <= track["start_frame"] < track["end_frame"] <= seed["frame_count"]
        ):
            _fail("invalid_acoustic_track_range", f"{seed_id}.{track['track_id']}")
        if track["voice_identifier"] not in provenance["voice_identifier"]:
            _fail("provenance_mismatch", f"{seed_id}.{track['track_id']} voice")

    seed_path = _resolve_fixture_path(fixture_root, seed["path"])
    if not verify_files:
        return
    if not seed_path.is_file():
        _fail("missing_fixture", seed["path"])
    if _sha256_file(seed_path) != seed["sha256"]:
        _fail("checksum_mismatch", seed["path"])
    with wave.open(str(seed_path), "rb") as audio:
        if (
            audio.getframerate() != SAMPLE_RATE_HZ
            or audio.getnchannels() != CHANNELS
            or audio.getsampwidth() != SAMPLE_WIDTH_BYTES
            or audio.getnframes() != seed["frame_count"]
        ):
            _fail("pcm_mismatch", seed["path"])
    regions = seed.get("assembly_regions")
    if regions is not None:
        required_regions = ("opening", "loop", "closing")
        previous_end = 0
        for region_name in required_regions:
            region = regions.get(region_name)
            if not isinstance(region, dict):
                _fail("invalid_assembly_region", f"{seed_id}.{region_name}")
            start = region.get("start_frame")
            end = region.get("end_frame")
            if not isinstance(start, int) or not isinstance(end, int):
                _fail("invalid_assembly_region", f"{seed_id}.{region_name}")
            if start != previous_end or not start < end <= seed["frame_count"]:
                _fail("invalid_assembly_region", f"{seed_id}.{region_name}")
            previous_end = end
        if previous_end != seed["frame_count"]:
            _fail("invalid_assembly_region", f"{seed_id}.closing")


def _canonical_record_checksum(record: dict[str, Any], checksum_field: str) -> str:
    payload = {key: value for key, value in record.items() if key != checksum_field}
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(serialized)


def _validate_structured_unavailable(
    record: dict[str, Any],
    *,
    context: str,
) -> None:
    if record.get("status") != "unavailable":
        _fail("invalid_pending_dependency", context)
    dependency = record.get("dependency")
    if not isinstance(dependency, dict):
        _fail("invalid_pending_dependency", context)
    _require_fields(
        dependency,
        {"reason_code", "required_artifact", "remediation"},
        context,
    )


def _validate_profile_keys(
    profile: dict[str, Any],
    *,
    expected_keys: set[str],
    context: str,
    ready: bool,
) -> None:
    missing = sorted(expected_keys - profile.keys())
    if missing:
        _fail("missing_provenance", f"{context}: {', '.join(missing)}")
    extra = sorted(profile.keys() - expected_keys)
    if extra:
        code = "invalid_ready_profile" if ready else "invalid_pending_profile"
        _fail(code, f"{context}: unexpected {', '.join(extra)}")


def _canonical_fixture_manifest_checksum(manifest: dict[str, Any]) -> str:
    """Hash immutable fixture definitions without readiness/profile cycles."""

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
    return _sha256_bytes(
        json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _validate_artifact_profiles(profiles: dict[str, Any]) -> None:
    chat = profiles.get("chat")
    tokenizer = profiles.get("tokenizer")
    features = profiles.get("features")
    if not all(isinstance(profile, dict) for profile in (chat, tokenizer, features)):
        _fail("missing_provenance", "artifact_profiles")
    _require_fields(
        chat,
        {"subset_version", "parser_version", "serializer_version", "status"},
        "CHAT profile",
    )
    if chat["status"] not in {"pending_task_10", "verified"}:
        _fail("invalid_profile_state", "CHAT profile")

    tokenizer_status = tokenizer.get("status")
    if tokenizer_status == "pending_task_11":
        _validate_profile_keys(
            tokenizer,
            expected_keys={
                "required_profile_id",
                "profile_version",
                "status",
                "dependency",
            },
            context="pending tokenizer profile",
            ready=False,
        )
        _validate_structured_unavailable(
            {
                "status": "unavailable",
                "dependency": tokenizer["dependency"],
            },
            context="pending tokenizer profile",
        )
    elif tokenizer_status == "ready":
        _validate_profile_keys(
            tokenizer,
            expected_keys={
                "status",
                "profile_id",
                "profile_version",
                "profile_checksum_sha256",
                "engine",
                "package_version",
                "segmentation_mode",
                "artifact_id",
                "artifact_checksum_sha256",
                "unicode_normalization",
                "punctuation_handling",
                "whitespace_handling",
                "filled_pause_handling",
                "repetition_handling",
                "partial_word_handling",
                "unintelligibility_marker_handling",
                "thai_english_code_switch_handling",
                "custom_vocabulary_version",
                "custom_vocabulary_checksum_sha256",
                "golden_fixture_manifest_checksum_sha256",
            },
            context="ready tokenizer profile",
            ready=True,
        )
        for field in (
            "profile_id",
            "engine",
            "package_version",
            "segmentation_mode",
            "artifact_id",
            "unicode_normalization",
            "punctuation_handling",
            "whitespace_handling",
            "filled_pause_handling",
            "repetition_handling",
            "partial_word_handling",
            "unintelligibility_marker_handling",
            "thai_english_code_switch_handling",
            "custom_vocabulary_version",
        ):
            if not isinstance(tokenizer[field], str) or not tokenizer[field]:
                _fail("missing_provenance", f"ready tokenizer {field}")
        if (
            not isinstance(tokenizer["profile_version"], int)
            or isinstance(tokenizer["profile_version"], bool)
            or tokenizer["profile_version"] < 1
        ):
            _fail("invalid_ready_profile", "ready tokenizer profile_version")
        if tokenizer["unicode_normalization"] != "NFC":
            _fail("invalid_ready_profile", "ready tokenizer requires NFC")
        for field in (
            "profile_checksum_sha256",
            "artifact_checksum_sha256",
            "custom_vocabulary_checksum_sha256",
            "golden_fixture_manifest_checksum_sha256",
        ):
            _assert_sha256(tokenizer[field], f"ready tokenizer {field}")
        canonical_profile_payload = {
            key: value
            for key, value in tokenizer.items()
            if key not in {"status", "profile_checksum_sha256"}
        }
        canonical_profile_checksum = _sha256_bytes(
            json.dumps(
                canonical_profile_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if tokenizer["profile_checksum_sha256"] != canonical_profile_checksum:
            _fail(
                "checksum_mismatch",
                "ready tokenizer canonical profile checksum",
            )
        if (
            tokenizer["custom_vocabulary_version"] == "not_used"
            and tokenizer["custom_vocabulary_checksum_sha256"]
            != _sha256_bytes(b"")
        ):
            _fail(
                "invalid_ready_profile",
                "not_used custom vocabulary must use the empty payload checksum",
            )
    else:
        _fail("invalid_profile_state", "tokenizer profile")

    feature_status = features.get("status")
    if feature_status == "pending_task_11":
        _validate_profile_keys(
            features,
            expected_keys={
                "feature_version",
                "status",
                "dependency",
            },
            context="pending feature profile",
            ready=False,
        )
        _validate_structured_unavailable(
            {
                "status": "unavailable",
                "dependency": features["dependency"],
            },
            context="pending feature profile",
        )
    elif feature_status == "ready":
        _validate_profile_keys(
            features,
            expected_keys={
                "status",
                "feature_version",
                "algorithm_version",
                "configuration_version",
                "configuration_checksum_sha256",
                "tokenizer_profile_id",
                "tokenizer_profile_version",
                "tokenizer_profile_checksum_sha256",
            },
            context="ready feature profile",
            ready=True,
        )
        for field in (
            "feature_version",
            "algorithm_version",
            "configuration_version",
            "tokenizer_profile_id",
        ):
            if not isinstance(features[field], str) or not features[field]:
                _fail("missing_provenance", f"ready features {field}")
        if (
            not isinstance(features["tokenizer_profile_version"], int)
            or isinstance(features["tokenizer_profile_version"], bool)
            or features["tokenizer_profile_version"] < 1
        ):
            _fail(
                "invalid_ready_profile",
                "ready features tokenizer_profile_version",
            )
        for field in (
            "configuration_checksum_sha256",
            "tokenizer_profile_checksum_sha256",
        ):
            _assert_sha256(features[field], f"ready features {field}")
        if tokenizer_status != "ready":
            _fail(
                "invalid_ready_profile",
                "ready feature profile requires ready tokenizer profile",
            )
        tokenizer_relation = {
            "tokenizer_profile_id": tokenizer["profile_id"],
            "tokenizer_profile_version": tokenizer["profile_version"],
            "tokenizer_profile_checksum_sha256": tokenizer[
                "profile_checksum_sha256"
            ],
        }
        if any(
            features[field] != value
            for field, value in tokenizer_relation.items()
        ):
            _fail(
                "provenance_mismatch",
                "feature profile tokenizer relation",
            )
    else:
        _fail("invalid_profile_state", "feature profile")


def _validate_expected_state(
    case_id: str,
    expected: dict[str, Any],
    *,
    case: dict[str, Any],
) -> str:
    status = expected["gold_status"]
    rejection_expected = (
        case.get("intake_expectation") == "audio_duration_limit_exceeded"
    )
    if status == "scaffold_pending_external_review":
        if (
            expected["source_transcript"].get("status") != "pending_human_review"
            or expected["reviewed_mapping"].get("status")
            != "draft_pending_human_review"
            or expected["attestation"].get("status") != "blocked"
            or expected["chat_artifact"].get("status") != "unavailable"
            or expected["tokenizer_profile"].get("status") != "unavailable"
            or any(
                feature.get("status") != "unavailable"
                for feature in expected["feature_expectations"]
            )
        ):
            _fail("invalid_scaffold_state", case_id)
        return status
    if status == "verified_rejection":
        if not rejection_expected:
            _fail("invalid_rejection_state", f"{case_id} is intake-eligible")
        if (
            expected["source_transcript"].get("status") != "not_created"
            or expected["reviewed_mapping"].get("status") != "not_applicable"
            or expected["reviewed_mapping"].get("entries") != []
            or expected["attestation"].get("status") != "not_created"
            or expected["chat_artifact"].get("status") != "unavailable"
            or expected["tokenizer_profile"].get("status") != "unavailable"
            or any(
                feature.get("status") != "unavailable"
                for feature in expected["feature_expectations"]
            )
        ):
            _fail("invalid_rejection_state", case_id)
        return status
    if status == "gold_ready":
        if rejection_expected:
            _fail(
                "invalid_rejection_state",
                f"{case_id} cannot fabricate post-intake artifacts",
            )
        if (
            expected["source_transcript"].get("status") != "reviewed"
            or expected["reviewed_mapping"].get("status") != "confirmed"
            or expected["attestation"].get("status") != "attested"
            or expected["chat_artifact"].get("status") != "verified"
            or expected["tokenizer_profile"].get("status") != "available"
            or any(
                feature.get("status")
                not in {"available", "insufficient_data", "experimental"}
                for feature in expected["feature_expectations"]
            )
        ):
            _fail("invalid_ready_state", case_id)
        return status
    _fail("invalid_gold_status", case_id)


def validate_expected_gold(
    case_id: str,
    expected: dict[str, Any],
    *,
    case: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    """Validate exact scaffold gold without claiming external review occurred."""

    required = {
        "case_id",
        "gold_contract_version",
        "gold_status",
        "source_provenance",
        "source_transcript",
        "temporary_speaker_labels",
        "beginning_anchor",
        "ending_anchor",
        "accepted_timestamp_bounds",
        "reviewed_mapping",
        "attestation",
        "chat_artifact",
        "tokenizer_profile",
        "feature_expectations",
        "known_limitations",
    }
    missing = sorted(required - expected.keys())
    if missing:
        _fail("missing_expected_field", f"{case_id}: {', '.join(missing)}")
    if expected["case_id"] != case_id:
        _fail("expected_case_mismatch", case_id)
    if expected["gold_contract_version"] != "v1.7.0-exact-scaffold-1":
        _fail("expected_contract_mismatch", case_id)
    expected_state = _validate_expected_state(case_id, expected, case=case)
    ready_state = expected_state == "gold_ready"
    rejection_state = expected_state == "verified_rejection"

    profiles = manifest.get("artifact_profiles")
    if not isinstance(profiles, dict):
        _fail("missing_provenance", "artifact_profiles")
    _validate_artifact_profiles(profiles)
    if (
        profiles["tokenizer"]["status"] == "ready"
        and profiles["tokenizer"][
            "golden_fixture_manifest_checksum_sha256"
        ]
        != _canonical_fixture_manifest_checksum(manifest)
    ):
        _fail(
            "checksum_mismatch",
            "ready tokenizer golden fixture manifest",
        )
    transcript = expected["source_transcript"]
    _require_fields(
        transcript,
        {"version", "status", "checksum_sha256", "segment_plan"},
        f"{case_id} transcript",
    )
    if transcript["version"] != 1:
        _fail("provenance_mismatch", f"{case_id} transcript version")
    _assert_sha256(
        transcript["checksum_sha256"],
        f"{case_id} transcript checksum",
    )

    plan = transcript["segment_plan"]
    if plan.get("sample_rate_hz") != SAMPLE_RATE_HZ:
        _fail("timestamp_basis_mismatch", case_id)
    sequence = plan.get("sequence")
    if not isinstance(sequence, list) or not sequence:
        _fail("segment_plan_coverage", case_id)
    target_frames = case.get("expected_frame_count")
    if target_frames is None:
        source_seed_id = case.get("source_seed_id")
        if source_seed_id not in manifest["seeds"]:
            _fail("source_seed_mismatch", case_id)
        target_frames = manifest["seeds"][source_seed_id]["frame_count"]
    previous_end = 0
    seen_ids: set[str] = set()
    referenced_speakers: set[str] = set()
    for index, component in enumerate(sequence):
        start_frame = component.get("start_frame")
        end_frame = component.get("end_frame")
        if not isinstance(start_frame, int) or not isinstance(end_frame, int):
            _fail("segment_plan_coverage", f"{case_id}[{index}]")
        if index == 0 and start_frame != 0:
            _fail("segment_plan_order", case_id)
        if start_frame < previous_end:
            _fail("segment_plan_order", case_id)
        if start_frame != previous_end or end_frame <= start_frame:
            _fail("segment_plan_coverage", case_id)
        kind = component.get("kind")
        if kind == "segment":
            _require_fields(
                component,
                {"segment_id", "speaker", "text"},
                f"{case_id} segment",
            )
            if component["segment_id"] in seen_ids:
                _fail("duplicate_segment_gold", component["segment_id"])
            seen_ids.add(component["segment_id"])
            referenced_speakers.add(component["speaker"])
        elif kind == "repeat":
            _require_fields(
                component,
                {
                    "segment_id_format",
                    "repeat_count",
                    "frame_stride",
                    "template_segments",
                },
                f"{case_id} repeat",
            )
            if "*" in component["segment_id_format"]:
                _fail("segment_plan_order", f"{case_id} wildcard")
            if (
                not isinstance(component["repeat_count"], int)
                or component["repeat_count"] <= 0
                or end_frame - start_frame
                != component["repeat_count"] * component["frame_stride"]
            ):
                _fail("segment_plan_coverage", f"{case_id} repeat")
            templates = component["template_segments"]
            if not isinstance(templates, list) or not templates:
                _fail("segment_plan_coverage", f"{case_id} templates")
            for template in templates:
                _require_fields(
                    template,
                    {
                        "segment_id_suffix",
                        "speaker",
                        "text",
                        "relative_start_frame",
                        "relative_end_frame",
                    },
                    f"{case_id} repeat template",
                )
                if not (
                    0 <= template["relative_start_frame"]
                    < template["relative_end_frame"]
                    <= component["frame_stride"]
                ):
                    _fail("segment_plan_coverage", f"{case_id} repeat template")
                referenced_speakers.add(template["speaker"])
        elif kind == "parallel":
            templates = component.get("template_segments")
            if not isinstance(templates, list) or len(templates) < 2:
                _fail("segment_plan_coverage", f"{case_id} parallel")
            span = end_frame - start_frame
            for template in templates:
                _require_fields(
                    template,
                    {
                        "segment_id_suffix",
                        "speaker",
                        "text",
                        "relative_start_frame",
                        "relative_end_frame",
                    },
                    f"{case_id} parallel template",
                )
                if not (
                    0 <= template["relative_start_frame"]
                    < template["relative_end_frame"]
                    <= span
                ):
                    _fail("segment_plan_coverage", f"{case_id} parallel template")
                referenced_speakers.add(template["speaker"])
        elif kind != "silence":
            _fail("invalid_segment_kind", f"{case_id}: {kind!r}")
        previous_end = end_frame
    if previous_end != target_frames:
        _fail("segment_plan_coverage", case_id)
    if (
        _canonical_record_checksum(transcript, "checksum_sha256")
        != transcript["checksum_sha256"]
    ):
        _fail("checksum_mismatch", f"{case_id} transcript plan")

    bounds = expected["accepted_timestamp_bounds"]
    if ready_state:
        expected_tolerance_status = "verified"
    elif rejection_state:
        expected_tolerance_status = "not_applicable_due_to_intake_rejection"
    else:
        expected_tolerance_status = "pending_human_review"
    if bounds != {
        "basis": "exact_frames",
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "coverage_start_frame": 0,
        "coverage_end_frame": target_frames,
        "asr_tolerance_status": expected_tolerance_status,
    }:
        _fail("timestamp_basis_mismatch", case_id)
    if expected["beginning_anchor"]["start_frame"] != 0:
        _fail("segment_plan_coverage", f"{case_id} beginning anchor")
    if expected["ending_anchor"]["end_frame"] != target_frames:
        _fail("segment_plan_coverage", f"{case_id} ending anchor")

    mapping = expected["reviewed_mapping"]
    _require_fields(
        mapping,
        {
            "mapping_id",
            "mapping_version",
            "transcript_version",
            "status",
            "entries",
        },
        f"{case_id} mapping",
    )
    if (
        mapping["mapping_version"] != 1
        or mapping["transcript_version"] != transcript["version"]
    ):
        _fail("provenance_mismatch", f"{case_id} mapping")
    if ready_state and mapping["status"] != "confirmed":
        _fail("invalid_ready_state", f"{case_id} mapping")
    if rejection_state and mapping["status"] != "not_applicable":
        _fail("invalid_rejection_state", f"{case_id} mapping")
    if (
        not ready_state
        and not rejection_state
        and mapping["status"] != "draft_pending_human_review"
    ):
        _fail("invalid_scaffold_state", f"{case_id} mapping")
    entries = mapping["entries"]
    if not isinstance(entries, list) or (not rejection_state and not entries):
        _fail("missing_provenance", f"{case_id} mapping entries")
    labels = expected["temporary_speaker_labels"]
    if not isinstance(labels, list) or not labels:
        _fail("missing_provenance", f"{case_id} speaker labels")
    if len(labels) != len(set(labels)):
        _fail("duplicate_speaker_label", case_id)
    if referenced_speakers != set(labels):
        _fail("speaker_reference_mismatch", case_id)
    if rejection_state:
        if entries:
            _fail("invalid_rejection_state", f"{case_id} mapping entries")
    else:
        mapping_speaker_ids = [
            entry.get("temporary_speaker_id") for entry in entries
        ]
        if len(mapping_speaker_ids) != len(set(mapping_speaker_ids)):
            _fail("duplicate_mapping_speaker", case_id)
        mapped_speakers = set(mapping_speaker_ids)
        if mapped_speakers != set(labels):
            _fail("speaker_reference_mismatch", case_id)
        code_field = (
            "confirmed_chat_code" if ready_state else "proposed_chat_code"
        )
        chat_codes: list[str] = []
        required_roles: list[str] = []
        for entry in entries:
            _require_fields(
                entry,
                {
                    "temporary_speaker_id",
                    code_field,
                    "participant_role",
                    "review_status",
                },
                f"{case_id} mapping entry",
            )
            chat_codes.append(entry[code_field])
            if entry["participant_role"] in {
                "synthetic_target",
                "synthetic_partner",
            }:
                required_roles.append(entry["participant_role"])
        if len(chat_codes) != len(set(chat_codes)):
            _fail("ambiguous_chat_code", case_id)
        if len(required_roles) != len(set(required_roles)):
            _fail("ambiguous_required_role", case_id)

    attestation = expected["attestation"]
    _require_fields(
        attestation,
        {
            "attestation_id",
            "attestation_version",
            "status",
            "transcript_version",
            "mapping_version",
            "reason_code",
        },
        f"{case_id} attestation",
    )
    if (
        attestation["transcript_version"] != transcript["version"]
        or attestation["mapping_version"] != mapping["mapping_version"]
    ):
        _fail("provenance_mismatch", f"{case_id} attestation")

    chat = expected["chat_artifact"]
    for field in ("subset_version", "parser_version", "serializer_version"):
        if chat.get(field) != profiles["chat"][field]:
            _fail("provenance_mismatch", f"{case_id} CHAT {field}")
    tokenizer = expected["tokenizer_profile"]
    tokenizer_profile = profiles["tokenizer"]
    if ready_state:
        expected_ready_tokenizer = {
            key: value
            for key, value in tokenizer_profile.items()
            if key != "status"
        }
        expected_ready_tokenizer["status"] = "available"
        if tokenizer != expected_ready_tokenizer:
            _fail("provenance_mismatch", f"{case_id} ready tokenizer")
    elif rejection_state:
        selected_profile_id = tokenizer_profile.get(
            "profile_id",
            tokenizer_profile.get("required_profile_id"),
        )
        if tokenizer.get("required_profile_id") != selected_profile_id:
            _fail("provenance_mismatch", f"{case_id} rejected tokenizer")
    elif (
        tokenizer_profile["status"] != "pending_task_11"
        or tokenizer.get("required_profile_id")
        != tokenizer_profile["required_profile_id"]
        or tokenizer.get("profile_version")
        != tokenizer_profile["profile_version"]
    ):
        _fail("provenance_mismatch", f"{case_id} pending tokenizer")
    features = expected["feature_expectations"]
    if not isinstance(features, list) or not features:
        _fail("missing_provenance", f"{case_id} feature expectations")
    for feature in features:
        _require_fields(
            feature,
            {
                "feature_id",
                "feature_version",
                "status",
                "reason_code",
                "remediation",
                "numerator",
                "denominator",
                "value",
                "tolerance",
                "exclusions",
            },
            f"{case_id} feature",
        )
        if feature["feature_version"] != profiles["features"]["feature_version"]:
            _fail("provenance_mismatch", f"{case_id} feature")
        if ready_state:
            for field, value in profiles["features"].items():
                if field != "status" and feature.get(field) != value:
                    _fail(
                        "provenance_mismatch",
                        f"{case_id} feature {field}",
                    )

    if ready_state:
        if transcript["status"] != "reviewed":
            _fail("invalid_ready_state", f"{case_id} transcript")
        if mapping["status"] != "confirmed" or any(
            entry["review_status"] != "confirmed" for entry in entries
        ):
            _fail("invalid_ready_state", f"{case_id} mapping")
        if (
            attestation["status"] != "attested"
            or not isinstance(attestation["attestation_version"], int)
            or attestation["attestation_version"] < 1
        ):
            _fail("invalid_ready_state", f"{case_id} attestation")
        if chat.get("status") != "verified":
            _fail("invalid_ready_state", f"{case_id} CHAT")
        for field in ("canonical_checksum_sha256", "artifact_checksum_sha256"):
            _assert_sha256(chat.get(field), f"{case_id} CHAT {field}")
        if tokenizer.get("status") != "available":
            _fail("invalid_ready_state", f"{case_id} tokenizer")
        if any(
            feature["status"]
            not in {"available", "insufficient_data", "experimental"}
            for feature in features
        ):
            _fail("invalid_ready_state", f"{case_id} features")
        if any(
            limitation.get("severity") == "blocking"
            for limitation in expected["known_limitations"]
        ):
            _fail("invalid_ready_state", f"{case_id} limitations")
    elif rejection_state:
        if transcript["status"] != "not_created":
            _fail("invalid_rejection_state", f"{case_id} transcript")
        if mapping["status"] != "not_applicable" or entries:
            _fail("invalid_rejection_state", f"{case_id} mapping")
        if (
            attestation["status"] != "not_created"
            or attestation["attestation_version"] != 0
            or attestation["reason_code"] != "audio_duration_limit_exceeded"
        ):
            _fail("invalid_rejection_state", f"{case_id} attestation")
        _validate_structured_unavailable(
            chat,
            context=f"{case_id} rejected CHAT",
        )
        _validate_structured_unavailable(
            tokenizer,
            context=f"{case_id} rejected tokenizer",
        )
        if (
            chat["dependency"]["reason_code"]
            != "audio_duration_limit_exceeded"
            or tokenizer["dependency"]["reason_code"]
            != "audio_duration_limit_exceeded"
        ):
            _fail("invalid_rejection_state", f"{case_id} downstream reason")
        if any(
            feature["status"] != "unavailable"
            or feature["reason_code"] != "audio_duration_limit_exceeded"
            or not all(
                feature[field] == {"state": "not_computed"}
                for field in ("numerator", "denominator", "value", "tolerance")
            )
            for feature in features
        ):
            _fail("invalid_rejection_state", f"{case_id} features")
        if expected["known_limitations"] != [
            {
                "code": "audio_duration_limit_exceeded",
                "severity": "integrity_blocker",
                "configured_limit_ms": 900_000,
                "actual_ms": case["expected_duration_ms"],
            }
        ]:
            _fail("invalid_rejection_state", f"{case_id} rejection evidence")
    else:
        if transcript["status"] != "pending_human_review":
            _fail("invalid_scaffold_state", f"{case_id} transcript")
        if mapping["status"] != "draft_pending_human_review" or any(
            entry["review_status"] != "pending_human_review" for entry in entries
        ):
            _fail("invalid_scaffold_state", f"{case_id} mapping")
        if (
            attestation["status"] != "blocked"
            or attestation["attestation_version"] != 0
        ):
            _fail("invalid_scaffold_state", f"{case_id} attestation")
        _validate_structured_unavailable(chat, context=f"{case_id} CHAT")
        _validate_structured_unavailable(
            tokenizer,
            context=f"{case_id} tokenizer",
        )
        if tokenizer.get("profile_version") != profiles["tokenizer"][
            "profile_version"
        ]:
            _fail("provenance_mismatch", f"{case_id} tokenizer profile version")
        if any(
            feature["status"] != "unavailable"
            or not all(
                feature[field] == {"state": "not_computed"}
                for field in ("numerator", "denominator", "value", "tolerance")
            )
            for feature in features
        ):
            _fail("invalid_scaffold_state", f"{case_id} features")

    source = expected["source_provenance"]
    _require_fields(
        source,
        {"asset_kind", "asset_id", "checksum_sha256", "fixture_version"},
        f"{case_id} source provenance",
    )
    if source["fixture_version"] != manifest["fixture_version"]:
        _fail("provenance_mismatch", f"{case_id} fixture version")
    expected_source_checksum = (
        case["generated_sha256"]
        if source["asset_kind"] == "generated_fixture"
        else manifest["seeds"][case["source_seed_id"]]["sha256"]
    )
    if source["checksum_sha256"] != expected_source_checksum:
        _fail("provenance_mismatch", f"{case_id} source checksum")
    _walk_for_identifiers(expected, path=f"expected.{case_id}")


def _validate_expected_artifact(
    case_id: str,
    path: Path,
    *,
    case: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    if not path.is_file():
        _fail("missing_expected_artifact", case_id)
    if _sha256_file(path) != case.get("expected_artifact_sha256"):
        _fail("checksum_mismatch", f"{case_id} expected artifact")
    expected = json.loads(path.read_text(encoding="utf-8"))
    validate_expected_gold(case_id, expected, case=case, manifest=manifest)


def validate_manifest(
    manifest: dict[str, Any],
    *,
    fixture_root: Path,
    verify_files: bool = True,
    require_gold_ready: bool = False,
) -> None:
    """Validate privacy, provenance, checksums, duration classes, and artifacts."""

    if require_gold_ready and not verify_files:
        _fail(
            "gold_ready_requires_verified_files",
            "strict readiness cannot skip file, hash, structure, or provenance checks",
        )
    _walk_for_identifiers(manifest)
    if manifest.get("schema_version") != "lingualens-audio-fixture-manifest-v1":
        _fail("schema_version_mismatch", str(manifest.get("schema_version")))
    if manifest.get("fixture_version") != "v1.7.0":
        _fail("fixture_version_mismatch", str(manifest.get("fixture_version")))
    profiles = manifest.get("artifact_profiles")
    if not isinstance(profiles, dict):
        _fail("missing_provenance", "artifact_profiles")
    _validate_artifact_profiles(profiles)
    if (
        profiles["tokenizer"]["status"] == "ready"
        and profiles["tokenizer"][
            "golden_fixture_manifest_checksum_sha256"
        ]
        != _canonical_fixture_manifest_checksum(manifest)
    ):
        _fail(
            "checksum_mismatch",
            "ready tokenizer golden fixture manifest",
        )
    readiness = manifest.get("gold_readiness")
    if not isinstance(readiness, dict):
        _fail("missing_provenance", "gold_readiness")
    _require_fields(
        readiness,
        {"status", "blocking_dependencies", "remediation"},
        "gold_readiness",
    )

    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        _fail("missing_provenance", "generator")
    _require_fields(generator, {"path", "sha256", "python_wave_module"}, "generator")
    runtime_matrix = generator.get("verified_runtime_matrix")
    if not isinstance(runtime_matrix, list) or not runtime_matrix:
        _fail("missing_provenance", "generator verified_runtime_matrix")
    for runtime in runtime_matrix:
        _require_fields(
            runtime,
            {
                "python_version",
                "implementation",
                "verified_roles",
                "evidence",
            },
            "generator runtime",
        )
        if (
            runtime["implementation"] != "CPython"
            or not isinstance(runtime["verified_roles"], list)
            or not runtime["verified_roles"]
        ):
            _fail("invalid_runtime_provenance", str(runtime))
    _assert_sha256(generator["sha256"], "generator.sha256")
    generator_relative_path = Path(generator["path"])
    if (
        generator_relative_path.is_absolute()
        or any(part in {"", ".", ".."} for part in generator_relative_path.parts)
    ):
        _fail("unsafe_fixture_path", generator["path"])
    repository_root = fixture_root.resolve().parents[3]
    generator_path = (repository_root / generator_relative_path).resolve()
    try:
        generator_path.relative_to(repository_root)
    except ValueError:
        _fail("unsafe_fixture_path", generator["path"])
    if verify_files:
        if not generator_path.is_file():
            _fail("missing_fixture", generator["path"])
        if _sha256_file(generator_path) != generator["sha256"]:
            _fail("checksum_mismatch", generator["path"])

    seeds = manifest.get("seeds")
    if not isinstance(seeds, dict) or set(seeds) != {
        "thai_only",
        "thai_english",
        "overlap",
    }:
        _fail("seed_set_mismatch", str(sorted(seeds or {})))
    for seed_id, seed in seeds.items():
        _validate_seed(
            seed_id,
            seed,
            fixture_root=fixture_root,
            verify_files=verify_files,
        )

    cases = manifest.get("cases")
    if not isinstance(cases, dict) or not REQUIRED_CASES <= set(cases):
        _fail("missing_required_case", str(sorted(REQUIRED_CASES - set(cases or {}))))
    for case_id, expected_duration_ms in EXPECTED_DURATIONS_MS.items():
        case = cases[case_id]
        if case.get("expected_duration_ms") != expected_duration_ms:
            _fail("duration_class_mismatch", case_id)
        expected_frames = expected_duration_ms * SAMPLE_RATE_HZ // 1000
        if case.get("expected_frame_count") != expected_frames:
            _fail("duration_class_mismatch", f"{case_id} frames")
        _assert_sha256(case.get("generated_sha256"), f"case {case_id} generated_sha256")
        filename = case.get("generated_filename")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename in {".", ".."}
        ):
            _fail("unsafe_generated_filename", str(filename))
        if filename != f"{case_id}-v1.7.0.wav":
            _fail("mutable_filename", str(filename))
        assembly = case.get("assembly")
        if not isinstance(assembly, dict) or assembly.get("seed_id") not in seeds:
            _fail("invalid_assembly", case_id)
        if not isinstance(assembly.get("inter_repeat_silence_frames"), int):
            _fail("invalid_assembly", case_id)
        intake_expectation = case.get("intake_expectation")
        if case_id == "thai_english_15m_plus_5s":
            if intake_expectation != "audio_duration_limit_exceeded":
                _fail("intake_expectation_mismatch", case_id)
        elif intake_expectation is not None:
            _fail("intake_expectation_mismatch", case_id)

    for case_id in REQUIRED_CASES:
        case = cases[case_id]
        expected_path = _resolve_fixture_path(fixture_root, case["expected_artifact"])
        if verify_files:
            _validate_expected_artifact(
                case_id,
                expected_path,
                case=case,
                manifest=manifest,
            )

    format_fixtures = manifest.get("format_fixtures")
    if not isinstance(format_fixtures, dict) or set(format_fixtures) != {"mp3"}:
        _fail("format_fixture_mismatch", "mp3")
    mp3 = format_fixtures["mp3"]
    _require_fields(
        mp3,
        {
            "path",
            "sha256",
            "source_seed_id",
            "source_seed_sha256",
            "encoder",
            "decoder",
            "decoded",
        },
        "MP3 fixture",
    )
    _require_fields(
        mp3["encoder"],
        {
            "package",
            "package_version",
            "library",
            "library_version",
            "format",
            "subtype",
            "compression_level",
            "bitrate_mode",
        },
        "MP3 encoder",
    )
    _require_fields(
        mp3["decoder"],
        {"package", "package_version", "library", "library_version"},
        "MP3 decoder",
    )
    _require_fields(
        mp3["decoded"],
        {"frame_count", "duration_ms", "sample_rate_hz", "channels"},
        "MP3 decoded metadata",
    )
    _assert_sha256(mp3["sha256"], "MP3 sha256")
    if mp3["source_seed_id"] not in seeds:
        _fail("source_seed_mismatch", str(mp3["source_seed_id"]))
    if mp3["source_seed_sha256"] != seeds[mp3["source_seed_id"]]["sha256"]:
        _fail("checksum_mismatch", "MP3 source seed")
    mp3_path = _resolve_fixture_path(fixture_root, mp3["path"])
    if verify_files:
        if not mp3_path.is_file():
            _fail("missing_fixture", mp3["path"])
        if _sha256_file(mp3_path) != mp3["sha256"]:
            _fail("checksum_mismatch", mp3["path"])
    if require_gold_ready:
        blockers = list(readiness["blocking_dependencies"])
        blockers.extend(
            f"{seed_id}.{review_name}"
            for seed_id, seed in seeds.items()
            for review_name in ("human_review", "license_review")
            if seed[review_name]["status"] != "confirmed"
        )
        for profile_name in ("chat", "tokenizer", "features"):
            if profiles[profile_name]["status"] not in {"ready", "verified"}:
                blockers.append(f"artifact_profiles.{profile_name}")
        for case_id in REQUIRED_CASES:
            case = cases[case_id]
            expected_path = _resolve_fixture_path(
                fixture_root,
                case["expected_artifact"],
            )
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            if (
                case.get("intake_expectation")
                == "audio_duration_limit_exceeded"
            ):
                if expected["gold_status"] != "verified_rejection":
                    blockers.append(f"{case_id}.rejection_status")
                if expected["source_transcript"]["status"] != "not_created":
                    blockers.append(f"{case_id}.transcript_must_not_exist")
                if expected["reviewed_mapping"]["status"] != "not_applicable":
                    blockers.append(f"{case_id}.speaker_mapping_must_not_exist")
                if expected["attestation"]["status"] != "not_created":
                    blockers.append(f"{case_id}.attestation_must_not_exist")
                if expected["chat_artifact"]["status"] != "unavailable":
                    blockers.append(f"{case_id}.chat_must_not_exist")
                if expected["tokenizer_profile"]["status"] != "unavailable":
                    blockers.append(f"{case_id}.tokenizer_must_not_run")
                if any(
                    feature["status"] != "unavailable"
                    for feature in expected["feature_expectations"]
                ):
                    blockers.append(f"{case_id}.features_must_not_run")
                continue
            if expected["gold_status"] != "gold_ready":
                blockers.append(f"{case_id}.gold_status")
            if expected["source_transcript"]["status"] != "reviewed":
                blockers.append(f"{case_id}.transcript")
            if expected["reviewed_mapping"]["status"] != "confirmed":
                blockers.append(f"{case_id}.speaker_mapping")
            if expected["attestation"]["status"] != "attested":
                blockers.append(f"{case_id}.attestation")
            if expected["chat_artifact"]["status"] != "verified":
                blockers.append(f"{case_id}.chat")
            if expected["tokenizer_profile"]["status"] != "available":
                blockers.append(f"{case_id}.tokenizer")
            if any(
                feature["status"] not in {
                    "available",
                    "insufficient_data",
                    "experimental",
                }
                for feature in expected["feature_expectations"]
            ):
                blockers.append(f"{case_id}.features")
        if readiness["status"] != "gold_ready":
            blockers.insert(0, "gold_readiness.status")
        if blockers:
            _fail("gold_not_ready", ", ".join(dict.fromkeys(blockers)))


def load_and_validate_manifest(
    manifest_path: Path,
    *,
    require_gold_ready: bool = False,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(
        manifest,
        fixture_root=manifest_path.parent,
        require_gold_ready=require_gold_ready,
    )
    return manifest


def _read_seed_frames(path: Path) -> bytes:
    with wave.open(str(path), "rb") as source:
        if (
            source.getnchannels() != CHANNELS
            or source.getsampwidth() != SAMPLE_WIDTH_BYTES
            or source.getframerate() != SAMPLE_RATE_HZ
        ):
            _fail("pcm_mismatch", str(path))
        return source.readframes(source.getnframes())


def _assemble_case(
    *,
    seed_path: Path,
    seed: dict[str, Any],
    target_frames: int,
    inter_repeat_silence_frames: int,
) -> bytes:
    source = _read_seed_frames(seed_path)
    regions = seed["assembly_regions"]

    def region_bytes(region_name: str) -> bytes:
        region = regions[region_name]
        start = region["start_frame"] * SAMPLE_WIDTH_BYTES
        end = region["end_frame"] * SAMPLE_WIDTH_BYTES
        return source[start:end]

    opening = region_bytes("opening")
    loop = region_bytes("loop")
    closing = region_bytes("closing")
    opening_frames = len(opening) // SAMPLE_WIDTH_BYTES
    closing_frames = len(closing) // SAMPLE_WIDTH_BYTES
    if opening_frames + closing_frames > target_frames:
        _fail("target_too_short", str(target_frames))

    middle_frames = target_frames - opening_frames - closing_frames
    silence = b"\x00" * inter_repeat_silence_frames * SAMPLE_WIDTH_BYTES
    loop_with_silence = loop + silence
    loop_frames = len(loop_with_silence) // SAMPLE_WIDTH_BYTES
    if loop_frames <= 0:
        _fail("invalid_assembly", "empty loop")
    repeated_count, remainder_frames = divmod(middle_frames, loop_frames)
    middle = loop_with_silence * repeated_count
    if remainder_frames:
        middle += b"\x00" * remainder_frames * SAMPLE_WIDTH_BYTES
    result = opening + middle + closing
    if len(result) != target_frames * SAMPLE_WIDTH_BYTES:
        _fail("generated_frame_mismatch", str(target_frames))
    return result


def _write_wave(path: Path, frames: bytes) -> None:
    with wave.open(str(path), "wb") as target:
        target.setnchannels(CHANNELS)
        target.setsampwidth(SAMPLE_WIDTH_BYTES)
        target.setframerate(SAMPLE_RATE_HZ)
        target.writeframes(frames)


def _prepare_output_directory(output_dir: Path) -> Path:
    output_dir = output_dir.absolute()
    for candidate in (output_dir, *output_dir.parents):
        try:
            metadata = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            _fail("unsafe_output_directory", f"symlink component: {candidate}")
        if not stat.S_ISDIR(metadata.st_mode):
            _fail("unsafe_output_directory", f"non-directory component: {candidate}")
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = output_dir.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        _fail("unsafe_output_directory", str(output_dir))
    return output_dir


def _regular_target_identity(path: Path) -> tuple[int, int] | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        _fail("unsafe_output_target", str(path))
    return (metadata.st_dev, metadata.st_ino)


def _write_verified_atomic_wave(
    *,
    output_path: Path,
    frames: bytes,
    expected_frame_count: int,
    expected_checksum: str,
    accepted_target_identity: tuple[int, int] | None,
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_metadata = temporary_path.lstat()
        if not stat.S_ISREG(temporary_metadata.st_mode):
            _fail("unsafe_output_target", str(temporary_path))
        _write_wave(temporary_path, frames)
        with wave.open(str(temporary_path), "rb") as audio:
            if (
                audio.getnchannels() != CHANNELS
                or audio.getsampwidth() != SAMPLE_WIDTH_BYTES
                or audio.getframerate() != SAMPLE_RATE_HZ
                or audio.getnframes() != expected_frame_count
            ):
                _fail("generated_frame_mismatch", output_path.name)
        actual_checksum = _sha256_file(temporary_path)
        if actual_checksum != expected_checksum:
            _fail(
                "generated_checksum_mismatch",
                f"{output_path.name}: expected {expected_checksum}, "
                f"got {actual_checksum}",
            )
        current_identity = _regular_target_identity(output_path)
        if current_identity != accepted_target_identity:
            _fail("unsafe_output_target", f"target changed: {output_path}")
        os.replace(temporary_path, output_path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def generate_fixtures(
    *,
    manifest_path: Path,
    output_dir: Path,
    rebuild: bool,
) -> dict[str, Path]:
    manifest_path = manifest_path.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    fixture_root = manifest_path.parent
    runtime_matrix = manifest["generator"]["verified_runtime_matrix"]
    current_python = platform.python_version()
    if not any(
        runtime["implementation"] == platform.python_implementation()
        and runtime["python_version"] == current_python
        and "long_fixture_generation" in runtime["verified_roles"]
        for runtime in runtime_matrix
    ):
        _fail(
            "unsupported_generator_runtime",
            f"{platform.python_implementation()} {current_python}",
        )
    output_dir = _prepare_output_directory(output_dir)
    generated: dict[str, Path] = {}

    for case_id in EXPECTED_DURATIONS_MS:
        case = manifest["cases"][case_id]
        output_path = output_dir / case["generated_filename"]
        expected_checksum = case["generated_sha256"]
        accepted_target_identity = _regular_target_identity(output_path)
        if accepted_target_identity is not None:
            actual_checksum = _sha256_file(output_path)
            if actual_checksum == expected_checksum:
                generated[case_id] = output_path
                continue
            if not rebuild:
                _fail(
                    "unexpected_existing_checksum",
                    f"{output_path}: {actual_checksum}",
                )

        seed = manifest["seeds"][case["assembly"]["seed_id"]]
        seed_path = _resolve_fixture_path(fixture_root, seed["path"])
        frames = _assemble_case(
            seed_path=seed_path,
            seed=seed,
            target_frames=case["expected_frame_count"],
            inter_repeat_silence_frames=case["assembly"][
                "inter_repeat_silence_frames"
            ],
        )
        _write_verified_atomic_wave(
            output_path=output_path,
            frames=frames,
            expected_frame_count=case["expected_frame_count"],
            expected_checksum=expected_checksum,
            accepted_target_identity=accepted_target_identity,
        )
        generated[case_id] = output_path

    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument(
        "--require-gold-ready",
        action="store_true",
        help="Refuse fixtures with pending external or downstream gold dependencies.",
    )
    arguments = parser.parse_args()
    manifest_path = arguments.manifest.resolve()
    repository_root = manifest_path.parents[4]
    required_output = (
        repository_root / ".local" / "golden-audio" / "v1.7.0"
    ).resolve()
    if arguments.output.resolve() != required_output:
        _fail(
            "output_path_mismatch",
            f"expected {required_output}, got {arguments.output.resolve()}",
        )
    if arguments.require_gold_ready:
        load_and_validate_manifest(manifest_path, require_gold_ready=True)
    else:
        print(
            "Scaffold-only generation: these fixtures are not gold-ready; "
            "human, license, CHAT, tokenizer, and feature gates remain pending.",
            file=sys.stderr,
        )
    generated = generate_fixtures(
        manifest_path=manifest_path,
        output_dir=arguments.output,
        rebuild=arguments.rebuild,
    )
    for case_id, path in generated.items():
        print(f"{case_id}: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FixtureManifestError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from None
