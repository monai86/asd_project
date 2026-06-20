from app.schemas.clinical import Utterance
from app.services.cha_service import build_cha_text, parse_cha_document


def test_parse_cha_document_preserves_codes_timestamps_metadata_and_warnings():
    parsed = parse_cha_document(
        "\n".join(
            [
                "@Begin",
                "@Languages:\teng",
                "@Participants:\tCHI Child Target_Child, GRM Grandmother Adult",
                "@ID:\teng|Demo|CHI|4;00.00|female|||Target_Child|||",
                "@Media:\tdemo_audio, audio",
                "*CHI:\tBlue car. \x15100_900\x15",
                "%mor:\tadj|blue n|car",
                "*GRM:\tYes. \x15950_1200\x15",
                "@End",
            ]
        )
    )

    assert parsed.metadata["languages"] == ["eng"]
    assert parsed.metadata["media"] == {"name": "demo_audio", "type": "audio"}
    assert [item.speaker for item in parsed.utterances] == ["CHI", "GRM"]
    assert parsed.utterances[0].start_ms == 100
    assert parsed.utterances[0].end_ms == 900
    assert "Line 7: dependent tier %mor is preserved but not analyzed by BasicFeatureProvider." in parsed.warnings


def test_build_cha_text_emits_basic_headers_ids_media_and_preserved_codes():
    chat = build_cha_text(
        [
            Utterance(utterance_id="u1", speaker="CHI", text="Blue car.", start_ms=100, end_ms=900),
            Utterance(utterance_id="u2", speaker="GRM", text="Yes.", start_ms=950, end_ms=1200),
        ],
        language="eng",
        participants="CHI Child Target_Child, GRM Grandmother Adult",
        participant_ids=[
            "eng|Demo|CHI|4;00.00|female|||Target_Child|||",
            "eng|Demo|GRM|||||Adult|||",
        ],
        media_name="session_audio",
    )

    assert "@Languages:\teng" in chat
    assert "@Participants:\tCHI Child Target_Child, GRM Grandmother Adult" in chat
    assert "@ID:\teng|Demo|GRM|||||Adult|||" in chat
    assert "@Media:\tsession_audio, audio" in chat
    assert "*CHI:\tBlue car. \x15100_900\x15" in chat
    assert "*GRM:\tYes. \x15950_1200\x15" in chat
