from app.schemas.clinical import Utterance, DependentTier, OrphanDependentTier
from app.services.cha_service import parse_cha_document, build_cha_text

def test_cha_parser_handles_continuation_lines():
    # Continuation line starts with a tab or spaces, followed by text.
    # It should merge into the previous speaker's utterance text.
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "*CHI:\tI see a very big and nice\n\tblue car. \x15100_900\x15",
            "@End"
        ])
    )
    assert len(parsed.utterances) == 1
    assert parsed.utterances[0].text == "I see a very big and nice blue car."
    assert parsed.utterances[0].start_ms == 100
    assert parsed.utterances[0].end_ms == 900

def test_cha_parser_preserves_dependent_tiers():
    # Dependent tiers start with % and should attach to the preceding utterance.
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "*CHI:\tBlue car. \x15100_900\x15",
            "%mor:\tadj|blue n|car",
            "%gra:\t1|2|SUBJ 2|0|ROOT",
            "@End"
        ])
    )
    assert len(parsed.utterances) == 1
    utt = parsed.utterances[0]
    assert len(utt.dependent_tiers) == 2
    assert utt.dependent_tiers[0].tier == "%mor"
    assert utt.dependent_tiers[0].raw_text == "adj|blue n|car"
    assert utt.dependent_tiers[0].line_number == 5
    assert utt.dependent_tiers[1].tier == "%gra"
    assert utt.dependent_tiers[1].raw_text == "1|2|SUBJ 2|0|ROOT"
    assert utt.dependent_tiers[1].line_number == 6

def test_cha_parser_preserves_orphan_dependent_tiers():
    # If a dependent tier appears before any speaker utterance, it is an orphan.
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "%mor:\tadj|blue n|car",
            "*CHI:\tBlue car. \x15100_900\x15",
            "@End"
        ])
    )
    # The parsed document should have orphan_dependent_tiers, let's verify how it is stored
    # In Task 1 we added: orphan_dependent_tiers: list[OrphanDependentTier] on Transcript.
    # Wait, the parse_cha_document returns a ParsedChaDocument. Let's see if ParsedChaDocument
    # needs to contain orphan_dependent_tiers and malformed_lines.
    # Yes! Let's check ParsedChaDocument fields. It currently has:
    # @dataclass
    # class ParsedChaDocument:
    #     metadata: dict
    #     utterances: list[Utterance]
    #     warnings: list[str]
    #     validation_issues: list[str]
    #
    # We should update ParsedChaDocument to also have:
    #     orphan_dependent_tiers: list[OrphanDependentTier]
    #     malformed_lines: list[dict]
    #
    # Let's write the test assuming it has these.
    assert hasattr(parsed, "orphan_dependent_tiers")
    assert len(parsed.orphan_dependent_tiers) == 1
    assert parsed.orphan_dependent_tiers[0].tier == "%mor"
    assert parsed.orphan_dependent_tiers[0].raw_text == "adj|blue n|car"
    assert parsed.orphan_dependent_tiers[0].line_number == 4

def test_cha_parser_logs_malformed_lines():
    # A line that is not metadata, speaker line, or dependent tier, and isn't a valid continuation
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "This is a malformed line that doesn't start with anything valid.",
            "*CHI:\tBlue car.",
            "@End"
        ])
    )
    assert len(parsed.malformed_lines) == 1
    assert parsed.malformed_lines[0]["raw_text"] == "This is a malformed line that doesn't start with anything valid."
    assert parsed.malformed_lines[0]["line_number"] == 4

def test_cha_parser_metadata_id_and_media():
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "@ID:\teng|Demo|CHI|4;00.00|female|||Target_Child|||",
            "@Media:\tdemo_audio, audio",
            "*CHI:\tBlue car.",
            "@End"
        ])
    )
    assert parsed.metadata["ids"] == [{"code": "CHI", "raw": "eng|Demo|CHI|4;00.00|female|||Target_Child|||"}]
    assert parsed.metadata["media"] == {"name": "demo_audio", "type": "audio"}

def test_build_cha_text_exports_dependent_tiers():
    # If an utterance has dependent_tiers, build_cha_text should write them right under the utterance speaker line
    utterances = [
        Utterance(
            utterance_id="u1",
            speaker="CHI",
            text="Blue car.",
            start_ms=100,
            end_ms=900,
            dependent_tiers=[
                DependentTier(tier="%mor", raw_text="adj|blue n|car", line_number=5),
                DependentTier(tier="%gra", raw_text="1|2|SUBJ 2|0|ROOT", line_number=6)
            ]
        )
    ]
    chat = build_cha_text(
        utterances,
        language="eng",
        participants="CHI Child Target_Child",
        participant_ids=["eng|Demo|CHI|4;00.00|female|||Target_Child|||"]
    )
    assert "*CHI:\tBlue car. \x15100_900\x15" in chat
    assert "%mor:\tadj|blue n|car" in chat
    assert "%gra:\t1|2|SUBJ 2|0|ROOT" in chat
