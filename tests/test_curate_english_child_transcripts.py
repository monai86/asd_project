from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.curate_english_child_transcripts import analyze_transcript, curate  # noqa: E402


def write_cha(path: Path, *, languages: str = "eng", child_lines: int = 1, include_chi: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    chi_tiers = "\n".join(f"*CHI:\tword {idx} ." for idx in range(child_lines)) if include_chi else ""
    adult_tier = "*MOT:\twhere is your spoon ?"
    text = f"""@UTF8
@Begin
@Languages:\t{languages}
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Test|CHI|4;00.00|male|||Target_Child|||
@ID:\teng|Test|MOT|||||Mother|||
{chi_tiers}
{adult_tier}
@End
"""
    path.write_text(text, encoding="utf-8")
    return path


def test_english_child_transcript_is_eligible_but_short_sample_not_analysis_ready(tmp_path):
    data_dir = tmp_path / "data"
    cha = write_cha(data_dir / "Nadig" / "123.cha", child_lines=1)

    row = analyze_transcript(cha, data_dir=data_dir, curated_dir=tmp_path / "curated")

    assert row.languages_raw == "eng"
    assert row.has_chi_id is True
    assert row.has_chi_tier is True
    assert row.child_utterance_count == 1
    assert row.eligible_english_child_transcript is True
    assert row.analysis_ready is False
    assert row.exclude_reason == ""
    assert row.qc_status == "eligible_short_sample"


def test_english_adult_only_transcript_is_excluded_as_missing_child_speech_tier(tmp_path):
    data_dir = tmp_path / "data"
    cha = write_cha(data_dir / "QuigleyMcNally" / "adult_only.cha", include_chi=False)

    row = analyze_transcript(cha, data_dir=data_dir, curated_dir=tmp_path / "curated")

    assert row.languages_raw == "eng"
    assert row.has_chi_id is True
    assert row.has_chi_tier is False
    assert row.eligible_english_child_transcript is False
    assert row.exclude_reason == "missing_child_speech_tier"
    assert row.qc_status == "excluded"


def test_bilingual_transcript_is_excluded_even_when_child_tier_exists(tmp_path):
    data_dir = tmp_path / "data"
    cha = write_cha(data_dir / "Mixed" / "bilingual.cha", languages="eng, spa", child_lines=2)

    row = analyze_transcript(cha, data_dir=data_dir, curated_dir=tmp_path / "curated")

    assert row.has_chi_tier is True
    assert row.eligible_english_child_transcript is False
    assert row.exclude_reason == "not_english_only"


def test_curate_writes_manifest_summary_and_copies_only_eligible_files(tmp_path):
    data_dir = tmp_path / "data"
    eligible = write_cha(data_dir / "Nadig" / "ready.cha", child_lines=50)
    excluded = write_cha(data_dir / "QuigleyMcNally" / "adult_only.cha", include_chi=False)
    manifest = tmp_path / "manifests" / "manifest.csv"
    summary = tmp_path / "manifests" / "summary.csv"
    curated_dir = tmp_path / "curated"

    rows = curate(
        data_dir=data_dir,
        manifest_path=manifest,
        summary_path=summary,
        curated_dir=curated_dir,
        copy_files=True,
    )

    assert len(rows) == 2
    ready_row = next(row for row in rows if row.source_path == eligible.resolve().as_posix())
    excluded_row = next(row for row in rows if row.source_path == excluded.resolve().as_posix())
    assert ready_row.analysis_ready is True
    assert excluded_row.exclude_reason == "missing_child_speech_tier"
    assert Path(ready_row.curated_path).exists()
    assert excluded_row.curated_path == ""

    with manifest.open(encoding="utf-8") as handle:
        manifest_rows = list(csv.DictReader(handle))
    assert {row["exclude_reason"] for row in manifest_rows} == {"", "missing_child_speech_tier"}

    with summary.open(encoding="utf-8") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert {row["qc_status"] for row in summary_rows} == {"pass", "excluded"}
