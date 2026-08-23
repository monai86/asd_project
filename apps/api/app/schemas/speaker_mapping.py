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
    persisted_status: MappingPersistedStatus = MappingPersistedStatus.draft
    entries: list[SpeakerMappingEntry] = Field(default_factory=list)
    confirmed_by: str | None = None
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
    entries: list[SpeakerMappingEntryInput] = Field(default_factory=list)


class SpeakerMappingConfirmRequest(BaseModel):
    expected_transcript_version: int
    expected_mapping_version: int
