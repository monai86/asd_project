# Therapist-Confirmed Speaker Mapping Salvage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a version-bound, therapist-confirmed mapping step for real ASR transcripts that contain temporary speaker IDs, without changing existing manual, CHAT, canonical-ASR, Desktop GUI, or Terminal TUI behavior.

**Architecture:** Extend utterances with optional ASR provenance, persist mapping drafts and immutable confirmations as a separate aggregate, and centralize activation, validation, and workflow gating in a focused speaker-mapping service. The current transcript router exposes the mapping endpoints, while confirmation is delegated to repository-specific atomic operations so transcript mutation, downstream invalidation, mapping persistence, and privacy-safe audit persistence commit together.

**Tech Stack:** Python 3, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, Next.js, React, TypeScript, Tailwind CSS, Vitest, Testing Library, Playwright.

---

## File map

- Create `apps/api/app/schemas/speaker_mapping.py`: mapping request/response and persistence contracts.
- Create `apps/api/app/services/speaker_mapping_service.py`: activation, server-derived drafts, validation, effective status, transcript application, and shared workflow gate.
- Create `apps/api/tests/test_speaker_mapping.py`: domain, repository, route, compatibility, authorization, and workflow-gate tests.
- Create `apps/api/tests/test_sql_speaker_mapping_transactions.py`: SQL persistence, optimistic concurrency, rollback, staleness, and audit tests.
- Create `apps/api/app/db/migrations/versions/0014_add_speaker_mappings.py`: additive mapping table migration.
- Modify `apps/api/app/schemas/clinical.py`: optional utterance provenance only.
- Modify `apps/api/app/repositories/base.py`: mapping repository contract and version-conflict exception.
- Modify `apps/api/app/repositories/mock_repository.py`: in-memory and JSON mapping persistence plus atomic confirmation.
- Modify `apps/api/app/db/models.py`: `SpeakerMappingRecord`.
- Modify `apps/api/app/repositories/sqlalchemy_repository.py`: SQL mapping conversion, loading, draft save, and atomic confirmation.
- Modify `apps/api/app/services/audio_job_service.py`: retain temporary ASR speaker IDs and provider labels when available.
- Modify `apps/api/app/services/transcript_service.py`: gate QA, attestation, and CHAT export.
- Modify `apps/api/app/services/feature_service.py`: gate role-dependent extraction.
- Modify `apps/api/app/api/v1/routes/transcripts.py`: GET, PUT, and confirm endpoints with existing tenant, consent, mutation, and therapist checks.
- Modify `scripts/check_api_migrations.py` and `tests/test_api_migration_smoke.py`: revision `0014` and table/column assertions.
- Modify `apps/lingualens-app/src/lib/workflow/types.ts` and `apps/lingualens-app/src/lib/workflow.ts`: frontend mapping contracts, request helpers, and temporary-ID conversion.
- Modify `apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts`: conditional mapping load plus draft/confirm calls.
- Create `apps/lingualens-app/src/features/sessions/transcript/speaker-mapping-panel.tsx`: accessible review and confirmation panel.
- Create `apps/lingualens-app/src/__tests__/speaker-mapping-service.test.ts`: conditional request and client contract tests.
- Create `apps/lingualens-app/src/__tests__/speaker-mapping-panel.test.tsx`: panel interaction, completeness, stale, and accessibility tests.
- Modify `apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx`: mapping state and mutations.
- Modify `apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx`: render the panel before QA/attestation controls and disable gated actions.
- Modify `apps/lingualens-app/src/components/transcript-editor-panel.tsx` and `apps/lingualens-app/src/components/transcript-review-controls.tsx`: disable QA, attestation, and export while mapping is pending without disabling transcript editing.
- Modify `apps/lingualens-app/src/__tests__/session-workspace-page.test.tsx`: integrated conditional-loading and gate assertions.
- Modify `apps/lingualens-app/e2e/therapist-workflow.smoke.spec.ts`: temporary-ASR mapping through QA and attestation.
- Modify `README.md`, `CHANGELOG.md`, and `docs/PROJECT_SOURCE_OF_TRUTH.md`: current behavior and compatibility boundary.

### Task 1: Add provenance and speaker-mapping domain contracts

**Files:**
- Create: `apps/api/app/schemas/speaker_mapping.py`
- Modify: `apps/api/app/schemas/clinical.py`
- Create: `apps/api/tests/test_speaker_mapping.py`

- [ ] **Step 1: Write failing activation and schema tests**

Create `apps/api/tests/test_speaker_mapping.py` with synthetic data and no child identifiers:

```python
from __future__ import annotations

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AttestationRequest, FeatureSet, ReviewStatus, Transcript, TranscriptPatch, Utterance
from app.schemas.speaker_mapping import MappingEffectiveStatus, SpeakerMapping, SpeakerMappingEntryInput
from app.services.speaker_mapping_service import derive_mapping_draft, requires_speaker_mapping


def make_asr_transcript(
    repo: MockRepository,
    *,
    source: str = "asr_draft:manual",
    temporary_speaker_ids: tuple[str | None, ...] = ("speaker-0", "speaker-1"),
) -> Transcript:
    session = repo.sessions["session_demo_001"]
    utterances = [
        Utterance(
            utterance_id=f"utt-{index}",
            speaker="UNK",
            text=f"Synthetic sample {index}",
            temporary_speaker_id=temporary_id,
            source_speaker_label=temporary_id,
        )
        for index, temporary_id in enumerate(temporary_speaker_ids)
    ]
    transcript = Transcript(
        transcript_id=f"tr-speaker-map-{len(repo.transcripts) + 1}",
        session_id=session.session_id,
        case_id=session.case_id,
        organization_id=session.organization_id,
        source=source,
        raw_text="",
        utterances=utterances,
        review_status=ReviewStatus.needs_review,
    )
    repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )
    return repo.transcripts[transcript.transcript_id]


def test_mapping_activates_only_for_real_asr_with_temporary_ids() -> None:
    repo = MockRepository()
    assert requires_speaker_mapping(make_asr_transcript(repo)) is True
    assert requires_speaker_mapping(make_asr_transcript(repo, source="mock_asr_draft:mock")) is False
    assert requires_speaker_mapping(make_asr_transcript(repo, source="manual")) is False
    assert requires_speaker_mapping(
        make_asr_transcript(repo, temporary_speaker_ids=(None, None))
    ) is False


def test_server_derived_draft_groups_utterances_without_preselecting_roles() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(
        repo,
        temporary_speaker_ids=("speaker-0", "speaker-0", "speaker-1"),
    )

    draft = derive_mapping_draft(transcript)

    assert draft.effective_status == MappingEffectiveStatus.draft
    assert draft.persisted is False
    assert [entry.temporary_speaker_id for entry in draft.entries] == ["speaker-0", "speaker-1"]
    assert draft.entries[0].affected_utterance_ids == ["utt-0", "utt-1"]
    assert draft.entries[0].confirmed_chat_code is None
    assert draft.entries[0].participant_role is None
    assert draft.entries[0].provider_metadata == {"provider_id": "manual"}


def test_entry_input_does_not_accept_provider_owned_fields() -> None:
    entry = SpeakerMappingEntryInput.model_validate({
        "temporary_speaker_id": "speaker-0",
        "confirmed_chat_code": "CHI",
        "participant_role": "target_child",
        "reviewed_utterance_ids": ["utt-0"],
        "source_speaker_label": "client-forged-label",
        "provider_metadata": {"provider_id": "client-forged-provider"},
    })
    assert not hasattr(entry, "source_speaker_label")
    assert not hasattr(entry, "provider_metadata")
```

- [ ] **Step 2: Run the new tests and verify the missing-contract failure**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py -q`

Expected: collection fails because `app.schemas.speaker_mapping` does not exist and `Utterance` has no `temporary_speaker_id` field.

- [ ] **Step 3: Add optional utterance provenance**

Add these fields to `Utterance` in `apps/api/app/schemas/clinical.py` immediately after `confidence`:

```python
    temporary_speaker_id: str | None = None
    source_speaker_label: str | None = None
```

Keep both optional so existing records and all non-ASR callers remain valid.

- [ ] **Step 4: Add the complete mapping schema module**

Create `apps/api/app/schemas/speaker_mapping.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.clinical import utc_now


class MappingPersistedStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"


class MappingEffectiveStatus(str, Enum):
    not_required = "not_required"
    draft = "draft"
    confirmed = "confirmed"
    stale = "stale"


class SpeakerMappingEntryInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    temporary_speaker_id: str = Field(min_length=1, max_length=128)
    confirmed_chat_code: Literal["CHI", "THER", "OTH"] | None = None
    participant_role: Literal["target_child", "therapist", "other"] | None = None
    reviewed_utterance_ids: list[str] = Field(default_factory=list)


class SpeakerMappingEntry(SpeakerMappingEntryInput):
    source_speaker_label: str | None = None
    provider_metadata: dict[str, str] = Field(default_factory=dict)
    affected_utterance_ids: list[str] = Field(default_factory=list)


class SpeakerMapping(BaseModel):
    mapping_id: str
    organization_id: str
    transcript_id: str
    source_transcript_version: int
    applied_transcript_version: int | None = None
    mapping_version: int = 1
    status: MappingPersistedStatus = MappingPersistedStatus.draft
    entries: list[SpeakerMappingEntry]
    confirmed_by_user_id: str | None = None
    confirmed_by_role: str | None = None
    confirmed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SpeakerMappingResponse(SpeakerMapping):
    required: bool
    persisted: bool
    effective_status: MappingEffectiveStatus
    issue_code: str | None = None
    issue_message: str | None = None


class SpeakerMappingDraftUpdate(BaseModel):
    expected_transcript_version: int
    expected_mapping_version: int | None = None
    entries: list[SpeakerMappingEntryInput]


class SpeakerMappingConfirmRequest(BaseModel):
    expected_transcript_version: int
    expected_mapping_version: int
```

- [ ] **Step 5: Add activation and server-derived draft functions**

Create `apps/api/app/services/speaker_mapping_service.py` with the first complete slice:

```python
from __future__ import annotations

from collections import OrderedDict

from app.repositories.mock_repository import new_id
from app.schemas.clinical import Transcript
from app.schemas.speaker_mapping import (
    MappingEffectiveStatus,
    MappingPersistedStatus,
    SpeakerMapping,
    SpeakerMappingEntry,
    SpeakerMappingResponse,
)


def requires_speaker_mapping(transcript: Transcript) -> bool:
    return transcript.source.startswith("asr_draft:") and any(
        bool((utterance.temporary_speaker_id or "").strip())
        for utterance in transcript.utterances
    )


def derive_mapping_draft(transcript: Transcript) -> SpeakerMappingResponse:
    groups: OrderedDict[str, list] = OrderedDict()
    for utterance in transcript.utterances:
        temporary_id = (utterance.temporary_speaker_id or "").strip()
        if temporary_id:
            groups.setdefault(temporary_id, []).append(utterance)
    provider_id = transcript.source.split(":", 1)[1] if transcript.source.startswith("asr_draft:") else ""
    entries = [
        SpeakerMappingEntry(
            temporary_speaker_id=temporary_id,
            source_speaker_label=next(
                (item.source_speaker_label for item in utterances if item.source_speaker_label),
                None,
            ),
            provider_metadata={"provider_id": provider_id} if provider_id else {},
            affected_utterance_ids=[item.utterance_id for item in utterances],
            reviewed_utterance_ids=[],
        )
        for temporary_id, utterances in groups.items()
    ]
    return SpeakerMappingResponse(
        mapping_id=f"unsaved-{transcript.transcript_id}-v{transcript.version}",
        organization_id=transcript.organization_id,
        transcript_id=transcript.transcript_id,
        source_transcript_version=transcript.version,
        status=MappingPersistedStatus.draft,
        entries=entries,
        required=requires_speaker_mapping(transcript),
        persisted=False,
        effective_status=(
            MappingEffectiveStatus.draft
            if requires_speaker_mapping(transcript)
            else MappingEffectiveStatus.not_required
        ),
    )
