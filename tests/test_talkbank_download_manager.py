from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.talkbank_download_manager import (  # noqa: E402
    audit_existing_corpus,
    scan_intake_source,
    summarize_inventory,
    write_outputs,
)


def write_chat(path: Path, *, include_child: bool = True, languages: str = "eng") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    child_tier = "*CHI:\tplay car ." if include_child else ""
    path.write_text(
        f"""@UTF8
@Begin
@Languages:\t{languages}
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Test|CHI|4;00.00|male|||Target_Child|||
@ID:\teng|Test|MOT|||||Mother|||
{child_tier}
*MOT:\tyes .
@End
""",
        encoding="utf-8",
    )
    return path


def test_scan_intake_source_copies_transcripts_sidecars_and_skips_media(tmp_path):
    source = tmp_path / "downloads" / "EllisWeismer"
    cha = write_chat(source / "child.cha")
    sidecar = source / "0types.txt"
    sidecar.write_text("toyplay\n", encoding="utf-8")
    xml = source / "child.xml"
    xml.write_text("<CHAT />\n", encoding="utf-8")
    media = source / "child.wav"
    media.write_bytes(b"not real audio")
    raw_root = tmp_path / "raw" / "talkbank"

    rows = scan_intake_source(
        bank="CHILDES",
        corpus="EllisWeismer",
        download_date="2026-05-31",
        source_dir=source,
        raw_mirror_root=raw_root,
    )

    assert {row.file_role for row in rows} == {"transcript", "sidecar", "documentation"}
    assert all(row.copied_to_raw_mirror for row in rows)
    assert (raw_root / "CHILDES" / "EllisWeismer" / "download_2026-05-31" / cha.name).exists()
    assert (raw_root / "CHILDES" / "EllisWeismer" / "download_2026-05-31" / sidecar.name).exists()
    assert (raw_root / "CHILDES" / "EllisWeismer" / "download_2026-05-31" / xml.name).exists()
    assert not (raw_root / "CHILDES" / "EllisWeismer" / "download_2026-05-31" / media.name).exists()
    transcript = next(row for row in rows if row.file_role == "transcript")
    assert transcript.languages_raw == "eng"
    assert transcript.has_chi_tier is True
    assert transcript.child_utterance_count == 1


def test_audit_existing_corpus_does_not_copy_into_raw_mirror(tmp_path):
    data_dir = tmp_path / "data"
    write_chat(data_dir / "Nadig" / "123.cha", include_child=False)

    rows = audit_existing_corpus("Nadig", data_dir=data_dir)

    assert len(rows) == 1
    row = rows[0]
    assert row.bank == "project_data"
    assert row.source_status == "existing_project_data"
    assert row.raw_mirror_path == ""
    assert row.copied_to_raw_mirror is False
    assert row.qc_status == "warn"
    assert "missing_child_speech_tier" in row.qc_notes


def test_summarize_inventory_groups_by_corpus_download_and_existing_source(tmp_path):
    source = tmp_path / "downloads" / "ENNI"
    write_chat(source / "one.cha")
    write_chat(source / "two.cha")
    raw_root = tmp_path / "raw" / "talkbank"
    intake_rows = scan_intake_source(
        bank="CHILDES",
        corpus="ENNI",
        download_date="2026-05-31",
        source_dir=source,
        raw_mirror_root=raw_root,
        dry_run=True,
    )
    data_dir = tmp_path / "data"
    write_chat(data_dir / "NYU-Emerson" / "2001.cha")
    existing_rows = audit_existing_corpus("NYU-Emerson", data_dir=data_dir)

    summary = summarize_inventory(intake_rows + existing_rows)

    assert len(summary) == 2
    enni = next(row for row in summary if row.corpus == "ENNI")
    nyu = next(row for row in summary if row.corpus == "NYU-Emerson")
    assert enni.file_count == 2
    assert enni.transcript_count == 2
    assert enni.copied_file_count == 0
    assert enni.raw_mirror_dir == "data/raw/talkbank/CHILDES/ENNI/download_2026-05-31"
    assert nyu.source_status == "existing_project_data"
    assert nyu.source_dir == "data/NYU-Emerson"


def test_write_outputs_creates_manifest_inventory_and_qc_summary(tmp_path):
    source = tmp_path / "downloads" / "Ambrose"
    write_chat(source / "child.cha")
    rows = scan_intake_source(
        bank="CHILDES",
        corpus="Ambrose",
        download_date="2026-05-31",
        source_dir=source,
        raw_mirror_root=tmp_path / "raw",
        dry_run=True,
    )
    manifest = tmp_path / "talkbank_download_manifest.csv"
    inventory = tmp_path / "talkbank_file_inventory.csv"
    qc = tmp_path / "talkbank_qc_summary.csv"

    write_outputs(rows, manifest_path=manifest, inventory_path=inventory, qc_summary_path=qc)

    for path in (manifest, inventory, qc):
        assert path.exists()
        with path.open(encoding="utf-8") as handle:
            assert list(csv.DictReader(handle))


def test_write_outputs_append_merges_existing_inventory_without_duplicates(tmp_path):
    source = tmp_path / "downloads" / "EllisWeismer"
    write_chat(source / "child.cha")
    rows = scan_intake_source(
        bank="CHILDES",
        corpus="EllisWeismer",
        download_date="2026-05-31",
        source_dir=source,
        raw_mirror_root=tmp_path / "raw",
        dry_run=True,
    )
    manifest = tmp_path / "manifest.csv"
    inventory = tmp_path / "inventory.csv"
    qc = tmp_path / "qc.csv"

    write_outputs(rows, manifest_path=manifest, inventory_path=inventory, qc_summary_path=qc)
    write_outputs(rows, manifest_path=manifest, inventory_path=inventory, qc_summary_path=qc, append=True)

    with inventory.open(encoding="utf-8") as handle:
        inventory_rows = list(csv.DictReader(handle))
    assert len(inventory_rows) == 1
