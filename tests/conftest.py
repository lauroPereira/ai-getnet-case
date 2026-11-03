from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api.app import create_app
from merchant_assistant.config import Settings
from merchant_assistant.testing import (
    TEST_TICKETING_SECRET,
    TEST_USER_PASSWORDS,
    offline_orchestrator,
    passwords_setting,
)


@pytest.fixture(scope="session")
def jwt_signing_key_path(tmp_path_factory):
    """One RSA key for the whole run (generated here, never versioned): issuing per test stays fast."""
    from merchant_assistant.api.identity import load_signing_key

    path = tmp_path_factory.mktemp("jwt") / "signing_key.pem"
    load_signing_key(path)
    return path


@pytest.fixture
def settings(tmp_path, jwt_signing_key_path) -> Settings:
    """Settings isolated from the developer's .env: no keys, temporary runtime directory."""
    return Settings(
        _env_file=None,
        openai_api_key=None,
        runtime_dir=tmp_path / "runtime",
        demo_mode=True,
        budget_limit_usd=1.0,
        qdrant_url=":memory:",
        retrieval_min_score=0.05,  # the offline hashing embedder produces lower similarities
        jwt_private_key_path=jwt_signing_key_path,
        demo_user_passwords=SecretStr(passwords_setting(TEST_USER_PASSWORDS)),
        ticketing_client_secret=SecretStr(TEST_TICKETING_SECRET),
        password_hash_iterations=1_000,  # the production default (600 000) is too slow for a test suite
    )


@pytest.fixture
def offline(settings):
    """Full system with the scripted model: returns (client, orchestrator, llm)."""

    def make(**kwargs):
        orchestrator, llm = offline_orchestrator(settings, **kwargs)
        return TestClient(create_app(orchestrator, settings)), orchestrator, llm

    return make