```

- [ ] **Step 6: Run the focused tests**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py -q`

Expected: `3 passed`.

- [ ] **Step 7: Commit the contracts**

```bash
git add apps/api/app/schemas/clinical.py apps/api/app/schemas/speaker_mapping.py apps/api/app/services/speaker_mapping_service.py apps/api/tests/test_speaker_mapping.py
git commit -m "feat: add speaker mapping contracts" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 2: Persist versioned drafts in memory and JSON

**Files:**
- Modify: `apps/api/app/repositories/base.py`
- Modify: `apps/api/app/repositories/mock_repository.py`
- Modify: `apps/api/app/services/speaker_mapping_service.py`
- Test: `apps/api/tests/test_speaker_mapping.py`

- [ ] **Step 1: Add failing draft persistence and optimistic-concurrency tests**

Append to `apps/api/tests/test_speaker_mapping.py`:

```python
import pytest

from app.repositories.base import SpeakerMappingVersionConflictError
from app.repositories.mock_repository import JsonFileRepository
from app.schemas.speaker_mapping import SpeakerMappingDraftUpdate
from app.services.speaker_mapping_service import get_mapping, save_mapping_draft


def complete_draft_payload(transcript: Transcript) -> SpeakerMappingDraftUpdate:
    return SpeakerMappingDraftUpdate(
        expected_transcript_version=transcript.version,
        entries=[
            {
                "temporary_speaker_id": "speaker-0",
                "confirmed_chat_code": "CHI",
                "participant_role": "target_child",
                "reviewed_utterance_ids": ["utt-0"],
            },
            {
                "temporary_speaker_id": "speaker-1",
                "confirmed_chat_code": "THER",
                "participant_role": "therapist",
                "reviewed_utterance_ids": ["utt-1"],
            },
        ],
    )


def test_save_draft_rebuilds_provider_owned_fields_and_increments_version() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo)
    first = save_mapping_draft(repo, transcript.transcript_id, complete_draft_payload(transcript))
    second_payload = complete_draft_payload(transcript).model_copy(
        update={"expected_mapping_version": first.mapping_version}
    )

    second = save_mapping_draft(repo, transcript.transcript_id, second_payload)

    assert first.persisted is True
    assert second.mapping_version == 2
    assert second.entries[0].source_speaker_label == "speaker-0"
    assert second.entries[0].provider_metadata == {"provider_id": "manual"}


def test_save_draft_rejects_stale_mapping_version_without_mutation() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo)
    saved = save_mapping_draft(repo, transcript.transcript_id, complete_draft_payload(transcript))
    stale = complete_draft_payload(transcript).model_copy(update={"expected_mapping_version": 0})

    with pytest.raises(SpeakerMappingVersionConflictError):
        save_mapping_draft(repo, transcript.transcript_id, stale)

    assert get_mapping(repo, transcript.transcript_id).mapping_version == saved.mapping_version


def test_json_repository_round_trips_mapping_draft(tmp_path) -> None:
    path = tmp_path / "speaker-mapping-state.json"
    repo = JsonFileRepository(path)
    transcript = make_asr_transcript(repo)
    saved = save_mapping_draft(repo, transcript.transcript_id, complete_draft_payload(transcript))
    repo.save()

    reopened = JsonFileRepository(path)
    restored = get_mapping(reopened, transcript.transcript_id)

    assert restored.mapping_id == saved.mapping_id
    assert restored.mapping_version == saved.mapping_version
    assert restored.entries == saved.entries
```

- [ ] **Step 2: Verify the repository tests fail**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py -q`

Expected: FAIL because the mapping repository methods and service functions are absent.

- [ ] **Step 3: Extend the repository protocol**

In `apps/api/app/repositories/base.py`, import `SpeakerMapping`, add the exception, and add these protocol methods:

```python
class SpeakerMappingVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale speaker mapping version."""


class ClinicalRepository(Protocol):
    def get_latest_speaker_mapping(self, transcript_id: str) -> SpeakerMapping | None: ...

    def save_speaker_mapping_draft(
        self,
        mapping: SpeakerMapping,
        *,
        expected_mapping_version: int | None,
        actor_id: str,
    ) -> SpeakerMapping: ...
```

- [ ] **Step 4: Add in-memory and JSON storage**

In `MockRepository.__init__`, initialize `self.speaker_mappings: dict[str, SpeakerMapping] = {}`. Add these methods after `update_transcript`:

```python
    def get_latest_speaker_mapping(self, transcript_id: str) -> SpeakerMapping | None:
        candidates = [
            item for item in self.speaker_mappings.values()
            if item.transcript_id == transcript_id
        ]
        if not candidates:
            return None
        return self.clone(max(candidates, key=lambda item: (item.source_transcript_version, item.mapping_version)))

    def save_speaker_mapping_draft(
        self,
        mapping: SpeakerMapping,
        *,
        expected_mapping_version: int | None,
        actor_id: str,
    ) -> SpeakerMapping:
        latest = self.get_latest_speaker_mapping(mapping.transcript_id)
        current_draft = latest if (
            latest is not None
            and latest.status == MappingPersistedStatus.draft
            and latest.source_transcript_version == mapping.source_transcript_version
        ) else None
        if current_draft is None and expected_mapping_version is not None:
            raise SpeakerMappingVersionConflictError("Speaker mapping draft version changed; reload and retry.")
        if current_draft is not None and current_draft.mapping_version != expected_mapping_version:
            raise SpeakerMappingVersionConflictError("Speaker mapping draft version changed; reload and retry.")
        mapping.mapping_id = current_draft.mapping_id if current_draft else mapping.mapping_id
        mapping.mapping_version = (latest.mapping_version + 1) if latest else 1
        mapping.created_at = current_draft.created_at if current_draft else mapping.created_at
        mapping.updated_at = utc_now()
        self.speaker_mappings[mapping.mapping_id] = self.clone(mapping)
        MockRepository.add_audit(
            self,
            "speaker_mapping.draft_save",
            mapping.mapping_id,
            "Speaker mapping draft saved.",
            actor_id=actor_id,
        )
        if isinstance(self, JsonFileRepository):
            self.save()
        return self.clone(mapping)
```

Add `speaker_mappings` to `snapshot()`, hydrate it in `JsonFileRepository.load()`, and include mapping IDs in `_organization_for_target`:

```python
"speaker_mappings": {
    key: value.model_dump(mode="json") for key, value in self.speaker_mappings.items()
},
```

```python
self.speaker_mappings = {
    key: SpeakerMapping.model_validate(value)
    for key, value in data.get("speaker_mappings", {}).items()
}
```

- [ ] **Step 5: Implement draft merging and effective-status reads**

Append these functions to `speaker_mapping_service.py`:

```python
from app.repositories.base import SpeakerMappingVersionConflictError, TranscriptVersionConflictError
from app.schemas.speaker_mapping import SpeakerMappingDraftUpdate


def get_mapping(repo, transcript_id: str) -> SpeakerMappingResponse:
    transcript = repo.transcripts[transcript_id]
    required = requires_speaker_mapping(transcript)
    stored = repo.get_latest_speaker_mapping(transcript_id)
    if stored is None:
        return derive_mapping_draft(transcript)
    if stored.status == MappingPersistedStatus.confirmed:
        current = stored.applied_transcript_version == transcript.version
        effective = MappingEffectiveStatus.confirmed if current else MappingEffectiveStatus.stale
    else:
        current = stored.source_transcript_version == transcript.version
        effective = MappingEffectiveStatus.draft if current else MappingEffectiveStatus.stale
    return SpeakerMappingResponse(
        **stored.model_dump(),
        required=required,
        persisted=True,
        effective_status=effective if required else MappingEffectiveStatus.not_required,
        issue_code="SPEAKER_MAPPING_STALE" if required and not current else None,
        issue_message="Transcript changed; reload and create a mapping for the current version." if required and not current else None,
    )


def save_mapping_draft(repo, transcript_id: str, payload: SpeakerMappingDraftUpdate, *, actor_id: str = "system") -> SpeakerMappingResponse:
    transcript = repo.transcripts[transcript_id]
    if transcript.version != payload.expected_transcript_version:
        raise TranscriptVersionConflictError("Transcript version changed; reload and retry.")
    derived = derive_mapping_draft(transcript)
    derived_by_id = {entry.temporary_speaker_id: entry for entry in derived.entries}
    entries = []
    for client_entry in payload.entries:
        server_entry = derived_by_id.get(client_entry.temporary_speaker_id)
        if server_entry is None:
            continue
        entries.append(server_entry.model_copy(update={
            "confirmed_chat_code": client_entry.confirmed_chat_code,
            "participant_role": client_entry.participant_role,
            "reviewed_utterance_ids": list(client_entry.reviewed_utterance_ids),
        }))
    mapping = SpeakerMapping(
        mapping_id=new_id("spmap"),
        organization_id=transcript.organization_id,
        transcript_id=transcript.transcript_id,
        source_transcript_version=transcript.version,
        status=MappingPersistedStatus.draft,
        entries=entries,
    )
    saved = repo.save_speaker_mapping_draft(
        mapping,
        expected_mapping_version=payload.expected_mapping_version,
        actor_id=actor_id,
    )
    return get_mapping(repo, saved.transcript_id)
```

- [ ] **Step 6: Run focused tests and commit**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py -q`

Expected: all tests pass.

```bash
git add apps/api/app/repositories/base.py apps/api/app/repositories/mock_repository.py apps/api/app/services/speaker_mapping_service.py apps/api/tests/test_speaker_mapping.py
git commit -m "feat: persist speaker mapping drafts" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 3: Validate and atomically confirm mappings in the local repositories

**Files:**
- Modify: `apps/api/app/repositories/base.py`
- Modify: `apps/api/app/repositories/mock_repository.py`
- Modify: `apps/api/app/services/speaker_mapping_service.py`
- Modify: `apps/api/app/services/transcript_service.py`
- Modify: `apps/api/app/services/feature_service.py`
- Test: `apps/api/tests/test_speaker_mapping.py`

- [ ] **Step 1: Write failing validation, confirmation, gate, staleness, and audit tests**

Append parameterized tests that assert each stable code and a successful confirmation:

