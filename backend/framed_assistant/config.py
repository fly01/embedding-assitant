from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str
    data_dir: Path
    provider: str
    conversation_mode: str
    openai_base_url: str
    openai_api_key: str | None
    openai_model: str

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            environment=os.getenv("FRAMED_ENV", "development"),
            data_dir=Path(os.getenv("FRAMED_DATA_DIR", ".data/dev")),
            provider=os.getenv("FRAMED_PROVIDER", "mock"),
            conversation_mode=os.getenv("FRAMED_CONVERSATION_MODE", "multiple"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        )
