from __future__ import annotations

import pytest

from app.services.tokenizer_service import TokenizerUnavailable, load_tokenizer_profile, tokenize_v170


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("สวัสดีครับ วันนี้เราเล่นอะไรดี", ["สวัสดี", "ครับ", "วันนี้", "เรา", "เล่น", "อะไร", "ดี"]),
        ("หนูชอบ blue car มาก", ["หนู", "ชอบ", "blue", "car", "มาก"]),
        ("สวัสดี   ค่ะ!", ["สวัสดี", "ค่ะ"]),
        ("เอ่อ หนู หนูอยากได้", ["หนู", "หนู", "อยากได้"]),
        ("กินข้าว[/] กินข้าว", ["กินข้าว", "กินข้าว"]),
        ("รถ&+ไฟ xxx", ["รถ", "ไฟ"]),
    ],
)
def test_verified_thai_profile_matches_hand_reviewed_golden_tokens(text: str, expected: list[str]) -> None:
    assert tokenize_v170(text) == expected


def test_profile_is_pinned_and_checksum_verified() -> None:
    profile = load_tokenizer_profile()

    assert profile.profile_id == "thai-aware-deterministic-v1.7.0"
    assert profile.engine == "newmm"
    assert profile.package_version == "5.3.4"
    assert len(profile.profile_checksum_sha256) == 64


def test_runtime_never_silently_falls_back_when_profile_is_invalid(monkeypatch) -> None:
    monkeypatch.setenv("LINGUALENS_V170_TOKENIZER_PROFILE", "/missing/tokenizer-profile.json")

    with pytest.raises(TokenizerUnavailable, match="profile"):
        load_tokenizer_profile()
