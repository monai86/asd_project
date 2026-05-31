"""Curate English child CHAT transcripts from TalkBank-style corpora.

The curation rule is intentionally strict:

* ``@Languages`` must be exactly ``eng``.
* The transcript must contain at least one ``*CHI:`` child speech tier.

Files that pass the strict language/child-tier rule are copied into an ignored
curated directory. Every scanned file is still written to the manifest with an
include/exclude reason so downstream reference-building can audit the decision.
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
CURATED_DIR = DATA_DIR / "curated" / "english_child_transcripts"
MANIFEST_DIR = DATA_DIR / "manifests"
MANIFEST_PATH = MANIFEST_DIR / "english_child_transcript_manifest.csv"
SUMMARY_PATH = MANIFEST_DIR / "english_child_transcript_qc_summary.csv"

LANGUAGES_RE = re.compile(r"^@Languages:\s*(.+)$", re.MULTILINE)
ID_CHI_RE = re.compile(r"^@ID:\s*[^\n]*\|CHI\|", re.MULTILINE)
CHI_TIER_RE = re.compile(r"^\*CHI:\s*(.*)$", re.MULTILINE)
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)

IGNORED_DATA_DIRS = {
    "curated",
    "manifests",
    "raw",
}


@dataclass(frozen=True)
class CurationRow:
    source_path: str
    curated_path: str
    corpus: str
    bank: str
    languages_raw: str
    has_chi_id: bool
    has_chi_tier: bool
    child_utterance_count: int
    child_token_count: int
    eligible_english_child_transcript: bool
    analysis_ready: bool
    exclude_reason: str
    sha256: str
    download_date: str
    qc_status: str


def _relative(path: Path, root: Path = PROJECT_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_languages(text: str) -> str:
    match = LANGUAGES_RE.search(text)
    return match.group(1).strip() if match else ""


def child_utterance_texts(text: str) -> list[str]:
    return [match.group(1).strip() for match in CHI_TIER_RE.finditer(text)]


def count_child_tokens(child_lines: list[str]) -> int:
    count = 0
    for line in child_lines:
        cleaned = re.sub(r"\x15\d+_\d+\x15", " ", line)
        cleaned = re.sub(r"&=[^\s]+", " ", cleaned)
        cleaned = re.sub(r"\b(?:xxx|yyy|www)\b", " ", cleaned, flags=re.IGNORECASE)
        count += len(TOKEN_RE.findall(cleaned))
    return count


def infer_source_metadata(path: Path, data_dir: Path = DATA_DIR) -> tuple[str, str, str]:
    """Return ``(bank, corpus, download_date)`` for a source transcript."""
    rel_parts = path.resolve().relative_to(data_dir.resolve()).parts

    if len(rel_parts) >= 5 and rel_parts[:2] == ("raw", "talkbank"):
        bank = rel_parts[2]
        corpus = rel_parts[3]
        download_date = rel_parts[4].removeprefix("download_")
        return bank, corpus, download_date

    corpus = rel_parts[0] if rel_parts else "unknown"
    return "project_data", corpus, ""


def curated_path_for(
    source_path: Path,
    corpus: str,
    curated_dir: Path = CURATED_DIR,
    data_dir: Path = DATA_DIR,
) -> Path:
    """Preserve enough source path to avoid collisions inside one corpus."""
    try:
        rel = source_path.resolve().relative_to(data_dir.resolve())
        parts = rel.parts
        if len(parts) >= 5 and parts[:2] == ("raw", "talkbank"):
            return curated_dir / corpus / Path(*parts[4:])
    except ValueError:
        pass

    try:
        rel_to_corpus = source_path.resolve().relative_to((data_dir / corpus).resolve())
    except ValueError:
        rel_to_corpus = Path(source_path.name)
    return curated_dir / corpus / rel_to_corpus


def analyze_transcript(path: Path, *, data_dir: Path = DATA_DIR, curated_dir: Path = CURATED_DIR) -> CurationRow:
    text = _read_text(path)
    languages_raw = parse_languages(text)
    child_lines = child_utterance_texts(text)
    bank, corpus, download_date = infer_source_metadata(path, data_dir=data_dir)
    has_chi_tier = bool(child_lines)
    has_chi_id = bool(ID_CHI_RE.search(text))
    child_utterance_count = len(child_lines)
    child_token_count = count_child_tokens(child_lines)
    english_only = languages_raw == "eng"

    if not languages_raw:
        exclude_reason = "missing_languages_header"
    elif not english_only:
        exclude_reason = "not_english_only"
    elif not has_chi_tier:
        exclude_reason = "missing_child_speech_tier"
    else:
        exclude_reason = ""

    eligible = not exclude_reason
    analysis_ready = eligible and child_utterance_count >= 50
    qc_status = "pass" if analysis_ready else "eligible_short_sample" if eligible else "excluded"
    destination = curated_path_for(path, corpus, curated_dir=curated_dir, data_dir=data_dir) if eligible else Path("")

    return CurationRow(
        source_path=_relative(path),
        curated_path=_relative(destination) if eligible else "",
        corpus=corpus,
        bank=bank,
        languages_raw=languages_raw,
        has_chi_id=has_chi_id,
        has_chi_tier=has_chi_tier,
        child_utterance_count=child_utterance_count,
        child_token_count=child_token_count,
        eligible_english_child_transcript=eligible,
        analysis_ready=analysis_ready,
        exclude_reason=exclude_reason,
        sha256=_sha256(path),
        download_date=download_date,
        qc_status=qc_status,
    )


def iter_source_transcripts(data_dir: Path = DATA_DIR) -> list[Path]:
    paths: set[Path] = set()

    raw_dir = data_dir / "raw" / "talkbank"
    if raw_dir.exists():
        paths.update(raw_dir.rglob("*.cha"))

    for child in data_dir.iterdir() if data_dir.exists() else []:
        if not child.is_dir() or child.name in IGNORED_DATA_DIRS:
            continue
        paths.update(child.rglob("*.cha"))

    return sorted(paths, key=lambda item: item.as_posix())


def write_manifest(rows: list[CurationRow], manifest_path: Path = MANIFEST_PATH) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(CurationRow.__dataclass_fields__)
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_summary(rows: list[CurationRow], summary_path: Path = SUMMARY_PATH) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary: dict[tuple[str, str, str], dict[str, int | str]] = {}
    for row in rows:
        key = (row.bank, row.corpus, row.qc_status)
        record = summary.setdefault(
            key,
            {
                "bank": row.bank,
                "corpus": row.corpus,
                "qc_status": row.qc_status,
                "file_count": 0,
                "eligible_count": 0,
                "analysis_ready_count": 0,
                "child_utterance_count": 0,
                "child_token_count": 0,
            },
        )
        record["file_count"] = int(record["file_count"]) + 1
        record["eligible_count"] = int(record["eligible_count"]) + int(row.eligible_english_child_transcript)
        record["analysis_ready_count"] = int(record["analysis_ready_count"]) + int(row.analysis_ready)
        record["child_utterance_count"] = int(record["child_utterance_count"]) + row.child_utterance_count
        record["child_token_count"] = int(record["child_token_count"]) + row.child_token_count

    fieldnames = [
        "bank",
        "corpus",
        "qc_status",
        "file_count",
        "eligible_count",
        "analysis_ready_count",
        "child_utterance_count",
        "child_token_count",
    ]
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in sorted(summary.values(), key=lambda item: (str(item["bank"]), str(item["corpus"]), str(item["qc_status"]))):
            writer.writerow(record)


def copy_curated_files(rows: list[CurationRow], *, project_root: Path = PROJECT_ROOT) -> int:
    copied = 0
    for row in rows:
        if not row.eligible_english_child_transcript or not row.curated_path:
            continue
        source = project_root / row.source_path
        destination = project_root / row.curated_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


def curate(
    *,
    data_dir: Path = DATA_DIR,
    manifest_path: Path = MANIFEST_PATH,
    summary_path: Path = SUMMARY_PATH,
    curated_dir: Path = CURATED_DIR,
    copy_files: bool = True,
    clean_curated: bool = True,
) -> list[CurationRow]:
    paths = iter_source_transcripts(data_dir)
    rows = [analyze_transcript(path, data_dir=data_dir, curated_dir=curated_dir) for path in paths]
    write_manifest(rows, manifest_path)
    write_summary(rows, summary_path)
    if copy_files:
        if clean_curated and curated_dir.exists():
            shutil.rmtree(curated_dir)
        copy_curated_files(rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--curated-dir", type=Path, default=CURATED_DIR)
    parser.add_argument("--manifest-only", action="store_true", help="Do not copy eligible transcripts into the curated directory.")
    args = parser.parse_args()

    rows = curate(
        data_dir=args.data_dir,
        manifest_path=args.manifest,
        summary_path=args.summary,
        curated_dir=args.curated_dir,
        copy_files=not args.manifest_only,
    )
    eligible = sum(row.eligible_english_child_transcript for row in rows)
    ready = sum(row.analysis_ready for row in rows)
    print(f"Scanned {len(rows)} transcript(s) on {date.today().isoformat()}.")
    print(f"Eligible English child transcripts: {eligible}")
    print(f"Analysis-ready transcripts (>=50 child utterances): {ready}")
    print(f"Manifest: {_relative(args.manifest)}")
    print(f"Summary: {_relative(args.summary)}")
    if not args.manifest_only:
        print(f"Curated directory: {_relative(args.curated_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