```python
from app.schemas.clinical import QaStatus
from app.schemas.speaker_mapping import SpeakerMappingConfirmRequest
from app.services import transcript_service
from app.services.speaker_mapping_service import SpeakerMappingError, confirm_mapping, require_confirmed_mapping


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (lambda entries: entries[:1], "SPEAKER_MAPPING_INCOMPLETE"),
        (lambda entries: [entry.model_copy(update={"confirmed_chat_code": "THER", "participant_role": "therapist"}) for entry in entries], "SPEAKER_MAPPING_TARGET_REQUIRED"),
        (lambda entries: [entry.model_copy(update={"confirmed_chat_code": "CHI", "participant_role": "target_child"}) for entry in entries], "SPEAKER_MAPPING_DUPLICATE_CODE"),
        (lambda entries: [entries[0].model_copy(update={"reviewed_utterance_ids": []}), entries[1]], "SPEAKER_MAPPING_INCOMPLETE"),
    ],
)
def test_confirmation_validation_is_fail_closed(mutate, expected_code) -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo)
    payload = complete_draft_payload(transcript)
    payload.entries = mutate(payload.entries)
    saved = save_mapping_draft(repo, transcript.transcript_id, payload)

    with pytest.raises(SpeakerMappingError) as exc_info:
        confirm_mapping(repo, transcript.transcript_id, SpeakerMappingConfirmRequest(
            expected_transcript_version=transcript.version,
            expected_mapping_version=saved.mapping_version,
        ), actor_id="therapist-demo", actor_role="therapist")

    assert exc_info.value.code == expected_code
    assert repo.transcripts[transcript.transcript_id].version == transcript.version


def test_confirmation_updates_transcript_once_preserves_provenance_and_audits_safely() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo)
    stale_candidate = FeatureSet(
        feature_set_id="fs-before-mapping",
        session_id=transcript.session_id,
        transcript_id=transcript.transcript_id,
        transcript_version=transcript.version,
        therapist_attested=False,
        features=[],
        review_status=ReviewStatus.ready,
    )
    repo.features[stale_candidate.feature_set_id] = stale_candidate
    repo.sessions[transcript.session_id].feature_set_id = stale_candidate.feature_set_id
    saved = save_mapping_draft(repo, transcript.transcript_id, complete_draft_payload(transcript))

    confirmed = confirm_mapping(repo, transcript.transcript_id, SpeakerMappingConfirmRequest(
        expected_transcript_version=transcript.version,
        expected_mapping_version=saved.mapping_version,
    ), actor_id="therapist-demo", actor_role="therapist")

    updated = repo.transcripts[transcript.transcript_id]
    assert [getattr(item.speaker, "value", item.speaker) for item in updated.utterances] == ["CHI", "THER"]
    assert [item.temporary_speaker_id for item in updated.utterances] == ["speaker-0", "speaker-1"]
    assert updated.version == transcript.version + 1
    assert updated.qa_status == QaStatus.not_run
    assert confirmed.applied_transcript_version == updated.version
    assert confirmed.effective_status == MappingEffectiveStatus.confirmed
    assert repo.features[stale_candidate.feature_set_id].review_status == ReviewStatus.stale
    event = repo.audit_log[-1]
    assert event["action"] == "speaker_mapping.confirm"
    assert "Synthetic sample" not in str(event)


def test_required_mapping_gates_qa_attestation_export_and_features() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo)

    with pytest.raises(SpeakerMappingError) as qa_error:
        transcript_service.run_qa(repo, transcript.transcript_id)
    with pytest.raises(SpeakerMappingError) as export_error:
        transcript_service.export_cha(repo, transcript.transcript_id)

    assert qa_error.value.code == "SPEAKER_MAPPING_REQUIRED"
    assert export_error.value.code == "SPEAKER_MAPPING_REQUIRED"


def test_confirmed_mapping_becomes_stale_after_a_provenance_preserving_edit() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo)
    saved = save_mapping_draft(repo, transcript.transcript_id, complete_draft_payload(transcript))
    confirm_mapping(repo, transcript.transcript_id, SpeakerMappingConfirmRequest(
        expected_transcript_version=transcript.version,
        expected_mapping_version=saved.mapping_version,
    ), actor_id="therapist-demo", actor_role="therapist")
    current = repo.transcripts[transcript.transcript_id]
    edited = [item.model_copy(update={"text": f"{item.text} reviewed"}) for item in current.utterances]
    transcript_service.patch_transcript(
        repo,
        transcript.transcript_id,
        TranscriptPatch(utterances=edited, reviewer_note="Synthetic edit."),
    )
    assert get_mapping(repo, transcript.transcript_id).effective_status == MappingEffectiveStatus.stale
    with pytest.raises(SpeakerMappingError) as exc_info:
        require_confirmed_mapping(repo, repo.transcripts[transcript.transcript_id])
    assert exc_info.value.code == "SPEAKER_MAPPING_STALE"
```

Append these exact cluster-limit tests:

```python
def test_three_unique_speakers_can_confirm_without_merging() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo, temporary_speaker_ids=("speaker-0", "speaker-1", "speaker-2"))
    payload = SpeakerMappingDraftUpdate(
        expected_transcript_version=transcript.version,
        entries=[
            {"temporary_speaker_id": "speaker-0", "confirmed_chat_code": "CHI", "participant_role": "target_child", "reviewed_utterance_ids": ["utt-0"]},
            {"temporary_speaker_id": "speaker-1", "confirmed_chat_code": "THER", "participant_role": "therapist", "reviewed_utterance_ids": ["utt-1"]},
            {"temporary_speaker_id": "speaker-2", "confirmed_chat_code": "OTH", "participant_role": "other", "reviewed_utterance_ids": ["utt-2"]},
        ],
    )
    saved = save_mapping_draft(repo, transcript.transcript_id, payload)
    confirmed = confirm_mapping(repo, transcript.transcript_id, SpeakerMappingConfirmRequest(
        expected_transcript_version=transcript.version,
        expected_mapping_version=saved.mapping_version,
    ), actor_id="therapist-demo", actor_role="therapist")
    assert confirmed.effective_status == MappingEffectiveStatus.confirmed


def test_four_unique_speakers_require_a_future_explicit_merge_design() -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(
        repo,
        temporary_speaker_ids=("speaker-0", "speaker-1", "speaker-2", "speaker-3"),
    )
    draft = derive_mapping_draft(transcript)
    repo.speaker_mappings[draft.mapping_id] = SpeakerMapping.model_validate({
        **draft.model_dump(exclude={"required", "persisted", "effective_status", "issue_code", "issue_message"}),
        "entries": [
            entry.model_copy(update={
                "confirmed_chat_code": ("CHI", "THER", "OTH", "OTH")[index],
                "participant_role": ("target_child", "therapist", "other", "other")[index],
                "reviewed_utterance_ids": entry.affected_utterance_ids,
            })
            for index, entry in enumerate(draft.entries)
        ],
    })
    with pytest.raises(SpeakerMappingError) as exc_info:
        confirm_mapping(repo, transcript.transcript_id, SpeakerMappingConfirmRequest(
            expected_transcript_version=transcript.version,
            expected_mapping_version=1,
        ), actor_id="therapist-demo", actor_role="therapist")
    assert exc_info.value.code == "SPEAKER_MAPPING_INCOMPLETE"
```

- [ ] **Step 2: Run the tests and verify they fail before mutation**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py -q`

Expected: FAIL because confirmation and the shared gate are not defined.

- [ ] **Step 3: Add the error, validation, mapping, and shared gate implementation**

Append to `speaker_mapping_service.py`:

```python
from app.schemas.clinical import QaStatus, ReviewStatus, utc_now
from app.schemas.speaker_mapping import SpeakerMappingConfirmRequest
from app.services.cha_service import build_cha_text, chat_build_options


class SpeakerMappingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_mapping_entries(transcript: Transcript, mapping: SpeakerMapping) -> None:
    derived = derive_mapping_draft(transcript)
    affected = {entry.temporary_speaker_id: set(entry.affected_utterance_ids) for entry in derived.entries}
    supplied = {entry.temporary_speaker_id: entry for entry in mapping.entries}
    if len(affected) > 3 or set(supplied) != set(affected):
        raise SpeakerMappingError("SPEAKER_MAPPING_INCOMPLETE", "Map every temporary speaker before continuing.")
    codes = [entry.confirmed_chat_code for entry in mapping.entries]
    if any(code is None for code in codes):
        raise SpeakerMappingError("SPEAKER_MAPPING_INCOMPLETE", "Choose a CHAT code for every temporary speaker.")
    if len(codes) != len(set(codes)):
        raise SpeakerMappingError("SPEAKER_MAPPING_DUPLICATE_CODE", "Each temporary speaker needs a unique CHAT code.")
    targets = [entry for entry in mapping.entries if entry.confirmed_chat_code == "CHI" and entry.participant_role == "target_child"]
    if len(targets) != 1:
        raise SpeakerMappingError("SPEAKER_MAPPING_TARGET_REQUIRED", "Select exactly one target child speaker.")
    for temporary_id, utterance_ids in affected.items():
        entry = supplied[temporary_id]
        if set(entry.reviewed_utterance_ids) != utterance_ids or entry.participant_role is None:
            raise SpeakerMappingError("SPEAKER_MAPPING_INCOMPLETE", "Review every affected utterance and select each participant role.")


def build_confirmed_transcript(transcript: Transcript, mapping: SpeakerMapping) -> Transcript:
    code_by_id = {entry.temporary_speaker_id: entry.confirmed_chat_code for entry in mapping.entries}
    role_label = {"CHI": "Target_Child", "THER": "Therapist", "OTH": "Other"}
    utterances = [
        utterance.model_copy(update={"speaker": code_by_id[utterance.temporary_speaker_id]})
        if utterance.temporary_speaker_id in code_by_id
        else utterance.model_copy(deep=True)
        for utterance in transcript.utterances
    ]
    options = chat_build_options(transcript.raw_text)
    options["participants"] = ", ".join(
        f"{entry.confirmed_chat_code} {entry.confirmed_chat_code} {role_label[entry.confirmed_chat_code]}"
        for entry in mapping.entries
        if entry.confirmed_chat_code is not None
    )
    options["participant_ids"] = []
    return transcript.model_copy(deep=True, update={
        "utterances": utterances,
        "raw_text": build_cha_text(utterances, **options),
        "version": transcript.version + 1,
        "qa_status": QaStatus.not_run,
        "qa_issues": [],
        "therapist_attested": False,
        "review_status": ReviewStatus.needs_review,
        "updated_at": utc_now(),
    })


def require_confirmed_mapping(repo, transcript: Transcript) -> None:
    if not requires_speaker_mapping(transcript):
        return
    mapping = get_mapping(repo, transcript.transcript_id)
    if mapping.effective_status == MappingEffectiveStatus.confirmed:
        return
    code = "SPEAKER_MAPPING_STALE" if mapping.effective_status == MappingEffectiveStatus.stale else "SPEAKER_MAPPING_REQUIRED"
    raise SpeakerMappingError(code, "Confirm the speaker mapping for the current transcript version before continuing.")


def confirm_mapping(repo, transcript_id: str, payload: SpeakerMappingConfirmRequest, *, actor_id: str, actor_role: str) -> SpeakerMappingResponse:
    transcript = repo.transcripts[transcript_id]
    mapping = repo.get_latest_speaker_mapping(transcript_id)
    if mapping is None or mapping.status != MappingPersistedStatus.draft:
        raise SpeakerMappingError("SPEAKER_MAPPING_REQUIRED", "Save a speaker mapping draft before confirmation.")
    if transcript.version != payload.expected_transcript_version or mapping.mapping_version != payload.expected_mapping_version:
        raise SpeakerMappingError("SPEAKER_MAPPING_VERSION_CONFLICT", "Transcript or mapping changed; reload and retry.")
    validate_mapping_entries(transcript, mapping)
    updated_transcript = build_confirmed_transcript(transcript, mapping)
    confirmed = mapping.model_copy(deep=True, update={
        "status": MappingPersistedStatus.confirmed,
        "applied_transcript_version": updated_transcript.version,
        "confirmed_by_user_id": actor_id,
        "confirmed_by_role": actor_role,
        "confirmed_at": utc_now(),
        "updated_at": utc_now(),
    })
    repo.confirm_speaker_mapping(
        confirmed,
        updated_transcript,
        expected_transcript_version=payload.expected_transcript_version,
        expected_mapping_version=payload.expected_mapping_version,
        actor_id=actor_id,
    )
    return get_mapping(repo, transcript_id)
```

Resolve the service import cycle by moving `chat_build_options` from `transcript_service.py` to `cha_service.py` as `chat_build_options`, then import it from both services. This is a mechanical move with the existing function body unchanged.

- [ ] **Step 4: Add repository atomic confirmation**

Add `confirm_speaker_mapping(...)` to `ClinicalRepository`. In `MockRepository`, validate both current versions before changing state, clone the prior state, apply the transcript and mapping, call `_mark_downstream_outputs_stale`, and append exactly these privacy-safe audit messages:

```python
    def confirm_speaker_mapping(
        self,
        mapping: SpeakerMapping,
        transcript: Transcript,
        *,
        expected_transcript_version: int,
        expected_mapping_version: int,
        actor_id: str,
    ) -> SpeakerMapping:
        current_transcript = self.transcripts[transcript.transcript_id]
        current_mapping = self.speaker_mappings[mapping.mapping_id]
        if current_transcript.version != expected_transcript_version:
            raise TranscriptVersionConflictError("Transcript version changed; reload and retry.")
        if current_mapping.mapping_version != expected_mapping_version:
            raise SpeakerMappingVersionConflictError("Speaker mapping version changed; reload and retry.")
        session = self.sessions[transcript.session_id]
        self._mark_downstream_outputs_stale(session)
        transcript.organization_id = session.organization_id
        self.transcripts[transcript.transcript_id] = self.clone(transcript)
        mapping.mapping_version = current_mapping.mapping_version + 1
        self.speaker_mappings[mapping.mapping_id] = self.clone(mapping)
        session.status = ReviewStatus.needs_review
        MockRepository.add_audit(
            self,
            "speaker_mapping.confirm",
            mapping.mapping_id,
            f"Speaker mapping confirmed for transcript version {transcript.version}.",
            actor_id=actor_id,
            correlation_id=f"speaker-mapping-confirm-{mapping.mapping_id}-v{mapping.mapping_version}",
        )
        if isinstance(self, JsonFileRepository):
            self.save()
        return self.clone(mapping)
