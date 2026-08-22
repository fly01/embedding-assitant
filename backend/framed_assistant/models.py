from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "0.1"


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VersionedModel(ApiModel):
    schema_version: Literal["0.1"] = SCHEMA_VERSION


class HostContext(ApiModel):
    actor_id: str
    scope_key: str
    denied_permissions: set[str] = Field(default_factory=set)


class ConversationMode(StrEnum):
    SINGLE = "single"
    MULTIPLE = "multiple"


class ContextProfile(StrEnum):
    LITE = "lite"
    BALANCED = "balanced"
    DURABLE = "durable"


class DisclosureLevel(StrEnum):
    HIDDEN = "hidden"
    STATUS = "status"
    CONTEXTUAL = "contextual"
    ACTIVITY = "activity"
    DEVELOPER = "developer"
    RAW_TRACE = "raw_trace"


class ExecutionMode(StrEnum):
    READ_ONLY = "read_only"
    CONFIRM_EACH = "confirm_each"
    AUTO_APPLY_ALLOWLIST = "auto_apply_allowlist"


class ContentPart(ApiModel):
    type: str
    order: int
    text: str | None = None
    attachment_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class Conversation(VersionedModel):
    id: str
    actor_id: str
    scope_key: str
    title: str
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime


class ConversationCreate(ApiModel):
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class ConversationUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    status: Literal["active", "archived"] | None = None


class Message(VersionedModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "tool"]
    sequence: int
    content: list[ContentPart]
    created_at: datetime
    visible_at: datetime | None = None
    completed_at: datetime | None = None
    edited_at: datetime | None = None


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Run(VersionedModel):
    id: str
    conversation_id: str
    input_message_id: str
    status: RunStatus
    provider: str
    usage: dict[str, int]
    created_at: datetime
    completed_at: datetime | None = None


class RunCreate(ApiModel):
    text: str = Field(min_length=1, max_length=20_000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)
    context_profile: ContextProfile = ContextProfile.LITE
    execution_mode: ExecutionMode = ExecutionMode.CONFIRM_EACH
    disclosure_level: DisclosureLevel = DisclosureLevel.STATUS


class RunCreated(ApiModel):
    run_id: str
    input_message_id: str
    latest_seq: int


class EventScope(ApiModel):
    kind: Literal["run", "conversation", "attachment", "privacy_job", "composer"]
    id: str


class AssistantEvent(VersionedModel):
    event_id: str
    scope: EventScope
    seq: int
    type: str
    created_at: datetime
    payload: dict[str, Any]
    conversation_id: str | None = None
    run_id: str | None = None


class AttachmentKind(StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    TEXT = "text"
    AUDIO = "audio"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


class Attachment(VersionedModel):
    id: str
    conversation_id: str | None
    owner_scope: str
    kind: AttachmentKind
    name: str
    mime_type: str
    size_bytes: int
    source: Literal["picker", "camera", "paste", "drag_drop", "voice"]
    upload_status: Literal["local", "uploading", "uploaded", "failed"]
    processing_status: Literal["none", "queued", "processing", "ready", "partial", "failed", "unsupported", "blocked"]
    retention_policy: str
    permission_scope: str
    metadata: dict[str, Any]
    created_at: datetime


class Transcript(VersionedModel):
    id: str
    attachment_id: str
    text: str
    language: str
    adapter: str
    revision: int
    is_user_correction: bool
    created_at: datetime


class TranscriptCorrection(ApiModel):
    text: str = Field(min_length=1, max_length=20_000)


class ActionState(StrEnum):
    PROPOSED = "proposed"
    POLICY_EVALUATING = "policy_evaluating"
    BLOCKED = "blocked"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EDITING = "editing"
    AUTO_APPLYING = "auto_applying"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BLOCKED_PLUGIN_DISABLED = "blocked_plugin_disabled"
    ARCHIVED = "archived"
    UNDOING = "undoing"
    UNDONE = "undone"
    UNDO_FAILED = "undo_failed"


class PendingAction(VersionedModel):
    id: str
    conversation_id: str
    run_id: str | None
    action_type: str
    payload: dict[str, Any]
    state: ActionState
    execution_mode: ExecutionMode
    idempotency_key: str
    policy_decision: dict[str, Any] | None
    result: dict[str, Any] | None
    plugin_id: str | None
    created_at: datetime
    updated_at: datetime


class ActionEdit(ApiModel):
    payload: dict[str, Any]


class MemoryRecord(VersionedModel):
    id: str
    actor_id: str
    conversation_id: str | None
    scope: Literal["conversation", "app", "user"]
    content: str
    provenance: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MemoryCreate(ApiModel):
    conversation_id: str | None = None
    scope: Literal["conversation", "app", "user"]
    content: str = Field(min_length=1, max_length=4_000)
    provenance: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(ApiModel):
    content: str = Field(min_length=1, max_length=4_000)


class PrivacyJobStatus(StrEnum):
    REQUESTED = "requested"
    PREVIEWING = "previewing"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class PrivacyJob(VersionedModel):
    id: str
    kind: Literal["export", "deletion"]
    status: PrivacyJobStatus
    scope: dict[str, Any]
    preview: dict[str, Any]
    results: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class PrivacyRequest(ApiModel):
    categories: list[str] = Field(default_factory=list)
    conversation_id: str | None = None


class KnowledgeDocument(VersionedModel):
    id: str
    actor_id: str
    title: str
    body: str
    source_url: str | None
    created_at: datetime


class KnowledgeDocumentCreate(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=100_000)
    source_url: str | None = None


class PluginState(VersionedModel):
    id: str
    version: str
    protocol_range: str
    data_schema_version: str
    enabled: bool
    capabilities: list[str]
