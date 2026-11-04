"""Settings of the ticketing service, read from the environment variables of the contract."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ASSISTANT = "http://127.0.0.1:8000"


def _default_db_path(env: Mapping[str, str]) -> Path:
    runtime = env.get("RUNTIME_DIR")
    return Path(runtime) / "ticketing.sqlite3" if runtime else Path("data/runtime/ticketing.sqlite3")


@dataclass(frozen=True)
class TicketingSettings:
    db_path: Path
    assistant_url: str = DEFAULT_ASSISTANT
    assistant_issuer: str = DEFAULT_ASSISTANT
    assistant_jwks_url: str = f"{DEFAULT_ASSISTANT}/.well-known/jwks.json"
    inbound_secret: str = ""  # TICKETING_WEBHOOK_SECRET: assistant -> ticketing
    outbound_secret: str = ""  # ASSISTANT_WEBHOOK_SECRET: ticketing -> assistant
    client_id: str = "ticketing-demo"
    client_secret: str = ""
    audience: str = "ticketing"
    required_scope: str = "handoff:operate"
    signature_tolerance_s: int = 300
    clock_skew_s: int = 30
    max_attempts: int = 3
    retry_waits_s: tuple[float, ...] = (1.0, 2.0)
    request_timeout_s: float = 3.0
    jwks_min_refresh_s: float = 5.0
    outbox_poll_s: float = 1.0  # 0 disables the background retry loop

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> TicketingSettings:
        env = os.environ if env is None else env
        issuer = env.get("ASSISTANT_ISSUER") or DEFAULT_ASSISTANT
        waits = env.get("TICKETING_WEBHOOK_RETRY_WAITS_S", "1,2")
        return cls(
            db_path=Path(env["TICKETING_DB_PATH"]) if env.get("TICKETING_DB_PATH") else _default_db_path(env),
            assistant_url=(env.get("ASSISTANT_URL") or DEFAULT_ASSISTANT).rstrip("/"),
            assistant_issuer=issuer,
            assistant_jwks_url=env.get("ASSISTANT_JWKS_URL") or f"{issuer.rstrip('/')}/.well-known/jwks.json",
            inbound_secret=env.get("TICKETING_WEBHOOK_SECRET", ""),
            outbound_secret=env.get("ASSISTANT_WEBHOOK_SECRET", ""),
            client_id=env.get("TICKETING_CLIENT_ID") or "ticketing-demo",
            client_secret=env.get("TICKETING_CLIENT_SECRET", ""),
            max_attempts=int(env.get("TICKETING_WEBHOOK_MAX_ATTEMPTS", "3")),
            retry_waits_s=tuple(float(w) for w in waits.split(",") if w.strip()),
            request_timeout_s=float(env.get("TICKETING_WEBHOOK_TIMEOUT_S", "3")),
            outbox_poll_s=float(env.get("TICKETING_OUTBOX_POLL_S", "1")),
        )
