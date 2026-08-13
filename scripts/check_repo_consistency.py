"""Fail fast when repository source-of-truth boundaries drift."""

from __future__ import annotations

from pathlib import Path
import sys

sys.dont_write_bytecode = True

from release_scope import consistency_violations


ROOT = Path(__file__).resolve().parents[1]
PROJECT_VERSION = "v1.6.3"


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
    print("Using canonical filesystem release policy for consistency check.")

    for path in (
        "apps/api/app/main.py",
        "apps/lingualens-app/package.json",
        "docs/PROJECT_SOURCE_OF_TRUTH.md",
        "docs/REPO_STRUCTURE.md",
    ):
        require_path(path, errors)

    errors.extend(consistency_violations(ROOT, ignore_local_runtime=True))
    for path in sorted(p.as_posix() for p in ROOT.rglob("*") if p.is_file()):
        path = Path(path).relative_to(ROOT).as_posix()
        if path.startswith("therapist-clinician-app/"):
            errors.append(f"retired therapist app file exists: {path}")
        if path.startswith(("public-screening/", "presentation-dashboard/")):
            errors.append(f"removed demo surface exists: {path}")

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
    require_text("pyproject.toml", 'requires-python = ">=3.11,<3.14"', errors)
    require_text(".python-version", "3.12", errors)
    require_text(".github/workflows/deploy.yml", '["3.11", "3.12", "3.13"]', errors)
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
