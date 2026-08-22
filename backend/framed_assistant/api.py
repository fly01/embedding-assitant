from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .actions import ActionService
from .attachments import AttachmentService
from .errors import ConflictError, NotFoundError
from .host import HostContext, host_context
from .models import (
    ActionEdit,
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    MemoryCreate,
    MemoryRecord,
    MemoryUpdate,
    Message,
    PendingAction,
    PluginState,
    PrivacyJob,
    PrivacyRequest,
    Run,
    RunCreate,
    RunCreated,
    RunStatus,
    Transcript,
    TranscriptCorrection,
)
from .privacy import PrivacyService
from .runtime import AssistantRuntime
from .store import Store

router = APIRouter(prefix="/v1/assistant")


def store(request: Request) -> Store:
    return request.app.state.store


def runtime(request: Request) -> AssistantRuntime:
    return request.app.state.runtime


def attachments(request: Request) -> AttachmentService:
    return request.app.state.attachments


def actions(request: Request) -> ActionService:
    return request.app.state.actions


def privacy(request: Request) -> PrivacyService:
    return request.app.state.privacy


Host = Annotated[HostContext, Depends(host_context)]
StoreDependency = Annotated[Store, Depends(store)]
RuntimeDependency = Annotated[AssistantRuntime, Depends(runtime)]
AttachmentDependency = Annotated[AttachmentService, Depends(attachments)]
ActionDependency = Annotated[ActionService, Depends(actions)]
PrivacyDependency = Annotated[PrivacyService, Depends(privacy)]


@router.post("/conversations", response_model=Conversation, status_code=201)
def create_conversation(
    request: Request,
    body: ConversationCreate,
    host: Host,
    repository: StoreDependency,
) -> Conversation:
    if request.app.state.settings.conversation_mode == "single" and any(
        conversation.status == "active" for conversation in repository.list_conversations(host)
    ):
        raise ConflictError("Single mode already has an active Conversation in this Host scope")
    return repository.create_conversation(host, body.title)


@router.get("/conversations", response_model=list[Conversation])
def list_conversations(host: Host, repository: StoreDependency) -> list[Conversation]:
    return repository.list_conversations(host)


@router.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str, host: Host, repository: StoreDependency) -> Conversation:
    return repository.get_conversation(host, conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=Conversation)
def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    host: Host,
    repository: StoreDependency,
) -> Conversation:
    return repository.update_conversation(
        host,
        conversation_id,
        title=body.title,
        status=body.status,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[Message])
def list_messages(
    conversation_id: str,
    host: Host,
    repository: StoreDependency,
    before: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Message]:
    return repository.list_messages(host, conversation_id, before=before, limit=limit)


@router.get("/conversations/{conversation_id}/context/manifest")
def get_context_manifest(
    conversation_id: str,
    profile: str,
    host: Host,
    repository: StoreDependency,
):
    repository.get_conversation(host, conversation_id)
    manifest = repository.latest_context_artifact(host, conversation_id, profile, "manifest")
    if manifest is None:
        raise NotFoundError("No Context Manifest exists for this profile")
    return manifest


@router.post("/conversations/{conversation_id}/runs", response_model=RunCreated, status_code=202)
async def create_run(
    conversation_id: str,
    body: RunCreate,
    host: Host,
    assistant_runtime: RuntimeDependency,
) -> RunCreated:
    run = assistant_runtime.start(host, conversation_id, body)
    return RunCreated(run_id=run.id, input_message_id=run.input_message_id, latest_seq=0)


@router.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str, host: Host, repository: StoreDependency) -> Run:
    return repository.get_run(host, run_id)


