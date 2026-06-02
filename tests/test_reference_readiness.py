from __future__ import annotations

import json
import sys
from pathlib import Path
from fastapi import status
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_workflow import MockClinicalRepository
from src.therapist_backend.app import create_app
from scripts.build_reference_readiness_index import build_readiness_index


def test_build_readiness_index():
    data = build_readiness_index()
    assert "summary" in data
    assert "cells" in data
    assert "generated_at" in data
    assert "source_files" in data

    assert isinstance(data["summary"]["ok"], int)
    assert isinstance(data["summary"]["low_n"], int)
    assert isinstance(data["summary"]["not_cohort_ready"], int)

    # Check cell structures
    assert len(data["cells"]) > 0
    for cell in data["cells"]:
        assert "language" in cell
        assert "age_band_12mo" in cell
        assert "task_type" in cell
        assert "group" in cell
        assert "cohort_n" in cell
        assert "coverage_status" in cell
        assert "confidence_flag" in cell
        assert "clan_metric_ready" in cell

        assert isinstance(cell["clan_metric_ready"], bool)
        assert isinstance(cell["cohort_n"], int)

    # Verify no raw transcript or file content leaks
    # (Just ensure cell values are simple metadata strings/ints/bools, not long text blocks)
    for cell in data["cells"]:
        assert len(str(cell.get("language"))) < 20
        assert len(str(cell.get("age_band_12mo"))) < 20
        assert len(str(cell.get("task_type"))) < 20
        assert len(str(cell.get("group"))) < 20


def test_api_reference_readiness_auth_required():
    repo = MockClinicalRepository()
    app = create_app(repo)
    client = TestClient(app)

    # Missing X-User-Id
    response = client.get("/api/reference/readiness")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Invalid user
    response = client.get(
        "/api/reference/readiness",
        headers={"X-User-Id": "invalid_user"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Valid user
    response = client.get(
        "/api/reference/readiness",
        headers={"X-User-Id": "user_therapist_001"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "cells" in payload
    assert "status" in payload
    assert payload["status"] in ("ready", "unavailable")


def test_api_reference_readiness_fallback_when_missing(monkeypatch, tmp_path):
    repo = MockClinicalRepository()
    app = create_app(repo)
    client = TestClient(app)

    # Temporarily point READINESS_INDEX_PATH to a missing file path using monkeypatch
    fake_path = tmp_path / "missing_index.json"
    monkeypatch.setattr("src.therapist_backend.app.READINESS_INDEX_PATH", fake_path)

    response = client.get(
        "/api/reference/readiness",
        headers={"X-User-Id": "user_therapist_001"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["summary"] == {"ok": 0, "low_n": 0, "not_cohort_ready": 0}
    assert payload["cells"] == []
