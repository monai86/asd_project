from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_clan_batch import (  # noqa: E402
    CommandResult,
    build_clan_jobs,
    command_locator_with_bin_dir,
    filter_jobs,
    run_clan_batch,
    select_manifest_rows,
)


INPUT_COLUMNS = [
    "source_path",
    "curated_path",
    "corpus",
    "bank",
    "languages_raw",
    "has_chi_id",
    "has_chi_tier",
    "child_utterance_count",
    "child_token_count",
    "eligible_english_child_transcript",
    "analysis_ready",
    "exclude_reason",
    "sha256",
    "download_date",
    "qc_status",
]


def write_transcript(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "@UTF8",
                "@Begin",
                "@Languages:\teng",
                "@Participants:\tCHI Child Target_Child",
                "@ID:\teng|Test|CHI|4;00.00|female|TD||Target_Child|||",
                "*CHI:\tI want cookie .",
                "@End",
            ]
        ),
        encoding="utf-8",
    )
    return path


def manifest_row(
    project_root: Path,
    curated_path: Path,
    *,
    corpus: str = "Synthetic",
    analysis_ready: bool = True,
    sha256: str = "abcdef123456",
) -> dict[str, str]:
    try:
        curated_value = curated_path.relative_to(project_root).as_posix()
    except ValueError:
        curated_value = curated_path.as_posix()
    return {
        "source_path": f"data/raw/talkbank/ChildBank/{corpus}/download_2026-05-31/{curated_path.name}",
        "curated_path": curated_value,
        "corpus": corpus,
        "bank": "ChildBank",
        "languages_raw": "eng",
        "has_chi_id": "True",
        "has_chi_tier": "True",
        "child_utterance_count": "50",
        "child_token_count": "150",
        "eligible_english_child_transcript": "True",
        "analysis_ready": str(analysis_ready),
        "exclude_reason": "",
        "sha256": sha256,
        "download_date": "2026-05-31",
        "qc_status": "pass",
    }


def write_manifest(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def all_commands_available(command: str) -> str:
    return f"/fake-clan/{command}"


def test_build_jobs_uses_analysis_ready_rows_and_plans_check_per_file_corpus_metrics(tmp_path):
    ready_a = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "a.cha"), sha256="a" * 64)
    ready_b = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "b.cha"), sha256="b" * 64)
    not_ready = manifest_row(
        tmp_path,
        write_transcript(tmp_path / "curated" / "Synthetic" / "short.cha"),
        analysis_ready=False,
        sha256="c" * 64,
    )

    jobs = build_clan_jobs([ready_a, ready_b])
    manifest = write_manifest(tmp_path / "manifest.csv", [ready_a, ready_b, not_ready])

    def forbidden_runner(command_args, output_path, stderr_path, stdin_path, cwd):  # noqa: ARG001
        raise AssertionError("dry-run must not call subprocess")

    run_rows, qc_rows = run_clan_batch(
        manifest_path=manifest,
        run_manifest_path=tmp_path / "run.csv",
        qc_summary_path=tmp_path / "qc.csv",
        raw_output_dir=tmp_path / "raw_outputs",
        project_root=tmp_path,
        command_locator=all_commands_available,
        command_runner=forbidden_runner,
    )

    assert [job.command for job in jobs].count("check") == 2
    assert [job.command for job in jobs].count("kideval") == 2
    assert len(jobs) == 7
    assert len(run_rows) == 7
    assert {row["status"] for row in run_rows} == {"planned"}
    assert {row["qc_status"] for row in run_rows} == {"pass"}
    assert all("short.cha" not in str(row["command_line"]) for row in run_rows)
    assert not (tmp_path / "raw_outputs").exists()
    assert read_csv(tmp_path / "run.csv")
    assert qc_rows == [
        {
            "command": "check",
            "run_scope": "file",
            "status": "planned",
            "qc_status": "pass",
            "skip_reason": "",
            "row_count": 2,
        },
        {
            "command": "freq",
            "run_scope": "corpus",
            "status": "planned",
            "qc_status": "pass",
            "skip_reason": "",
            "row_count": 1,
        },
        {
            "command": "kideval",
            "run_scope": "file",
            "status": "planned",
            "qc_status": "pass",
            "skip_reason": "",
            "row_count": 2,
        },
        {
            "command": "mlu",
            "run_scope": "corpus",
            "status": "planned",
            "qc_status": "pass",
            "skip_reason": "",
            "row_count": 1,
        },
        {
            "command": "vocd",
            "run_scope": "corpus",
            "status": "planned",
            "qc_status": "pass",
            "skip_reason": "",
            "row_count": 1,
        },
    ]


