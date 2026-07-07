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
    token_budget: int = int(os.environ.get("ATLAS_TOKEN_BUDGET", "8000"))
    db_path: str = os.environ.get("ATLAS_DB_PATH", "data/warehouse.duckdb")

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key)


CONFIG = Config()
