from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_reference_cohorts import (  # noqa: E402
    age_band_12mo,
    build_cohort_rows,
    build_reference_csvs,
    choose_group,
    parse_chat_metadata,
)
from src.feature_schema import FEATURES  # noqa: E402


def write_cha(
    path: Path,
    *,
    types: str = "long, toyplay, LT",
    age: str = "4;00.00",
    sex: str = "female",
    group: str = "LT",
    child_lines: int = 50,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    group_field = group if group is not None else ""
    age_field = age if age is not None else ""
    child_tiers = []
    for idx in range(child_lines):
        utterance = "I want cookie ?" if idx % 10 == 0 else "I want cookie ."
        child_tiers.append(f"*CHI:\t{utterance}")
        child_tiers.append("%mor:\tpro:sub|I v|want n|cookie .")
        child_tiers.append("*MOT:\there is a cookie .")
    text = f"""@UTF8
@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Test|CHI|{age_field}|{sex}|{group_field}||Target_Child|||
@ID:\teng|Test|MOT|||||Mother|||
@Types:\t{types}
{chr(10).join(child_tiers)}
@End
"""
    path.write_text(text, encoding="utf-8")
    return path


def manifest_row(path: Path, *, analysis_ready: bool = True, corpus: str = "Synthetic") -> dict[str, str]:
    return {
        "source_path": path.as_posix(),
        "curated_path": "",
        "corpus": corpus,
        "bank": "project_data",
        "languages_raw": "eng",
        "has_chi_id": "True",
        "has_chi_tier": "True",
        "child_utterance_count": "50",
        "child_token_count": "150",
        "eligible_english_child_transcript": "True",
        "analysis_ready": str(analysis_ready),
        "exclude_reason": "",
        "sha256": f"hash-{path.stem}",
        "download_date": "",
        "qc_status": "pass",
    }


def write_manifest(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_metadata_parser_reads_types_and_header_group(tmp_path):
    toyplay = write_cha(tmp_path / "toy.cha", types="long, toyplay, LT", group="LT")
    narrative = write_cha(tmp_path / "narr.cha", types="cross, narrative, TD", group="TD")

    toyplay_metadata = parse_chat_metadata(toyplay)
    narrative_metadata = parse_chat_metadata(narrative)

    assert (toyplay_metadata.design_type, toyplay_metadata.task_type, toyplay_metadata.group_type) == (
        "long",
        "toyplay",
        "LT",
    )
    assert choose_group(toyplay_metadata, toyplay.as_posix()) == "LT"
    assert (narrative_metadata.design_type, narrative_metadata.task_type, narrative_metadata.group_type) == (
        "cross",
        "narrative",
        "TD",
    )
    assert choose_group(narrative_metadata, narrative.as_posix()) == "TD"


def test_group_falls_back_from_path_when_header_lacks_group(tmp_path):
    transcript = write_cha(tmp_path / "data" / "Rollins" / "ASD" / "001.cha", group=None)
    metadata = parse_chat_metadata(transcript)

    assert choose_group(metadata, transcript.as_posix()) == "ASD"


def test_reference_builder_keeps_missing_age_in_qc_and_excludes_not_ready(tmp_path):
    ready = write_cha(tmp_path / "data" / "LT" / "ready.cha")
    missing_age = write_cha(tmp_path / "data" / "LT" / "missing_age.cha", age=None)
    not_ready = write_cha(tmp_path / "data" / "LT" / "short.cha", child_lines=10)
    manifest = write_manifest(
        tmp_path / "manifest.csv",
        [
            manifest_row(ready),
            manifest_row(missing_age),
            manifest_row(not_ready, analysis_ready=False),
        ],
    )

    features_df, cohorts_df, qc_df = build_reference_csvs(
        manifest_path=manifest,
        reference_dir=tmp_path / "reference",
        project_root=tmp_path,
    )

    assert len(features_df) == 2
    assert "short" not in set(features_df["source_path"])
    assert list(features_df.columns[-len(FEATURES) :]) == FEATURES
    assert "missing_age_months" in set(qc_df["reason"])
    assert all("*CHI:" not in value for value in features_df.to_csv(index=False).splitlines())
    assert "missing_age" not in set(cohorts_df.get("source_path", []))


def test_age_band_and_cohort_summary_low_n_columns(tmp_path):
    transcript = write_cha(tmp_path / "data" / "TD" / "ready.cha", types="cross, narrative, TD", group="TD")
    manifest = write_manifest(tmp_path / "manifest.csv", [manifest_row(transcript, corpus="ENNI")])

    features_df, cohorts_df, qc_df = build_reference_csvs(
        manifest_path=manifest,
        reference_dir=tmp_path / "reference",
        project_root=tmp_path,
    )

    assert age_band_12mo(24) == "24-35"
    assert age_band_12mo(47.9) == "36-47"
    assert features_df.iloc[0]["age_band_12mo"] == "48-59"
    assert cohorts_df.iloc[0]["confidence_flag"] == "low_n"
    assert "low_n" in set(qc_df["reason"])
    for feature in FEATURES:
        assert f"{feature}_n" in cohorts_df.columns
        assert f"{feature}_mean" in cohorts_df.columns
        assert f"{feature}_sd" in cohorts_df.columns
        assert f"{feature}_median" in cohorts_df.columns
        assert f"{feature}_q1" in cohorts_df.columns
        assert f"{feature}_q3" in cohorts_df.columns
        assert f"{feature}_min" in cohorts_df.columns
        assert f"{feature}_max" in cohorts_df.columns


def test_build_cohort_rows_flags_ok_when_n_at_least_twenty(tmp_path):
    rows = []
    for idx in range(20):
        transcript = write_cha(tmp_path / "data" / "TD" / f"{idx}.cha", group="TD")
        rows.append(manifest_row(transcript, corpus="Many"))
    manifest = write_manifest(tmp_path / "manifest.csv", rows)

    features_df, _, _ = build_reference_csvs(
        manifest_path=manifest,
        reference_dir=tmp_path / "reference",
        project_root=tmp_path,
    )
    cohort_rows, qc_rows = build_cohort_rows(features_df)

    assert cohort_rows[0]["cohort_n"] == 20
    assert cohort_rows[0]["confidence_flag"] == "ok"
    assert qc_rows == []