```

- [ ] **Step 5: Apply the shared gate at all four backend boundaries**

At the start of `run_qa`, `attest`, and `export_cha` in `transcript_service.py`, and after transcript lookup in `extract_features` in `feature_service.py`, call:

```python
speaker_mapping_service.require_confirmed_mapping(repo, transcript)
```

Import the module as `from app.services import speaker_mapping_service` to avoid a service symbol collision.

- [ ] **Step 6: Run focused and existing workflow tests**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py tests/test_workflow.py -q`

Expected: all tests pass; existing manual, CHAT, and mock-ASR tests remain unchanged.

- [ ] **Step 7: Commit confirmation and gates**

```bash
git add apps/api/app/repositories/base.py apps/api/app/repositories/mock_repository.py apps/api/app/services/cha_service.py apps/api/app/services/speaker_mapping_service.py apps/api/app/services/transcript_service.py apps/api/app/services/feature_service.py apps/api/tests/test_speaker_mapping.py
git commit -m "feat: confirm and gate temporary speaker mappings" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 4: Retain temporary speaker IDs from the maintained ASR pipeline

**Files:**
- Modify: `apps/api/app/services/asr_providers/base.py`
- Modify: `apps/api/app/services/audio_job_service.py`
- Modify: `apps/api/tests/test_asr_provider_registry.py`
- Modify: `apps/api/tests/test_workflow.py`

- [ ] **Step 1: Write failing ASR provenance tests**

Extend the ASR line contract test and the audio workflow test with:

```python
provider = ManualTranscriptionProvider()
result = provider.transcribe("local-audio-ref", {"draft_text": "SPK0: Synthetic sample"})
assert result.transcript_lines[0].temporary_speaker_id == "SPK0"
assert result.transcript_lines[0].source_speaker_label == "SPK0"
```

After processing a real manual-provider draft in `test_audio_process_creates_unreviewed_asr_draft_and_blocks_features`, assert:

```python
assert transcript["utterances"][0]["temporary_speaker_id"]
assert transcript["utterances"][0]["source_speaker_label"]
mapping = client.get(f"/api/v1/transcripts/{transcript_id}/speaker-mapping")
assert mapping.status_code == 200
assert mapping.json()["required"] is True
```

Keep the mock provider assertion explicit:

```python
assert client.get(f"/api/v1/transcripts/{mock_transcript_id}/speaker-mapping").json()["required"] is False
```

- [ ] **Step 2: Verify the provenance assertions fail**

Run: `cd apps/api && pytest tests/test_asr_provider_registry.py tests/test_workflow.py::test_audio_process_creates_unreviewed_asr_draft_and_blocks_features -q`

Expected: FAIL because the provider line has no temporary speaker fields.

- [ ] **Step 3: Extend the provider line and preserve it in utterances**

Add optional fields to the ASR provider `TranscriptLine` dataclass/model in `apps/api/app/services/asr_providers/base.py`:

```python
    temporary_speaker_id: str | None = None
    source_speaker_label: str | None = None
```

In `manual_provider.py`, preserve a non-canonical source label without assigning a clinical role:

```python
            raw_speaker = str(u.speaker)
            temporary_speaker_id = raw_speaker if raw_speaker not in {"CHI", "THER", "OTH"} else None
            lines.append(
                TranscriptLine(
                    line_id=f"man-{i+1:03d}",
                    speaker=raw_speaker,
                    text=u.text,
                    start_ms=u.start_ms,
                    end_ms=u.end_ms,
                    temporary_speaker_id=temporary_speaker_id,
                    source_speaker_label=temporary_speaker_id,
                    source="manual",
                )
            )
```

In `create_draft_transcript_from_result`, preserve those provider fields:

```python
        utt = Utterance(
            utterance_id=new_id("utt"),
            speaker=speaker_code,
            text=line.text,
            start_ms=line.start_ms,
            end_ms=line.end_ms,
            confidence=line.confidence,
            unintelligible=line.unclear,
            temporary_speaker_id=line.temporary_speaker_id,
            source_speaker_label=line.source_speaker_label,
            source=line.source,
            notes="ASR draft — therapist review required." if (line.unclear or speaker_code == "UNK") else "",
            review_status="draft",
        )
```

Do not manufacture temporary IDs when a provider returns canonical `CHI`/`THER` only; this preserves the canonical-ASR bypass.

- [ ] **Step 4: Run ASR and mapping tests, then commit**

Run: `cd apps/api && pytest tests/test_asr_provider_registry.py tests/test_speaker_mapping.py tests/test_workflow.py::test_audio_process_creates_unreviewed_asr_draft_and_blocks_features -q`

Expected: all selected tests pass.

```bash
git add apps/api/app/services/asr_providers/base.py apps/api/app/services/audio_job_service.py apps/api/tests/test_asr_provider_registry.py apps/api/tests/test_workflow.py
git commit -m "feat: retain temporary ASR speaker provenance" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 5: Add SQL persistence and migration revision 0014

**Files:**
- Create: `apps/api/app/db/migrations/versions/0014_add_speaker_mappings.py`
- Modify: `apps/api/app/db/models.py`
- Modify: `apps/api/app/repositories/sqlalchemy_repository.py`
- Modify: `scripts/check_api_migrations.py`
- Modify: `tests/test_api_migration_smoke.py`
- Create: `apps/api/tests/test_sql_speaker_mapping_transactions.py`

- [ ] **Step 1: Write failing migration and SQL transaction tests**

In `tests/test_api_migration_smoke.py`, require `speaker_mappings`. Create the SQL test file with these concrete helpers before the tests:

```python
from __future__ import annotations

import pytest

from app.repositories.base import SpeakerMappingVersionConflictError
from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
from app.schemas.clinical import ChildCaseCreate, ReviewStatus, TherapySessionCreate, Transcript, Utterance
from app.schemas.speaker_mapping import MappingPersistedStatus, SpeakerMappingConfirmRequest, SpeakerMappingDraftUpdate
from app.services.speaker_mapping_service import build_confirmed_transcript, confirm_mapping, save_mapping_draft


@pytest.fixture
def sql_repo(tmp_path) -> SqlAlchemyRepository:
    pytest.importorskip("sqlalchemy")
    return SqlAlchemyRepository(f"sqlite:///{tmp_path / 'speaker-mapping.db'}")


def seed_temporary_asr_transcript(repo: SqlAlchemyRepository) -> Transcript:
    case = repo.create_case(
        ChildCaseCreate(child_code="C-SPMAP-SQL", age_months=60, consent_status="granted"),
        actor_id="therapist-demo",
    )
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-08-23", session_type="language_sample"),
        actor_id="therapist-demo",
    )
    transcript = Transcript(
        transcript_id="tr-spmap-sql",
        session_id=session.session_id,
        case_id=case.case_id,
        organization_id=case.organization_id,
        source="asr_draft:manual",
        raw_text="",
        utterances=[
            Utterance(utterance_id="utt-0", speaker="UNK", text="Synthetic zero", temporary_speaker_id="speaker-0", source_speaker_label="speaker-0"),
            Utterance(utterance_id="utt-1", speaker="UNK", text="Synthetic one", temporary_speaker_id="speaker-1", source_speaker_label="speaker-1"),
        ],
        review_status=ReviewStatus.needs_review,
    )
    return repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="transcript.create",
        audit_message="Synthetic SQL transcript created.",
    )


def save_complete_mapping(repo: SqlAlchemyRepository, transcript: Transcript):
    return save_mapping_draft(repo, transcript.transcript_id, SpeakerMappingDraftUpdate(
        expected_transcript_version=transcript.version,
        entries=[
            {"temporary_speaker_id": "speaker-0", "confirmed_chat_code": "CHI", "participant_role": "target_child", "reviewed_utterance_ids": ["utt-0"]},
            {"temporary_speaker_id": "speaker-1", "confirmed_chat_code": "THER", "participant_role": "therapist", "reviewed_utterance_ids": ["utt-1"]},
        ],
    ))


def confirm_complete_mapping(repo: SqlAlchemyRepository, transcript: Transcript, draft):
    return confirm_mapping(repo, transcript.transcript_id, SpeakerMappingConfirmRequest(
        expected_transcript_version=transcript.version,
        expected_mapping_version=draft.mapping_version,
    ), actor_id="therapist-demo", actor_role="therapist")
```

Then add the transaction tests:

```python
def test_sql_confirmation_is_atomic_and_survives_reload(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    confirmed = confirm_complete_mapping(sql_repo, transcript, draft)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    persisted = reopened.get_latest_speaker_mapping(transcript.transcript_id)

    assert persisted is not None
    assert persisted.status == MappingPersistedStatus.confirmed
    assert persisted.applied_transcript_version == transcript.version + 1
    assert reopened.transcripts[transcript.transcript_id].version == transcript.version + 1


def test_sql_confirmation_conflict_rolls_back_transcript_mapping_and_audit(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    before_audits = len(sql_repo.audit_log)

    with pytest.raises(SpeakerMappingVersionConflictError):
        sql_repo.confirm_speaker_mapping(
            draft.model_copy(update={"status": MappingPersistedStatus.confirmed}),
            build_confirmed_transcript(transcript, draft),
            expected_transcript_version=transcript.version,
            expected_mapping_version=draft.mapping_version - 1,
            actor_id="therapist-demo",
        )

    assert sql_repo.transcripts[transcript.transcript_id].version == transcript.version
    assert sql_repo.get_latest_speaker_mapping(transcript.transcript_id).status == MappingPersistedStatus.draft
    assert len(sql_repo.audit_log) == before_audits
```

Use synthetic utterances and reuse the Task 1 factory logic locally in this file so the SQL test has no dependency on another test module.

- [ ] **Step 2: Run the migration and SQL tests to verify failure**

Run: `pytest tests/test_api_migration_smoke.py -q && cd apps/api && pytest tests/test_sql_speaker_mapping_transactions.py -q`

Expected: migration smoke fails on revision/table expectations, and SQL tests fail because `SpeakerMappingRecord` is absent.

- [ ] **Step 3: Create the additive Alembic migration**

Create `0014_add_speaker_mappings.py` with revision `0014_speaker_mappings`, down revision `0013_session_cues_acknowledgement`, and this table:

```python
def upgrade() -> None:
    op.create_table(
        "speaker_mappings",
        sa.Column("mapping_id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("transcript_id", sa.String(length=64), sa.ForeignKey("transcripts.transcript_id"), nullable=False),
        sa.Column("source_transcript_version", sa.Integer(), nullable=False),
        sa.Column("applied_transcript_version", sa.Integer(), nullable=True),
        sa.Column("mapping_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("entries", sa.JSON(), nullable=False),
        sa.Column("confirmed_by_user_id", sa.String(length=128), nullable=True),
        sa.Column("confirmed_by_role", sa.String(length=64), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("transcript_id", "mapping_version", name="uq_speaker_mapping_transcript_version"),
    )
    op.create_index("ix_speaker_mappings_organization_id", "speaker_mappings", ["organization_id"])
    op.create_index("ix_speaker_mappings_transcript_id", "speaker_mappings", ["transcript_id"])


def downgrade() -> None:
    op.drop_index("ix_speaker_mappings_transcript_id", table_name="speaker_mappings")
    op.drop_index("ix_speaker_mappings_organization_id", table_name="speaker_mappings")
    op.drop_table("speaker_mappings")
```

