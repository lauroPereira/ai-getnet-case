"""Start a loopback-only v0.4.0 API with scripted models and isolated synthetic data."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

import uvicorn
from pydantic import SecretStr

from merchant_assistant.api.app import create_app
from merchant_assistant.config import Settings
from merchant_assistant.testing import offline_orchestrator

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".pytest_cache"


def build(runtime_dir: Path):
    resolved = runtime_dir.resolve()
    if CACHE.resolve() not in resolved.parents:
        raise ValueError("runtime directory must be a new child of .pytest_cache")
    if resolved.exists():
        raise FileExistsError("runtime directory already exists; choose a new synthetic v0.4.0 path")
    settings = Settings(
        _env_file=None,
        app_env="test",
        demo_mode=False,
        openai_api_key=None,
        typesafe_api_key=None,
        deepseek_api_key=None,
        api_demo_access_key=SecretStr("v040-synthetic-demo-access-key"),
        api_admin_access_key=SecretStr("v040-synthetic-admin-access-key"),
        api_demo_customer_id="cliente1988",
        runtime_dir=resolved,
        qdrant_url=":memory:",
        budget_limit_usd=5.0,
        max_request_cost_usd=0.05,
    )
    orchestrator, _ = offline_orchestrator(settings)
    return create_app(orchestrator, settings)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runtime-dir", type=Path)
    args = parser.parse_args()
    runtime_dir = args.runtime_dir or CACHE / f"v040-http-{uuid.uuid4().hex[:12]}"
    app = build(runtime_dir)
    print(f"Synthetic /v1 server on http://127.0.0.1:{args.port}")
    print(f"Runtime: {runtime_dir.resolve()}")
    print("Demo/admin access keys are synthetic constants; no provider keys are configured.")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
