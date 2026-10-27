"""Application settings loaded from environment variables (and `.env` when present)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    demo_mode: bool = False
    timezone: str = "America/Sao_Paulo"
    log_level: str = "INFO"

    openai_api_key: SecretStr | None = None
    typesafe_api_key: SecretStr | None = None
    deepseek_api_key: SecretStr | None = None
    api_demo_access_key: SecretStr | None = None
    api_admin_access_key: SecretStr | None = None
    api_demo_customer_id: str = "cliente1988"

    agent_model: str = "gpt-6-luna"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    data_dir: Path = PROJECT_ROOT / "data"
    prompts_dir: Path = PROJECT_ROOT / "prompts"
    runtime_dir: Path | None = None

    qdrant_url: str | None = None
    qdrant_collection: str = "getnet_kb_v1"
    mocks_url: str = "http://mocks:8001"

    retrieval_top_k: int = 6
    retrieval_min_score: float = 0.30

    budget_limit_usd: float = 1.00
    max_request_cost_usd: float = 0.05
    max_model_calls: int = 8
    max_tool_calls: int = 8
    max_request_seconds: float = 90.0
    web_search_max_calls: int = 1

    user_id_pattern: str = Field(default=r"^[A-Za-z0-9_\-.]{1,64}$")

    @property
    def runtime_path(self) -> Path:
        return self.runtime_dir or (self.data_dir / "runtime")

    @property
    def db_path(self) -> Path:
        return self.runtime_path / "merchant.sqlite3"

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
