"""Structured CLAN command integration for reviewed clinical CHAT exports."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Literal, Sequence


CLAN_COMMANDS = {"mlu", "freq", "kwal"}
CLAN_PARTICIPANTS = {"CHI", "INV", "MOT", "FAT"}
CLAN_LANGUAGES = {"eng", "tha"}
TERM_RE = re.compile(r"^[\w'-]{1,64}$", re.UNICODE)


@dataclass(frozen=True)
class ClanDependencyCheck:
    available: bool
    missing_commands: list[str] = field(default_factory=list)
    setup_hint: str = "Install TalkBank CLAN/UnixCLAN and ensure mlu, freq, and kwal are on PATH."


@dataclass(frozen=True)
class StructuredClanRun:
    command: Literal["mlu", "freq", "kwal"]
    chat_path: Path
    participant: str = "CHI"
    language: str = "eng"
    kwal_terms: tuple[str, ...] = ()
    allow_preliminary: bool = False


@dataclass(frozen=True)
class ClanRunResult:
    command: str
    command_args: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    metrics: dict[str, float | int | str | list[str]]
    parse_warnings: list[str]
    parser_confidence: str
    dependency_check: ClanDependencyCheck

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.dependency_check.available


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
CommandLocator = Callable[[str], str | None]


def check_clan_dependencies(
    commands: Sequence[str] = ("mlu", "freq", "kwal"),
    *,
    command_locator: CommandLocator = shutil.which,
) -> ClanDependencyCheck:
    missing = [command for command in commands if command_locator(command) is None]
    return ClanDependencyCheck(available=not missing, missing_commands=missing)


def run_clan_command(
    request: StructuredClanRun,
    *,
    runner: CommandRunner = subprocess.run,
    command_locator: CommandLocator = shutil.which,
    timeout_seconds: int = 300,
) -> ClanRunResult:
    _validate_request(request)
    dependency_check = check_clan_dependencies((request.command,), command_locator=command_locator)
    args = build_clan_args(request, command_path=command_locator(request.command) or request.command)

    if not dependency_check.available:
        return ClanRunResult(
            command=request.command,
            command_args=args,
            returncode=None,
            stdout="",
            stderr=f"CLAN command unavailable: {', '.join(dependency_check.missing_commands)}",
            metrics={},
            parse_warnings=["clan_unavailable"],
            parser_confidence="none",
            dependency_check=dependency_check,
        )
    if not request.chat_path.exists():
        raise ValueError("CHAT file does not exist.")

    try:
        completed = runner(
            args,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        metrics, warnings, confidence = parse_clan_output(request.command, completed.stdout or "")
        return ClanRunResult(
            command=request.command,
            command_args=args,
            returncode=int(completed.returncode),
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            metrics=metrics,
            parse_warnings=warnings,
            parser_confidence=confidence,
            dependency_check=dependency_check,
        )
    except subprocess.TimeoutExpired as exc:
        return ClanRunResult(
            command=request.command,
            command_args=args,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"CLAN command timed out after {timeout_seconds} seconds.",
            metrics={},
            parse_warnings=["timeout"],
            parser_confidence="none",
            dependency_check=dependency_check,
        )


def build_clan_args(request: StructuredClanRun, *, command_path: str | None = None) -> list[str]:
    executable = command_path or request.command
    args = [executable, f"+t*{request.participant}", f"-l{request.language}"]
    if request.command == "kwal":
        for term in request.kwal_terms:
            args.append(f"+s{term}")
    args.append(request.chat_path.as_posix())
    return args


def parse_clan_output(command: str, stdout: str) -> tuple[dict[str, float | int | str | list[str]], list[str], str]:
    if command == "mlu":
        return parse_mlu_output(stdout)
    if command == "freq":
        return parse_freq_output(stdout)
    if command == "kwal":
        return parse_kwal_output(stdout)
    return {}, ["unsupported_command"], "none"


def parse_mlu_output(stdout: str) -> tuple[dict[str, float | int], list[str], str]:
    metrics: dict[str, float | int] = {}
    warnings: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        value_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", line)
        if value_match is None:
            continue
        value = float(value_match.group(1))
        lower = line.lower()
        if "utterance" in lower:
            metrics["utterances"] = int(value)
        elif "mluw" in lower or ("mlu" in lower and "word" in lower):
            metrics["mlu_words"] = value
        elif "mlu" in lower and "morpheme" in lower:
            metrics["mlu_morphemes"] = value
    if not metrics:
        warnings.append("no_common_mlu_metrics_parsed")
        return metrics, warnings, "none"
    return metrics, warnings, "medium"


def parse_freq_output(stdout: str, limit: int = 20) -> tuple[dict[str, int | list[str]], list[str], str]:
    token_counts: list[tuple[str, int]] = []
    for raw_line in stdout.splitlines():
        match = re.match(r"^\s*(\d+)\s+([^\s]+)\s*$", raw_line)
        if match:
            token_counts.append((match.group(2), int(match.group(1))))
    if not token_counts:
        return {}, ["no_frequency_table_parsed"], "none"
    return {
        "freq_types": len(token_counts),
        "top_tokens": [token for token, _count in token_counts[:limit]],
    }, [], "medium"


def parse_kwal_output(stdout: str) -> tuple[dict[str, int], list[str], str]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    match_lines = [line for line in lines if line.lstrip().startswith("*")]
    if match_lines:
        return {"kwal_match_count": len(match_lines)}, [], "medium"
    if stdout.strip():
        return {"kwal_raw_line_count": len(lines)}, ["matched_lines_not_identified"], "low"
    return {}, ["empty_kwal_output"], "none"


def _validate_request(request: StructuredClanRun) -> None:
    if request.command not in CLAN_COMMANDS:
        raise ValueError(f"Unsupported CLAN command: {request.command}")
    participant = request.participant.strip().upper()
    if participant not in CLAN_PARTICIPANTS:
        raise ValueError("Unsupported CLAN participant target.")
    if request.language not in CLAN_LANGUAGES:
        raise ValueError("Unsupported CLAN language.")
    if request.command == "kwal" and not request.kwal_terms:
        raise ValueError("kwal_terms are required for KWAL.")
    for term in request.kwal_terms:
        if not TERM_RE.match(term):
            raise ValueError("KWAL terms must be simple lexical terms.")
