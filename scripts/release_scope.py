"""Canonical filesystem policy for source review and repository hygiene."""

from __future__ import annotations

from pathlib import Path


APPROVED_ROOTS = (
    "apps",
    "packages",
    "src",
    "tests",
    "scripts",
    "migrations",
    "supabase",
    "docs",
    "artifacts",
    "data/fixtures",
    "data/manifests",
    "data/demo",
    "data/evaluation",
    "data/reference",
    ".github",
)
APPROVED_FILES = (
    ".env.example",
    ".python-version",
    "DESIGN.md",
    "README.md",
    "DEVELOPER_SETUP.md",
    "PROJECT_STATUS.md",
    "SCOPE_AND_DELIVERABLES.md",
    "CHANGELOG.md",
    "Dockerfile",
    "pyproject.toml",
    "pytest.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "data/combined_features.csv",
    "data/longitudinal_features.csv",
    "data/rollins_features.csv",
    "data/metadata.example.csv",
)
FORBIDDEN_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".local",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "coverage",
    "dist",
    "build",
    ".open-next",
    "uploads",
    "release_artifacts",
    "superpowers",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tsbuildinfo",
    ".sqlite",
    ".db",
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".zip",
    ".tar",
    ".gz",
    ".docx",
}
ARCHIVED_DOCUMENT_ROOT = "docs/archive/planning"
LOCAL_ONLY_ROOTS = {
    ".agents",
    ".codex",
    "data/raw",
    "data/curated",
    "docs/release_artifacts",
    "releases",
}
LOCAL_RUNTIME_DIR_NAMES = {
    ".freebuff",
    ".worktrees",
    ".venv",
    "venv",
    "node_modules",
    ".local",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "coverage",
    "dist",
    "build",
    ".open-next",
    "uploads",
}
LOCAL_RUNTIME_SUFFIXES = {".pyc", ".pyo", ".tsbuildinfo"}


def is_local_runtime_path(path: Path) -> bool:
    return bool(
        set(path.parts) & LOCAL_RUNTIME_DIR_NAMES
        or any(part.startswith(".venv") for part in path.parts)
        or path.suffix.lower() in LOCAL_RUNTIME_SUFFIXES
    )


def relative_files(root: Path) -> set[str]:
    """Return the same normalized filesystem view with or without Git metadata."""
    files: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        files.add(relative.as_posix())
    return files


def forbidden_reason(relative: str | Path) -> str | None:
    path = Path(relative)
    if set(path.parts) & FORBIDDEN_DIR_NAMES:
        return f"forbidden directory: {path.as_posix()}"
    if path.name == ".DS_Store" or path.name == ".env" or (
        path.name.startswith(".env.") and path.name != ".env.example"
    ):
        return f"forbidden local/secret file: {path.as_posix()}"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return f"forbidden file type: {path.as_posix()}"
    if path.as_posix().startswith(("scratch/", "docs/superpowers/")):
        return f"unclassified planning file: {path.as_posix()}"
    return None


def is_local_only(relative: str | Path) -> bool:
    value = Path(relative).as_posix()
    return any(value == root or value.startswith(root + "/") for root in LOCAL_ONLY_ROOTS)


def is_approved_source(relative: str | Path) -> bool:
    value = Path(relative).as_posix()
    if value in APPROVED_FILES:
        return True
    return any(value == root or value.startswith(root + "/") for root in APPROVED_ROOTS)


def source_files(root: Path) -> list[tuple[Path, Path]]:
    selected: list[tuple[Path, Path]] = []
    violations: list[str] = []
    for value in sorted(relative_files(root)):
        relative = Path(value)
        if is_local_only(relative) or not is_approved_source(relative):
            continue
        # Runtime/build artifacts are intentionally absent from a source-review
        # archive even when they exist below an otherwise approved source root.
        # Keep rejecting forbidden source content (for example .DS_Store), while
        # treating caches and dependency trees as local-only inputs.
        if is_local_runtime_path(relative):
            continue
        reason = forbidden_reason(relative)
        if reason:
            violations.append(reason)
        else:
            selected.append((root / relative, relative))
    if violations:
        raise ValueError("\n".join(violations))
    return selected


def consistency_violations(root: Path, *, ignore_local_runtime: bool = False) -> list[str]:
    """Evaluate hygiene without consulting Git, including local raw archives."""
    violations: list[str] = []
    for value in sorted(relative_files(root)):
        path = Path(value)
        if ignore_local_runtime and is_local_runtime_path(path):
            continue
        if value.startswith("data/raw/") and path.suffix.lower() in {".zip", ".tar", ".gz"}:
            violations.append(f"raw corpus archive exists: {value}")
            continue
        reason = forbidden_reason(path)
        if reason and not is_local_only(path):
            violations.append(reason)
    return violations
