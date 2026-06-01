"""Intake and audit TalkBank transcript downloads for the ASD project.

This script does not log in to TalkBank or download files from the network.
It organizes files that were downloaded manually/browser-assisted into a raw
mirror, records checksums, and runs lightweight CHAT transcript QC.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_TALKBANK_DIR = DATA_DIR / "raw" / "talkbank"
MANIFEST_DIR = DATA_DIR / "manifests"
DOWNLOAD_MANIFEST_PATH = MANIFEST_DIR / "talkbank_download_manifest.csv"
FILE_INVENTORY_PATH = MANIFEST_DIR / "talkbank_file_inventory.csv"
QC_SUMMARY_PATH = MANIFEST_DIR / "talkbank_qc_summary.csv"

DEFAULT_EXISTING_AUDIT_CORPORA = ("Nadig", "NYU-Emerson")

MEDIA_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
}
INTAKE_EXTENSIONS = {
    ".cha",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".cdc",
    ".txt",
    ".zip",
    ".pdf",
    ".html",
    ".htm",
    ".md",
    ".xml",
    ".properties",
}

LANGUAGES_RE = re.compile(r"^@Languages:\s*(.+)$", re.MULTILINE)
PARTICIPANTS_RE = re.compile(r"^@Participants:\s*(.+)$", re.MULTILINE)
ID_RE = re.compile(r"^@ID:\s*(.+)$", re.MULTILINE)
ID_CHI_RE = re.compile(r"^@ID:\s*[^\n]*\|CHI\|", re.MULTILINE)
CHI_TIER_RE = re.compile(r"^\*CHI:\s*(.*)$", re.MULTILINE)
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


@dataclass(frozen=True)
class DownloadManifestRow:
    bank: str
    corpus: str
    source_status: str
    download_date: str
    source_dir: str
    raw_mirror_dir: str
    file_count: int
    archive_count: int
    transcript_count: int
    sidecar_count: int
    copied_file_count: int
    parse_pass_count: int
    parse_warn_count: int
    parse_fail_count: int
    qc_fail_count: int


@dataclass(frozen=True)
class FileInventoryRow:
    bank: str
    corpus: str
    source_status: str
    download_date: str
    source_path: str
    raw_mirror_path: str
    file_role: str
    file_extension: str
    file_size_bytes: int
    sha256: str
    copied_to_raw_mirror: bool
    parse_status: str
    qc_status: str
    qc_notes: str
    languages_raw: str
    participants_raw: str
    id_count: int
    has_begin: bool
    has_end: bool
    has_participants: bool
    has_id: bool
    has_chi_id: bool
    has_chi_tier: bool
    child_utterance_count: int
    child_token_count: int


@dataclass(frozen=True)
class TranscriptQc:
    parse_status: str
    qc_status: str
    qc_notes: str
    languages_raw: str
    participants_raw: str
    id_count: int
    has_begin: bool
    has_end: bool
    has_participants: bool
    has_id: bool
    has_chi_id: bool
    has_chi_tier: bool
    child_utterance_count: int
    child_token_count: int


def _relative(path: Path, root: Path = PROJECT_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_intake_candidate(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.startswith(".DS_Store"):
        return False
    suffix = path.suffix.lower()
    if suffix in MEDIA_EXTENSIONS:
        return False
    if path.name == "0types.txt":
        return True
    return suffix in INTAKE_EXTENSIONS


def file_role(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".cha":
        return "transcript"
    if suffix == ".zip":
        return "archive"
    if path.name == "0types.txt" or suffix in {".csv", ".tsv", ".xlsx", ".xls", ".cdc", ".txt"}:
        return "sidecar"
    return "documentation"


def child_utterance_texts(text: str) -> list[str]:
    return [match.group(1).strip() for match in CHI_TIER_RE.finditer(text)]


def count_child_tokens(child_lines: list[str]) -> int:
    total = 0
    for line in child_lines:
        cleaned = re.sub(r"\x15\d+_\d+\x15", " ", line)
        cleaned = re.sub(r"&=[^\s]+", " ", cleaned)
        cleaned = re.sub(r"\b(?:xxx|yyy|www)\b", " ", cleaned, flags=re.IGNORECASE)
        total += len(TOKEN_RE.findall(cleaned))
    return total


def pylangacq_parse_status(path: Path) -> str:
    try:
        import pylangacq
    except ImportError:
        return "skipped_missing_pylangacq"

    try:
        pylangacq.read_chat(str(path))
        return "pass"
    except Exception:
        try:
            pylangacq.read_chat(str(path), strict=False)
            return "warn_nonstrict"
        except Exception:
            return "fail"


def qc_transcript(path: Path) -> TranscriptQc:
    text = path.read_text(encoding="utf-8", errors="replace")
    languages_match = LANGUAGES_RE.search(text)
    participants_match = PARTICIPANTS_RE.search(text)
    id_lines = ID_RE.findall(text)
    child_lines = child_utterance_texts(text)
    has_begin = any(line.strip() == "@Begin" for line in text.splitlines())
    has_end = any(line.strip() == "@End" for line in text.splitlines())
    has_participants = participants_match is not None
    has_id = bool(id_lines)
    has_chi_id = bool(ID_CHI_RE.search(text))
    has_chi_tier = bool(child_lines)
    parse_status = pylangacq_parse_status(path)

    notes = []
    if not has_begin:
        notes.append("missing_begin")
    if not has_end:
        notes.append("missing_end")
    if not has_participants:
        notes.append("missing_participants")
    if not has_id:
        notes.append("missing_id")
    if not has_chi_tier:
        notes.append("missing_child_speech_tier")
    if parse_status == "fail":
        notes.append("pylangacq_parse_failed")
    elif parse_status == "warn_nonstrict":
        notes.append("pylangacq_nonstrict_only")

    blocker_notes = {
        "missing_begin",
        "missing_end",
        "missing_participants",
        "missing_id",
        "pylangacq_parse_failed",
    }
    if any(note in blocker_notes for note in notes):
        qc_status = "fail"
    elif notes:
        qc_status = "warn"
    else:
        qc_status = "pass"

    return TranscriptQc(
        parse_status=parse_status,
        qc_status=qc_status,
        qc_notes=";".join(notes),
        languages_raw=languages_match.group(1).strip() if languages_match else "",
        participants_raw=participants_match.group(1).strip() if participants_match else "",
        id_count=len(id_lines),
        has_begin=has_begin,
        has_end=has_end,
        has_participants=has_participants,
        has_id=has_id,
        has_chi_id=has_chi_id,
        has_chi_tier=has_chi_tier,
        child_utterance_count=len(child_lines),
        child_token_count=count_child_tokens(child_lines),
    )


def blank_qc() -> TranscriptQc:
    return TranscriptQc(
        parse_status="not_applicable",
        qc_status="not_applicable",
        qc_notes="",
        languages_raw="",
        participants_raw="",
        id_count=0,
        has_begin=False,
        has_end=False,
        has_participants=False,
        has_id=False,
        has_chi_id=False,
        has_chi_tier=False,
        child_utterance_count=0,
        child_token_count=0,
    )


def mirror_destination(source: Path, source_dir: Path, raw_mirror_dir: Path) -> Path:
    try:
        relative = source.resolve().relative_to(source_dir.resolve())
    except ValueError:
        relative = Path(source.name)
    return raw_mirror_dir / relative


def scan_intake_source(
    *,
    bank: str,
    corpus: str,
    download_date: str,
    source_dir: Path,
    raw_mirror_root: Path = RAW_TALKBANK_DIR,
    dry_run: bool = False,
    move_files: bool = False,
) -> list[FileInventoryRow]:
    raw_mirror_dir = raw_mirror_root / bank / corpus / f"download_{download_date}"
    rows: list[FileInventoryRow] = []
    for source in sorted(source_dir.rglob("*")):
        if not is_intake_candidate(source):
            continue
        destination = mirror_destination(source, source_dir, raw_mirror_dir)
        copied = False
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if move_files:
                shutil.move(str(source), str(destination))
            else:
                shutil.copy2(source, destination)
            copied = True
        inspected_path = destination if copied else source
        rows.append(build_file_row(
            bank=bank,
            corpus=corpus,
            source_status="raw_download",
            download_date=download_date,
            source_path=source,
            raw_mirror_path=destination,
            inspected_path=inspected_path,
            copied=copied,
        ))
    return rows


def audit_existing_corpus(corpus: str, *, data_dir: Path = DATA_DIR) -> list[FileInventoryRow]:
    source_dir = data_dir / corpus
    if not source_dir.exists():
        return []
    rows = []
    for source in sorted(source_dir.rglob("*")):
        if not is_intake_candidate(source):
            continue
        rows.append(build_file_row(
            bank="project_data",
            corpus=corpus,
            source_status="existing_project_data",
            download_date="",
            source_path=source,
            raw_mirror_path=Path(""),
            inspected_path=source,
            copied=False,
        ))
    return rows


def build_file_row(
    *,
    bank: str,
    corpus: str,
    source_status: str,
    download_date: str,
    source_path: Path,
    raw_mirror_path: Path,
    inspected_path: Path,
    copied: bool,
) -> FileInventoryRow:
    role = file_role(source_path)
    qc = qc_transcript(inspected_path) if role == "transcript" else blank_qc()
    return FileInventoryRow(
        bank=bank,
        corpus=corpus,
        source_status=source_status,
        download_date=download_date,
        source_path=_relative(source_path),
        raw_mirror_path=_relative(raw_mirror_path) if raw_mirror_path != Path("") else "",
        file_role=role,
        file_extension=source_path.suffix.lower(),
        file_size_bytes=inspected_path.stat().st_size,
        sha256=sha256(inspected_path),
        copied_to_raw_mirror=copied,
        **asdict(qc),
    )


def summarize_inventory(rows: list[FileInventoryRow]) -> list[DownloadManifestRow]:
    groups: dict[tuple[str, str, str, str, str], list[FileInventoryRow]] = {}
    for row in rows:
        if row.source_status == "raw_download":
            raw_dir = f"data/raw/talkbank/{row.bank}/{row.corpus}/download_{row.download_date}"
            key = (row.bank, row.corpus, row.source_status, row.download_date, raw_dir)
        else:
            key = (row.bank, row.corpus, row.source_status, row.download_date, "")
        groups.setdefault(key, []).append(row)

    manifest_rows = []
    for (bank, corpus, source_status, download_date, raw_mirror_dir), items in sorted(groups.items()):
        if source_status == "raw_download":
            source_dir = common_source_dir(items)
        else:
            source_dir = f"data/{corpus}"
        parse_pass = sum(item.parse_status == "pass" for item in items)
        parse_warn = sum(item.parse_status == "warn_nonstrict" for item in items)
        parse_fail = sum(item.parse_status == "fail" for item in items)
        manifest_rows.append(DownloadManifestRow(
            bank=bank,
            corpus=corpus,
            source_status=source_status,
            download_date=download_date,
            source_dir=source_dir,
            raw_mirror_dir=raw_mirror_dir,
            file_count=len(items),
            archive_count=sum(item.file_role == "archive" for item in items),
            transcript_count=sum(item.file_role == "transcript" for item in items),
            sidecar_count=sum(item.file_role == "sidecar" for item in items),
            copied_file_count=sum(item.copied_to_raw_mirror for item in items),
            parse_pass_count=parse_pass,
            parse_warn_count=parse_warn,
            parse_fail_count=parse_fail,
            qc_fail_count=sum(item.qc_status == "fail" for item in items),
        ))
    return manifest_rows


def common_source_dir(rows: list[FileInventoryRow]) -> str:
    parents = [str(Path(row.source_path).parent) for row in rows if row.source_path]
    if not parents:
        return ""
    import os

    return os.path.commonpath(parents)


def write_csv(path: Path, rows: list[object], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_outputs(
    inventory_rows: list[FileInventoryRow],
    *,
    manifest_path: Path = DOWNLOAD_MANIFEST_PATH,
    inventory_path: Path = FILE_INVENTORY_PATH,
    qc_summary_path: Path = QC_SUMMARY_PATH,
    append: bool = False,
) -> None:
    if append and inventory_path.exists():
        inventory_rows = merge_inventory(read_inventory(inventory_path), inventory_rows)
    manifest_rows = summarize_inventory(inventory_rows)
    write_csv(manifest_path, manifest_rows, list(DownloadManifestRow.__dataclass_fields__))
    write_csv(inventory_path, inventory_rows, list(FileInventoryRow.__dataclass_fields__))
    write_qc_summary(inventory_rows, qc_summary_path)


def read_inventory(path: Path) -> list[FileInventoryRow]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            values = dict(raw)
            for key in [
                "file_size_bytes",
                "id_count",
                "child_utterance_count",
                "child_token_count",
            ]:
                values[key] = int(values[key])
            for key in [
                "copied_to_raw_mirror",
                "has_begin",
                "has_end",
                "has_participants",
                "has_id",
                "has_chi_id",
                "has_chi_tier",
            ]:
                values[key] = str(values[key]).lower() == "true"
            rows.append(FileInventoryRow(**values))
    return rows


def merge_inventory(existing: list[FileInventoryRow], new_rows: list[FileInventoryRow]) -> list[FileInventoryRow]:
    by_key: dict[tuple[str, str, str, str, str], FileInventoryRow] = {}
    for row in existing + new_rows:
        key = (row.bank, row.corpus, row.source_status, row.source_path, row.raw_mirror_path)
        by_key[key] = row
    return sorted(by_key.values(), key=lambda row: (row.bank, row.corpus, row.source_status, row.source_path))


def write_qc_summary(rows: list[FileInventoryRow], path: Path) -> None:
    summary: dict[tuple[str, str, str, str], dict[str, int | str]] = {}
    for row in rows:
        if row.file_role != "transcript":
            continue
        key = (row.bank, row.corpus, row.source_status, row.qc_status)
        record = summary.setdefault(
            key,
            {
                "bank": row.bank,
                "corpus": row.corpus,
                "source_status": row.source_status,
                "qc_status": row.qc_status,
                "transcript_count": 0,
                "parse_pass_count": 0,
                "parse_warn_count": 0,
                "parse_fail_count": 0,
                "child_utterance_count": 0,
                "child_token_count": 0,
            },
        )
        record["transcript_count"] = int(record["transcript_count"]) + 1
        record["parse_pass_count"] = int(record["parse_pass_count"]) + int(row.parse_status == "pass")
        record["parse_warn_count"] = int(record["parse_warn_count"]) + int(row.parse_status == "warn_nonstrict")
        record["parse_fail_count"] = int(record["parse_fail_count"]) + int(row.parse_status == "fail")
        record["child_utterance_count"] = int(record["child_utterance_count"]) + row.child_utterance_count
        record["child_token_count"] = int(record["child_token_count"]) + row.child_token_count

    fieldnames = [
        "bank",
        "corpus",
        "source_status",
        "qc_status",
        "transcript_count",
        "parse_pass_count",
        "parse_warn_count",
        "parse_fail_count",
        "child_utterance_count",
        "child_token_count",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for record in sorted(summary.values(), key=lambda item: (str(item["bank"]), str(item["corpus"]), str(item["qc_status"]))):
            writer.writerow(record)


def run_manager(
    *,
    corpus: str | None = None,
    bank: str | None = None,
    download_date: str | None = None,
    source_dir: Path | None = None,
    audit_existing: list[str] | None = None,
    dry_run: bool = False,
    move_files: bool = False,
    append: bool = False,
) -> list[FileInventoryRow]:
    rows: list[FileInventoryRow] = []
    if corpus and bank and source_dir:
        rows.extend(scan_intake_source(
            bank=bank,
            corpus=corpus,
            download_date=download_date or date.today().isoformat(),
            source_dir=source_dir,
            dry_run=dry_run,
            move_files=move_files,
        ))

    for existing_corpus in audit_existing or []:
        rows.extend(audit_existing_corpus(existing_corpus))

    write_outputs(rows, append=append)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", help="Corpus name for a newly downloaded source folder, e.g. EllisWeismer.")
    parser.add_argument("--bank", help="TalkBank bank for a newly downloaded source folder, e.g. CHILDES or ASDBank.")
    parser.add_argument("--download-date", default=date.today().isoformat())
    parser.add_argument("--source-dir", type=Path, help="Folder containing browser-downloaded transcripts/sidecars.")
    parser.add_argument(
        "--audit-existing",
        action="append",
        default=[],
        help="Audit an existing data/{Corpus} folder without copying it into the raw mirror. Repeatable.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not copy/move files into data/raw/talkbank.")
    parser.add_argument("--move", action="store_true", help="Move files from source-dir instead of copying them.")
    parser.add_argument("--append", action="store_true", help="Merge new rows with the existing file inventory instead of replacing it.")
    args = parser.parse_args()

    audit_existing = args.audit_existing or list(DEFAULT_EXISTING_AUDIT_CORPORA)
    rows = run_manager(
        corpus=args.corpus,
        bank=args.bank,
        download_date=args.download_date,
        source_dir=args.source_dir,
        audit_existing=audit_existing,
        dry_run=args.dry_run,
        move_files=args.move,
        append=args.append,
    )
    transcripts = [row for row in rows if row.file_role == "transcript"]
    print(f"Recorded {len(rows)} file(s).")
    print(f"Transcript files: {len(transcripts)}")
    print(f"QC pass/warn/fail: "
          f"{sum(row.qc_status == 'pass' for row in transcripts)}/"
          f"{sum(row.qc_status == 'warn' for row in transcripts)}/"
          f"{sum(row.qc_status == 'fail' for row in transcripts)}")
    print(f"Download manifest: {_relative(DOWNLOAD_MANIFEST_PATH)}")
    print(f"File inventory: {_relative(FILE_INVENTORY_PATH)}")
    print(f"QC summary: {_relative(QC_SUMMARY_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