- [ ] **Step 4: Add the SQLAlchemy record and converters**

Add this model after `TranscriptRecord` in `models.py`:

```python
class SpeakerMappingRecord(Base):
    __tablename__ = "speaker_mappings"
    __table_args__ = (
        UniqueConstraint("transcript_id", "mapping_version", name="uq_speaker_mapping_transcript_version"),
    )

    mapping_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.transcript_id"), nullable=False, index=True)
    source_transcript_version: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_transcript_version: Mapped[int | None] = mapped_column(Integer)
    mapping_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    entries: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    confirmed_by_user_id: Mapped[str | None] = mapped_column(String(128))
    confirmed_by_role: Mapped[str | None] = mapped_column(String(64))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
```

Import `SpeakerMappingRecord`, `SpeakerMapping`, `SpeakerMappingEntry`, and `MappingPersistedStatus` in `sqlalchemy_repository.py`, then add:

```python
    @staticmethod
    def _speaker_mapping_to_record(mapping: SpeakerMapping) -> SpeakerMappingRecord:
        return SpeakerMappingRecord(
            mapping_id=mapping.mapping_id,
            organization_id=mapping.organization_id,
            transcript_id=mapping.transcript_id,
            source_transcript_version=mapping.source_transcript_version,
            applied_transcript_version=mapping.applied_transcript_version,
            mapping_version=mapping.mapping_version,
            status=mapping.status.value,
            entries=[entry.model_dump(mode="json") for entry in mapping.entries],
            confirmed_by_user_id=mapping.confirmed_by_user_id,
            confirmed_by_role=mapping.confirmed_by_role,
            confirmed_at=mapping.confirmed_at,
            created_at=mapping.created_at,
            updated_at=mapping.updated_at,
        )

    @staticmethod
    def _speaker_mapping_from_record(row: SpeakerMappingRecord) -> SpeakerMapping:
        return SpeakerMapping(
            mapping_id=row.mapping_id,
            organization_id=row.organization_id,
            transcript_id=row.transcript_id,
            source_transcript_version=row.source_transcript_version,
            applied_transcript_version=row.applied_transcript_version,
            mapping_version=row.mapping_version,
            status=MappingPersistedStatus(row.status),
            entries=[SpeakerMappingEntry.model_validate(entry) for entry in row.entries],
            confirmed_by_user_id=row.confirmed_by_user_id,
            confirmed_by_role=row.confirmed_by_role,
            confirmed_at=row.confirmed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
```

In `load()`, add:

```python
self.speaker_mappings = {
    row.mapping_id: self._speaker_mapping_from_record(row)
    for row in db.query(SpeakerMappingRecord).all()
}
```

- [ ] **Step 5: Implement SQL draft save and atomic confirmation**

Add these repository methods; each writes one database transaction and updates in-memory mirrors only after commit:

```python
    def save_speaker_mapping_draft(
        self,
        mapping: SpeakerMapping,
        *,
        expected_mapping_version: int | None,
        actor_id: str,
    ) -> SpeakerMapping:
        with self.SessionLocal() as db:
            latest_row = (
                db.query(SpeakerMappingRecord)
                .filter(SpeakerMappingRecord.transcript_id == mapping.transcript_id)
                .order_by(SpeakerMappingRecord.mapping_version.desc())
                .first()
            )
            current_draft = latest_row if (
                latest_row is not None
                and latest_row.status == MappingPersistedStatus.draft.value
                and latest_row.source_transcript_version == mapping.source_transcript_version
            ) else None
            if current_draft is None and expected_mapping_version is not None:
                raise SpeakerMappingVersionConflictError("Speaker mapping draft version changed; reload and retry.")
            if current_draft is not None and current_draft.mapping_version != expected_mapping_version:
                raise SpeakerMappingVersionConflictError("Speaker mapping draft version changed; reload and retry.")
            mapping.mapping_id = current_draft.mapping_id if current_draft else mapping.mapping_id
            mapping.mapping_version = (latest_row.mapping_version + 1) if latest_row else 1
            mapping.created_at = current_draft.created_at if current_draft else mapping.created_at
            mapping.updated_at = utc_now()
            row = current_draft or self._speaker_mapping_to_record(mapping)
            row.organization_id = mapping.organization_id
            row.source_transcript_version = mapping.source_transcript_version
            row.applied_transcript_version = None
            row.mapping_version = mapping.mapping_version
            row.status = MappingPersistedStatus.draft.value
            row.entries = [entry.model_dump(mode="json") for entry in mapping.entries]
            row.confirmed_by_user_id = None
            row.confirmed_by_role = None
            row.confirmed_at = None
            row.updated_at = mapping.updated_at
            audit = validate_audit_event(
                actor_id=actor_id,
                action="speaker_mapping.draft_save",
                target_id=mapping.mapping_id,
                outcome="success",
                correlation_id=f"speaker-mapping-draft-{mapping.mapping_id}-v{mapping.mapping_version}",
                message="Speaker mapping draft saved.",
            )
            db.add(row)
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            saved = self._speaker_mapping_from_record(row)
        self.speaker_mappings[saved.mapping_id] = saved
        self.audit_log.append(audit.as_dict())
        return self.clone(saved)

    def confirm_speaker_mapping(
        self,
        mapping: SpeakerMapping,
        transcript: Transcript,
        *,
        expected_transcript_version: int,
        expected_mapping_version: int,
        actor_id: str,
    ) -> SpeakerMapping:
        audit = validate_audit_event(
            actor_id=actor_id,
            action="speaker_mapping.confirm",
            target_id=mapping.mapping_id,
            outcome="success",
            correlation_id=f"speaker-mapping-confirm-{mapping.mapping_id}-v{mapping.mapping_version}",
            message=f"Speaker mapping confirmed for transcript version {transcript.version}.",
        )
        with self.SessionLocal() as db:
            transcript_row = db.get(TranscriptRecord, transcript.transcript_id)
            mapping_row = db.get(SpeakerMappingRecord, mapping.mapping_id)
            if transcript_row is None or mapping_row is None:
                raise KeyError(mapping.mapping_id)
            if transcript_row.version != expected_transcript_version:
                raise TranscriptVersionConflictError("Transcript version changed; reload and retry.")
            if mapping_row.mapping_version != expected_mapping_version or mapping_row.status != MappingPersistedStatus.draft.value:
                raise SpeakerMappingVersionConflictError("Speaker mapping version changed; reload and retry.")
            session_row = db.get(SessionRecord, transcript.session_id)
            if session_row is None:
                raise KeyError(transcript.session_id)
            transcript_row.raw_text = transcript.raw_text
            transcript_row.utterances = [item.model_dump(mode="json") for item in transcript.utterances]
            transcript_row.qa_status = transcript.qa_status.value
            transcript_row.qa_issues = []
            transcript_row.review_status = transcript.review_status.value
            transcript_row.therapist_attested = False
            transcript_row.attestation_reason = ""
            transcript_row.version = transcript.version
            transcript_row.updated_at = transcript.updated_at
            self._mark_downstream_rows_stale(db, session_row)
            session_row.status = ReviewStatus.needs_review.value
            session_row.updated_at = utc_now()
            mapping_row.mapping_version = expected_mapping_version + 1
            mapping_row.status = MappingPersistedStatus.confirmed.value
            mapping_row.entries = [entry.model_dump(mode="json") for entry in mapping.entries]
            mapping_row.applied_transcript_version = transcript.version
            mapping_row.confirmed_by_user_id = mapping.confirmed_by_user_id
            mapping_row.confirmed_by_role = mapping.confirmed_by_role
            mapping_row.confirmed_at = mapping.confirmed_at
            mapping_row.updated_at = mapping.updated_at
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(transcript_row)
            db.refresh(mapping_row)
            db.refresh(session_row)
            saved_transcript = self._transcript_from_record(transcript_row)
            saved_mapping = self._speaker_mapping_from_record(mapping_row)
            saved_session = self._session_from_record(session_row)
        self.transcripts[saved_transcript.transcript_id] = saved_transcript
        self.speaker_mappings[saved_mapping.mapping_id] = saved_mapping
        self.sessions[saved_session.session_id] = saved_session
        self._mark_downstream_outputs_stale(saved_session)
        self.audit_log.append(audit.as_dict())
        return self.clone(saved_mapping)
```

- [ ] **Step 6: Advance migration smoke expectations**

In `scripts/check_api_migrations.py`, set:

```python
HEAD_REVISION = "0014_speaker_mappings"
```

Insert `"speaker_mappings",` into the existing `REQUIRED_TABLES` set and insert this key/value inside the existing `REQUIRED_COLUMNS` dictionary:

```python
    "speaker_mappings": {
    "mapping_id",
    "organization_id",
    "transcript_id",
    "source_transcript_version",
    "applied_transcript_version",
    "mapping_version",
    "status",
    "entries",
    "confirmed_by_user_id",
    "confirmed_by_role",
    "confirmed_at",
    "created_at",
    "updated_at",
    },
```

- [ ] **Step 7: Run migration and SQL verification**

Run: `pytest tests/test_api_migration_smoke.py -q`

Expected: `1 passed`.

Run: `cd apps/api && pytest tests/test_sql_speaker_mapping_transactions.py tests/test_sql_repository_transactions.py -q`

Expected: all selected tests pass with no partial mutations.

- [ ] **Step 8: Commit SQL persistence**

```bash
git add apps/api/app/db/migrations/versions/0014_add_speaker_mappings.py apps/api/app/db/models.py apps/api/app/repositories/sqlalchemy_repository.py apps/api/tests/test_sql_speaker_mapping_transactions.py scripts/check_api_migrations.py tests/test_api_migration_smoke.py
git commit -m "feat: persist speaker mappings in SQL" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 6: Expose tenant-safe mapping endpoints and stable errors

**Files:**
- Modify: `apps/api/app/api/v1/routes/transcripts.py`
- Modify: `apps/api/tests/test_speaker_mapping.py`
- Modify: `apps/api/tests/test_organization_admin_routes.py`

- [ ] **Step 1: Write failing endpoint, auth, consent, and compatibility tests**

Add these helpers to `test_speaker_mapping.py` for route tests:

```python
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app


THERAPIST_HEADERS = {
    "x-mock-user-id": "therapist-demo",
    "x-mock-role": "therapist",
    "x-organization-id": "pilot_org_001",
}


