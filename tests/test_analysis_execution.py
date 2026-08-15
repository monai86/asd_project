from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from packages.analysis_contract import (
    AnalysisStatus,
    execute_reviewed_transcript_analysis,
)


FIXTURE = Path("tests/fixtures/analysis_contract/synthetic_thai.cha")


def test_synchronous_execution_builds_versioned_request_and_provenance():
    source = FIXTURE.read_text(encoding="utf-8")
    analyzed_at = datetime(2026, 8, 16, 9, 30, tzinfo=timezone.utc)

    execution = execute_reviewed_transcript_analysis(
        input_ref="transcript-ref-001",
        session_ref="session-ref-001",
        transcript_version=3,
        chat_text=source,
        analyzed_at=analyzed_at,
    )

    assert execution.request.input.content_sha256 == sha256(
        source.encode("utf-8")
    ).hexdigest()
    assert execution.request.input.transcript_version == 3
    assert execution.request.pipeline_version == execution.profile.pipeline_version
    assert (
        execution.request.feature_schema_version
        == execution.profile.feature_definition_version
    )
    assert execution.result.status is AnalysisStatus.COMPLETED
    assert execution.result.provenance.input_ref == "transcript-ref-001"
    assert execution.result.provenance.session_ref == "session-ref-001"
    assert execution.result.provenance.analyzed_at == analyzed_at


def test_synchronous_execution_payload_never_includes_transcript_content():
    source = FIXTURE.read_text(encoding="utf-8")

    payload = execute_reviewed_transcript_analysis(
        input_ref="transcript-ref-002",
        session_ref="session-ref-002",
        transcript_version=1,
        chat_text=source,
        analyzed_at=datetime(2026, 8, 16, 9, 35, tzinfo=timezone.utc),
    ).to_dict()

    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["request"]["input"]["content_sha256"] == sha256(
        source.encode("utf-8")
    ).hexdigest()
    assert payload["profile"]["profile_checksum_sha256"]
    assert payload["result"]["status"] == "completed"
    assert "chat_text" not in serialized
    assert "raw_text" not in serialized
    assert "ไปเที่ยวกันไหม" not in serialized
