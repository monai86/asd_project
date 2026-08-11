"""Pinned Thai-aware tokenizer for deterministic v1.7.0 feature metrics."""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import unicodedata

from pydantic import BaseModel, ConfigDict, Field


class TokenizerUnavailable(RuntimeError):
    pass


class TokenizerProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    profile_version: int = Field(ge=1)
    engine: str
    package_name: str
    package_version: str
    segmentation_mode: str
    artifact_id: str
    artifact_checksum_sha256: str
    unicode_normalization: str
    punctuation_rule: str
    whitespace_rule: str
    filled_pause_rule: str
    repetition_rule: str
    partial_word_rule: str
    unintelligible_marker_rule: str
    code_switch_rule: str
    custom_vocabulary_version: str
    custom_vocabulary_checksum_sha256: str
    fixture_manifest_checksum_sha256: str
    profile_checksum_sha256: str


def _default_profile_path() -> Path:
    return Path(__file__).resolve().parents[4] / "artifacts" / "v1.7.0" / "tokenizer_profile.json"


def _canonical_checksum(payload: dict) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "profile_checksum_sha256"}
    return sha256(json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@lru_cache(maxsize=4)
def _load_profile_path(path_text: str) -> TokenizerProfile:
    path = Path(path_text)
    if not path.is_file():
        raise TokenizerUnavailable(f"Tokenizer profile is unavailable: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = _canonical_checksum(payload)
    if payload.get("profile_checksum_sha256") != expected:
        raise TokenizerUnavailable("Tokenizer profile checksum mismatch.")
    profile = TokenizerProfile.model_validate(payload)
    try:
        installed_version = importlib.metadata.version(profile.package_name)
    except importlib.metadata.PackageNotFoundError as exc:
        raise TokenizerUnavailable(f"Tokenizer package {profile.package_name} is unavailable.") from exc
    if installed_version != profile.package_version:
        raise TokenizerUnavailable(
            f"Tokenizer package version mismatch: expected {profile.package_version}, got {installed_version}."
        )
    return profile


def load_tokenizer_profile() -> TokenizerProfile:
    path = os.getenv("LINGUALENS_V170_TOKENIZER_PROFILE", str(_default_profile_path()))
    return _load_profile_path(path)


_EXCLUDED = {"xxx", "yyy", "www", "[/]", "[//]", "[?]", "&-", "&+", "&~", "เอ่อ", "อืม"}


def tokenize_v170(text: str) -> list[str]:
    profile = load_tokenizer_profile()
    try:
        from pythainlp.tokenize import word_tokenize
    except ImportError as exc:
        raise TokenizerUnavailable("Pinned Thai tokenizer package is unavailable.") from exc
    normalized = unicodedata.normalize("NFC", text)
    raw_tokens = word_tokenize(normalized, engine=profile.engine, keep_whitespace=False)
    output: list[str] = []
    for raw in raw_tokens:
        token = raw.strip().lower()
        if not token or token in _EXCLUDED or all(unicodedata.category(char).startswith("P") for char in token):
            continue
        if token.startswith("&+"):
            token = token[2:]
        if token and token not in _EXCLUDED:
            output.append(token)
    return output
