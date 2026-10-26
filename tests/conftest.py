from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from merchant_assistant.api.app import create_app
from merchant_assistant.config import Settings
from merchant_assistant.testing import offline_orchestrator


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Settings isolated from the developer's .env: no keys, temporary runtime directory."""
    return Settings(
        _env_file=None,
        openai_api_key=None,
        runtime_dir=tmp_path / "runtime",
        demo_mode=True,
        budget_limit_usd=1.0,
        qdrant_url=":memory:",
        retrieval_min_score=0.05,  # the offline hashing embedder produces lower similarities
    )


@pytest.fixture
def offline(settings):
    """Full system with the scripted model: returns (client, orchestrator, llm)."""

    def make(**kwargs):
        orchestrator, llm = offline_orchestrator(settings, **kwargs)
        return TestClient(create_app(orchestrator, settings)), orchestrator, llm

    return make
