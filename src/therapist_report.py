"""Thai-safe therapist progress report generation.

Reports are descriptive decision-support artifacts for longitudinal language
tracking. They are not clinical conclusions and do not imply Thai validation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LONGITUDINAL_PATH = PROJECT_ROOT / "data" / "longitudinal_features.csv"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "progress_reports"

REPORT_METRICS = [
    "total_utterances",
    "total_words",
    "mlu",
    "mluw",
    "ttr",
    "unintelligible_ratio",
    "zero_vocalization_count",
    "echolalia_ratio",
]

METRIC_DIRECTIONS = {
    "total_utterances": 1,
    "total_words": 1,
    "mlu": 1,
    "mluw": 1,
    "ttr": 1,
    "unintelligible_ratio": -1,
    "zero_vocalization_count": -1,
    "echolalia_ratio": -1,
    "composite_score": 1,
}


def load_longitudinal_features(path: str | Path | None = None) -> pd.DataFrame:
    """Load longitudinal feature rows sorted by child and session order."""
    csv_path = Path(path) if path is not None else DEFAULT_LONGITUDINAL_PATH
    return pd.read_csv(csv_path).sort_values(["child", "session_order"])


def _value(row: pd.Series, key: str) -> Any:
    value = row[key] if key in row else None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _metric_change(first: pd.Series, last: pd.Series, metric: str) -> dict[str, Any]:
    start = _value(first, metric)
    end = _value(last, metric)
    if start is None or end is None:
        delta = None
        improved = None
    else:
        delta = round(float(end) - float(start), 4)
        direction = METRIC_DIRECTIONS[metric]
        improved = (delta * direction) > 0
    return {
        "first": start,
        "last": end,
        "delta": delta,
        "direction": "higher_is_better" if METRIC_DIRECTIONS[metric] > 0 else "lower_is_better",
        "improved": improved,
    }


def summarize_child_progress(df: pd.DataFrame, child: str) -> dict[str, Any]:
    """Summarize first-vs-last longitudinal changes for one child."""
    if "child" not in df.columns:
        raise ValueError("DataFrame must include a child column.")

    child_rows = df[df["child"].astype(str) == str(child)].copy()
    if child_rows.empty:
        raise ValueError(f"No longitudinal rows found for child: {child}")

    child_rows = child_rows.sort_values("session_order")
    first = child_rows.iloc[0]
    last = child_rows.iloc[-1]

    metrics = [metric for metric in REPORT_METRICS if metric in child_rows.columns]
    metric_changes = {
        metric: _metric_change(first, last, metric)
        for metric in metrics
    }
    if "composite_score" in child_rows.columns:
        metric_changes["composite_score"] = _metric_change(
            first, last, "composite_score"
        )

    improving = [
        change for change in metric_changes.values()
        if change["improved"] is True
    ]
    age_start = _value(first, "age_months")
    age_end = _value(last, "age_months")

    return {
        "child": str(child),
        "n_sessions": int(len(child_rows)),
        "age_range_months": {
            "first": age_start,
            "last": age_end,
        },
        "first_session": {
            "session_id": str(_value(first, "session_id")),
            "session_order": int(_value(first, "session_order")),
        },
        "last_session": {
            "session_id": str(_value(last, "session_id")),
            "session_order": int(_value(last, "session_order")),
        },
        "metric_changes": metric_changes,
        "improving_metric_count": len(improving),
        "tracked_metric_count": len(metric_changes),
        "has_composite_score": "composite_score" in child_rows.columns,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "ไม่พบข้อมูล"
    if isinstance(value, (int, str)):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}".rstrip("0").rstrip(".")


def render_progress_report_markdown(summary: dict[str, Any]) -> str:
    """Render a Thai-safe Markdown progress report."""
    child = summary["child"]
    age = summary["age_range_months"]
    first_session = summary["first_session"]
    last_session = summary["last_session"]
    metric_rows = []
    for metric, change in summary["metric_changes"].items():
        trend = "ดีขึ้น" if change["improved"] is True else "ลดลง/คงที่"
        if change["improved"] is None:
            trend = "ข้อมูลไม่พอ"
        metric_rows.append(
            "| {metric} | {first} | {last} | {delta} | {trend} |".format(
                metric=metric,
                first=_fmt(change["first"]),
                last=_fmt(change["last"]),
                delta=_fmt(change["delta"]),
                trend=trend,
            )
        )

    if summary["has_composite_score"]:
        progress_line = (
            "มี composite progress score ในข้อมูล จึงแสดงการเปลี่ยนแปลงจาก session แรกถึง session ล่าสุดร่วมกับ metric รายตัว"
        )
    else:
        progress_line = (
            "ยังไม่มี composite progress score ในไฟล์นี้ จึงใช้การเปรียบเทียบ descriptive first-vs-last สำหรับ progress tracking"
        )

    return f"""# Therapist Progress Report: {child}

