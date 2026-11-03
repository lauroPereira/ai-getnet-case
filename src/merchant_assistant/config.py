"""Application settings loaded from environment variables (and `.env` when present)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from merchant_assistant.orchestration.budget import ABSOLUTE_BUDGET_LIMIT_USD

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
    api_demo_customer_id: str = "cliente1988"
    # v0.7.0 identity (ADR 0017, spec v0.7.0 D1, D2, D5, D12): JWT issued by the assistant.
    jwt_issuer: str = "http://127.0.0.1:8000"
    jwt_private_key_path: Path | None = None  # default: <runtime>/jwt/signing_key.pem, created on first use
    jwt_jwks_url: str | None = None  # external issuer: verify tokens with its JWKS instead of the local key
    demo_user_passwords: SecretStr | None = None  # `<username>:<password>,...` for the synthetic demo users
    ticketing_client_secret: SecretStr | None = None  # client `ticketing-demo` (client credentials)
    api_demo_password: SecretStr | None = None  # user `demo`; empty disables it
    api_admin_password: SecretStr | None = None  # user `admin`; empty disables it
    password_hash_iterations: int = Field(default=600_000, ge=1_000)
    merchant_assistant_token: SecretStr | None = None  # merchant token for the MCP server and local commands
    rate_limit_per_minute: int = Field(default=30, ge=1, le=10000)

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

    budget_limit_usd: float = Field(default=1.00, ge=0, le=ABSOLUTE_BUDGET_LIMIT_USD, allow_inf_nan=False)
    max_request_cost_usd: float = 0.05
    max_model_calls: int = 8
    max_tool_calls: int = 8
    max_request_seconds: float = 90.0
    web_search_max_calls: int = 1

    # v0.6.0 demonstration controls
    demo_session_message_limit: int = Field(default=20, ge=1, le=1000)
    evaluator_provider: str = "openai"
    evaluator_model: str = "gpt-6-luna"

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
