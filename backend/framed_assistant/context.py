from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .host import ReferenceHostAdapter
from .models import ContextProfile, HostContext, Message
from .store import Store


class Summarizer(Protocol):
    async def summarize(self, messages: list[Message]) -> str: ...


@dataclass(frozen=True)
class ContextBlock:
    kind: str
    content: Any
    source: str
    tokens: int
    required: bool = False


@dataclass(frozen=True)
class ContextView:
    profile: ContextProfile
    blocks: list[ContextBlock]
    manifest: dict[str, Any]

    def provider_messages(self) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for block in self.blocks:
            if block.kind == "message":
                messages.append(block.content)
            else:
                messages.append({"role": "system", "content": f"{block.kind}: {block.content}"})
        return messages


class ContextCompiler:
    def __init__(self, store: Store, host_adapter: ReferenceHostAdapter, summarizer: Summarizer):
        self.store = store
        self.host_adapter = host_adapter
        self.summarizer = summarizer

    async def compile(
        self,
        host: HostContext,
        conversation_id: str,
        profile: ContextProfile,
        current_input: str,
        token_budget: int = 6_000,
    ) -> ContextView:
        messages = self.store.list_messages(host, conversation_id, limit=500)
        memories = self.store.list_memories(host, conversation_id)
        actions = self.store.list_actions(host, conversation_id)
        blocks: list[ContextBlock] = []

        blocks.append(
            self._block(
                "system_policy",
                "Use only authorized context. Business changes require a typed Action and Host policy.",
                "framework",
                required=True,
            )
        )
        blocks.append(self._block("host_facts", self.host_adapter.page_context(host), "host_adapter", required=True))
        blocks.append(self._block("current_input", current_input, "user_input", required=True))

        active_actions = [
            {"id": action.id, "type": action.action_type, "state": action.state, "payload": action.payload}
            for action in actions
            if action.state not in {"applied", "cancelled", "archived", "undone"}
        ]
        if active_actions:
            blocks.append(self._block("active_actions", active_actions, "action_store", required=True))
        if memories:
            blocks.append(
                self._block(
                    "memory",
                    [{"content": memory.content, "scope": memory.scope, "id": memory.id} for memory in memories],
                    "memory_store",
                )
            )

        recent_limit = {
            ContextProfile.LITE: 8,
            ContextProfile.BALANCED: 12,
            ContextProfile.DURABLE: 16,
        }[profile]
        old_messages = messages[:-recent_limit]
        recent_messages = messages[-recent_limit:]

        if old_messages and profile is not ContextProfile.LITE:
            summary = await self.summarizer.summarize(old_messages)
            summary_block = self._block("summary", summary, f"messages:{old_messages[0].id}-{old_messages[-1].id}")
            blocks.append(summary_block)
            self.store.save_context_artifact(
                host,
                conversation_id,
                profile,
                "summary",
                self.store.message_count(conversation_id),
                {"text": summary, "source_message_ids": [message.id for message in old_messages]},
            )

        if profile is ContextProfile.DURABLE and old_messages:
            relevant = self._relevant_messages(old_messages, current_input)
            if relevant:
                blocks.append(
                    self._block(
                        "retrieved_history",
                        [self._message_text(message) for message in relevant],
                        "conversation_history",
                    )
                )

        for message in recent_messages:
            blocks.append(
                self._block(
                    "message",
                    {"role": message.role, "content": self._message_text(message)},
                    f"message:{message.id}",
                )
            )

        blocks = self._fit_budget(blocks, token_budget)
        manifest = {
            "profile": profile,
            "budget": token_budget,
            "used": sum(block.tokens for block in blocks),
            "blocks": [{"kind": block.kind, "source": block.source, "tokens": block.tokens} for block in blocks],
        }
        self.store.save_context_artifact(
            host,
            conversation_id,
            profile,
            "manifest",
            self.store.message_count(conversation_id),
            manifest,
        )
        return ContextView(profile=profile, blocks=blocks, manifest=manifest)

    @staticmethod
    def _block(kind: str, content: Any, source: str, *, required: bool = False) -> ContextBlock:
        return ContextBlock(
            kind=kind,
            content=content,
            source=source,
            tokens=max(1, len(str(content)) // 4),
            required=required,
        )

    @staticmethod
    def _message_text(message: Message) -> str:
        return "\n".join(part.text for part in message.content if part.text)

    def _relevant_messages(self, messages: list[Message], query: str) -> list[Message]:
        terms = {term.lower() for term in query.split() if len(term) > 2}
        return [message for message in messages if terms.intersection(self._message_text(message).lower().split())][-4:]

    @staticmethod
    def _fit_budget(blocks: list[ContextBlock], budget: int) -> list[ContextBlock]:
        required = [block for block in blocks if block.required]
        used = sum(block.tokens for block in required)
        if used > budget:
            raise ValueError("Context budget is smaller than the required policy and current input")
        fitted = list(required)
        for block in (block for block in blocks if not block.required):
            if used + block.tokens <= budget:
                fitted.append(block)
                used += block.tokens
        return fitted
