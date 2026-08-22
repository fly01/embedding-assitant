from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import httpx

from .context import ContextView
from .models import Attachment, DisclosureLevel, HostContext, Message


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderEvent:
    kind: str
    payload: dict[str, Any]


class ModelProvider(Protocol):
    name: str
    reasoning_visibility: str

    async def generate(
        self,
        *,
        host: HostContext,
        context: ContextView,
        user_text: str,
        attachments: list[Attachment],
        disclosure_level: DisclosureLevel,
    ) -> AsyncIterator[ProviderEvent]: ...

    async def summarize(self, messages: list[Message]) -> str: ...


class MockModelProvider:
    name = "mock"
    reasoning_visibility = "trace"

    CREATE_PATTERN = re.compile(r"^Create record:\s*(.+?)\s*\|\s*([0-9]+(?:\.[0-9]+)?)$", re.I)
    UPDATE_PATTERN = re.compile(
        r"^Update record:\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|\s*([0-9]+)$",
        re.I,
    )
    DELETE_PATTERN = re.compile(r"^Delete record:\s*([^|]+?)\s*\|\s*([0-9]+)$", re.I)
    PROMOTE_PATTERN = re.compile(r"^Promote attachment:\s*([^|]+)\|\s*(.+)$", re.I)

    async def generate(
        self,
        *,
        host: HostContext,
        context: ContextView,
        user_text: str,
        attachments: list[Attachment],
        disclosure_level: DisclosureLevel,
    ) -> AsyncIterator[ProviderEvent]:
        status: dict[str, Any] = {"stage": "analyzing"}
        if attachments and disclosure_level in {
            DisclosureLevel.CONTEXTUAL,
            DisclosureLevel.ACTIVITY,
            DisclosureLevel.DEVELOPER,
            DisclosureLevel.RAW_TRACE,
        }:
            status["context"] = [attachment.name for attachment in attachments]
        yield ProviderEvent("status", status)
        if disclosure_level is DisclosureLevel.RAW_TRACE:
            trace = f"Mock provider trace: matched deterministic request against {len(context.blocks)} context blocks."
            yield ProviderEvent(
                "trace",
                {"text": trace},
            )

        if match := self.CREATE_PATTERN.match(user_text):
            title, amount = match.groups()
            yield ProviderEvent(
                "action",
                {
                    "action_type": "host_data.record.create",
                    "payload": {
                        "title": title.strip(),
                        "amount": float(amount),
                        "occurred_at": date.today().isoformat(),
                    },
                },
            )
            text = f"I prepared a record for **{title.strip()}**. Review the Action before it is applied."
        elif match := self.UPDATE_PATTERN.match(user_text):
            record_id, title, amount, version = match.groups()
            yield ProviderEvent(
                "action",
                {
                    "action_type": "host_data.record.update",
                    "payload": {
                        "record_id": record_id.strip(),
                        "title": title.strip(),
                        "amount": float(amount),
                        "version": int(version),
                    },
                },
            )
            text = "I prepared the record update for confirmation."
        elif match := self.DELETE_PATTERN.match(user_text):
            record_id, version = match.groups()
            yield ProviderEvent(
                "action",
                {
                    "action_type": "host_data.record.delete",
                    "payload": {"record_id": record_id.strip(), "version": int(version)},
                },
            )
            text = "I prepared a delete Action. Deletion always requires confirmation."
        elif match := self.PROMOTE_PATTERN.match(user_text):
            attachment_id, title = match.groups()
            yield ProviderEvent(
                "action",
                {
                    "action_type": "attachment.promote",
                    "payload": {
                        "attachment_id": attachment_id.strip(),
                        "source_attachment_refs": [attachment_id.strip()],
                        "title": title.strip(),
                        "occurred_at": date.today().isoformat(),
                    },
                },
            )
            text = "I prepared an Attachment Promotion. Review the source before confirming."
        elif user_text.strip().lower() == "list records":
            yield ProviderEvent("tool_call", {"name": "host.records.list", "arguments": {}})
            text = "I loaded the current Host records."
        elif user_text.lower().startswith("calculate:"):
            expression = user_text.split(":", 1)[1].strip()
            yield ProviderEvent(
                "tool_call",
                {"name": "essentials.calculate", "arguments": {"expression": expression}},
            )
            text = "The calculation is complete."
        elif user_text.lower().startswith("search knowledge:"):
            query = user_text.split(":", 1)[1].strip()
            yield ProviderEvent(
                "tool_call",
                {"name": "knowledge.search", "arguments": {"query": query}},
            )
            text = "I searched the registered knowledge sources."
        elif user_text.lower().startswith("plugin record:"):
            title = user_text.split(":", 1)[1].strip()
            yield ProviderEvent(
                "action",
                {
                    "action_type": "sample.records.create",
                    "payload": {"title": title, "amount": 0, "occurred_at": date.today().isoformat()},
                    "plugin_id": "sample.records",
                },
            )
            text = "The sample plugin prepared an Action."
        else:
            suffix = f" I reviewed {len(attachments)} attachment(s)." if attachments else ""
            text = f"You said: **{user_text}**.{suffix}"

        yield ProviderEvent("reasoning_summary", {"text": "I used the current request and authorized Host context."})
        for chunk in chunk_text(text, 18):
            yield ProviderEvent("text", {"text": chunk})

    async def summarize(self, messages: list[Message]) -> str:
        lines: list[str] = []
        for message in messages:
            text = " ".join(part.text for part in message.content if part.text)
            lines.append(f"{message.role}: {text[:160]}")
        return "\n".join(lines)


class OpenAICompatibleProvider:
    name = "openai-compatible"
    reasoning_visibility = "none"

    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        *,
        host: HostContext,
        context: ContextView,
        user_text: str,
        attachments: list[Attachment],
        disclosure_level: DisclosureLevel,
    ) -> AsyncIterator[ProviderEvent]:
        yield ProviderEvent("status", {"stage": "generating"})
        if disclosure_level is DisclosureLevel.RAW_TRACE:
            yield ProviderEvent("trace_unavailable", {})

        payload = {
            "model": self.model,
            "stream": True,
            "messages": context.provider_messages() + [{"role": "user", "content": user_text}],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with (
            httpx.AsyncClient(timeout=60) as client,
            client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response,
        ):
            if response.status_code >= 400:
                raise ProviderError(f"Provider returned HTTP {response.status_code}")
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                content = json.loads(data)["choices"][0]["delta"].get("content")
                if content:
                    yield ProviderEvent("text", {"text": content})

    async def summarize(self, messages: list[Message]) -> str:
        text = "\n".join(
            f"{message.role}: {' '.join(part.text for part in message.content if part.text)}" for message in messages
        )
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": "Summarize these turns faithfully and concisely."},
                {"role": "user", "content": text},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise ProviderError(f"Provider returned HTTP {response.status_code}")
        return response.json()["choices"][0]["message"]["content"]


def chunk_text(text: str, size: int) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]