def test_execute_without_clan_records_unavailable_and_does_not_crash(tmp_path):
    ready = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "a.cha"))
    manifest = write_manifest(tmp_path / "manifest.csv", [ready])

    run_rows, qc_rows = run_clan_batch(
        manifest_path=manifest,
        run_manifest_path=tmp_path / "run.csv",
        qc_summary_path=tmp_path / "qc.csv",
        raw_output_dir=tmp_path / "raw_outputs",
        execute=True,
        project_root=tmp_path,
        command_locator=lambda command: None,
    )

    assert len(run_rows) == 5
    assert {row["status"] for row in run_rows} == {"clan_unavailable"}
    assert {row["qc_status"] for row in run_rows} == {"warn"}
    assert all(str(row["skip_reason"]).startswith("missing_") for row in run_rows)
    assert not (tmp_path / "raw_outputs").exists()
    assert {row["status"] for row in qc_rows} == {"clan_unavailable"}


def test_execute_records_failure_and_continues_to_later_jobs(tmp_path):
    ready_a = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "a.cha"), sha256="a" * 64)
    ready_b = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "b.cha"), sha256="b" * 64)
    manifest = write_manifest(tmp_path / "manifest.csv", [ready_a, ready_b])
    calls = []

    def runner(command_args, output_path, stderr_path, stdin_path, cwd):
        calls.append(command_args)
        assert cwd == output_path.parent
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("stdout\n", encoding="utf-8")
        stderr_path.write_text("stderr\n", encoding="utf-8")
        return CommandResult(returncode=1 if len(calls) == 1 else 0)

    run_rows, qc_rows = run_clan_batch(
        manifest_path=manifest,
        run_manifest_path=tmp_path / "run.csv",
        qc_summary_path=tmp_path / "qc.csv",
        raw_output_dir=tmp_path / "raw_outputs",
        execute=True,
        project_root=tmp_path,
        command_locator=all_commands_available,
        command_runner=runner,
    )

    assert len(calls) == 7
    assert [row["status"] for row in run_rows].count("failed") == 1
    assert [row["status"] for row in run_rows].count("completed") == 6
    assert any(row["exit_code"] == 1 for row in run_rows)
    assert any(row["status"] == "failed" and row["skip_reason"] == "nonzero_exit" for row in run_rows)
    assert (tmp_path / "raw_outputs").exists()
    assert {row["status"] for row in qc_rows} == {"completed", "failed"}


def test_execute_with_missing_curated_path_records_skipped(tmp_path):
    missing = manifest_row(tmp_path, tmp_path / "curated" / "Synthetic" / "missing.cha")
    manifest = write_manifest(tmp_path / "manifest.csv", [missing])

    run_rows, qc_rows = run_clan_batch(
        manifest_path=manifest,
        run_manifest_path=tmp_path / "run.csv",
        qc_summary_path=tmp_path / "qc.csv",
        raw_output_dir=tmp_path / "raw_outputs",
        execute=True,
        project_root=tmp_path,
        command_locator=all_commands_available,
    )

    assert {row["status"] for row in run_rows} == {"skipped"}
    assert {row["skip_reason"] for row in run_rows} == {"missing_curated_file"}
    assert {row["qc_status"] for row in run_rows} == {"fail"}
    assert {row["skip_reason"] for row in qc_rows} == {"missing_curated_file"}


def test_filter_jobs_supports_kideval_smoke_subset(tmp_path):
    ready_a = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "a.cha"), sha256="a" * 64)
    ready_b = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "b.cha"), sha256="b" * 64)
    jobs = build_clan_jobs([ready_a, ready_b])

    smoke_jobs = filter_jobs(jobs, commands={"kideval"}, limit=1)

    assert len(smoke_jobs) == 1
    assert smoke_jobs[0].command == "kideval"
    assert smoke_jobs[0].run_scope == "file"


def test_select_manifest_rows_filters_before_planning_smoke_jobs(tmp_path):
    ready_a = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "a.cha"), sha256="a" * 64)
    ready_b = manifest_row(tmp_path, write_transcript(tmp_path / "curated" / "Synthetic" / "b.cha"), sha256="b" * 64)
    ready_c = manifest_row(
        tmp_path,
        write_transcript(tmp_path / "curated" / "Other" / "c.cha"),
        corpus="Other",
        sha256="c" * 64,
    )

    selected = select_manifest_rows([ready_a, ready_b, ready_c], corpus="Synthetic", max_files=1)
    jobs = filter_jobs(build_clan_jobs(selected), commands={"check", "kideval"})

    assert [job.command for job in jobs] == ["check", "kideval"]
    assert {job.corpus for job in jobs} == {"Synthetic"}


def test_command_locator_with_bin_dir_prefers_explicit_clan_binary(tmp_path):
    bin_dir = tmp_path / "clan-bin"
    bin_dir.mkdir()
    command = bin_dir / "kideval"
    command.write_text("#!/bin/sh\n", encoding="utf-8")
    command.chmod(0o755)

    locate = command_locator_with_bin_dir(bin_dir)

    assert locate("kideval") == command.as_posix()
