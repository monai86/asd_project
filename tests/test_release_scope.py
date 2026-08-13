from pathlib import Path
import shutil
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from release_scope import consistency_violations, source_files  # noqa: E402


def write(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic fixture", encoding="utf-8")


def verdict(root: Path) -> list[str]:
    return consistency_violations(root)


def test_git_filesystem_and_extracted_tree_have_identical_verdict(tmp_path):
    source = tmp_path / "source"
    write(source, "apps/api/app/main.py")
    write(source, "data/fixtures/approved.txt")
    write(source, "docs/archive/planning/historical.md")
    (source / ".git").mkdir()

    without_git = tmp_path / "without-git"
    shutil.copytree(source, without_git, ignore=shutil.ignore_patterns(".git"))
    archive = tmp_path / "review.zip"
    with ZipFile(archive, "w") as bundle:
        for path in without_git.rglob("*"):
            if path.is_file():
                bundle.write(path, path.relative_to(without_git))
    extracted = tmp_path / "extracted"
    with ZipFile(archive) as bundle:
        bundle.extractall(extracted)

    assert verdict(source) == verdict(without_git) == verdict(extracted) == []


def test_forbidden_cases_are_independent_of_git_tracking(tmp_path):
    cases = {
        "apps/tracked.zip": "forbidden file type",
        "apps/untracked.zip": "forbidden file type",
        "data/raw/corpus.zip": "raw corpus archive",
        "apps/.DS_Store": "forbidden local/secret file",
        "docs/superpowers/plans/current.md": "forbidden directory",
    }
    for relative in cases:
        write(tmp_path, relative)
    (tmp_path / ".git").mkdir()
    errors = verdict(tmp_path)
    for relative, message in cases.items():
        assert any(relative in error and message in error for error in errors)


def test_local_consistency_mode_ignores_runtime_caches_but_not_release_content(tmp_path):
    write(tmp_path, ".venv/bin/python")
    write(tmp_path, ".venv313/lib/python3.13/site-packages/package/data.json.gz")
    write(tmp_path, "apps/lingualens-app/node_modules/pkg/index.js")
    write(tmp_path, "apps/lingualens-app/.next/types/app.d.ts")
    write(tmp_path, "apps/lingualens-app/tsconfig.tsbuildinfo")
    write(tmp_path, "apps/tracked.zip")

    errors = consistency_violations(tmp_path, ignore_local_runtime=True)

    assert not any(".venv" in error or "node_modules" in error or ".next" in error or "tsbuildinfo" in error for error in errors)
    assert any("apps/tracked.zip" in error for error in errors)


def test_local_consistency_mode_ignores_tool_state_and_linked_worktrees(tmp_path):
    write(tmp_path, ".freebuff/desktop-v2.db")
    write(tmp_path, ".worktrees/feature/tests/fixtures/audio/sample.wav")

    errors = consistency_violations(tmp_path, ignore_local_runtime=True)

    assert errors == []


def test_source_archive_skips_local_runtime_artifacts_below_approved_roots(tmp_path):
    write(tmp_path, "apps/api/app/main.py")
    write(tmp_path, "apps/api/.local/repository.json")
    write(tmp_path, "apps/api/app/__pycache__/main.pyc")
    write(tmp_path, "apps/lingualens-app/node_modules/pkg/index.js")
    write(tmp_path, "apps/lingualens-app/.next/server/app.js")
    write(tmp_path, "apps/lingualens-app/tsconfig.tsbuildinfo")

    selected = {relative.as_posix() for _, relative in source_files(tmp_path)}

    assert selected == {"apps/api/app/main.py"}


def test_source_archive_includes_root_design_authority(tmp_path):
    write(tmp_path, "DESIGN.md")
    write(tmp_path, "apps/lingualens-app/DESIGN.md")

    selected = {relative.as_posix() for _, relative in source_files(tmp_path)}

    assert selected == {"DESIGN.md", "apps/lingualens-app/DESIGN.md"}
