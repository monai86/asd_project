"""Plan and optionally run CLAN commands for curated English child transcripts.

This script is intentionally an orchestration layer. It writes an auditable
run manifest and QC summary, but v1 does not parse CLAN metric values back into
the project reference feature tables.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "english_child_transcript_manifest.csv"
RUN_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "english_child_clan_run_manifest.csv"
QC_SUMMARY_PATH = PROJECT_ROOT / "data" / "manifests" / "english_child_clan_qc_summary.csv"
RAW_OUTPUT_DIR = PROJECT_ROOT / "data" / "clan" / "raw_outputs"

CLAN_COMMANDS = ("check", "mlu", "freq", "vocd", "kideval")
PER_FILE_COMMANDS = ("check", "kideval")
PER_CORPUS_COMMANDS = ("mlu", "freq", "vocd")
STDIN_COMMANDS = {"check", "kideval"}

RUN_MANIFEST_COLUMNS = [
    "job_id",
    "source_path",
    "curated_path",
    "corpus",
    "bank",
    "sha256",
    "command",
    "run_scope",
    "status",
    "exit_code",
    "output_path",
    "stderr_path",
    "artifact_path",
    "stdin_path",
    "run_started_at",
    "run_finished_at",
    "clan_available",
    "skip_reason",
    "qc_status",
    "transcript_count",
    "command_line",
]

QC_SUMMARY_COLUMNS = [
    "command",
    "run_scope",
    "status",
    "qc_status",
    "skip_reason",
    "row_count",
]


@dataclass(frozen=True)
class ClanJob:
    job_id: str
    command: str
    run_scope: str
    corpus: str
    bank: str
    rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class CommandResult:
    returncode: int


CommandLocator = Callable[[str], str | None]
CommandRunner = Callable[[Sequence[str], Path, Path, Path | None, Path | None], CommandResult]


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _relative(path: Path, root: Path = PROJECT_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _resolve_path(value: str, project_root: Path = PROJECT_ROOT) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def load_manifest_rows(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def analysis_ready_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if _truthy(row.get("analysis_ready"))]


def select_manifest_rows(
    rows: Iterable[dict[str, str]],
    *,
    corpus: str | None = None,
    max_files: int | None = None,
) -> list[dict[str, str]]:
    selected = [row for row in rows if corpus is None or row.get("corpus") == corpus]
    if max_files is not None:
        selected = selected[:max_files]
    return selected


def build_clan_jobs(rows: Iterable[dict[str, str]]) -> list[ClanJob]:
    ready_rows = list(rows)
    jobs: list[ClanJob] = []

    for index, row in enumerate(ready_rows, start=1):
        corpus = row.get("corpus", "") or "unknown"
        for command in PER_FILE_COMMANDS:
            jobs.append(
                ClanJob(
                    job_id=f"{command}:{corpus}:{index}",
                    command=command,
                    run_scope="file",
                    corpus=corpus,
                    bank=row.get("bank", ""),
                    rows=(row,),
                )
            )

    by_corpus: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in ready_rows:
        key = (row.get("corpus", "") or "unknown", row.get("bank", ""))
        by_corpus.setdefault(key, []).append(row)

    for (corpus, bank), corpus_rows in sorted(by_corpus.items()):
        for command in PER_CORPUS_COMMANDS:
            jobs.append(
                ClanJob(
                    job_id=f"{command}:{corpus}",
                    command=command,
                    run_scope="corpus",
                    corpus=corpus,
                    bank=bank,
                    rows=tuple(corpus_rows),
                )
            )

    return jobs


def filter_jobs(
    jobs: Iterable[ClanJob],
    *,
    commands: set[str] | None = None,
    limit: int | None = None,
) -> list[ClanJob]:
    """Return jobs filtered for smoke runs without changing default planning."""
    filtered = [job for job in jobs if commands is None or job.command in commands]
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def availability_map(
    commands: Iterable[str] = CLAN_COMMANDS,
    *,
    command_locator: CommandLocator = shutil.which,
) -> dict[str, str | None]:
    return {command: command_locator(command) for command in commands}


def command_locator_with_bin_dir(clan_bin_dir: Path | None = None) -> CommandLocator:
    def locate(command: str) -> str | None:
        if clan_bin_dir is not None:
            candidate = clan_bin_dir / command
            if candidate.exists() and os.access(candidate, os.X_OK):
                return candidate.as_posix()
        return shutil.which(command)

    return locate


def output_paths(job: ClanJob, raw_output_dir: Path = RAW_OUTPUT_DIR) -> tuple[Path, Path, Path]:
    command_dir = raw_output_dir / job.command / job.corpus
    if job.run_scope == "file":
        row = job.rows[0]
        sha = (row.get("sha256") or "nohash")[:12]
        stem = Path(row.get("curated_path") or row.get("source_path") or "transcript").stem
        base = f"{stem}.{sha}"
    else:
        base = job.corpus
    return (
        command_dir / f"{base}.stdout.txt",
        command_dir / f"{base}.stderr.txt",
        command_dir / f"{base}.filelist.txt",
    )


def artifact_path(job: ClanJob, raw_output_dir: Path = RAW_OUTPUT_DIR) -> Path | None:
    if job.command != "kideval":
        return None
    output_path, _, _ = output_paths(job, raw_output_dir)
    return output_path.parent / output_path.name.replace(".stdout.txt", ".kideval.xls")


def stdin_path(job: ClanJob, *, project_root: Path = PROJECT_ROOT) -> Path | None:
    if job.command not in STDIN_COMMANDS or job.run_scope != "file":
        return None
    return _resolve_path(job.rows[0].get("curated_path", ""), project_root)


def planned_command_args(
    job: ClanJob,
    command_path: str | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
    raw_output_dir: Path = RAW_OUTPUT_DIR,
) -> list[str]:
    executable = command_path or job.command
    if job.run_scope == "file":
        if job.command == "kideval":
            return [executable, "+t*CHI", "-leng"]
        if job.command in STDIN_COMMANDS:
            return [executable]
        transcript = _resolve_path(job.rows[0].get("curated_path", ""), project_root)
        return [executable, transcript.as_posix()]
    _, _, filelist_path = output_paths(job, raw_output_dir)
    return [executable, "+t*CHI", f"@{filelist_path.as_posix()}"]


def _job_identity(job: ClanJob) -> dict[str, str]:
    if job.run_scope == "file":
        row = job.rows[0]
        return {
            "source_path": row.get("source_path", ""),
            "curated_path": row.get("curated_path", ""),
            "corpus": row.get("corpus", "") or job.corpus,
            "bank": row.get("bank", "") or job.bank,
            "sha256": row.get("sha256", ""),
        }
    return {
        "source_path": "",
        "curated_path": "",
        "corpus": job.corpus,
        "bank": job.bank,
        "sha256": "",
    }


def _row_for_job(
    job: ClanJob,
    *,
    status: str,
    clan_available: bool,
    output_path: Path,
    stderr_path: Path,
    artifact_output_path: Path | None = None,
    stdin_input_path: Path | None = None,
    exit_code: int | str = "",
    skip_reason: str = "",
    started_at: str = "",
    finished_at: str = "",
    project_root: Path = PROJECT_ROOT,
    raw_output_dir: Path = RAW_OUTPUT_DIR,
    command_path: str | None = None,
) -> dict[str, object]:
    qc_status = "pass" if status in {"planned", "completed"} else "warn" if status == "clan_unavailable" else "fail"
    identity = _job_identity(job)
    command_parts = planned_command_args(job, None, project_root=project_root, raw_output_dir=raw_output_dir)
    if stdin_input_path is not None:
        command_parts = [*command_parts, "<", _relative(stdin_input_path, project_root)]
    command_line = " ".join(command_parts)
    return {
        "job_id": job.job_id,
        **identity,
        "command": job.command,
        "run_scope": job.run_scope,
        "status": status,
        "exit_code": exit_code,
        "output_path": _relative(output_path, project_root),
        "stderr_path": _relative(stderr_path, project_root),
        "artifact_path": _relative(artifact_output_path, project_root) if artifact_output_path else "",
        "stdin_path": _relative(stdin_input_path, project_root) if stdin_input_path else "",
        "run_started_at": started_at,
        "run_finished_at": finished_at,
        "clan_available": clan_available,
        "skip_reason": skip_reason,
        "qc_status": qc_status,
        "transcript_count": len(job.rows),
        "command_line": command_line,
    }


def _default_runner(
    command_args: Sequence[str],
    output_path: Path,
    stderr_path: Path,
    stdin_input_path: Path | None = None,
    cwd: Path | None = None,
) -> CommandResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        stdin_handle = stdin_input_path.open("rb") if stdin_input_path is not None else None
        completed = subprocess.run(
            list(command_args),
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=stdin_handle,
            cwd=cwd,
            check=False,
        )
        if stdin_handle is not None:
            stdin_handle.close()
    return CommandResult(returncode=completed.returncode)


def _write_filelist(job: ClanJob, filelist_path: Path, *, project_root: Path = PROJECT_ROOT) -> None:
    filelist_path.parent.mkdir(parents=True, exist_ok=True)
    transcripts = [_resolve_path(row.get("curated_path", ""), project_root).as_posix() for row in job.rows]
    filelist_path.write_text("\n".join(transcripts) + "\n", encoding="utf-8")


def run_job(
    job: ClanJob,
    *,
    dry_run: bool,
    command_path: str | None,
    project_root: Path = PROJECT_ROOT,
    raw_output_dir: Path = RAW_OUTPUT_DIR,
    command_runner: CommandRunner = _default_runner,
) -> dict[str, object]:
    output_path, stderr_path, filelist_path = output_paths(job, raw_output_dir)
    kideval_artifact_path = artifact_path(job, raw_output_dir)
    job_stdin_path = stdin_path(job, project_root=project_root)
    clan_available = bool(command_path)

    if not clan_available:
        return _row_for_job(
            job,
            status="clan_unavailable",
            clan_available=False,
            output_path=output_path,
            stderr_path=stderr_path,
            artifact_output_path=kideval_artifact_path,
            stdin_input_path=job_stdin_path,
            skip_reason=f"missing_{job.command}_command",
            project_root=project_root,
            raw_output_dir=raw_output_dir,
        )

    missing_inputs = [
        row.get("curated_path", "")
        for row in job.rows
        if not row.get("curated_path") or not _resolve_path(row.get("curated_path", ""), project_root).exists()
    ]
    if missing_inputs:
        return _row_for_job(
            job,
            status="skipped",
            clan_available=True,
            output_path=output_path,
            stderr_path=stderr_path,
            artifact_output_path=kideval_artifact_path,
            stdin_input_path=job_stdin_path,
            skip_reason="missing_curated_file",
            project_root=project_root,
            raw_output_dir=raw_output_dir,
            command_path=command_path,
        )

    if dry_run:
        return _row_for_job(
            job,
            status="planned",
            clan_available=True,
            output_path=output_path,
            stderr_path=stderr_path,
            artifact_output_path=kideval_artifact_path,
            stdin_input_path=job_stdin_path,
            project_root=project_root,
            raw_output_dir=raw_output_dir,
            command_path=command_path,
        )

    if job.run_scope == "corpus":
        _write_filelist(job, filelist_path, project_root=project_root)
    command_args = planned_command_args(job, command_path, project_root=project_root, raw_output_dir=raw_output_dir)
    started_at = _now()
    result = command_runner(command_args, output_path, stderr_path, job_stdin_path, output_path.parent)
    finished_at = _now()
    if kideval_artifact_path is not None:
        pipeout_path = output_path.parent / "pipeout.kideval.xls"
        if pipeout_path.exists():
            kideval_artifact_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(pipeout_path, kideval_artifact_path)
    status = "completed" if result.returncode == 0 else "failed"
    return _row_for_job(
        job,
        status=status,
        clan_available=True,
        output_path=output_path,
        stderr_path=stderr_path,
        artifact_output_path=kideval_artifact_path,
        stdin_input_path=job_stdin_path,
        exit_code=result.returncode,
        skip_reason="" if result.returncode == 0 else "nonzero_exit",
        started_at=started_at,
        finished_at=finished_at,
        project_root=project_root,
        raw_output_dir=raw_output_dir,
        command_path=command_path,
    )


def build_qc_summary(manifest_rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    counts: Counter[tuple[str, str, str, str, str]] = Counter()
    for row in manifest_rows:
        key = (
            str(row.get("command", "")),
            str(row.get("run_scope", "")),
            str(row.get("status", "")),
            str(row.get("qc_status", "")),
            str(row.get("skip_reason", "")),
        )
        counts[key] += 1

    return [
        {
            "command": command,
            "run_scope": run_scope,
            "status": status,
            "qc_status": qc_status,
            "skip_reason": skip_reason,
            "row_count": count,
        }
        for (command, run_scope, status, qc_status, skip_reason), count in sorted(counts.items())
    ]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_clan_batch(
    *,
    manifest_path: Path = MANIFEST_PATH,
    run_manifest_path: Path = RUN_MANIFEST_PATH,
    qc_summary_path: Path = QC_SUMMARY_PATH,
    execute: bool = False,
    project_root: Path = PROJECT_ROOT,
    raw_output_dir: Path = RAW_OUTPUT_DIR,
    command_locator: CommandLocator = shutil.which,
    command_runner: CommandRunner = _default_runner,
    commands: set[str] | None = None,
    limit: int | None = None,
    corpus: str | None = None,
    max_files: int | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    manifest_rows = select_manifest_rows(
        analysis_ready_rows(load_manifest_rows(manifest_path)),
        corpus=corpus,
        max_files=max_files,
    )
    jobs = filter_jobs(build_clan_jobs(manifest_rows), commands=commands, limit=limit)
    availability = availability_map(command_locator=command_locator)
    dry_run = not execute

    run_rows = [
        run_job(
            job,
            dry_run=dry_run,
            command_path=availability.get(job.command),
            project_root=project_root,
            raw_output_dir=raw_output_dir,
            command_runner=command_runner,
        )
        for job in jobs
    ]
    qc_rows = build_qc_summary(run_rows)
    write_csv(run_manifest_path, run_rows, RUN_MANIFEST_COLUMNS)
    write_csv(qc_summary_path, qc_rows, QC_SUMMARY_COLUMNS)
    return run_rows, qc_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--run-manifest", type=Path, default=RUN_MANIFEST_PATH)
    parser.add_argument("--qc-summary", type=Path, default=QC_SUMMARY_PATH)
    parser.add_argument("--raw-output-dir", type=Path, default=RAW_OUTPUT_DIR)
    parser.add_argument("--clan-bin-dir", type=Path, default=None, help="Directory containing CLAN command binaries.")
    parser.add_argument("--execute", action="store_true", help="Run CLAN commands. Default is dry-run planning only.")
    parser.add_argument(
        "--commands",
        default=",".join(CLAN_COMMANDS),
        help="Comma-separated CLAN command subset for smoke runs, e.g. check,kideval.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit planned jobs after command filtering.")
    parser.add_argument("--corpus", default=None, help="Limit manifest rows to one corpus before planning jobs.")
    parser.add_argument("--max-files", type=int, default=None, help="Limit manifest rows before planning jobs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_rows, qc_rows = run_clan_batch(
        manifest_path=args.manifest,
        run_manifest_path=args.run_manifest,
        qc_summary_path=args.qc_summary,
        raw_output_dir=args.raw_output_dir,
        execute=args.execute,
        command_locator=command_locator_with_bin_dir(args.clan_bin_dir),
        commands={item.strip() for item in args.commands.split(",") if item.strip()},
        limit=args.limit,
        corpus=args.corpus,
        max_files=args.max_files,
    )
    status_counts = Counter(str(row["status"]) for row in run_rows)
    mode = "execute" if args.execute else "dry-run"
    print(f"CLAN batch {mode}: wrote {len(run_rows)} manifest row(s).")
    for status, count in sorted(status_counts.items()):
        print(f"{status}: {count}")
    print(f"Run manifest: {_relative(args.run_manifest)}")
    print(f"QC summary: {_relative(args.qc_summary)} ({len(qc_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
