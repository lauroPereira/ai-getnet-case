from __future__ import annotations

import pytest

from merchant_assistant.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Settings isolated from the developer's .env: no keys, temporary runtime directory."""
    return Settings(
        _env_file=None,
        openai_api_key=None,
        runtime_dir=tmp_path / "runtime",
        demo_mode=True,
        budget_limit_usd=1.0,
    )
