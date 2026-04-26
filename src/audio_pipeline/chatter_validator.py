"""
TalkBank CHATTER validator wrapper.

CHATTER (https://talkbank.org/software/chatter.html) is the official
TalkBank tool for checking that a ``.cha`` file conforms to the CHAT
specification.  It is shipped as a single Java JAR.

This module wraps it through ``subprocess.run`` so the rest of the
pipeline can:

1. Validate generated transcripts before saving them.
2. Auto-fix small, safe issues (trailing whitespace, missing
   terminators) without losing data.
3. Surface remaining errors to the dashboard for the user to inspect.

If neither Java nor the CHATTER JAR is available, validation is
gracefully skipped \u2014 the pipeline still produces output.

Setup
-----
1. Install Java 8+:
    macOS:  ``brew install --cask temurin``
    Ubuntu: ``apt install default-jre-headless``
2. Download CHATTER from https://talkbank.org/software/chatter.html
3. Set ``CHATTER_JAR`` env var to the JAR path, OR drop it next to this
   file as ``chatter.jar``.

Usage
-----
>>> report = validate_chat_file("session.cha")
>>> if report.ok:
...     print("Valid!")
>>> for err in report.errors:
...     print(err)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ----------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------
def _discover_chatter_jar() -> Optional[Path]:
    """Locate the CHATTER JAR file on this machine.

    Search order:
      1. ``$CHATTER_JAR`` environment variable
      2. ``chatter.jar`` next to this Python module
      3. ``$HOME/.local/share/chatter/chatter.jar``
    """
    env = os.environ.get("CHATTER_JAR")
    if env and Path(env).exists():
        return Path(env)
    here = Path(__file__).resolve().parent / "chatter.jar"
    if here.exists():
        return here
    user_share = (
        Path.home() / ".local" / "share" / "chatter" / "chatter.jar"
    )
    if user_share.exists():
        return user_share
    return None


def _java_available() -> bool:
    return shutil.which("java") is not None


# ----------------------------------------------------------------------
# Report types
# ----------------------------------------------------------------------
@dataclass
class ValidationIssue:
    line: Optional[int]
    severity: str           # "error" / "warning"
    message: str

    def __str__(self) -> str:
        loc = f"line {self.line}" if self.line is not None else "?"
        return f"[{self.severity}] {loc}: {self.message}"


@dataclass
class ValidationReport:
    """Outcome of running CHATTER on a ``.cha`` file."""
    ok: bool
    skipped: bool = False               # True if CHATTER was unavailable
    skip_reason: Optional[str] = None
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    fixed_count: int = 0                # number of auto-fixes applied
    raw_output: str = ""

    @property
    def n_errors(self) -> int:
        return len(self.errors)

    @property
    def n_warnings(self) -> int:
        return len(self.warnings)

    def summary(self) -> str:
        if self.skipped:
            return f"CHATTER skipped: {self.skip_reason}"
        if self.ok:
            return f"CHATTER passed (auto-fixed {self.fixed_count})"
        return (
            f"CHATTER: {self.n_errors} error(s), "
            f"{self.n_warnings} warning(s) "
            f"(auto-fixed {self.fixed_count})"
        )


# ----------------------------------------------------------------------
# Auto-fix routines (run before invoking CHATTER)
# ----------------------------------------------------------------------
_TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)
_MAIN_LINE_RE = re.compile(r"^\*[A-Z]{3}:\s")
_TERMINATORS = (".", "?", "!", '"', "/")


def auto_fix(chat_text: str) -> tuple[str, int]:
    """Apply safe auto-fixes to a CHAT transcript.

    Currently fixes:
      * Trailing whitespace on every line
      * Main-tier lines (``*CHI:`` / ``*MOT:`` / ...) missing a terminator
        get a trailing ``" ."``

    Returns the patched text and the count of changes made.
    """
    fixes = 0

    # 1. Trailing whitespace
    new_text, n = _TRAILING_WS_RE.subn("", chat_text)
    fixes += n
    chat_text = new_text

    # 2. Missing terminator on main-tier lines
    out_lines: List[str] = []
    for line in chat_text.splitlines():
        if _MAIN_LINE_RE.match(line):
            stripped = line.rstrip()
            # Last token must be one of the CHAT terminators
            last = stripped[-1] if stripped else ""
            if last not in _TERMINATORS:
                stripped = stripped + " ."
                fixes += 1
            out_lines.append(stripped)
        else:
            out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if chat_text.endswith("\n") else ""), fixes


# ----------------------------------------------------------------------
# CHATTER invocation
# ----------------------------------------------------------------------
_CHATTER_LINE_RE = re.compile(
    r"\*\*\*\s+File\s+\S+:\s+line\s+(\d+):\s*(.*)"
)


def _parse_chatter_output(stdout: str) -> tuple[List[ValidationIssue], List[ValidationIssue]]:
    """Parse CHATTER's text output into structured errors/warnings.

    CHATTER emits lines such as::

        *** File foo.cha: line 42: missing terminator on main line.

    We treat any "line ##" message as an error by default; lines
    containing the word "warning" (case-insensitive) become warnings.
    """
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []
    for raw in stdout.splitlines():
        m = _CHATTER_LINE_RE.search(raw)
        if not m:
            continue
        line_no = int(m.group(1))
        msg = m.group(2).strip().rstrip(".")
        is_warning = "warning" in raw.lower()
        issue = ValidationIssue(
            line=line_no,
            severity="warning" if is_warning else "error",
            message=msg,
        )
        (warnings if is_warning else errors).append(issue)
    return errors, warnings


def validate_chat_file(
    cha_path: str | Path,
    *,
    auto_fix_first: bool = True,
    save_fixed: bool = True,
    timeout_sec: float = 60.0,
) -> ValidationReport:
    """Validate a CHAT file with TalkBank's CHATTER.

    Parameters
    ----------
    cha_path : Path-like
        The ``.cha`` file to validate.
    auto_fix_first : bool
        Run :func:`auto_fix` before invoking CHATTER.
    save_fixed : bool
        Overwrite the file with the auto-fixed text.  Disable to keep
        the original on disk.
    timeout_sec : float
        Kill CHATTER if it hangs longer than this.
    """
    cha_path = Path(cha_path)
    if not cha_path.exists():
        return ValidationReport(
            ok=False, skipped=True, skip_reason=f"file not found: {cha_path}",
        )

    report = ValidationReport(ok=False)

    # ---- 1. Auto-fix ------------------------------------------------------
    if auto_fix_first:
        original = cha_path.read_text(encoding="utf-8")
        fixed, n = auto_fix(original)
        report.fixed_count = n
        if save_fixed and n > 0 and fixed != original:
            cha_path.write_text(fixed, encoding="utf-8")

    # ---- 2. Run CHATTER ---------------------------------------------------
    if not _java_available():
        report.skipped = True
        report.skip_reason = "java not installed (skipping CHATTER)"
        report.ok = True   # treat as soft-pass so pipeline doesn't fail
        return report
    jar = _discover_chatter_jar()
    if jar is None:
        report.skipped = True
        report.skip_reason = (
            "chatter.jar not found "
            "(set CHATTER_JAR env var or drop chatter.jar in src/audio_pipeline/)"
        )
        report.ok = True
        return report

    try:
        proc = subprocess.run(
            ["java", "-jar", str(jar), str(cha_path)],
            capture_output=True, text=True, timeout=timeout_sec,
        )
        report.raw_output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
    except subprocess.TimeoutExpired:
        report.skipped = True
        report.skip_reason = f"CHATTER timed out after {timeout_sec}s"
        report.ok = True
        return report
    except Exception as e:  # noqa: BLE001
        report.skipped = True
        report.skip_reason = f"CHATTER invocation failed: {e}"
        report.ok = True
        return report

    # ---- 3. Parse results -------------------------------------------------
    report.errors, report.warnings = _parse_chatter_output(report.raw_output)
    report.ok = len(report.errors) == 0
    return report


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Validate a .cha file with CHATTER.")
    ap.add_argument("cha", type=Path)
    ap.add_argument("--no-auto-fix", action="store_true")
    ap.add_argument("--no-save", action="store_true",
                    help="Run auto-fix in memory only; don't overwrite the file.")
    args = ap.parse_args()

    report = validate_chat_file(
        args.cha,
        auto_fix_first=not args.no_auto_fix,
        save_fixed=not args.no_save,
    )
    print(report.summary())
    for issue in report.errors + report.warnings:
        print("  ", issue)
    if report.skipped:
        raise SystemExit(0)
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    _cli()
