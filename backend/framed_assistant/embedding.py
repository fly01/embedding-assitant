from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .actions import ActionService
from .api import router
from .attachments import AttachmentService
from .context import ContextCompiler
from .database import Database
from .errors import ConflictError, NotFoundError, ValidationError
from .host import HostAdapter, host_context
from .integrations import HostIntegrationManifest
from .models import HostContext, PluginState
from .policy import PolicyEngine
from .privacy import PrivacyService
from .providers import ModelProvider
from .runtime import AssistantRuntime
from .store import Store
from .tools import ToolRegistry, create_essentials_registry

ProviderFactory = Callable[[Store], ModelProvider]
HostAdapterFactory = Callable[[Store], HostAdapter]
ToolRegistryFactory = Callable[[Store], ToolRegistry]
HostContextDependency = Callable[..., HostContext]


def _default_tools(_store: Store) -> ToolRegistry:
    return create_essentials_registry()


@dataclass(frozen=True)
class EmbeddedSettings:
    conversation_mode: str


@dataclass
class EmbeddedAssistant:
    settings: EmbeddedSettings
    store: Store
    runtime: AssistantRuntime
    attachments: AttachmentService
    actions: ActionService
    privacy: PrivacyService
    manifest: HostIntegrationManifest
    tools: ToolRegistry
    plugins: tuple[PluginState, ...]

    @classmethod
    def create(
        cls,
        *,
        data_dir: Path,
        conversation_mode: str,
        manifest: HostIntegrationManifest,
        provider_factory: ProviderFactory,
        host_adapter_factory: HostAdapterFactory,
        tool_registry_factory: ToolRegistryFactory = _default_tools,
        plugins: Iterable[PluginState] = (),
    ) -> EmbeddedAssistant:
        if conversation_mode not in {"single", "multiple"}:
            raise ValueError("conversation_mode must be single or multiple")
        store = Store(Database(data_dir / "framed-assistant.sqlite3"), data_dir / "attachments")
        provider = provider_factory(store)
        host_adapter = host_adapter_factory(store)
        tools = tool_registry_factory(store)
        actions = ActionService(store, PolicyEngine(manifest), host_adapter)
        runtime = AssistantRuntime(
            store=store,
            provider=provider,
            context_compiler=ContextCompiler(store, host_adapter, provider),
            tools=tools,
            actions=actions,
            host_adapter=host_adapter,
        )
        return cls(
            settings=EmbeddedSettings(conversation_mode),
            store=store,
            runtime=runtime,
            attachments=AttachmentService(store),
            actions=actions,
            privacy=PrivacyService(store),
            manifest=manifest,
            tools=tools,
            plugins=tuple(plugins),
        )

    def initialize(self) -> None:
        self.store.initialize()
        for plugin in self.plugins:
            self.store.register_plugin(plugin)

    def mount(
        self,
        app: FastAPI,
        *,
        host_context_dependency: HostContextDependency = host_context,
    ) -> None:
        host_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(application: FastAPI):
            self.initialize()
            async with host_lifespan(application):
                yield

        app.state.framed_assistant = self
        app.dependency_overrides[host_context] = host_context_dependency
        app.include_router(router)
        app.router.lifespan_context = lifespan
        app.add_exception_handler(NotFoundError, _not_found)
        app.add_exception_handler(ConflictError, _conflict)
        app.add_exception_handler(ValidationError, _invalid)


def _error_payload(code: str, message: str, retryable: bool) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "retryable": retryable,
        "correlation_id": f"error_{uuid4().hex}",
    }


def _not_found(_request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(_error_payload("not_found", str(error), False), status_code=404)


def _conflict(_request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(_error_payload("conflict", str(error), True), status_code=409)


def _invalid(_request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(_error_payload("validation", str(error), False), status_code=422)
