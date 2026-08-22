from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .embedding import EmbeddedAssistant
from .host import ReferenceHostAdapter
from .integrations import REFERENCE_MANIFEST, REFERENCE_PLUGIN
from .providers import MockModelProvider, OpenAICompatibleProvider
from .tools import create_tool_registry

settings = Settings.from_environment()
if settings.conversation_mode not in {"single", "multiple"}:
    raise ValueError("FRAMED_CONVERSATION_MODE must be single or multiple")


def create_provider(_store):
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


assistant = EmbeddedAssistant.create(
    data_dir=settings.data_dir,
    conversation_mode=settings.conversation_mode,
    manifest=REFERENCE_MANIFEST,
    provider_factory=create_provider,
    host_adapter_factory=lambda store: ReferenceHostAdapter(store, REFERENCE_MANIFEST),
    tool_registry_factory=create_tool_registry,
    plugins=[REFERENCE_PLUGIN],
)

app = FastAPI(title="Framed Assistant", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
assistant.mount(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
