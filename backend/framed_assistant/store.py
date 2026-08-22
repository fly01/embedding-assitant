from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .database import Database
from .errors import ConflictError, NotFoundError
from .models import (
    ActionState,
    AssistantEvent,
    Attachment,
    AttachmentKind,
    ContentPart,
    Conversation,
    ExecutionMode,
    HostContext,
    KnowledgeDocument,
    MemoryRecord,
    Message,
    PendingAction,
    PluginState,
    PrivacyJob,
    PrivacyJobStatus,
    Run,
    RunStatus,
    Transcript,
    utc_now,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def decode(value: str) -> Any:
    return json.loads(value)


def decode_optional(value: str | None) -> Any | None:
    return None if value is None else decode(value)


def parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class Store:
    def __init__(self, database: Database, attachments_dir: Path):
        self.database = database
        self.attachments_dir = attachments_dir
        self._event_lock = threading.Lock()
        self._event_sequences: dict[tuple[str, str], int] = {}
        self._ephemeral_events: dict[tuple[str, str], list[AssistantEvent]] = {}

    def initialize(self) -> None:
        self.database.initialize()
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

    # Conversations and messages

    def create_conversation(self, host: HostContext, title: str) -> Conversation:
        now = utc_now()
        conversation = Conversation(
            id=new_id("conv"),
            actor_id=host.actor_id,
            scope_key=host.scope_key,
            title=title,
            status="active",
            created_at=now,
            updated_at=now,
        )
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation.id,
                    conversation.actor_id,
                    conversation.scope_key,
                    conversation.title,
                    conversation.status,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                ),
            )
        return conversation

    def list_conversations(self, host: HostContext) -> list[Conversation]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM conversations WHERE actor_id = ? AND scope_key = ? ORDER BY updated_at DESC",
                (host.actor_id, host.scope_key),
            ).fetchall()
        return [self._conversation(row) for row in rows]

    def get_conversation(self, host: HostContext, conversation_id: str) -> Conversation:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ? AND actor_id = ? AND scope_key = ?",
                (conversation_id, host.actor_id, host.scope_key),
            ).fetchone()
        if row is None:
            raise NotFoundError("Conversation not found")
        return self._conversation(row)

    def update_conversation(
        self,
        host: HostContext,
        conversation_id: str,
        *,
        title: str | None,
        status: str | None,
    ) -> Conversation:
        current = self.get_conversation(host, conversation_id)
        updated = current.model_copy(
            update={
                "title": title or current.title,
                "status": status or current.status,
                "updated_at": utc_now(),
            }
        )
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE conversations SET title = ?, status = ?, updated_at = ? WHERE id = ?",
                (updated.title, updated.status, updated.updated_at.isoformat(), updated.id),
            )
        return updated

    def create_message(
        self,
        conversation_id: str,
        role: str,
        content: list[ContentPart],
        *,
        visible: bool = True,
    ) -> Message:
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()[0]
            message = Message(
                id=new_id("msg"),
                conversation_id=conversation_id,
                role=role,
                sequence=sequence,
                content=content,
                created_at=now,
                visible_at=now if visible else None,
            )
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    message.id,
                    message.conversation_id,
                    message.role,
                    message.sequence,
                    encode([part.model_dump(mode="json") for part in message.content]),
                    message.created_at.isoformat(),
                    message.visible_at.isoformat() if message.visible_at else None,
                    None,
                    None,
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now.isoformat(), conversation_id),
            )
        return message

    def update_message_content(
        self,
        message_id: str,
        content: list[ContentPart],
        *,
        complete: bool = False,
    ) -> Message:
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE messages SET content = ?, visible_at = COALESCE(visible_at, ?), completed_at = ? WHERE id = ?",
                (
                    encode([part.model_dump(mode="json") for part in content]),
                    now.isoformat(),
                    now.isoformat() if complete else None,
                    message_id,
                ),
            )
            row = connection.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if row is None:
            raise NotFoundError("Message not found")
        return self._message(row)

    def list_messages(
        self,
        host: HostContext,
        conversation_id: str,
        *,
        before: str | None = None,
        limit: int = 50,
    ) -> list[Message]:
        self.get_conversation(host, conversation_id)
        before_sequence = 2**63 - 1
        with self.database.connect() as connection:
            if before:
                row = connection.execute(
                    "SELECT sequence FROM messages WHERE id = ? AND conversation_id = ?",
                    (before, conversation_id),
                ).fetchone()
                if row is None:
                    raise NotFoundError("Pagination anchor not found")
                before_sequence = row[0]
            rows = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ? AND sequence < ? ORDER BY sequence DESC LIMIT ?",
                (conversation_id, before_sequence, limit),
            ).fetchall()
        return [self._message(row) for row in reversed(rows)]

    def message_count(self, conversation_id: str) -> int:
        with self.database.connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()[0]

    # Runs and scoped events

    def create_run(self, conversation_id: str, input_message_id: str, provider: str) -> Run:
        run = Run(
            id=new_id("run"),
            conversation_id=conversation_id,
            input_message_id=input_message_id,
            status=RunStatus.QUEUED,
            provider=provider,
            usage={},
            created_at=utc_now(),
        )
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run.id,
                    run.conversation_id,
                    run.input_message_id,
                    run.status,
                    run.provider,
                    encode(run.usage),
                    run.created_at.isoformat(),
                    None,
                ),
            )
        return run

    def get_run(self, host: HostContext, run_id: str) -> Run:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT runs.* FROM runs
                JOIN conversations ON conversations.id = runs.conversation_id
                WHERE runs.id = ? AND conversations.actor_id = ? AND conversations.scope_key = ?
                """,
                (run_id, host.actor_id, host.scope_key),
            ).fetchone()
        if row is None:
            raise NotFoundError("Run not found")
        return self._run(row)

    def set_run_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        usage: dict[str, int] | None = None,
    ) -> None:
        completed_at = (
            utc_now().isoformat()
            if status
            in {
                RunStatus.COMPLETED,
                RunStatus.CANCELLED,
                RunStatus.INTERRUPTED,
                RunStatus.FAILED,
            }
            else None
        )
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE runs SET status = ?, usage = COALESCE(?, usage), completed_at = ? WHERE id = ?",
                (status, encode(usage) if usage is not None else None, completed_at, run_id),
            )

    def run_status(self, run_id: str) -> RunStatus:
        with self.database.connect() as connection:
            row = connection.execute("SELECT status FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise NotFoundError("Run not found")
        return RunStatus(row["status"])

    def append_event(
        self,
        *,
        scope_kind: str,
        scope_id: str,
        event_type: str,
        payload: dict[str, Any],
        conversation_id: str | None = None,
        run_id: str | None = None,
        persist: bool = True,
    ) -> AssistantEvent:
        key = (scope_kind, scope_id)
        with self._event_lock:
            if key not in self._event_sequences:
                with self.database.connect() as connection:
                    self._event_sequences[key] = connection.execute(
                        "SELECT COALESCE(MAX(seq), 0) FROM events WHERE scope_kind = ? AND scope_id = ?",
                        key,
                    ).fetchone()[0]
            self._event_sequences[key] += 1
            seq = self._event_sequences[key]
            event = AssistantEvent(
                event_id=new_id("evt"),
                scope={"kind": scope_kind, "id": scope_id},
                seq=seq,
                type=event_type,
                created_at=utc_now(),
                payload=payload,
                conversation_id=conversation_id,
                run_id=run_id,
            )
            if not persist:
                self._ephemeral_events.setdefault(key, []).append(event)
                return event

        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    scope_kind,
                    scope_id,
                    event.seq,
                    conversation_id,
                    run_id,
                    event.type,
                    encode(event.payload),
                    event.created_at.isoformat(),
                ),
            )
        return event

    def list_events(self, scope_kind: str, scope_id: str, after_seq: int) -> list[AssistantEvent]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE scope_kind = ? AND scope_id = ? AND seq > ? ORDER BY seq",
                (scope_kind, scope_id, after_seq),
            ).fetchall()
        persisted = [self._event(row) for row in rows]
        with self._event_lock:
            ephemeral = [
                event for event in self._ephemeral_events.get((scope_kind, scope_id), []) if event.seq > after_seq
            ]
        return sorted([*persisted, *ephemeral], key=lambda event: event.seq)

    def clear_ephemeral_events(self, scope_kind: str, scope_id: str) -> None:
        with self._event_lock:
            self._ephemeral_events.pop((scope_kind, scope_id), None)

    # Attachments and transcripts

    def create_attachment(
        self,
        host: HostContext,
        *,
        conversation_id: str | None,
        kind: AttachmentKind,
        name: str,
        mime_type: str,
        size_bytes: int,
        source: str,
        storage_path: Path,
    ) -> Attachment:
        attachment = Attachment(
            id=new_id("att"),
            conversation_id=conversation_id,
            owner_scope=host.scope_key,
            kind=kind,
            name=name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            source=source,
            upload_status="uploaded",
            processing_status="queued",
            retention_policy="host-default",
            permission_scope="private",
            metadata={},
            created_at=utc_now(),
        )
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO attachments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    attachment.id,
                    attachment.conversation_id,
                    host.actor_id,
                    attachment.owner_scope,
                    attachment.kind,
                    attachment.name,
                    attachment.mime_type,
                    attachment.size_bytes,
                    attachment.source,
                    str(storage_path),
                    attachment.upload_status,
                    attachment.processing_status,
                    attachment.retention_policy,
                    attachment.permission_scope,
                    encode(attachment.metadata),
                    attachment.created_at.isoformat(),
                ),
            )
        return attachment

    def get_attachment(self, host: HostContext, attachment_id: str) -> tuple[Attachment, Path]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM attachments WHERE id = ? AND actor_id = ? AND owner_scope = ?",
                (attachment_id, host.actor_id, host.scope_key),
            ).fetchone()
        if row is None:
            raise NotFoundError("Attachment not found")
        return self._attachment(row), Path(row["storage_path"])

    def list_attachments(self, host: HostContext, conversation_id: str | None = None) -> list[Attachment]:
        query = "SELECT * FROM attachments WHERE actor_id = ? AND owner_scope = ?"
        parameters: list[Any] = [host.actor_id, host.scope_key]
        if conversation_id:
            query += " AND conversation_id = ?"
            parameters.append(conversation_id)
        query += " ORDER BY created_at"
        with self.database.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._attachment(row) for row in rows]

    def update_attachment(
        self,
        attachment_id: str,
        *,
        processing_status: str,
        metadata: dict[str, Any],
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE attachments SET processing_status = ?, metadata = ? WHERE id = ?",
                (processing_status, encode(metadata), attachment_id),
            )

    def add_attachment_result(
        self,
        attachment_id: str,
        *,
        processor: str,
        processor_version: str,
        status: str,
        result: dict[str, Any],
        warnings: list[str],
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO attachment_results VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id("result"),
                    attachment_id,
                    processor,
                    processor_version,
                    status,
                    encode(result),
                    encode(warnings),
                    utc_now().isoformat(),
                ),
            )

    def create_transcript(
        self,
        attachment_id: str,
        text: str,
        *,
        adapter: str,
        is_user_correction: bool,
        language: str = "en",
    ) -> Transcript:
        with self.database.connect() as connection:
            revision = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM transcripts WHERE attachment_id = ?",
                (attachment_id,),
            ).fetchone()[0]
            transcript = Transcript(
                id=new_id("transcript"),
                attachment_id=attachment_id,
                text=text,
                language=language,
                adapter=adapter,
                revision=revision,
                is_user_correction=is_user_correction,
                created_at=utc_now(),
            )
            connection.execute(
                "INSERT INTO transcripts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    transcript.id,
                    transcript.attachment_id,
                    transcript.text,
                    transcript.language,
                    transcript.adapter,
                    transcript.revision,
                    int(transcript.is_user_correction),
                    transcript.created_at.isoformat(),
                ),
            )
        return transcript

    def list_transcripts(self, attachment_id: str) -> list[Transcript]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcripts WHERE attachment_id = ? ORDER BY revision",
                (attachment_id,),
            ).fetchall()
        return [self._transcript(row) for row in rows]

    # Actions

    def create_action(
        self,
        *,
        conversation_id: str,
        run_id: str | None,
        action_type: str,
        payload: dict[str, Any],
        execution_mode: ExecutionMode,
        state: ActionState,
        policy_decision: dict[str, Any],
        plugin_id: str | None = None,
    ) -> PendingAction:
        now = utc_now()
        action = PendingAction(
            id=new_id("action"),
            conversation_id=conversation_id,
            run_id=run_id,
            action_type=action_type,
            payload=payload,
            state=state,
            execution_mode=execution_mode,
            idempotency_key=new_id("idem"),
            policy_decision=policy_decision,
            result=None,
            plugin_id=plugin_id,
            created_at=now,
            updated_at=now,
        )
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO actions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    action.id,
                    action.conversation_id,
                    action.run_id,
                    action.action_type,
                    encode(action.payload),
                    action.state,
                    action.execution_mode,
                    action.idempotency_key,
                    encode(action.policy_decision),
                    None,
                    action.plugin_id,
                    action.created_at.isoformat(),
                    action.updated_at.isoformat(),
                ),
            )
        return action

    def get_action(self, host: HostContext, action_id: str) -> PendingAction:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT actions.* FROM actions
                JOIN conversations ON conversations.id = actions.conversation_id
                WHERE actions.id = ? AND conversations.actor_id = ? AND conversations.scope_key = ?
                """,
                (action_id, host.actor_id, host.scope_key),
            ).fetchone()
        if row is None:
            raise NotFoundError("Action not found")
        return self._action(row)

    def list_actions(self, host: HostContext, conversation_id: str) -> list[PendingAction]:
        self.get_conversation(host, conversation_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM actions WHERE conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            ).fetchall()
        return [self._action(row) for row in rows]

    def update_action(
        self,
        action_id: str,
        *,
        state: ActionState | None = None,
        payload: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        policy_decision: dict[str, Any] | None = None,
    ) -> PendingAction:
        updates: list[str] = ["updated_at = ?"]
        values: list[Any] = [utc_now().isoformat()]
        for column, value in (
            ("state", state),
            ("payload", encode(payload) if payload is not None else None),
            ("result", encode(result) if result is not None else None),
            ("policy_decision", encode(policy_decision) if policy_decision is not None else None),
        ):
            if value is not None:
                updates.append(f"{column} = ?")
                values.append(value)
        values.append(action_id)
        with self.database.connect() as connection:
            connection.execute(f"UPDATE actions SET {', '.join(updates)} WHERE id = ?", values)
            row = connection.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        if row is None:
            raise NotFoundError("Action not found")
        return self._action(row)

    # Memory and context

    def create_memory(
        self,
        host: HostContext,
        *,
        conversation_id: str | None,
        scope: str,
        content: str,
        provenance: dict[str, Any],
    ) -> MemoryRecord:
        now = utc_now()
        memory = MemoryRecord(
            id=new_id("memory"),
            actor_id=host.actor_id,
            conversation_id=conversation_id,
            scope=scope,
            content=content,
            provenance=provenance,
            created_at=now,
            updated_at=now,
        )
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    memory.id,
                    memory.actor_id,
                    memory.conversation_id,
                    memory.scope,
                    memory.content,
                    encode(memory.provenance),
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                ),
            )
            if conversation_id:
                connection.execute("DELETE FROM context_artifacts WHERE conversation_id = ?", (conversation_id,))
            else:
                connection.execute("DELETE FROM context_artifacts WHERE actor_id = ?", (host.actor_id,))
        return memory

    def list_memories(self, host: HostContext, conversation_id: str | None = None) -> list[MemoryRecord]:
        with self.database.connect() as connection:
            if conversation_id:
                rows = connection.execute(
                    """
                    SELECT * FROM memories
                    WHERE actor_id = ? AND (conversation_id = ? OR scope IN ('app', 'user'))
                    ORDER BY updated_at DESC
                    """,
                    (host.actor_id, conversation_id),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM memories WHERE actor_id = ? ORDER BY updated_at DESC",
                    (host.actor_id,),
                ).fetchall()
        return [self._memory(row) for row in rows]

    def update_memory(self, host: HostContext, memory_id: str, content: str) -> MemoryRecord:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE memories SET content = ?, updated_at = ? WHERE id = ? AND actor_id = ?",
                (content, utc_now().isoformat(), memory_id, host.actor_id),
            )
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ? AND actor_id = ?",
                (memory_id, host.actor_id),
            ).fetchone()
            if row:
                if row["conversation_id"]:
                    connection.execute(
                        "DELETE FROM context_artifacts WHERE conversation_id = ?",
                        (row["conversation_id"],),
                    )
                else:
                    connection.execute("DELETE FROM context_artifacts WHERE actor_id = ?", (host.actor_id,))
        if row is None:
            raise NotFoundError("Memory not found")
        return self._memory(row)

    def delete_memory(self, host: HostContext, memory_id: str) -> None:
        with self.database.connect() as connection:
            memory = connection.execute(
                "SELECT conversation_id FROM memories WHERE id = ? AND actor_id = ?",
                (memory_id, host.actor_id),
            ).fetchone()
            if memory is None:
                raise NotFoundError("Memory not found")
            connection.execute(
                "DELETE FROM memories WHERE id = ? AND actor_id = ?",
                (memory_id, host.actor_id),
            )
            if memory["conversation_id"]:
                connection.execute(
                    "DELETE FROM context_artifacts WHERE conversation_id = ?",
                    (memory["conversation_id"],),
                )
            else:
                connection.execute("DELETE FROM context_artifacts WHERE actor_id = ?", (host.actor_id,))

    def save_context_artifact(
        self,
        host: HostContext,
        conversation_id: str,
        profile: str,
        kind: str,
        source_revision: int,
        content: dict[str, Any],
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO context_artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id("context"),
                    host.actor_id,
                    conversation_id,
                    profile,
                    kind,
                    source_revision,
                    encode(content),
                    utc_now().isoformat(),
                ),
            )

    def latest_context_artifact(
        self,
        host: HostContext,
        conversation_id: str,
        profile: str,
        kind: str,
    ) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT content FROM context_artifacts
                WHERE actor_id = ? AND conversation_id = ? AND profile = ? AND kind = ?
                ORDER BY source_revision DESC LIMIT 1
                """,
                (host.actor_id, conversation_id, profile, kind),
            ).fetchone()
        return decode(row["content"]) if row else None

    def invalidate_context(self, conversation_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM context_artifacts WHERE conversation_id = ?", (conversation_id,))

    # Knowledge

    def create_knowledge_document(
        self,
        host: HostContext,
        *,
        title: str,
        body: str,
        source_url: str | None,
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            id=new_id("knowledge"),
            actor_id=host.actor_id,
            title=title,
            body=body,
            source_url=source_url,
            created_at=utc_now(),
        )
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO knowledge_documents VALUES (?, ?, ?, ?, ?, ?)",
                (
                    document.id,
                    document.actor_id,
                    document.title,
                    document.body,
                    document.source_url,
                    document.created_at.isoformat(),
                ),
            )
        return document

    def search_knowledge(self, host: HostContext, query: str) -> list[KnowledgeDocument]:
        terms = [term for term in query.lower().split() if term]
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_documents WHERE actor_id = ? ORDER BY created_at DESC",
                (host.actor_id,),
            ).fetchall()
        documents = [self._knowledge(row) for row in rows]
        return [document for document in documents if any(term in document.body.lower() for term in terms)][:5]

    # Plugins

    def register_plugin(self, plugin: PluginState) -> None:
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT data_schema_version FROM plugins WHERE id = ?",
                (plugin.id,),
            ).fetchone()
            if existing and existing["data_schema_version"] != plugin.data_schema_version:
                raise ConflictError(
                    f"Plugin {plugin.id} data schema {existing['data_schema_version']} requires migration"
                )
            connection.execute(
                """
                INSERT INTO plugins VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  version = excluded.version,
                  protocol_range = excluded.protocol_range,
                  data_schema_version = excluded.data_schema_version,
                  capabilities = excluded.capabilities
                """,
                (
                    plugin.id,
                    plugin.version,
                    plugin.protocol_range,
                    plugin.data_schema_version,
                    int(plugin.enabled),
                    encode(plugin.capabilities),
                ),
            )

    def list_plugins(self) -> list[PluginState]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM plugins ORDER BY id").fetchall()
        return [self._plugin(row) for row in rows]

    def get_plugin(self, plugin_id: str) -> PluginState:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM plugins WHERE id = ?", (plugin_id,)).fetchone()
        if row is None:
            raise NotFoundError("Plugin not found")
        return self._plugin(row)

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> PluginState:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "UPDATE plugins SET enabled = ? WHERE id = ?",
                (int(enabled), plugin_id),
            )
            if cursor.rowcount == 0:
                raise NotFoundError("Plugin not found")
            if not enabled:
                connection.execute(
                    """
                    UPDATE actions SET state = ?, updated_at = ?
                    WHERE plugin_id = ? AND state IN (
                      'proposed', 'policy_evaluating', 'awaiting_confirmation', 'editing', 'failed', 'retrying'
                    )
                    """,
                    (ActionState.BLOCKED_PLUGIN_DISABLED, utc_now().isoformat(), plugin_id),
                )
            row = connection.execute("SELECT * FROM plugins WHERE id = ?", (plugin_id,)).fetchone()
        return self._plugin(row)

    def list_plugin_actions(
        self,
        host: HostContext,
        plugin_id: str,
        state: ActionState,
    ) -> list[PendingAction]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT actions.* FROM actions
                JOIN conversations ON conversations.id = actions.conversation_id
                WHERE actions.plugin_id = ? AND actions.state = ?
                  AND conversations.actor_id = ? AND conversations.scope_key = ?
                ORDER BY actions.created_at
                """,
                (plugin_id, state, host.actor_id, host.scope_key),
            ).fetchall()
        return [self._action(row) for row in rows]

    # Reference Host records and audit

    def list_host_records(self, host: HostContext) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM host_records WHERE actor_id = ? AND scope_key = ? ORDER BY occurred_at DESC",
                (host.actor_id, host.scope_key),
            ).fetchall()
        return [dict(row) for row in rows]

    def apply_host_record_action(self, host: HostContext, action: PendingAction) -> dict[str, Any]:
        operation = action.action_type.removeprefix("host_data.record.")
        now = utc_now().isoformat()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_audit = connection.execute(
                "SELECT metadata FROM audit_events WHERE operation = ? AND decision = 'applied'",
                (action.idempotency_key,),
            ).fetchone()
            if existing_audit:
                return decode(existing_audit["metadata"])

            result = self._apply_record_operation(connection, host, operation, action.payload, now)
            connection.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id("audit"),
                    host.actor_id,
                    host.scope_key,
                    action.idempotency_key,
                    "applied",
                    encode(result),
                    now,
                ),
            )
        return result

    def _apply_record_operation(
        self,
        connection: sqlite3.Connection,
        host: HostContext,
        operation: str,
        payload: dict[str, Any],
        now: str,
    ) -> dict[str, Any]:
        if operation == "create":
            record_id = new_id("record")
            connection.execute(
                "INSERT INTO host_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record_id,
                    host.actor_id,
                    host.scope_key,
                    payload["title"],
                    float(payload["amount"]),
                    payload["occurred_at"],
                    1,
                    now,
                    now,
                ),
            )
            return {"operation": operation, "record_id": record_id, "version": 1}

        record_id = payload.get("record_id", new_id("record"))
        row = connection.execute(
            "SELECT * FROM host_records WHERE id = ? AND actor_id = ? AND scope_key = ?",
            (record_id, host.actor_id, host.scope_key),
        ).fetchone()
        if operation == "upsert" and row is None:
            connection.execute(
                "INSERT INTO host_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record_id,
                    host.actor_id,
                    host.scope_key,
                    payload["title"],
                    float(payload["amount"]),
                    payload["occurred_at"],
                    1,
                    now,
                    now,
                ),
            )
            return {"operation": operation, "record_id": record_id, "version": 1, "created": True}
        if row is None:
            raise NotFoundError("Host record not found")
        expected_version = payload.get("version")
        if expected_version is not None and row["version"] != expected_version:
            raise ConflictError("Host record version changed")

        if operation in {"update", "upsert"}:
            version = row["version"] + 1
            previous = {
                "title": row["title"],
                "amount": row["amount"],
                "occurred_at": row["occurred_at"],
                "version": row["version"],
            }
            connection.execute(
                """
                UPDATE host_records SET title = ?, amount = ?, occurred_at = ?, version = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.get("title", row["title"]),
                    float(payload.get("amount", row["amount"])),
                    payload.get("occurred_at", row["occurred_at"]),
                    version,
                    now,
                    record_id,
                ),
            )
            return {
                "operation": operation,
                "record_id": record_id,
                "version": version,
                "previous": previous,
            }
        if operation == "delete":
            connection.execute("DELETE FROM host_records WHERE id = ?", (record_id,))
            return {"operation": operation, "record_id": record_id}
        if operation in {"link", "unlink"}:
            target_id = payload["target_id"]
            target = connection.execute(
                "SELECT id FROM host_records WHERE id = ? AND actor_id = ? AND scope_key = ?",
                (target_id, host.actor_id, host.scope_key),
            ).fetchone()
            if target is None:
                raise NotFoundError("Target Host record not found")
            if operation == "link":
                connection.execute(
                    "INSERT INTO host_links VALUES (?, ?, ?, ?)",
                    (record_id, target_id, host.actor_id, host.scope_key),
                )
            else:
                connection.execute(
                    "DELETE FROM host_links WHERE source_id = ? AND target_id = ? AND actor_id = ? AND scope_key = ?",
                    (record_id, target_id, host.actor_id, host.scope_key),
                )
            return {"operation": operation, "record_id": record_id, "target_id": target_id}
        raise ValueError(f"Unsupported operation: {operation}")

    def undo_host_record_action(
        self,
        host: HostContext,
        action: PendingAction,
    ) -> dict[str, Any]:
        if action.result is None:
            raise ConflictError("Action has no applied result")
        result = action.result
        now = utc_now().isoformat()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if result["operation"] == "create" or result.get("created") is True:
                connection.execute(
                    "DELETE FROM host_records WHERE id = ? AND actor_id = ? AND scope_key = ?",
                    (result["record_id"], host.actor_id, host.scope_key),
                )
                return {"operation": "undo_create", "record_id": result["record_id"]}
            if result["operation"] in {"update", "upsert"}:
                previous = result["previous"]
                connection.execute(
                    """
                    UPDATE host_records SET title = ?, amount = ?, occurred_at = ?, version = ?, updated_at = ?
                    WHERE id = ? AND actor_id = ? AND scope_key = ?
                    """,
                    (
                        previous["title"],
                        previous["amount"],
                        previous["occurred_at"],
                        previous["version"],
                        now,
                        result["record_id"],
                        host.actor_id,
                        host.scope_key,
                    ),
                )
                return {"operation": "undo_update", "record_id": result["record_id"]}
        raise ConflictError("Action does not declare an undo")

    def record_attachment_promotion(
        self,
        host: HostContext,
        attachment_id: str,
        host_record_id: str,
    ) -> dict[str, Any]:
        promotion_id = new_id("promotion")
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM attachment_promotions WHERE attachment_id = ? AND host_record_id = ?",
                (attachment_id, host_record_id),
            ).fetchone()
            if existing:
                promotion_id = existing["id"]
            row = connection.execute(
                "SELECT metadata FROM attachments WHERE id = ? AND actor_id = ? AND owner_scope = ?",
                (attachment_id, host.actor_id, host.scope_key),
            ).fetchone()
            if row is None:
                raise NotFoundError("Attachment not found")
            metadata = decode(row["metadata"])
            host_refs = list(metadata.get("host_resource_refs", []))
            if host_record_id not in host_refs:
                host_refs.append(host_record_id)
            metadata["host_resource_refs"] = host_refs
            if existing is None:
                connection.execute(
                    "INSERT INTO attachment_promotions VALUES (?, ?, ?, ?, ?, ?)",
                    (promotion_id, attachment_id, host_record_id, host.actor_id, host.scope_key, utc_now().isoformat()),
                )
            connection.execute(
                "UPDATE attachments SET metadata = ? WHERE id = ?",
                (encode(metadata), attachment_id),
            )
        return {
            "promotion_id": promotion_id,
            "source_attachment_refs": [attachment_id],
            "promoted_attachment_refs": [host_record_id],
            "host_resource_ref": host_record_id,
        }

    # Privacy

    def privacy_inventory(self, host: HostContext) -> list[dict[str, Any]]:
        queries = {
            "conversations": (
                "SELECT COUNT(*) FROM conversations WHERE actor_id = ? AND scope_key = ?",
                (host.actor_id, host.scope_key),
            ),
            "attachments": (
                "SELECT COUNT(*) FROM attachments WHERE actor_id = ? AND owner_scope = ?",
                (host.actor_id, host.scope_key),
            ),
            "memory": (
                "SELECT COUNT(*) FROM memories WHERE actor_id = ?",
                (host.actor_id,),
            ),
            "actions": (
                """
                SELECT COUNT(*) FROM actions JOIN conversations ON conversations.id = actions.conversation_id
                WHERE conversations.actor_id = ? AND conversations.scope_key = ?
                """,
                (host.actor_id, host.scope_key),
            ),
            "context": (
                "SELECT COUNT(*) FROM context_artifacts WHERE actor_id = ?",
                (host.actor_id,),
            ),
            "host_records": (
                "SELECT COUNT(*) FROM host_records WHERE actor_id = ? AND scope_key = ?",
                (host.actor_id, host.scope_key),
            ),
        }
        resources: list[dict[str, Any]] = []
        with self.database.connect() as connection:
            for category, (query, parameters) in queries.items():
                count = connection.execute(query, parameters).fetchone()[0]
                if count:
                    resources.append(
                        {
                            "category": category,
                            "count": count,
                            "owner": "host" if category == "host_records" else "framework",
                            "retention": "host-controlled",
                            "exportable": True,
                            "deletable": category != "host_records",
                        }
                    )
        return resources

    def export_privacy_data(self, host: HostContext) -> dict[str, Any]:
        conversations = self.list_conversations(host)
        messages = {
            conversation.id: [
                message.model_dump(mode="json") for message in self.list_messages(host, conversation.id, limit=500)
            ]
            for conversation in conversations
        }
        with self.database.connect() as connection:
            context_rows = connection.execute(
                """
                SELECT conversation_id, profile, kind, source_revision, content, created_at
                FROM context_artifacts WHERE actor_id = ?
                """,
                (host.actor_id,),
            ).fetchall()
            audit_rows = connection.execute(
                """
                SELECT operation, decision, metadata, created_at
                FROM audit_events WHERE actor_id = ? AND scope_key = ?
                """,
                (host.actor_id, host.scope_key),
            ).fetchall()
        return {
            "conversations": [conversation.model_dump(mode="json") for conversation in conversations],
            "messages": messages,
            "attachments": [attachment.model_dump(mode="json") for attachment in self.list_attachments(host)],
            "memory": [memory.model_dump(mode="json") for memory in self.list_memories(host)],
            "actions": {
                conversation.id: [action.model_dump(mode="json") for action in self.list_actions(host, conversation.id)]
                for conversation in conversations
            },
            "context": [
                {
                    "conversation_id": row["conversation_id"],
                    "profile": row["profile"],
                    "kind": row["kind"],
                    "source_revision": row["source_revision"],
                    "content": decode(row["content"]),
                    "created_at": row["created_at"],
                }
                for row in context_rows
            ],
            "audit": [
                {
                    "operation": row["operation"],
                    "decision": row["decision"],
                    "metadata": decode(row["metadata"]),
                    "created_at": row["created_at"],
                }
                for row in audit_rows
            ],
            "host_records": self.list_host_records(host),
        }

    def create_privacy_job(
        self,
        host: HostContext,
        *,
        kind: str,
        scope: dict[str, Any],
        status: PrivacyJobStatus,
        preview: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> PrivacyJob:
        now = utc_now()
        job = PrivacyJob(
            id=new_id("privacy"),
            kind=kind,
            status=status,
            scope=scope,
            preview=preview,
            results=results,
            created_at=now,
            updated_at=now,
        )
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO privacy_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job.id,
                    host.actor_id,
                    host.scope_key,
                    job.kind,
                    job.status,
                    encode(job.scope),
                    encode(job.preview),
                    encode(job.results),
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )
        return job

    def get_privacy_job(self, host: HostContext, job_id: str) -> PrivacyJob:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM privacy_jobs WHERE id = ? AND actor_id = ? AND scope_key = ?",
                (job_id, host.actor_id, host.scope_key),
            ).fetchone()
        if row is None:
            raise NotFoundError("Privacy job not found")
        return self._privacy_job(row)

    def update_privacy_job(
        self,
        job_id: str,
        *,
        status: PrivacyJobStatus,
        results: list[dict[str, Any]],
    ) -> PrivacyJob:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE privacy_jobs SET status = ?, results = ?, updated_at = ? WHERE id = ?",
                (status, encode(results), utc_now().isoformat(), job_id),
            )
            row = connection.execute("SELECT * FROM privacy_jobs WHERE id = ?", (job_id,)).fetchone()
        return self._privacy_job(row)

    def delete_privacy_categories(
        self,
        host: HostContext,
        *,
        categories: list[str],
        conversation_id: str | None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if "memory" in categories:
                cursor = connection.execute("DELETE FROM memories WHERE actor_id = ?", (host.actor_id,))
                results.append({"category": "memory", "status": "deleted", "count": cursor.rowcount})
            if "context" in categories:
                cursor = connection.execute("DELETE FROM context_artifacts WHERE actor_id = ?", (host.actor_id,))
                results.append({"category": "context", "status": "deleted", "count": cursor.rowcount})
            if "attachments" in categories:
                rows = connection.execute(
                    "SELECT id, storage_path FROM attachments WHERE actor_id = ? AND owner_scope = ?",
                    (host.actor_id, host.scope_key),
                ).fetchall()
                for row in rows:
                    Path(row["storage_path"]).unlink()
                connection.execute(
                    "DELETE FROM attachments WHERE actor_id = ? AND owner_scope = ?",
                    (host.actor_id, host.scope_key),
                )
                connection.execute("DELETE FROM context_artifacts WHERE actor_id = ?", (host.actor_id,))
                results.append({"category": "attachments", "status": "deleted", "count": len(rows)})
            if "actions" in categories:
                cursor = connection.execute(
                    """
                    DELETE FROM actions WHERE conversation_id IN (
                      SELECT id FROM conversations WHERE actor_id = ? AND scope_key = ?
                    )
                    """,
                    (host.actor_id, host.scope_key),
                )
                results.append({"category": "actions", "status": "deleted", "count": cursor.rowcount})
            if "conversations" in categories:
                if conversation_id:
                    cursor = connection.execute(
                        "DELETE FROM conversations WHERE id = ? AND actor_id = ? AND scope_key = ?",
                        (conversation_id, host.actor_id, host.scope_key),
                    )
                else:
                    cursor = connection.execute(
                        "DELETE FROM conversations WHERE actor_id = ? AND scope_key = ?",
                        (host.actor_id, host.scope_key),
                    )
                results.append({"category": "conversations", "status": "deleted", "count": cursor.rowcount})
            if "host_records" in categories:
                count = connection.execute(
                    "SELECT COUNT(*) FROM host_records WHERE actor_id = ? AND scope_key = ?",
                    (host.actor_id, host.scope_key),
                ).fetchone()[0]
                results.append({"category": "host_records", "status": "host_handoff", "count": count})
        return results

    # Row mapping

    @staticmethod
    def _conversation(row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            actor_id=row["actor_id"],
            scope_key=row["scope_key"],
            title=row["title"],
            status=row["status"],
            created_at=parse_time(row["created_at"]),
            updated_at=parse_time(row["updated_at"]),
        )

    @staticmethod
    def _message(row: sqlite3.Row) -> Message:
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            sequence=row["sequence"],
            content=[ContentPart.model_validate(part) for part in decode(row["content"])],
            created_at=parse_time(row["created_at"]),
            visible_at=parse_time(row["visible_at"]),
            completed_at=parse_time(row["completed_at"]),
            edited_at=parse_time(row["edited_at"]),
        )

    @staticmethod
    def _run(row: sqlite3.Row) -> Run:
        return Run(
            id=row["id"],
            conversation_id=row["conversation_id"],
            input_message_id=row["input_message_id"],
            status=row["status"],
            provider=row["provider"],
            usage=decode(row["usage"]),
            created_at=parse_time(row["created_at"]),
            completed_at=parse_time(row["completed_at"]),
        )

    @staticmethod
    def _event(row: sqlite3.Row) -> AssistantEvent:
        return AssistantEvent(
            event_id=row["event_id"],
            scope={"kind": row["scope_kind"], "id": row["scope_id"]},
            seq=row["seq"],
            conversation_id=row["conversation_id"],
            run_id=row["run_id"],
            type=row["type"],
            payload=decode(row["payload"]),
            created_at=parse_time(row["created_at"]),
        )

    @staticmethod
    def _attachment(row: sqlite3.Row) -> Attachment:
        return Attachment(
            id=row["id"],
            conversation_id=row["conversation_id"],
            owner_scope=row["owner_scope"],
            kind=row["kind"],
            name=row["name"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            source=row["source"],
            upload_status=row["upload_status"],
            processing_status=row["processing_status"],
            retention_policy=row["retention_policy"],
            permission_scope=row["permission_scope"],
            metadata=decode(row["metadata"]),
            created_at=parse_time(row["created_at"]),
        )

    @staticmethod
    def _transcript(row: sqlite3.Row) -> Transcript:
        return Transcript(
            id=row["id"],
            attachment_id=row["attachment_id"],
            text=row["text"],
            language=row["language"],
            adapter=row["adapter"],
            revision=row["revision"],
            is_user_correction=bool(row["is_user_correction"]),
            created_at=parse_time(row["created_at"]),
        )

    @staticmethod
    def _action(row: sqlite3.Row) -> PendingAction:
        return PendingAction(
            id=row["id"],
            conversation_id=row["conversation_id"],
            run_id=row["run_id"],
            action_type=row["action_type"],
            payload=decode(row["payload"]),
            state=row["state"],
            execution_mode=row["execution_mode"],
            idempotency_key=row["idempotency_key"],
            policy_decision=decode_optional(row["policy_decision"]),
            result=decode_optional(row["result"]),
            plugin_id=row["plugin_id"],
            created_at=parse_time(row["created_at"]),
            updated_at=parse_time(row["updated_at"]),
        )

    @staticmethod
    def _memory(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            actor_id=row["actor_id"],
            conversation_id=row["conversation_id"],
            scope=row["scope"],
            content=row["content"],
            provenance=decode(row["provenance"]),
            created_at=parse_time(row["created_at"]),
            updated_at=parse_time(row["updated_at"]),
        )

    @staticmethod
    def _knowledge(row: sqlite3.Row) -> KnowledgeDocument:
        return KnowledgeDocument(
            id=row["id"],
            actor_id=row["actor_id"],
            title=row["title"],
            body=row["body"],
            source_url=row["source_url"],
            created_at=parse_time(row["created_at"]),
        )

    @staticmethod
    def _plugin(row: sqlite3.Row) -> PluginState:
        return PluginState(
            id=row["id"],
            version=row["version"],
            protocol_range=row["protocol_range"],
            data_schema_version=row["data_schema_version"],
            enabled=bool(row["enabled"]),
            capabilities=decode(row["capabilities"]),
        )

    @staticmethod
    def _privacy_job(row: sqlite3.Row) -> PrivacyJob:
        return PrivacyJob(
            id=row["id"],
            kind=row["kind"],
            status=row["status"],
            scope=decode(row["scope"]),
            preview=decode(row["preview"]),
            results=decode(row["results"]),
            created_at=parse_time(row["created_at"]),
            updated_at=parse_time(row["updated_at"]),
        )
