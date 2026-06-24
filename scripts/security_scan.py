"""Local security scan checks for committed high-risk secrets.

This intentionally avoids external services so it can run in CI before build
and deploy jobs. Dependency scanners remain separate CI steps because they need
package-manager metadata and may require network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_MARKER = "security-scan: allowlist"
MAX_TEXT_BYTES = 1_000_000


@dataclass(frozen=True)
class Finding:
    relative_path: str
    line_number: int
    message: str


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI API key", re.compile(r"\bsk-(?:proj|svcacct)?-[A-Za-z0-9_-]{20,}\b")),
    ("Supabase service role JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)


EXCLUDED_PARTS = {
    ".git",
    ".next",
    ".local",
    ".venv",
    "dist",
    "node_modules",
    "__pycache__",
}
EXCLUDED_SUFFIXES = {
    ".DS_Store",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".pyc",
    ".zip",
}


def candidate_paths() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    )
    return [ROOT / line for line in output.splitlines() if line]


def should_scan(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        relative = path
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file() and path.stat().st_size <= MAX_TEXT_BYTES


def scan_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if not should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if ALLOWLIST_MARKER in line:
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            relative_path=_display_path(path),
                            line_number=line_number,
                            message=f"{label} pattern found; remove the secret and rotate the credential.",
                        )
                    )
    return findings


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    findings = scan_paths(candidate_paths())
    if findings:
        print("Security scan failed:")
        for finding in findings:
            print(f"- {finding.relative_path}:{finding.line_number}: {finding.message}")
        return 1
    print("Security scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
