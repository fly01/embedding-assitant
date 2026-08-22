from __future__ import annotations

import asyncio
from typing import Any

from .actions import ActionService
from .context import ContextCompiler
from .errors import ToolError, ValidationError
from .host import ReferenceHostAdapter
from .models import (
    ContentPart,
    ContextProfile,
    DisclosureLevel,
    HostContext,
    Run,
    RunCreate,
    RunStatus,
)
from .providers import ModelProvider, ProviderError
from .store import Store
from .tools import ToolRegistry

MAX_TOTAL_ATTACHMENT_BYTES = 50 * 1024 * 1024


class AssistantRuntime:
    def __init__(
        self,
        *,
        store: Store,
        provider: ModelProvider,
        context_compiler: ContextCompiler,
        tools: ToolRegistry,
        actions: ActionService,
        host_adapter: ReferenceHostAdapter,
    ):
        self.store = store
        self.provider = provider
        self.context_compiler = context_compiler
        self.tools = tools
        self.actions = actions
        self.host_adapter = host_adapter

    def start(self, host: HostContext, conversation_id: str, request: RunCreate) -> Run:
        self.store.get_conversation(host, conversation_id)
        attachments = [self.store.get_attachment(host, attachment_id)[0] for attachment_id in request.attachment_ids]
        if sum(attachment.size_bytes for attachment in attachments) > MAX_TOTAL_ATTACHMENT_BYTES:
            raise ValidationError("Attachments exceed the 50 MiB message limit")
        for attachment in attachments:
            if attachment.processing_status not in {"ready", "partial"}:
                raise ValidationError(f"Attachment {attachment.id} is not ready")

        parts = [
            ContentPart(type="attachment", order=index, attachment_id=attachment.id)
            for index, attachment in enumerate(attachments)
        ]
        parts.append(ContentPart(type="text", order=len(parts), text=request.text))
        input_message = self.store.create_message(conversation_id, "user", parts)
        run = self.store.create_run(conversation_id, input_message.id, self.provider.name)
        asyncio.create_task(self.execute(host, run, request, attachments))
        return run

    async def execute(
        self,
        host: HostContext,
        run: Run,
        request: RunCreate,
        attachments: list[Any],
    ) -> None:
        self.store.set_run_status(run.id, RunStatus.RUNNING)
        self._emit(run, "run.started", {"run": run.model_dump(mode="json")})
        try:
            context = await self.context_compiler.compile(
                host,
                run.conversation_id,
                request.context_profile,
                request.text,
            )
        except ProviderError as error:
            if request.context_profile is ContextProfile.LITE:
                self._emit(run, "run.failed", {"code": "context_compilation_failed", "message": str(error)})
                self.store.set_run_status(run.id, RunStatus.FAILED)
                return
            self._emit(run, "thinking.status", {"stage": "context_fallback", "profile": "lite"})
            context = await self.context_compiler.compile(
                host,
                run.conversation_id,
                ContextProfile.LITE,
                request.text,
            )
        assistant_message = self.store.create_message(
            run.conversation_id,
            "assistant",
            [ContentPart(type="markdown", order=0, text="")],
            visible=False,
        )
        self._emit(run, "message.created", {"message": assistant_message.model_dump(mode="json")})

        text = ""
        content: list[ContentPart] = [ContentPart(type="markdown", order=0, text="")]
        usage = {"input_tokens": context.manifest["used"], "output_tokens": 0}
        try:
            async for provider_event in self.provider.generate(
                context=context,
                user_text=request.text,
                attachments=attachments,
                disclosure_level=request.disclosure_level,
            ):
                if self.store.run_status(run.id) is RunStatus.CANCELLED:
                    return
                if provider_event.kind == "status":
                    if request.disclosure_level is not DisclosureLevel.HIDDEN:
                        self._emit(run, "thinking.status", provider_event.payload)
                elif provider_event.kind == "reasoning_summary":
                    if request.disclosure_level in {
                        DisclosureLevel.ACTIVITY,
                        DisclosureLevel.DEVELOPER,
                        DisclosureLevel.RAW_TRACE,
                    }:
                        self._emit(run, "reasoning.summary.delta", provider_event.payload)
                elif provider_event.kind == "trace":
                    if request.disclosure_level is DisclosureLevel.RAW_TRACE:
                        self._emit(run, "reasoning.trace.delta", provider_event.payload, persist=False)
                elif provider_event.kind == "trace_unavailable":
                    self._emit(run, "reasoning.trace.unavailable", {})
                elif provider_event.kind == "text":
                    chunk = provider_event.payload["text"]
                    text += chunk
                    content[0] = ContentPart(type="markdown", order=0, text=text)
                    self.store.update_message_content(assistant_message.id, content)
                    self._emit(run, "content.delta", {"message_id": assistant_message.id, "text": chunk})
                elif provider_event.kind == "tool_call":
                    result = await self._execute_tool(host, run, provider_event.payload)
                    content.append(
                        ContentPart(
                            type="tool_activity",
                            order=len(content),
                            data={"name": provider_event.payload["name"], "result": result},
                        )
                    )
                elif provider_event.kind == "action":
                    execution = self.actions.propose(
                        host,
                        conversation_id=run.conversation_id,
                        run_id=run.id,
                        action_type=provider_event.payload["action_type"],
                        payload=provider_event.payload["payload"],
                        execution_mode=request.execution_mode,
                        plugin_id=provider_event.payload.get("plugin_id"),
                    )
                    content.append(
                        ContentPart(
                            type="action",
                            order=len(content),
                            data={"action_id": execution.action.id},
                        )
                    )
        except ProviderError as error:
            self._emit(run, "run.failed", {"code": "provider_unavailable", "message": str(error)})
            self.store.set_run_status(run.id, RunStatus.FAILED)
            return

        usage["output_tokens"] = max(1, len(text) // 4)
        completed = self.store.update_message_content(assistant_message.id, content, complete=True)
        self._emit(run, "message.completed", {"message": completed.model_dump(mode="json")})
        self._emit(run, "run.completed", {"usage": usage})
        self.store.set_run_status(run.id, RunStatus.COMPLETED, usage=usage)

    def cancel(self, host: HostContext, run_id: str) -> Run:
        run = self.store.get_run(host, run_id)
        self._emit(run, "run.interrupted", {"reason": "cancelled"})
        self.store.set_run_status(run_id, RunStatus.CANCELLED)
        return run.model_copy(update={"status": RunStatus.CANCELLED})

    async def _execute_tool(self, host: HostContext, run: Run, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload["name"]
        arguments = payload["arguments"]
        self._emit(run, "tool.requested", {"name": name, "arguments": arguments})
        permission = self.host_adapter.authorize(host, name)
        self._emit(run, "tool.started", {"name": name, "permission": permission})
        if not permission["allowed"]:
            self._emit(run, "tool.failed", {"name": name, "message": "Permission denied"})
            return {"error": "Permission denied"}
        try:
            result = await self.tools.execute(name, host, arguments)
        except (KeyError, ToolError) as error:
            self._emit(run, "tool.failed", {"name": name, "message": str(error)})
            return {"error": str(error)}
        self._emit(run, "tool.completed", {"name": name, "result": result})
        if name == "knowledge.search":
            for document in result["documents"]:
                self._emit(
                    run,
                    "citation.added",
                    {
                        "title": document["title"],
                        "source_url": document["source_url"],
                        "document_id": document["id"],
                    },
                )
        return result

    def _emit(self, run: Run, event_type: str, payload: dict[str, Any], *, persist: bool = True) -> None:
        self.store.append_event(
            scope_kind="run",
            scope_id=run.id,
            event_type=event_type,
            payload=payload,
            conversation_id=run.conversation_id,
            run_id=run.id,
            persist=persist,
        )