รายงานนี้ใช้ประกอบการติดตามพัฒนาการด้านภาษาและการสื่อสาร

## Child / Session Overview
- Child: {child}
- Number of sessions: {summary["n_sessions"]}
- First session: {first_session["session_id"]} (order {first_session["session_order"]})
- Last session: {last_session["session_id"]} (order {last_session["session_order"]})
- Age range: {_fmt(age["first"])} ถึง {_fmt(age["last"])} เดือน

## Key Metrics
| Metric | First | Last | Delta | Descriptive trend |
|---|---:|---:|---:|---|
{chr(10).join(metric_rows)}

## Descriptive Summary
{progress_line}

ตัวชี้วัดที่เปลี่ยนไปในทิศทางที่คาดว่าเป็นพัฒนาการเชิงบวก: {summary["improving_metric_count"]}/{summary["tracked_metric_count"]} metrics

รายงานนี้เป็น progress tracking และ decision support สำหรับการติดตามแนวโน้มจากหลาย session เท่านั้น ไม่ใช่การวินิจฉัย ASD และไม่ควรใช้แทนการประเมินโดยผู้เชี่ยวชาญ

## Safe Use Boundary
- This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.
- ไม่ใช่การวินิจฉัย ASD
- ควรใช้ร่วมกับการประเมินโดยนักบำบัดหรือแพทย์ผู้เชี่ยวชาญ
- ต้องมี human-in-the-loop ในการอ่าน transcript, ตีความบริบท, และตัดสินใจทางคลินิก
- ยังไม่มีการ validated กับข้อมูลเด็กไทย จึงต้องมี external validation ก่อนใช้งานจริงทางคลินิก
"""


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "child"


def save_progress_report(
    child: str,
    out_dir: str | Path = DEFAULT_REPORT_DIR,
    format: str = "md",
) -> Path:
    """Generate and save a progress report for one child."""
    normalized = format.lower().strip(".")
    if normalized == "pdf":
        return export_progress_report_pdf(child, Path(out_dir))
    if normalized != "md":
        raise ValueError("format must be 'md' or 'pdf'.")
    df = load_longitudinal_features()
    summary = summarize_child_progress(df, child)
    markdown = render_progress_report_markdown(summary)
    report_dir = Path(out_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / f"{_slug(child)}_progress_report.md"
    out_path.write_text(markdown, encoding="utf-8")
    return out_path


def _report_html(markdown: str, style: str = "default") -> str:
    try:
        import markdown2
    except ImportError as exc:
        raise ImportError(
            "PDF export requires markdown2. Install dependencies from requirements.txt."
        ) from exc

    body = markdown2.markdown(markdown, extras=["tables"])
    css = """
    @page { size: A4; margin: 18mm; }
    body {
        font-family: "Thonburi", "Noto Sans Thai", "Arial", sans-serif;
        color: #1f2937;
        line-height: 1.55;
        font-size: 11pt;
    }
    h1 { color: #1d4ed8; font-size: 22pt; margin-bottom: 8px; }
    h2 { color: #374151; font-size: 14pt; margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; }
    th, td { border: 1px solid #d1d5db; padding: 6px 8px; }
    th { background: #eff6ff; text-align: left; }
    li { margin-bottom: 4px; }
    """
    if style != "default":
        css += "\nbody { font-size: 10.5pt; }\n"
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"


def export_progress_report_pdf(
    child: str,
    out_dir: str | Path,
    style: str = "default",
) -> Path:
    """Export a Thai-safe progress report PDF from the Markdown report."""
    df = load_longitudinal_features()
    summary = summarize_child_progress(df, child)
    markdown = render_progress_report_markdown(summary)
    report_dir = Path(out_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / f"{_slug(child)}_progress_report.pdf"
    html = _report_html(markdown, style=style)
    try:
        from weasyprint import HTML

        HTML(string=html, base_url=str(PROJECT_ROOT)).write_pdf(str(out_path))
    except Exception:
        # WeasyPrint needs native Pango/GObject libraries that are not present
        # in every local demo environment. ReportLab keeps PDF export usable.
        _export_pdf_reportlab(markdown, out_path)
    return out_path


def _export_pdf_reportlab(markdown: str, out_path: Path) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise ImportError(
            "PDF export requires weasyprint or reportlab. Install dependencies from requirements.txt."
        ) from exc

    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 8))
            continue
        if line.startswith("|"):
            story.append(Paragraph(line.replace("|", " | "), styles["Code"]))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Title"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("- "):
            story.append(Paragraph(f"• {line[2:]}", styles["BodyText"]))
        else:
            story.append(Paragraph(line, styles["BodyText"]))
    doc.build(story)
