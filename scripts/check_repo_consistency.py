"""Fail fast when repository source-of-truth boundaries drift."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROJECT_VERSION = "v1.6.3"


def git_files() -> set[str]:
    output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return {
        line
        for line in output.splitlines()
        if line and (ROOT / line).exists()
    }


def require_path(relative: str, errors: list[str]) -> None:
    if not (ROOT / relative).exists():
        errors.append(f"missing canonical path: {relative}")


def require_text(relative: str, expected: str, errors: list[str]) -> None:
    path = ROOT / relative
    if not path.exists():
        errors.append(f"missing file: {relative}")
    elif expected not in path.read_text(encoding="utf-8"):
        errors.append(f"{relative} does not contain expected text: {expected}")


def main() -> int:
    errors: list[str] = []
    tracked = git_files()

    for path in (
        "apps/api/app/main.py",
        "apps/lingualens-app/package.json",
        "docs/PROJECT_SOURCE_OF_TRUTH.md",
        "docs/REPO_STRUCTURE.md",
    ):
        require_path(path, errors)

    forbidden_parts = (
        "/.next/",
        "/.local/",
        "/dist/",
        "/node_modules/",
        "/__pycache__/",
    )
    forbidden_suffixes = (".pyc", ".tsbuildinfo", ".DS_Store")
    for path in sorted(tracked):
        normalized = f"/{path}"
        if any(part in normalized for part in forbidden_parts) or path.endswith(
            forbidden_suffixes
        ):
            errors.append(f"generated/local file is tracked: {path}")
        if path.startswith("therapist-clinician-app/"):
            errors.append(f"retired therapist app file is tracked: {path}")
        if path.startswith(("public-screening/", "presentation-dashboard/")):
            errors.append(f"removed demo surface is tracked: {path}")
        if path.startswith(("scratch/", "docs/superpowers/")):
            errors.append(f"temporary/historical planning file is tracked: {path}")
        if path.endswith((".docx", ".zip")):
            errors.append(f"non-source document/archive is tracked: {path}")

    require_text("README.md", PROJECT_VERSION, errors)
    require_text("PROJECT_STATUS.md", PROJECT_VERSION, errors)
    require_text("CHANGELOG.md", f"## [{PROJECT_VERSION}]", errors)
    require_text(
        "docs/PROJECT_SOURCE_OF_TRUTH.md",
        "Current ML runtime surface",
        errors,
    )
    require_text(
        "PROJECT_STATUS.md",
        "Legacy benchmark and demo surfaces removed",
        errors,
    )
    require_text("requirements.txt", "scikit-learn==1.9.0", errors)
    require_text("Dockerfile", "FROM python:3.11-slim", errors)
    require_text("Dockerfile", 'CMD ["uvicorn", "app.main:app"', errors)
    require_text(
        ".github/workflows/deploy.yml",
        'python-version: "3.11"',
        errors,
    )
    require_text(
        ".github/workflows/deploy.yml",
        'PYTHONPATH=apps/api:src pytest -m "not audio"',
        errors,
    )

    if errors:
        print("Repository consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
