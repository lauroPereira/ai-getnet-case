"""Application settings loaded from environment variables (and `.env` when present)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
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
    auth_attempts_per_minute: int = Field(default=10, ge=1, le=1000)  # D19: per account and address on /v1/auth/token
    auth_attempts_per_ip_per_minute: int = Field(default=30, ge=1, le=10000)  # D19: per address, across accounts
    # v0.7.0 webhooks (task 66; spec "Contrato entre os times / Webhooks", D11): one secret per direction. An empty
    # URL sends nothing; an empty ASSISTANT_WEBHOOK_SECRET refuses every ticketing event (503).
    ticketing_webhook_url: str | None = None  # assistant -> ticketing: handoff.created, conversation.replied, closed
    ticketing_webhook_secret: SecretStr | None = None
    conversation_webhook_url: str | None = None  # assistant -> merchant: conversation.replied
    conversation_webhook_secret: SecretStr | None = None
    assistant_webhook_secret: SecretStr | None = None  # ticketing -> assistant: ticket.assigned, action, solved
    webhook_max_attempts: int = Field(default=3, ge=1, le=10)
    webhook_retry_waits_s: str = "1,2"  # waits between attempts, in seconds
    webhook_timeout_s: float = Field(default=3.0, gt=0, le=60)

    agent_model: str = "gpt-6-luna"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    data_dir: Path = PROJECT_ROOT / "data"
    prompts_dir: Path = PROJECT_ROOT / "prompts"
    runtime_dir: Path | None = None
    checkpoints_path: Path | None = None  # v0.7.0: graph checkpoints of handed-off cases (default: runtime dir)

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
    # v0.8.0 (D11): the evaluator is not the agent. The campaign judge refuses an evaluator equal to AGENT_MODEL or one
    # without its provider key; the on-demand evaluation of /v1 uses the same settings.
    evaluator_provider: str = "deepseek"
    evaluator_model: str = "deepseek-flash"

    user_id_pattern: str = Field(default=r"^[A-Za-z0-9_\-.]{1,64}$")

    @field_validator(
        "runtime_dir",
        "checkpoints_path",
        "jwt_private_key_path",
        "jwt_jwks_url",
        "ticketing_webhook_url",
        "conversation_webhook_url",
        mode="before",
    )
    @classmethod
    def _empty_is_unset(cls, value):
        """`KEY=` in .env (as in .env.example) means "not set": never Path(".") or an empty URL."""
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def webhook_waits(self) -> tuple[float, ...]:
        return tuple(float(w) for w in self.webhook_retry_waits_s.split(",") if w.strip()) or (0.0,)

    @property
    def runtime_path(self) -> Path:
        return self.runtime_dir or (self.data_dir / "runtime")

    @property
    def checkpoint_db_path(self) -> Path:
        return self.checkpoints_path or (self.runtime_path / "checkpoints.sqlite3")

    @property
    def db_path(self) -> Path:
        return self.runtime_path / "merchant.sqlite3"

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
