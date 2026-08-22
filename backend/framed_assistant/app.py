from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .actions import ActionService
from .api import router
from .attachments import AttachmentService
from .config import Settings
from .context import ContextCompiler
from .database import Database
from .errors import ConflictError, NotFoundError, ValidationError
from .host import ReferenceHostAdapter
from .integrations import REFERENCE_MANIFEST
from .policy import PolicyEngine
from .privacy import PrivacyService
from .providers import MockModelProvider, OpenAICompatibleProvider
from .runtime import AssistantRuntime
from .store import Store
from .tools import create_tool_registry

settings = Settings.from_environment()
if settings.conversation_mode not in {"single", "multiple"}:
    raise ValueError("FRAMED_CONVERSATION_MODE must be single or multiple")
database = Database(settings.data_dir / "framed-assistant.sqlite3")
store = Store(database, settings.data_dir / "attachments")
host_adapter = ReferenceHostAdapter(store, REFERENCE_MANIFEST)


def create_provider():
    if settings.provider == "mock":
        return MockModelProvider()
    if settings.provider == "openai-compatible":
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI-compatible provider")
        return OpenAICompatibleProvider(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    raise ValueError(f"Unknown provider: {settings.provider}")


provider = create_provider()
tools = create_tool_registry(store)
policy = PolicyEngine(REFERENCE_MANIFEST)
action_service = ActionService(store, policy, host_adapter)
context_compiler = ContextCompiler(store, host_adapter, provider)
assistant_runtime = AssistantRuntime(
    store=store,
    provider=provider,
    context_compiler=context_compiler,
    tools=tools,
    actions=action_service,
    host_adapter=host_adapter,
)
attachment_service = AttachmentService(store)
privacy_service = PrivacyService(store)


@asynccontextmanager
async def lifespan(application: FastAPI):
    store.initialize()
    yield


app = FastAPI(title="Framed Assistant", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.state.store = store
app.state.runtime = assistant_runtime
app.state.attachments = attachment_service
app.state.actions = action_service
app.state.privacy = privacy_service
app.state.manifest = REFERENCE_MANIFEST
app.state.tools = tools
app.state.settings = settings


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def error_payload(code: str, message: str, retryable: bool) -> dict[str, object]:
    return {
        "code": code,
        "message": message,
        "retryable": retryable,
        "correlation_id": f"error_{uuid4().hex}",
    }


@app.exception_handler(NotFoundError)
def not_found(_request: Request, error: NotFoundError) -> JSONResponse:
    return JSONResponse(error_payload("not_found", str(error), False), status_code=404)


@app.exception_handler(ConflictError)
def conflict(_request: Request, error: ConflictError) -> JSONResponse:
    return JSONResponse(error_payload("conflict", str(error), True), status_code=409)


@app.exception_handler(ValidationError)
def invalid(_request: Request, error: ValidationError) -> JSONResponse:
    return JSONResponse(error_payload("validation", str(error), False), status_code=422)
