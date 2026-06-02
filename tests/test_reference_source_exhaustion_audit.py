from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.audit_reference_source_exhaustion import (  # noqa: E402
    AUDIT_COLUMNS,
    build_audit_rows,
    write_audit_outputs,
)


def test_audit_marks_policy_exhausted_when_ready_rows_are_already_matched():
    manifest_df = pd.DataFrame(
        [
            _manifest_row("ready-a", analysis_ready=True, child_utterances=55),
            _manifest_row("short-a", analysis_ready=False, child_utterances=20),
        ]
    )
    features_df = pd.DataFrame([_feature_row("ready-a")])
    clan_df = pd.DataFrame([_feature_row("ready-a")])
    coverage_df = pd.DataFrame([_coverage_row()])

    rows = build_audit_rows(
        manifest_df,
        features_df,
        clan_df,
        coverage_df,
        target_corpus="Gillam",
        triage_bucket="candidate_gillam",
    )

    assert list(rows[0]) == AUDIT_COLUMNS
    assert rows[0]["analysis_ready_source_rows"] == 1
    assert rows[0]["short_sample_source_rows"] == 1
    assert rows[0]["missing_feature_rows"] == 0
    assert rows[0]["missing_clan_rows"] == 0
    assert rows[0]["audit_status"] == "policy_exhausted_keep_low_confidence"


def test_audit_marks_feature_and_clan_rebuild_gaps():
    coverage_df = pd.DataFrame([_coverage_row()])
    empty_df = pd.DataFrame(columns=["corpus", "source_path", "age_band_12mo", "task_type", "group"])
    missing_feature_rows = build_audit_rows(
        pd.DataFrame([_manifest_row("ready-a", analysis_ready=True)]),
        empty_df,
        empty_df,
        coverage_df,
        target_corpus="Gillam",
        triage_bucket="candidate_gillam",
    )
    missing_clan_rows = build_audit_rows(
        pd.DataFrame([_manifest_row("ready-a", analysis_ready=True)]),
        pd.DataFrame([_feature_row("ready-a")]),
        empty_df,
        coverage_df,
        target_corpus="Gillam",
        triage_bucket="candidate_gillam",
    )

    assert missing_feature_rows[0]["audit_status"] == "needs_feature_rebuild"
    assert missing_feature_rows[0]["missing_feature_rows"] == 1
    assert missing_clan_rows[0]["audit_status"] == "needs_clan_rebuild"
    assert missing_clan_rows[0]["missing_clan_rows"] == 1


def test_audit_marks_no_local_target_source_when_cell_has_no_matching_source_rows():
    rows = build_audit_rows(
        pd.DataFrame([_manifest_row("other-cell", age_band="96-107", analysis_ready=True)]),
        pd.DataFrame(columns=["corpus", "source_path", "age_band_12mo", "task_type", "group"]),
        pd.DataFrame(columns=["corpus", "source_path", "age_band_12mo", "task_type", "group"]),
        pd.DataFrame([_coverage_row()]),
        target_corpus="Gillam",
        triage_bucket="candidate_gillam",
    )

    assert rows[0]["source_transcript_rows"] == 0
    assert rows[0]["audit_status"] == "no_local_target_source_keep_low_confidence"


def test_audit_is_idempotent_after_coverage_consumes_audit_status():
    consumed_coverage_row = _coverage_row()
    consumed_coverage_row["triage_bucket"] = "policy_exhausted_keep_low_confidence"
    consumed_coverage_row["source_audit_status"] = "policy_exhausted_keep_low_confidence"
    consumed_coverage_row["source_audit_action"] = (
        "No additional analysis-ready Gillam rows remain under the current Reference Cohort policy."
    )

    rows = build_audit_rows(
        pd.DataFrame([_manifest_row("ready-a", analysis_ready=True)]),
        pd.DataFrame([_feature_row("ready-a")]),
        pd.DataFrame([_feature_row("ready-a")]),
        pd.DataFrame([consumed_coverage_row]),
        target_corpus="Gillam",
        triage_bucket="candidate_gillam",
    )

    assert len(rows) == 1
    assert rows[0]["audit_status"] == "policy_exhausted_keep_low_confidence"


