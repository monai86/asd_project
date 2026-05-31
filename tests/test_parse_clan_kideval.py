from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.parse_clan_kideval import (  # noqa: E402
    METRIC_SOURCE,
    build_clan_feature_rows,
    parse_clan_kideval,
    parse_kideval_table,
)


def test_parse_kideval_table_finds_tabular_output_after_preamble():
    table = parse_kideval_table(
        "\n".join(
            [
                "CLAN KIDEVAL output",
                "File\tMLU Utts\tFREQ types\tFREQ tokens\tFREQ TTR\tVOCD score",
                "a.cha\t51\t34\t101\t0.337\t42.1",
            ]
        )
    )

    assert table.file_column == "File"
    assert table.rows == [
        {
            "File": "a.cha",
            "MLU Utts": "51",
            "FREQ types": "34",
            "FREQ tokens": "101",
            "FREQ TTR": "0.337",
            "VOCD score": "42.1",
        }
    ]


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_build_clan_feature_rows_maps_kideval_metrics_to_manifest_and_reference(tmp_path):
    output = tmp_path / "data" / "clan" / "raw_outputs" / "kideval" / "Synthetic" / "Synthetic.stdout.txt"
    output.parent.mkdir(parents=True)
    output.write_text(
        "\n".join(
            [
                "File\tMLU Utts\tFREQ types\tFREQ tokens\tFREQ TTR\tVOCD score\tDSS Utterances\tDSS\tIPSyn Total",
                "a.cha\t51\t34\t101\t0.337\t42.1\t50\t7.5\tN/A",
            ]
        ),
        encoding="utf-8",
    )
    run_rows = [
        {
            "command": "kideval",
            "status": "completed",
            "corpus": "Synthetic",
            "output_path": output.relative_to(tmp_path).as_posix(),
        }
    ]
    transcript_rows = [
        {
            "source_path": "data/raw/talkbank/ChildBank/Synthetic/a.cha",
            "curated_path": "data/curated/english_child_transcripts/Synthetic/a.cha",
            "corpus": "Synthetic",
            "bank": "ChildBank",
            "sha256": "a" * 64,
            "download_date": "2026-05-31",
            "child_utterance_count": "51",
            "child_token_count": "101",
        }
    ]
    reference_rows = [
        {
            "transcript_uid": "Synthetic:a:aaaaaaaaaaaa",
            "sha256": "a" * 64,
            "language": "eng",
            "design_type": "cross",
            "task_type": "toyplay",
            "group_type": "TD",
            "group": "TD",
            "sex": "female",
            "age_band_12mo": "48-59",
        }
    ]

    rows, qc_rows = build_clan_feature_rows(
        run_manifest_rows=run_rows,
        transcript_manifest_rows=transcript_rows,
        reference_feature_rows=reference_rows,
        project_root=tmp_path,
    )

    assert qc_rows == []
    assert rows[0]["metric_source"] == METRIC_SOURCE
    assert rows[0]["transcript_uid"] == "Synthetic:a:aaaaaaaaaaaa"
    assert rows[0]["kideval_mlu_utts"] == "51"
    assert rows[0]["kideval_freq_tokens"] == "101"
    assert rows[0]["kideval_freq_ttr"] == "0.337"
    assert rows[0]["kideval_vocd_score"] == "42.1"
    assert rows[0]["kideval_dss"] == "7.5"
    assert rows[0]["kideval_ipsyn_total"] == ""


def test_parse_clan_kideval_writes_empty_table_and_qc_when_no_completed_jobs(tmp_path):
    run_manifest = tmp_path / "run.csv"
    transcript_manifest = tmp_path / "transcripts.csv"
    reference_features = tmp_path / "reference.csv"
    output = tmp_path / "clan_features.csv"
    qc = tmp_path / "clan_qc.csv"

    _write_csv(run_manifest, [{"command": "kideval", "status": "clan_unavailable", "output_path": ""}], ["command", "status", "output_path"])
    _write_csv(transcript_manifest, [], ["source_path", "curated_path", "corpus", "bank", "sha256"])
    _write_csv(reference_features, [], ["sha256"])

    rows, qc_rows = parse_clan_kideval(
        run_manifest_path=run_manifest,
        transcript_manifest_path=transcript_manifest,
        reference_features_path=reference_features,
        output_path=output,
        qc_path=qc,
        project_root=tmp_path,
    )

    assert rows == []
    assert qc_rows[0]["reason"] == "no_completed_kideval_jobs"
    assert _read_csv(output) == []
    assert _read_csv(qc)[0]["qc_status"] == "warn"