@router.get("/runs/{run_id}/events")
def stream_run_events(
    run_id: str,
    host: Host,
    repository: StoreDependency,
    after_seq: Annotated[int, Query(ge=0)] = 0,
) -> StreamingResponse:
    repository.get_run(host, run_id)

    async def event_stream():
        cursor = after_seq
        try:
            while True:
                events = repository.list_events("run", run_id, cursor)
                for event in events:
                    cursor = event.seq
                    yield f"id: {event.seq}\nevent: {event.type}\ndata: {event.model_dump_json(exclude_none=True)}\n\n"
                status = repository.run_status(run_id)
                if not events and status in {
                    RunStatus.COMPLETED,
                    RunStatus.FAILED,
                    RunStatus.CANCELLED,
                    RunStatus.INTERRUPTED,
                }:
                    break
                await asyncio.sleep(0.02)
        finally:
            repository.clear_ephemeral_events("run", run_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/runs/{run_id}/cancel", response_model=Run)
def cancel_run(run_id: str, host: Host, assistant_runtime: RuntimeDependency) -> Run:
    return assistant_runtime.cancel(host, run_id)


@router.post("/attachments", status_code=201)
async def upload_attachment(
    host: Host,
    service: AttachmentDependency,
    file: Annotated[UploadFile, File()],
    conversation_id: Annotated[str | None, Form()] = None,
    source: Annotated[str, Form()] = "picker",
):
    return await service.upload(
        host,
        file,
        conversation_id=conversation_id,
        source=source,
    )


@router.get("/attachments/{attachment_id}")
def get_attachment(attachment_id: str, host: Host, repository: StoreDependency):
    return repository.get_attachment(host, attachment_id)[0]


def attachment_file(
    attachment_id: str,
    host: HostContext,
    repository: Store,
) -> FileResponse:
    attachment, path = repository.get_attachment(host, attachment_id)
    return FileResponse(path, media_type=attachment.mime_type, filename=attachment.name)


@router.get("/attachments/{attachment_id}/thumbnail")
def get_attachment_thumbnail(
    attachment_id: str,
    host: Host,
    repository: StoreDependency,
) -> FileResponse:
    return attachment_file(attachment_id, host, repository)


@router.get("/attachments/{attachment_id}/preview")
def get_attachment_preview(
    attachment_id: str,
    host: Host,
    repository: StoreDependency,
) -> FileResponse:
    return attachment_file(attachment_id, host, repository)


@router.get("/attachments/{attachment_id}/original")
def get_attachment_original(
    attachment_id: str,
    host: Host,
    repository: StoreDependency,
) -> FileResponse:
    return attachment_file(attachment_id, host, repository)


@router.post("/attachments/{attachment_id}/retry-processing")
def retry_attachment(
    attachment_id: str,
    host: Host,
    service: AttachmentDependency,
):
    return service.process(host, attachment_id)


@router.post("/attachments/{attachment_id}/transcriptions", response_model=Transcript)
def transcribe_attachment(
    attachment_id: str,
    host: Host,
    service: AttachmentDependency,
) -> Transcript:
    return service.transcribe(host, attachment_id)


@router.get("/attachments/{attachment_id}/transcriptions", response_model=list[Transcript])
def list_transcripts(
    attachment_id: str,
    host: Host,
    repository: StoreDependency,
) -> list[Transcript]:
    repository.get_attachment(host, attachment_id)
    return repository.list_transcripts(attachment_id)


@router.post("/attachments/{attachment_id}/transcriptions/corrections", response_model=Transcript)
def correct_transcript(
    attachment_id: str,
    body: TranscriptCorrection,
    host: Host,
    service: AttachmentDependency,
) -> Transcript:
    return service.correct_transcript(host, attachment_id, body.text)


@router.get("/conversations/{conversation_id}/actions", response_model=list[PendingAction])
def list_actions(
    conversation_id: str,
    host: Host,
    repository: StoreDependency,
) -> list[PendingAction]:
    return repository.list_actions(host, conversation_id)


@router.patch("/actions/{action_id}", response_model=PendingAction)
def edit_action(
    action_id: str,
    body: ActionEdit,
    host: Host,
    service: ActionDependency,
) -> PendingAction:
    return service.edit(host, action_id, body.payload)


@router.post("/actions/{action_id}/confirm", response_model=PendingAction)
def confirm_action(action_id: str, host: Host, service: ActionDependency) -> PendingAction:
    execution = service.confirm(host, action_id)
    if execution.error:
        raise ConflictError(execution.error)
    return execution.action


@router.post("/actions/{action_id}/cancel", response_model=PendingAction)
def cancel_action(action_id: str, host: Host, service: ActionDependency) -> PendingAction:
    return service.cancel(host, action_id)


@router.post("/actions/{action_id}/undo", response_model=PendingAction)
def undo_action(action_id: str, host: Host, service: ActionDependency) -> PendingAction:
    execution = service.undo(host, action_id)
    if execution.error:
        raise ConflictError(execution.error)
    return execution.action


@router.get("/memory", response_model=list[MemoryRecord])
def list_memory(
    host: Host,
    repository: StoreDependency,
    conversation_id: str | None = None,
) -> list[MemoryRecord]:
    return repository.list_memories(host, conversation_id)


@router.post("/memory", response_model=MemoryRecord, status_code=201)
def create_memory(body: MemoryCreate, host: Host, repository: StoreDependency) -> MemoryRecord:
    return repository.create_memory(
        host,
        conversation_id=body.conversation_id,
        scope=body.scope,
        content=body.content,
        provenance=body.provenance,
    )


@router.patch("/memory/{memory_id}", response_model=MemoryRecord)
def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    host: Host,
    repository: StoreDependency,
) -> MemoryRecord:
    return repository.update_memory(host, memory_id, body.content)


@router.delete("/memory/{memory_id}", status_code=204)
def delete_memory(memory_id: str, host: Host, repository: StoreDependency) -> None:
    repository.delete_memory(host, memory_id)


