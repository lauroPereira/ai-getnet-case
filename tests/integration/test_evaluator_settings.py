"""v0.8.0 task 70, round 2 (P2-01): the /v1 on-demand evaluator and the campaign judge have separate settings.

An installation with only OPENAI_API_KEY (as the README asks) estimates and confirms an on-demand evaluation through
the real model factory; the DeepSeek judge of the campaign is not required for it. The provider client is simulated:
no network and no paid call."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

import merchant_assistant.main as main
from merchant_assistant.testing import key_token

DEMO_KEY = "synthetic-demo-access-key-t70"


class FakeOpenAI:
    """Stands for the OpenAI client: `responses.parse` returns a valid three-criteria judgement and counts the calls."""

    def __init__(self) -> None:
        self.models: list[str] = []
        self.responses = SimpleNamespace(parse=self.parse)

    def parse(self, *, input, text_format, model, **kwargs):
        self.models.append(model)
        parsed = text_format(answers_question=4, clarity_and_tone=5, honesty=5, comment="Synthetic judgement.")
        usage = SimpleNamespace(
            input_tokens=500, output_tokens=40, input_tokens_details=SimpleNamespace(cached_tokens=0)
        )
        return SimpleNamespace(output_parsed=parsed, usage=usage, output=[], status="completed")


@pytest.fixture
def only_openai(settings, offline, monkeypatch):
    """An installation with only OPENAI_API_KEY, the real model factory for the evaluator and a simulated client."""
    settings.api_demo_password = SecretStr(DEMO_KEY)
    settings.openai_api_key = SecretStr("synthetic-openai-key")
    settings.deepseek_api_key = None
    client, orchestrator, _ = offline()
    headers = {"Authorization": f"Bearer {key_token(client, DEMO_KEY)}"}
    sent = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "message": "Olá, preciso de ajuda.",
            "profile_id": "reference",
            "profile_version": 1,
            "router_mechanism": "llm",
        },
    )
    assert sent.status_code == 200, sent.text
    fake = FakeOpenAI()
    monkeypatch.setattr(main, "openai_client", lambda _settings: fake)
    orchestrator.llm_factory = main.model_factory(
        settings
    )  # the attendance is done; the evaluator uses the real factory
    return client, headers, sent.json()["message"]["request_id"], fake


def estimate_and_confirm(client, headers, request_id):
    estimate = client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=headers)
    assert estimate.status_code == 200, estimate.text
    body = estimate.json()
    payload = {
        "confirmed": True,
        "max_cost_usd": body["estimated_cost_usd"],
        "expected_estimate_digest": body["estimate_digest"],
    }
    return body, client.post(f"/v1/runs/{request_id}/evaluations", headers=headers, json=payload)


def test_an_installation_with_only_an_openai_key_estimates_and_confirms_the_on_demand_evaluation(only_openai):
    client, headers, request_id, fake = only_openai
    estimate, confirmed = estimate_and_confirm(client, headers, request_id)
    assert estimate["evaluator"]["provider"] == "openai" and estimate["evaluator"]["model"] == "gpt-6-luna"
    assert estimate["rubric_version"] == "2"
    assert confirmed.status_code == 201, confirmed.text
    evaluation = confirmed.json()
    assert evaluation["state"] == "completed" and evaluation["evaluator"]["model_used"] == "gpt-6-luna"
    assert set(evaluation["result"]) == {"answers_question", "clarity_and_tone", "honesty", "comment"}
    assert fake.models == ["gpt-6-luna"]  # one simulated call, through the real factory


def test_the_old_failure_is_real_without_the_key_of_the_provider_in_the_evaluator_settings(only_openai, settings):
    """The same installation with a DeepSeek evaluator fails safe: this is what the v0.8.0 default used to cause."""
    client, headers, request_id, fake = only_openai
    settings.evaluator_provider, settings.evaluator_model = "deepseek", "deepseek-flash"
    _, confirmed = estimate_and_confirm(client, headers, request_id)
    assert confirmed.status_code == 503 and confirmed.json()["error"]["code"] == "evaluator_unavailable"
    assert fake.models == []
