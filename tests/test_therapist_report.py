from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.therapist_report import (
    export_progress_report_pdf,
    load_longitudinal_features,
    render_progress_report_markdown,
    save_progress_report,
    summarize_child_progress,
)


def sample_df() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "child": "Demo",
            "session_id": "s2",
            "session_order": 2,
            "age_months": 38,
            "total_utterances": 20,
            "total_words": 60,
            "mlu": 1.8,
            "mluw": 2.0,
            "ttr": 0.30,
            "unintelligible_ratio": 0.20,
            "zero_vocalization_count": 8,
            "echolalia_ratio": 0.08,
        },
        {
            "child": "Demo",
            "session_id": "s1",
            "session_order": 1,
            "age_months": 36,
            "total_utterances": 10,
            "total_words": 20,
            "mlu": 1.0,
            "mluw": 1.4,
            "ttr": 0.20,
            "unintelligible_ratio": 0.30,
            "zero_vocalization_count": 12,
            "echolalia_ratio": 0.10,
        },
    ])


def test_load_longitudinal_features_reads_default_csv():
    df = load_longitudinal_features()

    assert not df.empty
    assert {"child", "session_order", "mlu", "total_words"} <= set(df.columns)


def test_summarize_child_progress_sorts_sessions_and_counts_improvements():
    summary = summarize_child_progress(sample_df(), "Demo")

    assert summary["child"] == "Demo"
    assert summary["n_sessions"] == 2
    assert summary["first_session"]["session_id"] == "s1"
    assert summary["last_session"]["session_id"] == "s2"
    assert summary["metric_changes"]["total_words"]["delta"] == 40
    assert summary["improving_metric_count"] == 8


def test_render_progress_report_markdown_includes_safe_thai_wording():
    report = render_progress_report_markdown(
        summarize_child_progress(sample_df(), "Demo")
    )

    assert "รายงานนี้ใช้ประกอบการติดตามพัฒนาการด้านภาษาและการสื่อสาร" in report
    assert "ไม่ใช่การวินิจฉัย ASD" in report
    assert "ควรใช้ร่วมกับการประเมินโดยนักบำบัดหรือแพทย์ผู้เชี่ยวชาญ" in report
    assert "total_words" in report
    assert "progress tracking" in report


def test_save_progress_report_writes_markdown(tmp_path):
    out = save_progress_report("Roger", out_dir=tmp_path)

    assert out.exists()
    assert out.name == "roger_progress_report.md"
    assert "Roger" in out.read_text(encoding="utf-8")


def test_export_progress_report_pdf_writes_non_empty_file(tmp_path):
    out = export_progress_report_pdf("Roger", out_dir=tmp_path)

    assert out.exists()
    assert out.suffix == ".pdf"
    assert out.stat().st_size > 1000


def test_save_progress_report_routes_pdf_format(tmp_path):
    out = save_progress_report("Roger", out_dir=tmp_path, format="pdf")

    assert out.exists()
    assert out.suffix == ".pdf"
    assert out.stat().st_size > 1000


def test_save_progress_report_rejects_unknown_format(tmp_path):
    with pytest.raises(ValueError, match="format must be"):
        save_progress_report("Roger", out_dir=tmp_path, format="docx")


def test_summarize_missing_child_raises_value_error():
    with pytest.raises(ValueError, match="No longitudinal rows found"):
        summarize_child_progress(sample_df(), "Missing")