@router.post("/knowledge", response_model=KnowledgeDocument, status_code=201)
def create_knowledge_document(
    body: KnowledgeDocumentCreate,
    host: Host,
    repository: StoreDependency,
) -> KnowledgeDocument:
    return repository.create_knowledge_document(
        host,
        title=body.title,
        body=body.body,
        source_url=body.source_url,
    )


@router.get("/knowledge/search", response_model=list[KnowledgeDocument])
def search_knowledge(query: str, host: Host, repository: StoreDependency) -> list[KnowledgeDocument]:
    return repository.search_knowledge(host, query)


@router.get("/plugins", response_model=list[PluginState])
def list_plugins(repository: StoreDependency) -> list[PluginState]:
    return repository.list_plugins()


class PluginToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


@router.patch("/plugins/{plugin_id}", response_model=PluginState)
def toggle_plugin(
    plugin_id: str,
    body: PluginToggle,
    host: Host,
    repository: StoreDependency,
    service: ActionDependency,
) -> PluginState:
    plugin = repository.set_plugin_enabled(plugin_id, body.enabled)
    if body.enabled:
        service.revalidate_plugin(host, plugin_id)
    return plugin


@router.get("/host/records")
def list_host_records(host: Host, repository: StoreDependency):
    return repository.list_host_records(host)


@router.get("/privacy/resources")
def privacy_inventory(host: Host, service: PrivacyDependency):
    return service.inventory(host)


@router.post("/privacy/exports", response_model=PrivacyJob, status_code=201)
def export_privacy(body: PrivacyRequest, host: Host, service: PrivacyDependency) -> PrivacyJob:
    return service.export(host, body)


@router.post("/privacy/deletions/preview", response_model=PrivacyJob, status_code=201)
def preview_privacy_deletion(
    body: PrivacyRequest,
    host: Host,
    service: PrivacyDependency,
) -> PrivacyJob:
    return service.preview_deletion(host, body)


@router.post("/privacy/deletions/{job_id}/confirm", response_model=PrivacyJob)
def confirm_privacy_deletion(job_id: str, host: Host, service: PrivacyDependency) -> PrivacyJob:
    return service.confirm_deletion(host, job_id)


class DeletionConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str


@router.post("/privacy/deletions", response_model=PrivacyJob)
def confirm_privacy_deletion_from_body(
    body: DeletionConfirm,
    host: Host,
    service: PrivacyDependency,
) -> PrivacyJob:
    return service.confirm_deletion(host, body.job_id)


@router.post("/privacy/jobs/{job_id}/retry", response_model=PrivacyJob)
def retry_privacy_job(job_id: str, host: Host, service: PrivacyDependency) -> PrivacyJob:
    return service.retry(host, job_id)


@router.get("/privacy/jobs/{job_id}", response_model=PrivacyJob)
def get_privacy_job(job_id: str, host: Host, repository: StoreDependency) -> PrivacyJob:
    return repository.get_privacy_job(host, job_id)


class GeneratorOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str
    method: str
    path: str
    side_effect: str


class GeneratorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id: str
    operations: list[GeneratorOperation] = Field(min_length=1)


@router.post("/developer/integrations/generate")
def generate_integration(body: GeneratorRequest):
    tools = []
    actions = []
    risks = []
    for operation in body.operations:
        if operation.side_effect == "read":
            tools.append(
                {
                    "id": operation.operation_id,
                    "source": "openapi",
                    "method": operation.method,
                    "path": operation.path,
                }
            )
        else:
            actions.append(
                {
                    "id": operation.operation_id,
                    "source": "openapi",
                    "method": operation.method,
                    "path": operation.path,
                }
            )
            risks.append(
                {
                    "operation_id": operation.operation_id,
                    "blocking": True,
                    "unresolved": ["authorization", "validation", "idempotency", "transaction", "confirmation"],
                }
            )
    return {
        "manifest": {
            "schema_version": "0.1",
            "application": {"id": body.application_id},
            "tools": tools,
            "actions": actions,
            "review_status": "draft",
        },
        "risks": risks,
        "activated": False,
    }


@router.get("/capabilities")
def capabilities(request: Request, repository: StoreDependency):
    manifest = request.app.state.manifest
    return {
        "schema_version": "0.1",
        "conversation_modes": ["single", "multiple"],
        "active_conversation_mode": request.app.state.settings.conversation_mode,
        "context_profiles": ["lite", "balanced", "durable"],
        "execution_modes": ["read_only", "confirm_each", "auto_apply_allowlist"],
        "disclosure_levels": ["hidden", "status", "contextual", "activity", "developer", "raw_trace"],
        "host_data_tools": manifest.host_data_tools.model_dump(),
        "plugins": [plugin.model_dump(mode="json") for plugin in repository.list_plugins()],
        "tools": request.app.state.tools.definitions(),
    }
