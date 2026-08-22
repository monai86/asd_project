"""Unit tests for LinguaLens Interactive Terminal UI."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from packages.tui.client import LinguaLensClient


def test_tui_client_cases_and_sessions():
    client = LinguaLensClient(mock_mode=True)
    
    # 1. Clean default starts empty
    cases = client.list_cases()
    assert len(cases) == 0

    # Explicit demo seeding works when requested
    client.seed_demo_dataset()
    demo_cases = client.list_cases()
    assert len(demo_cases) >= 2
    assert "case-demo-001" in [c["case_id"] for c in demo_cases]

    # Create new case
    new_case = client.create_case(child_id="C-TEST-99", birth_year_month="2022-01", notes="Test case")
    assert new_case["child_id"] == "C-TEST-99"
    assert new_case["case_id"].startswith("case-local-")

    # 2. Sessions
    sessions = client.list_sessions(new_case["case_id"])
    assert len(sessions) == 0

    new_sess = client.create_session(new_case["case_id"], session_date="2026-08-16", notes="Test session")
    assert new_sess["session_id"].startswith("sess-local-")
    assert new_sess["status"] == "Intake"

    updated_sessions = client.list_sessions(new_case["case_id"])
    assert len(updated_sessions) == 1


def test_tui_transcript_ingestion_and_review():
    client = LinguaLensClient(mock_mode=True)
    session_id = "sess-test-888"

    raw_dialogue = (
        "INV: สวัสดีครับ มาเล่นกันนะ\n"
        "CHI: เล่น บอล\n"
        "INV: โยนบอลมาสิครับ\n"
        "CHI: โยน บอล ไป"
    )

    tr = client.ingest_transcript_text(session_id, raw_dialogue)
    assert tr["status"] == "pending_review"
    assert len(tr["utterances"]) == 4
    assert tr["utterances"][1]["speaker"] == "CHI"
    assert tr["utterances"][1]["text"] == "เล่น บอล"

    # Edit utterance
    tr_id = tr["transcript_id"]
    updated_tr = client.update_utterance(tr_id, "u-2", "เล่น ลูกบอล", "CHI")
    assert updated_tr["utterances"][1]["text"] == "เล่น ลูกบอล"

    # Attest / Sign-off
    attested_tr = client.attest_transcript(tr_id, therapist_name="Kru Joy (SLP)")
    assert attested_tr["attested"] is True
    assert attested_tr["attested_by"] == "Kru Joy (SLP)"
    assert attested_tr["status"] == "Attested"


def test_tui_findings_and_report_signoff(tmp_path: Path):
    client = LinguaLensClient(mock_mode=True)
    session_id = "sess-test-999"

    # 1. Before ingestion: No fake findings!
    empty_findings = client.get_findings(session_id)
    assert empty_findings["has_data"] is False
    assert empty_findings["metrics"] == {}

    # Ingest real dialogue
    raw_dialogue = (
        "INV: วันนี้เรามาเล่นกันนะ\n"
        "CHI: เล่น รถ สี แดง\n"
        "INV: รถวิ่งเร็วไหมครับ\n"
        "CHI: เร็ว มาก เลย"
    )
    client.ingest_transcript_text(session_id, raw_dialogue)

    # 2. After ingestion: Genuine findings calculated
    findings = client.get_findings(session_id)
    assert findings["has_data"] is True
    assert "metrics" in findings
    assert "guideline_links" in findings
    assert findings["metrics"]["mlu_words"] > 0
    assert findings["metrics"]["total_child_utterances"] == 2

    # Draft report
    report = client.draft_report(session_id, prompt_notes="Child showed good engagement")
    assert report["status"] == "Draft"
    assert "การประเมินทักษะทางภาษา" in report["narrative"]

    # Sign-off report
    signed_report = client.sign_off_report(report["report_id"], therapist_name="Kru Joy (SLP)")
    assert signed_report["status"] == "Signed Off"
    assert signed_report["signed_by"] == "Kru Joy (SLP)"
    assert "sha256_hash" in signed_report
    assert len(signed_report["sha256_hash"]) == 64


def test_tui_audio_ingestion_and_acoustic_features(tmp_path: Path):
    client = LinguaLensClient(mock_mode=True)
    session_id = "sess-audio-123"

    # Create dummy audio file
    dummy_wav = tmp_path / "sample.wav"
    dummy_wav.write_bytes(b"RIFFdummyWAVEfmt ")

    tr = client.ingest_audio_file(session_id, str(dummy_wav))
    assert tr["status"] == "pending_review"
    assert tr["audio_file"] == "sample.wav"
    assert len(tr["utterances"]) > 0

    findings = client.get_findings(session_id)
    assert "f0_median_hz" in findings["metrics"]
    assert "voiced_ratio_pct" in findings["metrics"]
    assert "audio_duration_sec" in findings["metrics"]

