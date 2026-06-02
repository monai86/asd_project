"""Build a Reference Cohort coverage CSV and Markdown summary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
FEATURES_PATH = REFERENCE_DIR / "english_child_reference_features.csv"
COHORTS_PATH = REFERENCE_DIR / "english_child_reference_cohorts.csv"
CLAN_FEATURES_PATH = REFERENCE_DIR / "english_child_clan_features.csv"
QC_PATH = REFERENCE_DIR / "english_child_reference_qc.csv"
SOURCE_AUDIT_PATH = REFERENCE_DIR / "english_child_source_exhaustion_audit.csv"
COVERAGE_PATH = REFERENCE_DIR / "english_child_reference_coverage.csv"
MARKDOWN_PATH = PROJECT_ROOT / "docs" / "REFERENCE_COHORT_COVERAGE.md"

UNASSIGNED = "UNASSIGNED"
COVERAGE_COLUMNS = [
    "language",
    "age_band_12mo",
    "task_type",
    "group",
    "feature_row_count",
    "cohort_ready_row_count",
    "cohort_n",
    "confidence_flag",
    "clan_row_count",
    "clan_coverage_status",
    "corpus_count",
    "corpora",
    "design_types",
    "coverage_status",
    "triage_bucket",
    "triage_action",
    "phase2_recommendation",
    "source_audit_status",
    "source_audit_action",
]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, keep_default_na=False)


def _clean_value(value: object) -> str:
    text = str(value or "").strip()
    return text if text else UNASSIGNED


def _coverage_key(row: pd.Series) -> tuple[str, str, str, str]:
    return (
        _clean_value(row.get("language") or "eng"),
        _clean_value(row.get("age_band_12mo")),
        _clean_value(row.get("task_type")),
        _clean_value(row.get("group")),
    )


def _group_counts(df: pd.DataFrame) -> dict[tuple[str, str, str, str], int]:
    if df.empty:
        return {}
    counts: dict[tuple[str, str, str, str], int] = {}
    for _, row in df.iterrows():
        key = _coverage_key(row)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _cohort_rows(cohorts_df: pd.DataFrame) -> dict[tuple[str, str, str, str], dict[str, object]]:
    rows: dict[tuple[str, str, str, str], dict[str, object]] = {}
    if cohorts_df.empty:
        return rows
    for _, row in cohorts_df.iterrows():
        key = (
            _clean_value(row.get("language") or "eng"),
            _clean_value(row.get("age_band_12mo")),
            _clean_value(row.get("task_type")),
            _clean_value(row.get("group")),
        )
        rows[key] = row.to_dict()
    return rows


def _feature_metadata(
    features_df: pd.DataFrame,
) -> dict[tuple[str, str, str, str], dict[str, object]]:
    metadata: dict[tuple[str, str, str, str], dict[str, object]] = {}
    if features_df.empty:
        return metadata
    for key, group in features_df.groupby(
        ["language", "age_band_12mo", "task_type", "group"],
        dropna=False,
        sort=True,
    ):
        normalized_key = tuple(_clean_value(value) for value in key)
        corpora = ";".join(
            sorted(str(item) for item in group["corpus"].dropna().unique() if str(item))
        )
        design_types = ";".join(
            sorted(str(item) for item in group["design_type"].dropna().unique() if str(item))
        )
        metadata[normalized_key] = {
            "corpus_count": int(group["corpus"].nunique()),
            "corpora": corpora,
            "design_types": design_types,
        }
    return metadata


def _source_audit_rows(source_audit_df: pd.DataFrame) -> dict[tuple[str, str, str, str], dict[str, object]]:
    rows: dict[tuple[str, str, str, str], dict[str, object]] = {}
    if source_audit_df.empty:
        return rows
    required = {"language", "age_band_12mo", "task_type", "group"}
    if not required.issubset(source_audit_df.columns):
        return rows
    for _, row in source_audit_df.iterrows():
        key = (
            _clean_value(row.get("language") or "eng"),
            _clean_value(row.get("age_band_12mo")),
            _clean_value(row.get("task_type")),
            _clean_value(row.get("group")),
        )
        rows[key] = row.to_dict()
    return rows


def _phase2_recommendation(age_band: str, task_type: str, group: str, status: str) -> str:
    if status == "ok":
        return ""
    if age_band == UNASSIGNED:
        return "Keep the known unresolved age row excluded unless a new unambiguous official age source is added."
    if status == "missing_clan":
        return "Run CLAN check/kideval for newly added reference transcripts, then regenerate CLAN-Derived Metrics."
    if group == "SLI" and task_type == "narrative":
        return "Prioritize Gillam to strengthen narrative SLI and TD school-age cells."
    if group == "LT":
        return "Prioritize Rescorla to strengthen late-talker toyplay cells."
    if group in {"HL", "NH"}:
        return "Prioritize Nicholas to strengthen hearing-related toyplay cells."
    if group == "ASD":
        return "Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated."
    if group == "DD":
        return "No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence."
    return "Add matched Phase 2 data or keep this cell low-confidence."


def _audit_recommendation(audit_status: str) -> str:
    if audit_status == "policy_exhausted_keep_low_confidence":
        return "Keep this cell low-confidence; no additional analysis-ready Gillam rows remain under the current Reference Cohort policy."
    if audit_status == "no_local_target_source_keep_low_confidence":
        return "Keep this cell low-confidence unless a new matched source is selected."
    if audit_status == "needs_feature_rebuild":
        return "Rebuild Python-derived reference features before choosing new data."
    if audit_status == "needs_clan_rebuild":
        return "Run CLAN check/kideval and regenerate CLAN-Derived Metrics before choosing new data."
    if audit_status == "needs_manifest_rebuild":
        return "Rebuild the transcript manifest and derived artifacts before choosing new data."
    return ""


def _apply_source_audit(
    *,
    triage_bucket: str,
    triage_action: str,
    phase2_recommendation: str,
    audit: dict[str, object],
) -> tuple[str, str, str, str, str]:
    audit_status = str(audit.get("audit_status") or "")
    audit_action = str(audit.get("audit_action") or "")
    if not audit_status:
        return triage_bucket, triage_action, phase2_recommendation, "", ""
    if audit_status in {
        "policy_exhausted_keep_low_confidence",
        "no_local_target_source_keep_low_confidence",
        "needs_feature_rebuild",
        "needs_clan_rebuild",
        "needs_manifest_rebuild",
    }:
        return (
            audit_status,
            audit_action,
            _audit_recommendation(audit_status) or phase2_recommendation,
            audit_status,
            audit_action,
        )
    return triage_bucket, triage_action, phase2_recommendation, audit_status, audit_action


def _triage_decision(age_band: str, task_type: str, group: str, status: str) -> tuple[str, str]:
    if status == "ok":
        return "", ""
    if status == "missing_clan":
        return "run_clan", "Run CLAN check/kideval and regenerate CLAN-Derived Metrics before data-intake decisions."
    if age_band == UNASSIGNED:
        return "known_exclusion", "Keep this row out of age-band cohort summaries unless a new unambiguous official age source is added."
    if status != "low_n":
        return "defer_or_keep_low_confidence", "Keep this cell visible but do not prioritize new intake from it yet."
    if task_type == "narrative" and group in {"SLI", "TD"}:
        return "candidate_gillam", "Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps."
    if task_type == "toyplay" and group == "ASD":
        return "candidate_rollins_or_asd_addon", "Consider an ASD toyplay add-on such as Rollins-like material, but keep low-confidence cells separated."
    if group == "DD":
        return "no_direct_phase2_fill", "No direct Phase 2 corpus fills this DD toyplay cell; retain low-confidence labeling."
    return "defer_or_keep_low_confidence", "Keep this cell low-confidence unless a clearly matched corpus is selected."


def _coverage_status(
    *,
    age_band: str,
    task_type: str,
    group: str,
    cohort_n: int,
    confidence_flag: str,
    clan_status: str,
) -> str:
    if age_band == UNASSIGNED or task_type == UNASSIGNED or group == UNASSIGNED:
        return "not_cohort_ready"
    if cohort_n <= 0:
        return "not_cohort_ready"
    if clan_status != "matched":
        return "missing_clan"
    if confidence_flag == "low_n":
        return "low_n"
    return "ok"


def build_coverage_rows(
    features_df: pd.DataFrame,
    cohorts_df: pd.DataFrame,
    clan_df: pd.DataFrame,
    source_audit_df: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    feature_counts = _group_counts(features_df)
    clan_counts = _group_counts(clan_df)
    cohort_rows = _cohort_rows(cohorts_df)
    metadata = _feature_metadata(features_df)
    source_audit = _source_audit_rows(source_audit_df if source_audit_df is not None else pd.DataFrame())
    keys = sorted(set(feature_counts) | set(clan_counts) | set(cohort_rows))

    rows: list[dict[str, object]] = []
    for key in keys:
        language, age_band, task_type, group = key
        cohort = cohort_rows.get(key, {})
        feature_row_count = feature_counts.get(key, 0)
        clan_row_count = clan_counts.get(key, 0)
        cohort_n = int(cohort.get("cohort_n") or 0)
        confidence_flag = str(cohort.get("confidence_flag") or "")
        clan_status = "matched"
        if clan_row_count == 0 and feature_row_count > 0:
            clan_status = "missing_clan"
        elif clan_row_count > 0 and feature_row_count == 0:
            clan_status = "clan_only"
        elif 0 < clan_row_count < feature_row_count:
            clan_status = "partial_clan"

        status = _coverage_status(
            age_band=age_band,
            task_type=task_type,
            group=group,
            cohort_n=cohort_n,
            confidence_flag=confidence_flag,
            clan_status=clan_status,
        )
        triage_bucket, triage_action = _triage_decision(age_band, task_type, group, status)
        phase2_recommendation = _phase2_recommendation(age_band, task_type, group, status)
        triage_bucket, triage_action, phase2_recommendation, audit_status, audit_action = (
            _apply_source_audit(
                triage_bucket=triage_bucket,
                triage_action=triage_action,
                phase2_recommendation=phase2_recommendation,
                audit=source_audit.get(key, {}),
            )
        )
        meta = metadata.get(key, {})
        rows.append(
            {
                "language": language,
                "age_band_12mo": age_band,
                "task_type": task_type,
                "group": group,
                "feature_row_count": feature_row_count,
                "cohort_ready_row_count": cohort_n,
                "cohort_n": cohort_n,
                "confidence_flag": confidence_flag,
                "clan_row_count": clan_row_count,
                "clan_coverage_status": clan_status,
                "corpus_count": int(cohort.get("corpus_count") or meta.get("corpus_count") or 0),
                "corpora": str(cohort.get("corpora") or meta.get("corpora") or ""),
                "design_types": str(cohort.get("design_types") or meta.get("design_types") or ""),
                "coverage_status": status,
                "triage_bucket": triage_bucket,
                "triage_action": triage_action,
                "phase2_recommendation": phase2_recommendation,
                "source_audit_status": audit_status,
                "source_audit_action": audit_action,
            }
        )
    return rows


def build_coverage_report(
    *,
    features_path: Path = FEATURES_PATH,
    cohorts_path: Path = COHORTS_PATH,
    clan_features_path: Path = CLAN_FEATURES_PATH,
    source_audit_path: Path = SOURCE_AUDIT_PATH,
) -> pd.DataFrame:
    features_df = _read_csv(features_path)
    cohorts_df = _read_csv(cohorts_path)
    clan_df = _read_csv(clan_features_path)
    source_audit_df = _read_csv(source_audit_path)
    return pd.DataFrame(
        build_coverage_rows(features_df, cohorts_df, clan_df, source_audit_df=source_audit_df),
        columns=COVERAGE_COLUMNS,
    )


def _markdown_table(rows: list[list[object]], headers: list[str]) -> str:
    output = ["| " + " | ".join(headers) + " |"]
    output.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        output.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(output)


def _status_rows(coverage_df: pd.DataFrame) -> list[list[object]]:
    if coverage_df.empty:
        return []
    counts = coverage_df["coverage_status"].value_counts().sort_index()
    return [[status, int(count)] for status, count in counts.items()]


def _task_group_rows(coverage_df: pd.DataFrame) -> list[list[object]]:
    if coverage_df.empty:
        return []
    grouped = (
        coverage_df.groupby(["task_type", "group", "coverage_status"], dropna=False)
        .size()
        .reset_index(name="cell_count")
        .sort_values(["task_type", "group", "coverage_status"])
    )
    return grouped.values.tolist()


def _low_confidence_rows(coverage_df: pd.DataFrame) -> list[list[object]]:
    if coverage_df.empty:
        return []
    subset = coverage_df[
        coverage_df["coverage_status"].isin(["low_n", "not_cohort_ready", "missing_clan"])
    ]
    subset = subset.sort_values(["coverage_status", "task_type", "age_band_12mo", "group"])
    return subset[
        [
            "age_band_12mo",
            "task_type",
            "group",
            "feature_row_count",
            "cohort_n",
            "clan_row_count",
            "clan_coverage_status",
            "coverage_status",
            "triage_bucket",
            "triage_action",
            "phase2_recommendation",
        ]
    ].values.tolist()


def _triage_rows(coverage_df: pd.DataFrame) -> list[list[object]]:
    if coverage_df.empty or "triage_bucket" not in coverage_df.columns:
        return []
    subset = coverage_df[coverage_df["triage_bucket"].astype(str) != ""]
    if subset.empty:
        return []
    grouped = (
        subset.groupby(["triage_bucket", "triage_action"], dropna=False)
        .agg(
            cell_count=("triage_bucket", "size"),
            row_gap=("cohort_n", lambda s: int((20 - s).clip(lower=0).sum())),
        )
        .reset_index()
        .sort_values(["row_gap", "cell_count", "triage_bucket"], ascending=[False, False, True])
    )
    return grouped[["triage_bucket", "cell_count", "row_gap", "triage_action"]].values.tolist()


def _recommendation_rows(coverage_df: pd.DataFrame) -> list[list[object]]:
    if coverage_df.empty:
        return []
    subset = coverage_df[coverage_df["phase2_recommendation"].astype(str) != ""]
    if subset.empty:
        return []
    grouped = (
        subset.groupby("phase2_recommendation", dropna=False)
        .agg(
            cell_count=("phase2_recommendation", "size"),
            row_gap=("cohort_n", lambda s: int((20 - s).clip(lower=0).sum())),
        )
        .reset_index()
        .sort_values(
            ["row_gap", "cell_count", "phase2_recommendation"],
            ascending=[False, False, True],
        )
    )
    return grouped[["phase2_recommendation", "cell_count", "row_gap"]].values.tolist()


def _source_audit_summary_rows(coverage_df: pd.DataFrame) -> list[list[object]]:
    if coverage_df.empty or "source_audit_status" not in coverage_df.columns:
        return []
    subset = coverage_df[coverage_df["source_audit_status"].astype(str) != ""]
    if subset.empty:
        return []
    grouped = (
        subset.groupby(["source_audit_status", "source_audit_action"], dropna=False)
        .agg(
            cell_count=("source_audit_status", "size"),
            row_gap=("cohort_n", lambda s: int((20 - s).clip(lower=0).sum())),
        )
        .reset_index()
        .sort_values(["row_gap", "cell_count", "source_audit_status"], ascending=[False, False, True])
    )
    return grouped[["source_audit_status", "cell_count", "row_gap", "source_audit_action"]].values.tolist()


def build_markdown(coverage_df: pd.DataFrame, qc_df: pd.DataFrame | None = None) -> str:
    qc_df = qc_df if qc_df is not None else pd.DataFrame()
    total_feature_rows = int(coverage_df["feature_row_count"].sum()) if not coverage_df.empty else 0
    total_clan_rows = int(coverage_df["clan_row_count"].sum()) if not coverage_df.empty else 0
    cohort_ready_cells = int((coverage_df["cohort_n"] > 0).sum()) if not coverage_df.empty else 0
    unassigned_rows = (
        coverage_df[coverage_df["age_band_12mo"] == UNASSIGNED]
        if not coverage_df.empty
        else pd.DataFrame()
    )
    missing_age_qc = 0
    known_unresolved_age_qc = 0
    if not qc_df.empty and "reason" in qc_df.columns:
        missing_age_qc = int((qc_df["reason"] == "missing_age_months").sum())
        known_unresolved_age_qc = int((qc_df["reason"] == "known_unresolved_age_months").sum())

    summary_rows = [
        ["Feature rows", total_feature_rows],
        ["CLAN rows", total_clan_rows],
        ["Coverage cells", int(len(coverage_df))],
        ["Cohort-ready cells", cohort_ready_cells],
        [
            "Rows without age band",
            int(unassigned_rows["feature_row_count"].sum()) if not unassigned_rows.empty else 0,
        ],
        ["QC missing_age_months rows", missing_age_qc],
        ["QC known_unresolved_age_months rows", known_unresolved_age_qc],
    ]

    parts = [
        "# Reference Cohort Coverage Report",
        "",
        (
            "รายงานนี้สรุปความพร้อมของ Reference Cohort โดยเทียบ coverage ของ "
            "Python-derived features, cohort summary และ CLAN-Derived Metrics "
            "แบบ side-by-side เพื่อใช้ตัดสินใจขั้นถัดไปของข้อมูลอ้างอิง."
        ),
        "",
        (
            "รายงานนี้เป็น research readiness artifact สำหรับทีมพัฒนา ไม่ใช่ clinical output "
            "และไม่ควรใช้แทนการตีความโดยผู้เชี่ยวชาญ."
        ),
        "",
        "## Snapshot",
        "",
        _markdown_table(summary_rows, ["Metric", "Value"]),
        "",
        "## Coverage Status",
        "",
        _markdown_table(_status_rows(coverage_df), ["coverage_status", "cell_count"]),
        "",
        "## Task and Group Coverage",
        "",
        _markdown_table(
            _task_group_rows(coverage_df),
            ["task_type", "group", "coverage_status", "cell_count"],
        ),
        "",
        "## Cells Needing Attention",
        "",
        _markdown_table(
            _low_confidence_rows(coverage_df),
            [
                "age_band_12mo",
                "task_type",
                "group",
                "feature_rows",
                "cohort_n",
                "clan_rows",
                "clan_coverage_status",
                "coverage_status",
                "triage_bucket",
                "triage_action",
                "phase2_recommendation",
            ],
        ),
        "",
        "## Triage Decision",
        "",
        _markdown_table(
            _triage_rows(coverage_df),
            ["triage_bucket", "cell_count", "row_gap_to_20", "triage_action"],
        ),
        "",
        "## Policy-Exhaustion Audit",
        "",
        _markdown_table(
            _source_audit_summary_rows(coverage_df),
            ["source_audit_status", "cell_count", "row_gap_to_20", "source_audit_action"],
        ),
        "",
        "## Phase 2 Download Guidance",
        "",
        _markdown_table(
            _recommendation_rows(coverage_df),
            ["Recommendation", "cell_count", "row_gap_to_20"],
        ),
        "",
        "## Notes",
        "",
        (
            "- `ok` หมายถึง cell มี cohort summary อย่างน้อย 20 rows และมี "
            "CLAN-Derived Metrics match กับ feature rows."
        ),
        (
            "- `low_n` หมายถึง cell มี cohort summary แล้วแต่ยังต่ำกว่า threshold "
            "20 rows ตามนโยบายเดิมของ Reference Cohort."
        ),
        (
            "- `not_cohort_ready` หมายถึง row ยังไม่พร้อมเข้า cohort summary "
            "เช่นไม่มี age band, task type หรือ group."
        ),
        (
            "- `known_exclusion` หมายถึง row ที่มีนโยบาย exclusion ชัดเจนแล้ว "
            "และไม่ควรถูกเติม metadata จาก source ที่ไม่ตรงกัน."
        ),
        (
            "- `policy_exhausted_keep_low_confidence` หมายถึงไม่มี analysis-ready "
            "rows เพิ่มภายใต้นโยบาย Reference Cohort ปัจจุบัน แต่ไม่ได้แปลว่า raw corpus ไม่มีไฟล์เหลือ."
        ),
        (
            "- `missing_clan`, `partial_clan` และ `clan_only` ใช้ตรวจความตรงกัน"
            "ของ CLAN-Derived Metrics กับ Python-derived features."
        ),
    ]
    return "\n".join(parts).rstrip() + "\n"


def write_coverage_outputs(
    *,
    coverage_path: Path = COVERAGE_PATH,
    markdown_path: Path = MARKDOWN_PATH,
    features_path: Path = FEATURES_PATH,
    cohorts_path: Path = COHORTS_PATH,
    clan_features_path: Path = CLAN_FEATURES_PATH,
    qc_path: Path = QC_PATH,
    source_audit_path: Path = SOURCE_AUDIT_PATH,
) -> tuple[pd.DataFrame, str]:
    coverage_df = build_coverage_report(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=clan_features_path,
        source_audit_path=source_audit_path,
    )
    qc_df = _read_csv(qc_path)
    markdown = build_markdown(coverage_df, qc_df)

    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_df.to_csv(coverage_path, index=False)
    markdown_path.write_text(markdown, encoding="utf-8")
    return coverage_df, markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=FEATURES_PATH)
    parser.add_argument("--cohorts", type=Path, default=COHORTS_PATH)
    parser.add_argument("--clan-features", type=Path, default=CLAN_FEATURES_PATH)
    parser.add_argument("--qc", type=Path, default=QC_PATH)
    parser.add_argument("--coverage-output", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--markdown-output", type=Path, default=MARKDOWN_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    coverage_df, _ = write_coverage_outputs(
        coverage_path=args.coverage_output,
        markdown_path=args.markdown_output,
        features_path=args.features,
        cohorts_path=args.cohorts,
        clan_features_path=args.clan_features,
        qc_path=args.qc,
    )
    print(f"Saved: {args.coverage_output} ({len(coverage_df)} rows)")
    print(f"Saved: {args.markdown_output}")


if __name__ == "__main__":
    main()
