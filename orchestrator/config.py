"""Runtime configuration loaded from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv optional at runtime
    pass


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
    model: str = os.environ.get("ATLAS_MODEL", "claude-sonnet-4-5")
    max_tokens: int = int(os.environ.get("ATLAS_MAX_TOKENS", "2048"))
    max_steps: int = int(os.environ.get("ATLAS_MAX_STEPS", "16"))
    token_budget: int = int(os.environ.get("ATLAS_TOKEN_BUDGET", "8000"))
    db_path: str = os.environ.get("ATLAS_DB_PATH", "data/warehouse.duckdb")
    sessions_path: str = os.environ.get("ATLAS_SESSIONS_DB", "data/sessions.db")
    persist_memory: bool = os.environ.get("ATLAS_PERSIST_MEMORY", "1") != "0"

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key)


CONFIG = Config()
