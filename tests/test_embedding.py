from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from framed_assistant import EmbeddedAssistant
from framed_assistant.host import ReferenceHostAdapter
from framed_assistant.integrations import REFERENCE_MANIFEST
from framed_assistant.providers import MockModelProvider


def test_mount_composes_lifespan_and_exposes_only_essentials(tmp_path) -> None:
    lifecycle: list[str] = []

    @asynccontextmanager
    async def host_lifespan(_app: FastAPI):
        lifecycle.append("started")
        yield
        lifecycle.append("stopped")

    app = FastAPI(lifespan=host_lifespan)
    assistant = EmbeddedAssistant.create(
        data_dir=tmp_path,
        conversation_mode="single",
        manifest=REFERENCE_MANIFEST,
        provider_factory=lambda _store: MockModelProvider(),
        host_adapter_factory=lambda store: ReferenceHostAdapter(store, REFERENCE_MANIFEST),
    )
    assistant.mount(app)
    headers = {
        "X-Actor-ID": "actor-1",
        "X-Scope-Key": "scope-1",
        "X-Page-Context": '{"month":"2026-08"}',
    }

    with TestClient(app) as client:
        capabilities = client.get("/v1/assistant/capabilities", headers=headers)
        assert capabilities.status_code == 200
        names = {tool["name"] for tool in capabilities.json()["tools"]}
        assert "essentials.calculate" in names
        assert "host.records.list" not in names

        memory = client.post(
            "/v1/assistant/memory",
            headers=headers,
            json={"scope": "user", "content": "Keep this preference"},
        )
        deleted = client.delete(f"/v1/assistant/memory/{memory.json()['id']}", headers=headers)
        assert deleted.status_code == 204
        assert deleted.content == b""
        assert lifecycle == ["started"]

    assert lifecycle == ["started", "stopped"]