def route_client(repo: MockRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def seed_api_temporary_asr_transcript(repo: MockRepository) -> str:
    return make_asr_transcript(repo).transcript_id


def save_api_mapping_draft(client: TestClient, transcript_id: str) -> dict:
    current = client.get(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        headers=THERAPIST_HEADERS,
    ).json()
    return client.put(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        headers=THERAPIST_HEADERS,
        json={
            "expected_transcript_version": current["source_transcript_version"],
            "entries": [
                {"temporary_speaker_id": "speaker-0", "confirmed_chat_code": "CHI", "participant_role": "target_child", "reviewed_utterance_ids": ["utt-0"]},
                {"temporary_speaker_id": "speaker-1", "confirmed_chat_code": "THER", "participant_role": "therapist", "reviewed_utterance_ids": ["utt-1"]},
            ],
        },
    ).json()
```

Use those helpers to cover:

```python
def test_mapping_get_is_read_only_and_save_ignores_provider_metadata() -> None:
    repo = MockRepository()
    client = route_client(repo)
    transcript_id = seed_api_temporary_asr_transcript(repo)
    before = len(repo.speaker_mappings)

    response = client.get(f"/api/v1/transcripts/{transcript_id}/speaker-mapping", headers=THERAPIST_HEADERS)

    assert response.status_code == 200
    assert response.json()["persisted"] is False
    assert len(repo.speaker_mappings) == before
    app.dependency_overrides.clear()


def test_mapping_confirm_requires_therapist_and_returns_stable_conflict() -> None:
    repo = MockRepository()
    client = route_client(repo)
    transcript_id = seed_api_temporary_asr_transcript(repo)
    draft = save_api_mapping_draft(client, transcript_id)
    denied = client.post(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping/confirm",
        headers={**THERAPIST_HEADERS, "x-mock-user-id": "supervisor-demo", "x-mock-role": "clinical_supervisor"},
        json={"expected_transcript_version": draft["source_transcript_version"], "expected_mapping_version": draft["mapping_version"]},
    )
    assert denied.status_code == 403

    conflict = client.post(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping/confirm",
        headers=THERAPIST_HEADERS,
        json={"expected_transcript_version": draft["source_transcript_version"], "expected_mapping_version": 0},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "SPEAKER_MAPPING_VERSION_CONFLICT"
    app.dependency_overrides.clear()
```

Append these boundary and compatibility tests:

```python
def test_mapping_routes_preserve_tenant_and_consent_boundaries() -> None:
    repo = MockRepository()
    client = route_client(repo)
    transcript = make_asr_transcript(repo)
    foreign = client.get(
        f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping",
        headers={**THERAPIST_HEADERS, "x-organization-id": "other-org"},
    )
    assert foreign.status_code == 404
    repo.cases[transcript.case_id].consent_status = "withdrawn"
    withdrawn = client.get(
        f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping",
        headers=THERAPIST_HEADERS,
    )
    assert withdrawn.status_code == 400
    app.dependency_overrides.clear()


def test_confirmation_identity_is_always_authenticated_user() -> None:
    repo = MockRepository()
    client = route_client(repo)
    transcript_id = seed_api_temporary_asr_transcript(repo)
    draft = save_api_mapping_draft(client, transcript_id)
    response = client.post(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping/confirm",
        headers=THERAPIST_HEADERS,
        json={
            "expected_transcript_version": draft["source_transcript_version"],
            "expected_mapping_version": draft["mapping_version"],
            "confirmed_by_user_id": "forged-user",
        },
    )
    assert response.status_code == 200
    assert response.json()["confirmed_by_user_id"] == "therapist-demo"
    app.dependency_overrides.clear()


@pytest.mark.parametrize("source", ["manual", "cha_upload", "mock_asr_draft:mock", "asr_draft:canonical"])
def test_unaffected_transcripts_bypass_mapping_gate(source: str) -> None:
    repo = MockRepository()
    transcript = make_asr_transcript(repo, source=source, temporary_speaker_ids=(None, None))
    qa = transcript_service.run_qa(repo, transcript.transcript_id)
    assert qa.transcript_id == transcript.transcript_id
    transcript_service.attest(
        repo,
        transcript.transcript_id,
        AttestationRequest(reason="Synthetic compatibility review.", override_qa_failure=True),
        actor_id="therapist-demo",
        attested_by="Demo Therapist",
    )


def test_required_action_routes_return_stable_mapping_code() -> None:
    repo = MockRepository()
    client = route_client(repo)
    transcript_id = seed_api_temporary_asr_transcript(repo)
    for method, path, payload in (
        ("post", f"/api/v1/transcripts/{transcript_id}/qa", None),
        ("post", f"/api/v1/transcripts/{transcript_id}/attest", {"reason": "Synthetic review."}),
        ("get", f"/api/v1/transcripts/{transcript_id}/export-cha", None),
        ("post", f"/api/v1/transcripts/{transcript_id}/extract-features", {}),
    ):
        response = client.request(method.upper(), path, headers=THERAPIST_HEADERS, json=payload)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "SPEAKER_MAPPING_REQUIRED"
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run endpoint tests and verify failure**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py tests/test_organization_admin_routes.py -q`

Expected: new route tests return `404` until endpoints are registered.

- [ ] **Step 3: Add a route error translator**

In `transcripts.py`, add:

```python
from fastapi import HTTPException, status
from app.repositories.base import SpeakerMappingVersionConflictError, TranscriptVersionConflictError
from app.schemas.speaker_mapping import SpeakerMappingConfirmRequest, SpeakerMappingDraftUpdate, SpeakerMappingResponse
from app.services.speaker_mapping_service import SpeakerMappingError
from app.services import speaker_mapping_service


def speaker_mapping_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SpeakerMappingError):
        status_code = status.HTTP_409_CONFLICT if exc.code in {
            "SPEAKER_MAPPING_VERSION_CONFLICT",
            "SPEAKER_MAPPING_STALE",
        } else status.HTTP_400_BAD_REQUEST
        return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, (SpeakerMappingVersionConflictError, TranscriptVersionConflictError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SPEAKER_MAPPING_VERSION_CONFLICT", "message": "Transcript or mapping changed; reload and retry."},
        )
    return bad_request(str(exc))
```

- [ ] **Step 4: Add the three routes with existing boundaries**

```python
@router.get("/transcripts/{transcript_id}/speaker-mapping", response_model=SpeakerMappingResponse)
def get_speaker_mapping(transcript_id: str, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    require_transcript(repo, transcript_id, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return speaker_mapping_service.get_mapping(repo, transcript_id)
    except (ValueError, SpeakerMappingVersionConflictError, TranscriptVersionConflictError) as exc:
        raise speaker_mapping_http_error(exc) from exc


@router.put("/transcripts/{transcript_id}/speaker-mapping", response_model=SpeakerMappingResponse)
def put_speaker_mapping(transcript_id: str, payload: SpeakerMappingDraftUpdate, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return speaker_mapping_service.save_mapping_draft(repo, transcript_id, payload, actor_id=user.user_id)
    except (ValueError, SpeakerMappingVersionConflictError, TranscriptVersionConflictError) as exc:
        raise speaker_mapping_http_error(exc) from exc


@router.post("/transcripts/{transcript_id}/speaker-mapping/confirm", response_model=SpeakerMappingResponse)
def confirm_speaker_mapping(transcript_id: str, payload: SpeakerMappingConfirmRequest, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    require_transcript(repo, transcript_id, user)
    require_therapist(user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return speaker_mapping_service.confirm_mapping(
            repo,
            transcript_id,
            payload,
            actor_id=user.user_id,
            actor_role=user.role,
        )
    except (ValueError, SpeakerMappingVersionConflictError, TranscriptVersionConflictError) as exc:
        raise speaker_mapping_http_error(exc) from exc
```

- [ ] **Step 5: Preserve stable mapping errors from existing action routes**

Add `except SpeakerMappingError as exc: raise speaker_mapping_http_error(exc) from exc` before generic `ValueError` handlers in QA, attestation, export, and feature extraction routes. Keep the generic handlers for all unrelated legacy errors.

- [ ] **Step 6: Run API tests and commit**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py tests/test_organization_admin_routes.py tests/test_workflow.py -q`

Expected: all selected tests pass, including compatibility cases.

```bash
git add apps/api/app/api/v1/routes/transcripts.py apps/api/app/api/v1/routes/features.py apps/api/tests/test_speaker_mapping.py apps/api/tests/test_organization_admin_routes.py
git commit -m "feat: expose speaker mapping API" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 7: Add conditional web client loading and mapping mutations

**Files:**
- Modify: `apps/lingualens-app/src/lib/workflow/types.ts`
- Modify: `apps/lingualens-app/src/lib/workflow.ts`
- Modify: `apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts`
- Create: `apps/lingualens-app/src/__tests__/speaker-mapping-service.test.ts`

- [ ] **Step 1: Write failing client tests**

Create `speaker-mapping-service.test.ts` using `vi.stubGlobal("fetch", ...)` and synthetic responses:

```typescript
import { afterEach, expect, test, vi } from "vitest";
import { sessionWorkflowService } from "@/features/sessions/services/session-workflow-service";

afterEach(() => vi.unstubAllGlobals());

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function buildLoadFetch(input: { source: string; temporarySpeakerId?: string }) {
  return vi.fn(async (request: RequestInfo | URL) => {
    const url = String(request);
    if (url.includes("/sessions/session-1") && !url.includes("/reports")) {
      return json({ session_id: "session-1", transcript_id: "tr-1" });
    }
    if (url.endsWith("/transcripts/tr-1")) {
      return json({
        transcript_id: "tr-1",
        session_id: "session-1",
        source: input.source,
        version: 1,
        utterances: [{
          utterance_id: "utt-1",
          speaker: "UNK",
          text: "Synthetic",
          temporary_speaker_id: input.temporarySpeakerId,
        }],
      });
    }
    throw new Error(`Unexpected request: ${url}`);
  });
}

test("loads speaker mapping only for transcripts with temporary speaker ids", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/sessions/session-1")) return json({ session_id: "session-1", transcript_id: "tr-1" });
    if (url.endsWith("/transcripts/tr-1")) return json({
      transcript_id: "tr-1",
      session_id: "session-1",
      source: "asr_draft:manual",
      version: 1,
      utterances: [{ utterance_id: "utt-1", speaker: "UNK", text: "Synthetic", temporary_speaker_id: "speaker-0" }],
    });
    if (url.endsWith("/transcripts/tr-1/speaker-mapping")) return json({ required: true, effective_status: "draft", entries: [] });
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  const loaded = await sessionWorkflowService.load({ sessionId: "session-1" });

  expect(loaded.speakerMapping?.required).toBe(true);
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/speaker-mapping"))).toBe(true);
});

test.each([
  ["manual", undefined],
  ["mock_asr_draft:mock", "speaker-0"],
  ["asr_draft:manual", undefined],
])("does not request mapping for unaffected source %s", async (source, temporarySpeakerId) => {
  const fetchMock = buildLoadFetch({ source, temporarySpeakerId });
  vi.stubGlobal("fetch", fetchMock);
  await sessionWorkflowService.load({ sessionId: "session-1" });
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/speaker-mapping"))).toBe(false);
});
```

- [ ] **Step 2: Verify conditional-loading tests fail**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/speaker-mapping-service.test.ts`

Expected: FAIL because frontend mapping types and service loading are absent.

- [ ] **Step 3: Add frontend mapping contracts and transcript provenance**

In both exported type surfaces used by this app, add:

```typescript
export type SpeakerMappingEntry = {
  temporary_speaker_id: string;
  confirmed_chat_code?: "CHI" | "THER" | "OTH" | null;
  participant_role?: "target_child" | "therapist" | "other" | null;
  source_speaker_label?: string | null;
  provider_metadata: Record<string, string>;
  affected_utterance_ids: string[];
  reviewed_utterance_ids: string[];
};

export type SpeakerMapping = {
  mapping_id: string;
  transcript_id: string;
  source_transcript_version: number;
  applied_transcript_version?: number | null;
  mapping_version: number;
  status: "draft" | "confirmed";
  required: boolean;
  persisted: boolean;
  effective_status: "not_required" | "draft" | "confirmed" | "stale";
  issue_code?: string | null;
  issue_message?: string | null;
  entries: SpeakerMappingEntry[];
};
```

Add `temporary_speaker_id?: string | null` and `source_speaker_label?: string | null` to `BackendTranscript.utterances`, and preserve them as `temporarySpeakerId` and `sourceSpeakerLabel` in `TranscriptLine`/`backendTranscriptLines`.

- [ ] **Step 4: Add request helpers and exact activation check**

```typescript
export function backendTranscriptRequiresSpeakerMapping(transcript: BackendTranscript): boolean {
  return Boolean(
    transcript.source?.startsWith("asr_draft:")
      && transcript.utterances?.some((item) => Boolean(item.temporary_speaker_id?.trim())),
  );
}

export async function getSpeakerMapping(transcriptId: string): Promise<SpeakerMapping> {
  return apiRequest<SpeakerMapping>(`/transcripts/${transcriptId}/speaker-mapping`);
}

export async function saveSpeakerMappingDraft(transcriptId: string, payload: {
  expected_transcript_version: number;
  expected_mapping_version?: number;
  entries: Array<Pick<SpeakerMappingEntry, "temporary_speaker_id" | "confirmed_chat_code" | "participant_role" | "reviewed_utterance_ids">>;
}): Promise<SpeakerMapping> {
  return apiRequest<SpeakerMapping>(`/transcripts/${transcriptId}/speaker-mapping`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function confirmSpeakerMapping(transcriptId: string, payload: {
  expected_transcript_version: number;
  expected_mapping_version: number;
}): Promise<SpeakerMapping> {
  return apiRequest<SpeakerMapping>(`/transcripts/${transcriptId}/speaker-mapping/confirm`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 5: Load only when the transcript activates mapping**

Change `sessionWorkflowService.load` to load session/transcript/report first, then execute:

```typescript
    const speakerMapping = transcript && backendTranscriptRequiresSpeakerMapping(transcript)
      ? await getSpeakerMapping(transcript.transcript_id)
      : undefined;
    return { session, transcript, report, speakerMapping };
```

Expose `saveSpeakerMappingDraft` and `confirmSpeakerMapping` as service methods that call the helpers with exact transcript/mapping versions.

- [ ] **Step 6: Run client tests and typecheck, then commit**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/speaker-mapping-service.test.ts && npm run typecheck`

Expected: tests and TypeScript check pass.

```bash
git add apps/lingualens-app/src/lib/workflow/types.ts apps/lingualens-app/src/lib/workflow.ts apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts apps/lingualens-app/src/__tests__/speaker-mapping-service.test.ts
git commit -m "feat: add conditional speaker mapping client" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 8: Build the accessible speaker-mapping panel

**Files:**
- Create: `apps/lingualens-app/src/features/sessions/transcript/speaker-mapping-panel.tsx`
- Create: `apps/lingualens-app/src/__tests__/speaker-mapping-panel.test.tsx`

- [ ] **Step 1: Write failing panel interaction tests**

Render a two-speaker draft and assert no defaults, per-utterance review, save-before-confirm, stale handling, and accessible names:

```typescript
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { SpeakerMappingPanel } from "@/features/sessions/transcript/speaker-mapping-panel";

function syntheticLines() {
  return [
    { lineId: "utt-0", speaker: "UNK", text: "Synthetic zero", temporarySpeakerId: "speaker-0" },
    { lineId: "utt-1", speaker: "UNK", text: "Synthetic one", temporarySpeakerId: "speaker-1" },
  ];
}

function mappingDraft() {
  return {
    mapping_id: "spmap-1",
    transcript_id: "tr-1",
    source_transcript_version: 1,
    applied_transcript_version: null,
    mapping_version: 1,
    status: "draft" as const,
    required: true,
    persisted: false,
    effective_status: "draft" as const,
    entries: [
      { temporary_speaker_id: "speaker-0", source_speaker_label: "speaker-0", provider_metadata: { provider_id: "manual" }, affected_utterance_ids: ["utt-0"], reviewed_utterance_ids: [], confirmed_chat_code: null, participant_role: null },
      { temporary_speaker_id: "speaker-1", source_speaker_label: "speaker-1", provider_metadata: { provider_id: "manual" }, affected_utterance_ids: ["utt-1"], reviewed_utterance_ids: [], confirmed_chat_code: null, participant_role: null },
    ],
  };
}

test("requires explicit role, code, and every utterance review before save", () => {
  const onChange = vi.fn();
  render(<SpeakerMappingPanel mapping={mappingDraft()} lines={syntheticLines()} dirty={true} busy={false} onChange={onChange} onSave={vi.fn()} onConfirm={vi.fn()} />);

  expect(screen.getByLabelText("CHAT code for speaker-0")).toHaveValue("");
  expect(screen.getByLabelText("Participant role for speaker-0")).toHaveValue("");
  expect(screen.getByRole("button", { name: "Save speaker mapping draft" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();

  fireEvent.change(screen.getByLabelText("CHAT code for speaker-0"), { target: { value: "CHI" } });
  fireEvent.change(screen.getByLabelText("Participant role for speaker-0"), { target: { value: "target_child" } });
  fireEvent.click(screen.getByLabelText("Reviewed utterance utt-0 for speaker-0"));
  expect(onChange).toHaveBeenCalled();
});

test("disables confirmation and announces reload for stale mapping", () => {
  render(<SpeakerMappingPanel mapping={{ ...mappingDraft(), effective_status: "stale", issue_message: "Transcript changed; reload." }} lines={syntheticLines()} dirty={false} busy={false} onChange={vi.fn()} onSave={vi.fn()} onConfirm={vi.fn()} />);
  expect(screen.getByRole("alert")).toHaveTextContent("Transcript changed; reload.");
  expect(screen.getByRole("button", { name: "Confirm speaker mapping" })).toBeDisabled();
});
```

- [ ] **Step 2: Verify the component test fails**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/speaker-mapping-panel.test.tsx`

Expected: FAIL because `SpeakerMappingPanel` does not exist.

- [ ] **Step 3: Implement the panel with explicit selections and 44px controls**

Create a controlled component that:

- renders one `<fieldset>` per entry with `<legend>` equal to provider label or temporary ID;
- renders `select` controls whose first option is `Choose a code`/`Choose a role` with value `""`;
- renders every `affected_utterance_id` as a checkbox labelled `Reviewed utterance {id} for {temporary_id}`;
- receives the current `TranscriptLine[]`, resolves each affected ID to its visible utterance text and timestamp, and displays it beside the review checkbox without copying transcript text into error messages or logs;
- derives completeness with exact set equality, exactly one `CHI`/`target_child`, unique non-null codes, and no more than three entries;
- receives a parent-owned `dirty` boolean, enables Save only when locally complete and `dirty`, and enables Confirm only when complete, persisted, `dirty === false`, and effective status is `draft`;
- uses `min-h-11`, `focus-visible:outline`, and `focus-visible:ring-2` on interactive controls;
- renders stale/conflict issues in `role="alert"` and never renders transcript text from an error payload.

Use this exact completeness helper in the component:

```typescript
export function isSpeakerMappingComplete(mapping: SpeakerMapping): boolean {
  if (mapping.entries.length === 0 || mapping.entries.length > 3) return false;
  const codes = mapping.entries.map((entry) => entry.confirmed_chat_code).filter(Boolean);
  if (codes.length !== mapping.entries.length || new Set(codes).size !== codes.length) return false;
  if (mapping.entries.filter((entry) => entry.confirmed_chat_code === "CHI" && entry.participant_role === "target_child").length !== 1) return false;
  return mapping.entries.every((entry) => (
    Boolean(entry.participant_role)
      && entry.affected_utterance_ids.length === entry.reviewed_utterance_ids.length
      && entry.affected_utterance_ids.every((id) => entry.reviewed_utterance_ids.includes(id))
  ));
}
```

- [ ] **Step 4: Run component tests and lint**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/speaker-mapping-panel.test.tsx && npm run lint`

Expected: tests and lint pass.

- [ ] **Step 5: Commit the panel**

```bash
git add apps/lingualens-app/src/features/sessions/transcript/speaker-mapping-panel.tsx apps/lingualens-app/src/__tests__/speaker-mapping-panel.test.tsx
git commit -m "feat: add accessible speaker mapping panel" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 9: Integrate mapping into the Session Transcript workspace

**Files:**
- Modify: `apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx`
- Modify: `apps/lingualens-app/src/components/transcript-editor-panel.tsx`
- Modify: `apps/lingualens-app/src/components/transcript-review-controls.tsx`
- Modify: `apps/lingualens-app/src/__tests__/session-workspace-page.test.tsx`
- Modify: `apps/lingualens-app/e2e/therapist-workflow.smoke.spec.ts`

- [ ] **Step 1: Write failing integrated workspace tests**

Add this route fixture above the workspace tests:

```typescript
function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function installWorkflowResponses(mappingRequired: boolean) {
  let mappingPersisted = false;
  let mappingConfirmed = false;
  const entries = [
    { temporary_speaker_id: "speaker-0", source_speaker_label: "speaker-0", provider_metadata: { provider_id: "manual" }, affected_utterance_ids: ["utt-0"], reviewed_utterance_ids: [], confirmed_chat_code: null, participant_role: null },
    { temporary_speaker_id: "speaker-1", source_speaker_label: "speaker-1", provider_metadata: { provider_id: "manual" }, affected_utterance_ids: ["utt-1"], reviewed_utterance_ids: [], confirmed_chat_code: null, participant_role: null },
  ];
  const fetchMock = vi.fn(async (request: RequestInfo | URL, init?: RequestInit) => {
    const url = String(request);
    if (url.endsWith("/sessions/session-1")) return json({ session_id: "session-1", case_id: "case_demo_001", transcript_id: "tr-1" });
    if (url.endsWith("/cases/case_demo_001")) return json({ case_id: "case_demo_001", child_code: "C-DEMO", consent_status: "granted" });
    if (url.endsWith("/sessions/session-1/audio-files")) return json([]);
    if (url.includes("/ml-readiness")) return json({ ready: false, provider_id: "reference", reason_codes: [], reasons: [] });
    if (url.endsWith("/sessions/session-1/ml-review") || url.endsWith("/sessions/session-1/ai-review")) return new Response("Not found", { status: 404 });
    if (url.endsWith("/transcripts/tr-1/speaker-mapping/confirm") && init?.method === "POST") {
      mappingConfirmed = true;
      return json({ mapping_id: "spmap-1", transcript_id: "tr-1", source_transcript_version: 1, applied_transcript_version: 2, mapping_version: 3, status: "confirmed", required: true, persisted: true, effective_status: "confirmed", entries });
    }
    if (url.endsWith("/transcripts/tr-1/speaker-mapping") && init?.method === "PUT") {
      mappingPersisted = true;
      return json({ mapping_id: "spmap-1", transcript_id: "tr-1", source_transcript_version: 1, mapping_version: 2, status: "draft", required: true, persisted: true, effective_status: "draft", entries: JSON.parse(String(init.body)).entries.map((entry: object, index: number) => ({ ...entries[index], ...entry })) });
    }
    if (url.endsWith("/transcripts/tr-1/speaker-mapping")) {
      return json({ mapping_id: "spmap-1", transcript_id: "tr-1", source_transcript_version: 1, applied_transcript_version: mappingConfirmed ? 2 : null, mapping_version: mappingPersisted ? 2 : 1, status: mappingConfirmed ? "confirmed" : "draft", required: mappingRequired, persisted: mappingPersisted || mappingConfirmed, effective_status: mappingConfirmed ? "confirmed" : "draft", entries });
    }
    if (url.endsWith("/transcripts/tr-1")) {
      return json({ transcript_id: "tr-1", session_id: "session-1", case_id: "case_demo_001", source: mappingRequired ? "asr_draft:manual" : "manual", version: mappingConfirmed ? 2 : 1, raw_text: "", qa_status: "NOT_RUN", utterances: entries.map((entry, index) => ({ utterance_id: `utt-${index}`, speaker: mappingConfirmed ? (index === 0 ? "CHI" : "THER") : "UNK", text: `Synthetic ${index}`, temporary_speaker_id: mappingRequired ? entry.temporary_speaker_id : null })) });
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
```

Then add these tests:

```typescript
test("places required mapping before transcript QA and refreshes transcript after confirmation", async () => {
  installWorkflowResponses(true);
  render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);

  const mapping = await screen.findByRole("region", { name: "Speaker mapping review" });
  const runQa = await screen.findByRole("button", { name: /run qa/i });
  expect(mapping.compareDocumentPosition(runQa) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(runQa).toBeDisabled();

  fireEvent.change(screen.getByLabelText("CHAT code for speaker-0"), { target: { value: "CHI" } });
  fireEvent.change(screen.getByLabelText("Participant role for speaker-0"), { target: { value: "target_child" } });
  fireEvent.click(screen.getByLabelText("Reviewed utterance utt-0 for speaker-0"));
  fireEvent.change(screen.getByLabelText("CHAT code for speaker-1"), { target: { value: "THER" } });
  fireEvent.change(screen.getByLabelText("Participant role for speaker-1"), { target: { value: "therapist" } });
  fireEvent.click(screen.getByLabelText("Reviewed utterance utt-1 for speaker-1"));
  fireEvent.click(screen.getByRole("button", { name: "Save speaker mapping draft" }));
  fireEvent.click(await screen.findByRole("button", { name: "Confirm speaker mapping" }));
  expect(await screen.findByText("Speaker mapping confirmed")).toBeInTheDocument();
  expect(runQa).toBeEnabled();
});

test("does not mount a mapping request or panel for manual transcripts", async () => {
  const fetchMock = installWorkflowResponses(false);
  render(<SessionWorkflowWorkspace sessionId="session-1" view="transcript" />);
  await screen.findByText("Review Transcript");
  expect(screen.queryByRole("region", { name: "Speaker mapping review" })).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/speaker-mapping"))).toBe(false);
});
```

- [ ] **Step 2: Run the workspace test and verify failure**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/session-workspace-page.test.tsx`

Expected: the required mapping panel is absent and QA is not mapping-gated.

- [ ] **Step 3: Add mapping state and mutations to the model**

Add `speakerMapping`, `speakerMappingDirty`, and `speakerMappingBusy` state. Hydrate mapping from `loaded?.speakerMapping` with dirty false; set dirty true on every controlled entry edit and false only after a successful draft save or reload. Pass that boolean to the panel. Use these handlers for editing and draft save:

```typescript
function handleSpeakerMappingChange(next: SpeakerMapping) {
  setSpeakerMapping(next);
  setSpeakerMappingDirty(true);
}

async function handleSaveSpeakerMapping() {
  if (!state.backendTranscriptId || !speakerMapping) return;
  setSpeakerMappingBusy(true);
  try {
    const saved = await sessionWorkflowService.saveSpeakerMappingDraft(
      state.backendTranscriptId,
      {
        expected_transcript_version: speakerMapping.source_transcript_version,
        expected_mapping_version: speakerMapping.persisted ? speakerMapping.mapping_version : undefined,
        entries: speakerMapping.entries.map((entry) => ({
          temporary_speaker_id: entry.temporary_speaker_id,
          confirmed_chat_code: entry.confirmed_chat_code,
          participant_role: entry.participant_role,
          reviewed_utterance_ids: entry.reviewed_utterance_ids,
        })),
      },
    );
    setSpeakerMapping(saved);
    setSpeakerMappingDirty(false);
  } finally {
    setSpeakerMappingBusy(false);
  }
}
```

Confirmation must re-fetch the transcript because the backend increments its version and rewrites speakers:

```typescript
async function handleConfirmSpeakerMapping() {
  if (!state.backendTranscriptId || !speakerMapping?.persisted || speakerMapping.effective_status !== "draft") return;
  setSpeakerMappingBusy(true);
  try {
    await sessionWorkflowService.confirmSpeakerMapping(state.backendTranscriptId, {
      expected_transcript_version: speakerMapping.source_transcript_version,
      expected_mapping_version: speakerMapping.mapping_version,
    });
    const transcript = await getBackendTranscript(state.backendTranscriptId);
    const refreshedMapping = await getSpeakerMapping(state.backendTranscriptId);
    const lines = backendTranscriptLines(transcript);
    setEditorLines(lines);
    setSpeakerMapping(refreshedMapping);
    persist({
      ...state,
      backendTranscriptVersion: transcript.version,
      transcriptText: transcript.raw_text ?? "",
      transcriptLines: lines,
      qaStatus: "not_run",
      qaIssues: [],
      transcriptAttested: false,
      transcriptReviewStatus: "in_review",
      statusMessage: "Speaker mapping confirmed. Run transcript QA next.",
      error: undefined,
    });
  } catch (error) {
    const code = error instanceof ApiError ? error.detailCode : undefined;
    setSpeakerMapping((current) => current ? {
      ...current,
      effective_status: code === "SPEAKER_MAPPING_STALE" || code === "SPEAKER_MAPPING_VERSION_CONFLICT" ? "stale" : current.effective_status,
      issue_code: code,
      issue_message: "Transcript or mapping changed. Reload the current transcript before confirming.",
    } : current);
  } finally {
    setSpeakerMappingBusy(false);
  }
}
```

Reset `speakerMapping` to `undefined` whenever the workspace identity changes. In `pollBackendTranscriptionJob`, conditionally load it from the completed transcript with the same activation predicate:

```typescript
const completedMapping = backendTranscriptRequiresSpeakerMapping(transcript)
  ? await getSpeakerMapping(transcript.transcript_id)
  : undefined;
setSpeakerMapping(completedMapping);
```

Extend `ApiError` in `apps/lingualens-app/src/lib/api.ts` with a privacy-safe parsed code while retaining its current status/body compatibility:

```typescript
export class ApiError extends Error {
  status: number;
  body: string;
  detailCode?: string;

  constructor(status: number, body: string) {
    super(body || `API request failed: ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    try {
      const parsed = JSON.parse(body) as { detail?: { code?: unknown } };
      if (typeof parsed.detail?.code === "string") this.detailCode = parsed.detail.code;
    } catch {
      this.detailCode = undefined;
    }
  }
}
```

- [ ] **Step 4: Render before existing transcript controls and gate local actions**

Add mapping props to `SessionTranscriptViewProps`, render `<SpeakerMappingPanel>` immediately before `<TranscriptEditorPanel>`, and derive:

```typescript
const mappingReady = !speakerMapping?.required || speakerMapping.effective_status === "confirmed";
```

Add `reviewActionsDisabled?: boolean` to `TranscriptEditorPanelProps` and `TranscriptReviewControls` props. Pass it through and apply it only to the three mapped workflow buttons:

```typescript
disabled={busy || reviewActionsDisabled || !canAttest || attested}
```

```typescript
disabled={busy || reviewActionsDisabled || linesCount === 0}
```

```typescript
disabled={busy || reviewActionsDisabled || Boolean(qaBlockedReason)}
```

Call the editor as `<TranscriptEditorPanel reviewActionsDisabled={!mappingReady} ... />`, include `mappingReady` in both `canRetryAttestation` and `canExtractFeatures`, change the helper call to `getReviewReportBlockedReason(state, mappingReady)`, and make its first branch `if (!mappingReady) return "Confirm the speaker mapping before continuing transcript review.";`. Keep transcript edit/save controls enabled. The server gates remain authoritative.

- [ ] **Step 5: Add the browser E2E path**

Extend the existing smoke route fixture with a temporary-ASR transcript and mapping responses. In Playwright:

```typescript
await page.getByLabel("CHAT code for speaker-0").selectOption("CHI");
await page.getByLabel("Participant role for speaker-0").selectOption("target_child");
await page.getByLabel("Reviewed utterance utt-0 for speaker-0").check();
await page.getByLabel("CHAT code for speaker-1").selectOption("THER");
await page.getByLabel("Participant role for speaker-1").selectOption("therapist");
await page.getByLabel("Reviewed utterance utt-1 for speaker-1").check();
await page.getByRole("button", { name: "Save speaker mapping draft" }).click();
await page.getByRole("button", { name: "Confirm speaker mapping" }).click();
await expect(page.getByText("Speaker mapping confirmed")).toBeVisible();
await page.getByRole("button", { name: /run qa/i }).click();
await page.getByRole("button", { name: /attest transcript/i }).click();
```

- [ ] **Step 6: Run integrated web verification and commit**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/speaker-mapping-service.test.ts src/__tests__/speaker-mapping-panel.test.tsx src/__tests__/session-workspace-page.test.tsx && npm run typecheck && npm run build`

Expected: focused tests, typecheck, and production build pass.

Run: `cd apps/lingualens-app && npm run e2e:smoke`

Expected: smoke suite passes including mapping → QA → attestation.

```bash
git add apps/lingualens-app/src/lib/api.ts apps/lingualens-app/src/components/transcript-editor-panel.tsx apps/lingualens-app/src/components/transcript-review-controls.tsx apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx apps/lingualens-app/src/__tests__/session-workspace-page.test.tsx apps/lingualens-app/e2e/therapist-workflow.smoke.spec.ts
git commit -m "feat: integrate speaker mapping review" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

### Task 10: Prove compatibility, document the behavior, and prepare the pull request

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Verify without modifying: `packages/gui/`, `packages/tui/`

- [ ] **Step 1: Run the Desktop GUI and Terminal TUI regression gate before documentation**

Run: `pytest tests/test_gui.py tests/test_tui.py -q`

Expected: all tests pass or GUI-only tests skip solely because the runner has no display. Confirm with `git diff -- packages/gui packages/tui` that output is empty.

- [ ] **Step 2: Add current behavior to the source-of-truth docs**

Add these facts without changing the product version:

- `README.md`: real ASR drafts with temporary speaker IDs require explicit therapist mapping before QA/attestation; manual, CHAT import, and canonical-ASR flows remain unchanged.
- `CHANGELOG.md`: under the current unreleased section, record the separate versioned mapping record, fail-closed workflow gates, and web review panel.
- `docs/PROJECT_SOURCE_OF_TRUTH.md`: state the exact activation predicate (`asr_draft:` plus a non-empty `temporary_speaker_id`), persisted confirmation boundary, and that `packages/gui/`/`packages/tui/` do not activate this gate in their current canonical-speaker flows.

Use this safety sentence consistently: “Speaker mapping is a therapist-reviewed source-integrity step in a research and education prototype; it does not infer a diagnosis or clinical interpretation.”

- [ ] **Step 3: Run focused backend and frontend suites**

Run: `cd apps/api && pytest tests/test_speaker_mapping.py tests/test_sql_speaker_mapping_transactions.py tests/test_workflow.py tests/test_organization_admin_routes.py -q`

Expected: all selected backend tests pass.

Run: `cd apps/lingualens-app && npm test -- src/__tests__/speaker-mapping-service.test.ts src/__tests__/speaker-mapping-panel.test.tsx src/__tests__/session-workspace-page.test.tsx && npm run typecheck && npm run lint`

Expected: all selected frontend tests, typecheck, and lint pass.

- [ ] **Step 4: Run migration, UI, build, and full project gates**

Run: `pytest tests/test_api_migration_smoke.py -q`

Expected: migration reaches `0014_speaker_mappings` and includes `speaker_mappings`.

Run: `cd apps/lingualens-app && npm run build && npm run audit:ui`

Expected: production build and UI audit pass.

Run: `bash scripts/check_project.sh`

Expected: full project verification exits `0`.

- [ ] **Step 5: Inspect diff scope and privacy safety**

Run:

```bash
git diff --check
git diff -- packages/gui packages/tui
git diff --stat main...HEAD
rg -n "Synthetic sample|speaker-0|speaker-1" apps/api/app apps/lingualens-app/src --glob '!**/__tests__/**'
```

Expected: no whitespace errors; no GUI/TUI production diff; production code contains no synthetic transcript text or test-only IDs.

- [ ] **Step 6: Commit documentation**

```bash
git add README.md CHANGELOG.md docs/PROJECT_SOURCE_OF_TRUTH.md
git commit -m "docs: explain temporary speaker mapping gate" -m "Co-Authored-By: OpenAI Codex (GPT-5) <codex@openai.com>"
```

- [ ] **Step 7: Push and open the small salvage pull request**

```bash
git status --short
git log --oneline main..HEAD
git push -u origin codex/salvage-speaker-mapping
gh pr create --base main --head codex/salvage-speaker-mapping --title "feat: add therapist-confirmed speaker mapping" --body-file docs/superpowers/specs/2026-08-23-speaker-mapping-salvage-design.md
```

Expected: clean worktree before push, only the reviewed salvage commits above main, and a PR targeting `main`. Do not deploy, merge the donor branch, delete the donor worktree, or remove its recovery stash as part of this plan.

- [ ] **Step 8: Wait for all GitHub checks and report the result**

Run: `gh pr checks --watch`

Expected: every required check is green. If a check fails, reproduce that exact command locally, add a failing regression test when applicable, fix only the scoped issue, rerun the focused and full gates, and push the corrective commit with the required co-author trailer.