def test_write_audit_outputs_creates_csv(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    features_path = tmp_path / "features.csv"
    clan_path = tmp_path / "clan.csv"
    coverage_path = tmp_path / "coverage.csv"
    audit_path = tmp_path / "audit.csv"
    pd.DataFrame([_manifest_row("ready-a", analysis_ready=True)]).to_csv(manifest_path, index=False)
    pd.DataFrame([_feature_row("ready-a")]).to_csv(features_path, index=False)
    pd.DataFrame([_feature_row("ready-a")]).to_csv(clan_path, index=False)
    pd.DataFrame([_coverage_row()]).to_csv(coverage_path, index=False)

    audit_df = write_audit_outputs(
        transcript_manifest_path=manifest_path,
        features_path=features_path,
        clan_features_path=clan_path,
        coverage_path=coverage_path,
        output_path=audit_path,
        target_corpus="Gillam",
        triage_bucket="candidate_gillam",
    )

    assert audit_path.exists()
    assert list(pd.read_csv(audit_path).columns) == AUDIT_COLUMNS
    assert len(audit_df) == 1


def test_write_audit_outputs_appends_and_replaces_matching_target_key(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    features_path = tmp_path / "features.csv"
    clan_path = tmp_path / "clan.csv"
    coverage_path = tmp_path / "coverage.csv"
    audit_path = tmp_path / "audit.csv"

    coverage_row = _coverage_row(
        age_band="24-35",
        task_type="toyplay",
        group="ASD",
        triage_bucket="candidate_rollins_or_asd_addon",
    )
    pd.DataFrame(
        [
            _manifest_row(
                "rollins-ready",
                age_band="24-35",
                task_type="toyplay",
                group="ASD",
                analysis_ready=True,
                corpus="Rollins",
            )
        ]
    ).to_csv(manifest_path, index=False)
    pd.DataFrame([_feature_row("rollins-ready", age_band="24-35", task_type="toyplay", group="ASD", corpus="Rollins")]).to_csv(
        features_path,
        index=False,
    )
    pd.DataFrame([_feature_row("rollins-ready", age_band="24-35", task_type="toyplay", group="ASD", corpus="Rollins")]).to_csv(
        clan_path,
        index=False,
    )
    pd.DataFrame([coverage_row]).to_csv(coverage_path, index=False)
    pd.DataFrame(
        [
            {
                **{column: "" for column in AUDIT_COLUMNS},
                "language": "eng",
                "age_band_12mo": "84-95",
                "task_type": "narrative",
                "group": "SLI",
                "triage_bucket": "candidate_gillam",
                "target_corpus": "Gillam",
                "audit_status": "policy_exhausted_keep_low_confidence",
                "audit_action": "old Gillam row",
            },
            {
                **{column: "" for column in AUDIT_COLUMNS},
                "language": "eng",
                "age_band_12mo": "24-35",
                "task_type": "toyplay",
                "group": "ASD",
                "triage_bucket": "candidate_rollins_or_asd_addon",
                "target_corpus": "Rollins",
                "audit_status": "needs_feature_rebuild",
                "audit_action": "stale Rollins row",
            },
        ],
        columns=AUDIT_COLUMNS,
    ).to_csv(audit_path, index=False)

    audit_df = write_audit_outputs(
        transcript_manifest_path=manifest_path,
        features_path=features_path,
        clan_features_path=clan_path,
        coverage_path=coverage_path,
        output_path=audit_path,
        target_corpus="Rollins",
        triage_bucket="candidate_rollins_or_asd_addon",
        append=True,
    )

    by_target = {
        (row["triage_bucket"], row["target_corpus"]): row
        for row in audit_df.to_dict(orient="records")
    }
    assert len(audit_df) == 2
    assert by_target[("candidate_gillam", "Gillam")]["audit_action"] == "old Gillam row"
    assert by_target[("candidate_rollins_or_asd_addon", "Rollins")]["audit_status"] == (
        "policy_exhausted_keep_low_confidence"
    )
    assert "stale Rollins row" not in audit_path.read_text(encoding="utf-8")


def _manifest_row(
    stem: str,
    *,
    age_band: str = "84-95",
    task_type: str = "narrative",
    group: str = "SLI",
    analysis_ready: bool,
    child_utterances: int = 50,
    corpus: str = "Gillam",
) -> dict[str, object]:
    return {
        "source_path": f"data/raw/talkbank/CHILDES/{corpus}/download_2026-06-01/{stem}.cha",
        "curated_path": "",
        "corpus": corpus,
        "bank": "CHILDES",
        "languages_raw": "eng",
        "has_chi_id": True,
        "has_chi_tier": True,
        "child_utterance_count": child_utterances,
        "child_token_count": child_utterances * 3,
        "eligible_english_child_transcript": True,
        "analysis_ready": analysis_ready,
        "exclude_reason": "",
        "sha256": f"hash-{stem}",
        "download_date": "2026-06-01",
        "qc_status": "pass" if analysis_ready else "eligible_short_sample",
        "age_band_12mo": age_band,
        "task_type": task_type,
        "group": group,
    }


def _feature_row(
    stem: str,
    *,
    age_band: str = "84-95",
    task_type: str = "narrative",
    group: str = "SLI",
    corpus: str = "Gillam",
) -> dict[str, object]:
    row = _manifest_row(
        stem,
        age_band=age_band,
        task_type=task_type,
        group=group,
        analysis_ready=True,
        corpus=corpus,
    )
    return {
        "source_path": row["source_path"],
        "corpus": corpus,
        "language": "eng",
        "age_band_12mo": row["age_band_12mo"],
        "task_type": row["task_type"],
        "group": row["group"],
    }


def _coverage_row(
    *,
    age_band: str = "84-95",
    task_type: str = "narrative",
    group: str = "SLI",
    triage_bucket: str = "candidate_gillam",
) -> dict[str, object]:
    return {
        "language": "eng",
        "age_band_12mo": age_band,
        "task_type": task_type,
        "group": group,
        "feature_row_count": 19,
        "cohort_ready_row_count": 19,
        "cohort_n": 19,
        "confidence_flag": "low_n",
        "clan_row_count": 19,
        "clan_coverage_status": "matched",
        "corpus_count": 2,
        "corpora": "ENNI;Gillam",
        "design_types": "cross",
        "coverage_status": "low_n",
        "triage_bucket": triage_bucket,
        "triage_action": "Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps.",
        "phase2_recommendation": "Prioritize Gillam to strengthen narrative SLI and TD school-age cells.",
    }
