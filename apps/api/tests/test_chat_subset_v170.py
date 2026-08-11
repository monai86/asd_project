from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.services.chat_subset import (
    CanonicalAnnotation,
    CanonicalChatDocument,
    CanonicalChatUtterance,
    CanonicalDependentTier,
    CanonicalOpaqueExtension,
    CanonicalParticipant,
    compare_semantics,
    parse_chat,
    semantic_checksum,
    serialize_chat,
)


def _thai_document() -> CanonicalChatDocument:
    return CanonicalChatDocument(
        language_codes=("tha", "eng"),
        media_reference="fixture-thai-english",
        participants=(
            CanonicalParticipant(
                code="CHI",
                display_name="Child",
                role="Target_Child",
                id_fields=("tha", "LinguaLens", "CHI", "", "", "", "", "Target_Child", "", ""),
            ),
            CanonicalParticipant(
                code="THE",
                display_name="Therapist",
                role="Therapist",
                id_fields=("tha", "LinguaLens", "THE", "", "", "", "", "Therapist", "", ""),
            ),
        ),
        utterances=(
            CanonicalChatUtterance(
                utterance_id="utt-1",
                speaker_code="CHI",
                reviewed_text_nfc="เด็ก <แมว> ไทย-English [?]",
                start_ms=0,
                end_ms=1200,
                terminator="?",
                continuation_parts=("ต่อบรรทัด",),
                dependent_tiers=(
                    CanonicalDependentTier(tier="%mor", text="เด็ก|N แมว|N"),
                ),
                annotations=(CanonicalAnnotation(kind="uncertainty", payload="?"),),
            ),
            CanonicalChatUtterance(
                utterance_id="utt-2",
                speaker_code="THE",
                reviewed_text_nfc="ขอบคุณ\tครับ",
                start_ms=1200,
                end_ms=2200,
                terminator=".",
            ),
        ),
        optional_headers=(("@Date", "2026-08-11"), ("@Comment", "synthetic fixture")),
        opaque_extensions=(
            CanonicalOpaqueExtension(
                action="preserved_opaque",
                location="header",
                key="@x-lingualens-fixture",
                content="thai-v1",
            ),
        ),
    )


def test_canonical_chat_serialization_is_utf8_nfc_and_deterministic() -> None:
    document = _thai_document()

    first = serialize_chat(document)
    second = serialize_chat(parse_chat(first).document)

    assert first == second
    assert first.endswith("\n")
    assert "@UTF8\n@Begin\n" in first
    assert "เด็ก" in first
    assert hashlib.sha256(first.encode("utf-8")).hexdigest() == hashlib.sha256(second.encode("utf-8")).hexdigest()


def test_external_import_normalizes_harmless_formatting_but_preserves_semantics() -> None:
    document = _thai_document()
    generated = serialize_chat(document)
    imported = generated.replace("\n", "\r\n").replace("@Begin\r\n", "  @Begin\r\n")

    parsed = parse_chat(imported, profile="external-chat-import-v1.7.0")
    assert parsed.errors == []
    assert compare_semantics(document, parsed.document, profile="external-chat-import-v1.7.0") == []


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (lambda value: value.replace("เด็ก", "ผู้ใหญ่"), "CHAT_TEXT_CHANGED"),
        (lambda value: value.replace("%mor", "%gra"), "CHAT_TIER_CHANGED"),
        (lambda value: value.replace("1200_2200", "1300_2200"), "CHAT_TIMESTAMP_CHANGED"),
    ],
)
def test_semantic_mutation_returns_structured_blocking_error(mutation, expected_code: str) -> None:
    document = _thai_document()
    parsed = parse_chat(mutation(serialize_chat(document))).document

    errors = compare_semantics(document, parsed)

    assert errors
    assert any(error.code == expected_code for error in errors)
    assert all(error.severity == "error" for error in errors)
    assert all(error.parser_version == "lingualens-chat-parser-v1.7.0" for error in errors)


def test_malformed_timestamp_and_unknown_main_tier_are_blocking() -> None:
    parsed = parse_chat(
        "\n".join(
            [
                "@UTF8",
                "@Begin",
                "@Languages:\ttha",
                "@Participants:\tCHI Child Target_Child",
                "*CHI:\tสวัสดี . \u00151200_bad\u0015",
                "*UNK:\tไม่ควรนำเข้า .",
                "@End",
                "",
            ]
        )
    )

    assert any(error.code == "CHAT_TIMESTAMP_MALFORMED" for error in parsed.errors)
    assert any(error.code == "CHAT_UNKNOWN_MAIN_TIER" for error in parsed.errors)


def test_unknown_x_header_is_preserved_and_repeated_optional_headers_keep_order() -> None:
    document = _thai_document().model_copy(
        update={
            "optional_headers": (
                ("@Comment", "first"),
                ("@Comment", "second"),
            ),
            "opaque_extensions": (
                CanonicalOpaqueExtension(
                    action="preserved_opaque",
                    location="header",
                    key="@x-custom",
                    content="opaque-value",
                ),
            ),
        }
    )

    parsed = parse_chat(serialize_chat(document))

    assert parsed.errors == []
    assert parsed.document.optional_headers == document.optional_headers
    assert parsed.document.opaque_extensions == document.opaque_extensions


def test_unknown_inline_annotation_is_a_blocking_structured_error() -> None:
    parsed = parse_chat(
        "\n".join(
            [
                "@UTF8",
                "@Begin",
                "@Languages:\ttha",
                "@Participants:\tCHI Child Target_Child",
                "*CHI:\tสวัสดี [unknown] .",
                "@End",
                "",
            ]
        )
    )

    assert any(error.code == "CHAT_UNKNOWN_ANNOTATION" for error in parsed.errors)


@pytest.mark.parametrize("fixture_name", ["thai_only.cha", "thai_english.cha", "opaque_extension.cha"])
def test_versioned_chat_golden_fixtures_parse_and_reexport(fixture_name: str) -> None:
    fixture = Path(__file__).parents[3] / "tests" / "fixtures" / "chat" / "v1.7.0" / fixture_name
    expected = json.loads((fixture.parent / "expected" / f"{fixture.stem}.json").read_text(encoding="utf-8"))

    parsed = parse_chat(fixture.read_text(encoding="utf-8"))
    assert not [error for error in parsed.errors if error.severity == "error"]
    serialized = serialize_chat(parsed.document)
    assert serialized == serialize_chat(parse_chat(serialized).document)
    assert semantic_checksum(parsed.document) == expected["semantic_checksum_sha256"]
    assert hashlib.sha256(serialized.encode("utf-8")).hexdigest() == expected["export_checksum_sha256"]
