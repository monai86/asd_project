"""Optional Batchalign2 subprocess integration for backend workers."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Sequence


BATCHALIGN_ENV_FLAG = "ASD_ENABLE_BATCHALIGN"
BATCHALIGN_COMMANDS = {"transcribe", "align", "morphotag"}


@dataclass(frozen=True)
class DependencyCheck:
    enabled: bool
    available: bool
    errors: list[str] = field(default_factory=list)
    setup_hint: str = ""


@dataclass(frozen=True)
class BatchalignResult:
    command: str
    command_args: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    generated_cha_files: list[Path]
    dependency_check: DependencyCheck

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.dependency_check.available


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
CommandLocator = Callable[[str], str | None]


def check_batchalign_dependencies(
    *,
    env: dict[str, str] | None = None,
    command_locator: CommandLocator = shutil.which,
) -> DependencyCheck:
    env_values = env if env is not None else os.environ
    enabled = str(env_values.get(BATCHALIGN_ENV_FLAG, "")).strip().lower() in {"1", "true", "yes", "on"}
    errors: list[str] = []
    if not enabled:
        errors.append(f"{BATCHALIGN_ENV_FLAG} is not enabled.")
    if command_locator("batchalign") is None:
        errors.append("Batchalign2 command 'batchalign' was not found on PATH.")
    if command_locator("ffmpeg") is None:
        errors.append("FFmpeg command 'ffmpeg' was not found on PATH.")
    return DependencyCheck(
        enabled=enabled,
        available=enabled and not errors,
        errors=errors,
        setup_hint="Install Batchalign2 and FFmpeg locally, then set ASD_ENABLE_BATCHALIGN=true.",
    )


def run_batchalign(
    command: str,
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    lang: str = "eng",
    use_whisper: bool = True,
    env: dict[str, str] | None = None,
    runner: CommandRunner = subprocess.run,
    command_locator: CommandLocator = shutil.which,
    timeout_seconds: int = 1800,
) -> BatchalignResult:
    normalized_command = command.strip().lower()
    if normalized_command not in BATCHALIGN_COMMANDS:
        raise ValueError(f"Unsupported Batchalign2 command: {command}")

    dependency_check = check_batchalign_dependencies(env=env, command_locator=command_locator)
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    args = _build_batchalign_args(normalized_command, input_path, output_path, lang=lang, use_whisper=use_whisper)

    if not dependency_check.available:
        return BatchalignResult(
            command=normalized_command,
            command_args=args,
            returncode=None,
            stdout="",
            stderr="\n".join(dependency_check.errors),
            generated_cha_files=[],
            dependency_check=dependency_check,
        )
    if not input_path.exists() or not input_path.is_dir():
        raise ValueError("Batchalign2 input_dir must be an existing directory.")
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        completed = runner(
            args,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        return BatchalignResult(
            command=normalized_command,
            command_args=args,
            returncode=int(completed.returncode),
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            generated_cha_files=sorted(output_path.rglob("*.cha")),
            dependency_check=dependency_check,
        )
    except subprocess.TimeoutExpired as exc:
        return BatchalignResult(
            command=normalized_command,
            command_args=args,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"Batchalign2 command timed out after {timeout_seconds} seconds.",
            generated_cha_files=sorted(output_path.rglob("*.cha")) if output_path.exists() else [],
            dependency_check=dependency_check,
        )


def _build_batchalign_args(
    command: str,
    input_dir: Path,
    output_dir: Path,
    *,
    lang: str,
    use_whisper: bool,
) -> list[str]:
    args = ["batchalign", command]
    if command == "transcribe":
        args.extend([f"--lang={lang}"])
        if use_whisper:
            args.append("--whisper")
    args.extend([input_dir.as_posix(), output_dir.as_posix()])
    return args
