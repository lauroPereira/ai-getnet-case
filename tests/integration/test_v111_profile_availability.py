"""v1.1.0 task 111 (D3, CA-78, RF-132): `GET /v1/profiles` says which profiles and which Router engines this backend
can run, from the provider keys it has configured, without returning any key value. Scripted model, no network, no
cost: every key below is a synthetic value and no model client reaches a provider."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from merchant_assistant.api.identity import Principal
from merchant_assistant.config import Settings
from merchant_assistant.main import model_factory
from merchant_assistant.profiles import missing_providers
from merchant_assistant.testing import key_token, merchant_headers, token_headers

OPENAI_KEY = "synthetic-openai-key-v111"
DEEPSEEK_KEY = "synthetic-deepseek-key-v111"
TYPESAFE_KEY = "synthetic-typesafe-key-v111"
DEMO_KEY = "synthetic-demo-access-key-v111"
KEYS = {"openai_api_key": OPENAI_KEY, "deepseek_api_key": DEEPSEEK_KEY, "typesafe_api_key": TYPESAFE_KEY}


def configure(settings, **keys):
    """Sets the given provider keys (a value, an empty string or None) on the app's settings."""
    for field, value in keys.items():
        setattr(settings, field, None if value is None else SecretStr(value))


def listing(client, headers=None):
    response = client.get("/v1/profiles", headers=headers or merchant_headers(client))
    assert response.status_code == 200, response.text
    for value in KEYS.values():  # no key value, whatever the configuration
        assert value not in response.text
    return response.json()


def by_id(body):
    return {item["profile_id"]: (item["available"], item["missing_providers"]) for item in body["profiles"]}


def test_only_the_openai_key_leaves_the_deepseek_profiles_and_jev_unavailable(offline, settings):
    configure(settings, openai_api_key=OPENAI_KEY, deepseek_api_key=None, typesafe_api_key=None)
    client, _, _ = offline()
    body = listing(client)
    assert by_id(body) == {
        "adjusted": (False, ["deepseek"]),
        "hybrid": (False, ["deepseek"]),
        "reference": (True, []),
    }
    assert body["router_mechanisms"] == {"llm": True, "jev": False}


def test_with_every_key_everything_is_available_and_no_value_is_returned(offline, settings):
    configure(settings, **KEYS)
    client, _, _ = offline()
    body = listing(client)
    assert by_id(body) == {"adjusted": (True, []), "hybrid": (True, []), "reference": (True, [])}
    assert body["router_mechanisms"] == {"llm": True, "jev": True}
    # the fields before v1.1.0 are unchanged
    reference = next(item for item in body["profiles"] if item["profile_id"] == "reference")
    assert set(reference) == {
        "profile_id",
        "name",
        "version",
        "state",
        "agents",
        "digest",
        "demo_allowed",
        "available",
        "missing_providers",
    }


def test_each_key_alone(offline, settings):
    configure(settings, openai_api_key=OPENAI_KEY, deepseek_api_key=DEEPSEEK_KEY, typesafe_api_key=None)
    client, _, _ = offline()
    body = listing(client)
    assert all(available for available, _ in by_id(body).values())
    assert body["router_mechanisms"]["jev"] is False

    configure(settings, deepseek_api_key=None, typesafe_api_key=TYPESAFE_KEY)
    body = listing(client)
    assert by_id(body)["hybrid"] == (False, ["deepseek"])
    assert body["router_mechanisms"]["jev"] is True


def test_an_empty_key_counts_as_missing(offline, settings):
    configure(settings, openai_api_key="", deepseek_api_key="", typesafe_api_key="")
    client, _, _ = offline()
    body = listing(client)
    assert by_id(body) == {
        "adjusted": (False, ["deepseek", "openai"]),
        "hybrid": (False, ["deepseek", "openai"]),
        "reference": (False, ["openai"]),
    }
    assert body["router_mechanisms"] == {"llm": True, "jev": False}


def test_demo_and_admin_see_the_same_fields_and_admin_drafts_have_them(offline, settings):
    configure(settings, openai_api_key=OPENAI_KEY, deepseek_api_key=None, typesafe_api_key=None)
    settings.api_demo_password = SecretStr(DEMO_KEY)
    client, _, _ = offline()
    demo = listing(client, {"Authorization": f"Bearer {key_token(client, DEMO_KEY)}"})
    assert by_id(demo)["hybrid"] == (False, ["deepseek"])
    assert demo["router_mechanisms"] == {"llm": True, "jev": False}

    admin = token_headers(client, Principal.of("admin", "default"))
    agents = next(item["agents"] for item in demo["profiles"] if item["profile_id"] == "adjusted")
    created = client.post(
        "/v1/profiles", headers=admin, json={"name": "Rascunho", "agents": agents, "demo_allowed": False}
    )
    assert created.status_code == 201, created.text
    drafts = [item for item in listing(client, admin)["profiles"] if item["state"] == "draft"]
    assert [(item["available"], item["missing_providers"]) for item in drafts] == [(False, ["deepseek"])]


def test_an_unavailable_choice_sent_anyway_is_still_refused(offline, settings):
    """The interface does not send it; the API keeps refusing it with `503 provider_unavailable` (D3) before any
    model client is built: no key is configured, so nothing can reach a provider."""
    configure(settings, openai_api_key=None, deepseek_api_key=None, typesafe_api_key=None)
    client, orchestrator, _ = offline()
    orchestrator.llm_factory = model_factory(settings)  # the real factory: no scripted model for profile agents
    headers = merchant_headers(client)
    for profile_id, mechanism in (("hybrid", "llm"), ("reference", "jev")):
        response = client.post(
            "/v1/messages",
            headers=headers,
            json={
                "message": "Quando recebo minhas vendas?",
                "profile_id": profile_id,
                "profile_version": 1,
                "router_mechanism": mechanism,
            },
        )
        assert response.status_code == 503, response.text
        assert response.json()["error"]["code"] == "provider_unavailable"


def test_openapi_documents_the_fields_with_an_example():
    from merchant_assistant.api.app import create_app

    operation = create_app(settings=Settings(_env_file=None)).openapi()["paths"]["/v1/profiles"]["get"]
    example = operation["responses"]["200"]["content"]["application/json"]["example"]
    assert example["router_mechanisms"] == {"llm": True, "jev": False}
    assert {"available", "missing_providers"} <= set(example["profiles"][0])
    assert "TYPESAFE_API_KEY" in operation["description"]


def test_missing_providers_ignores_the_unused_evaluation_field():
    agents = {
        "router": {"provider": "openai"},
        "support": {"provider": "deepseek"},
        "evaluation": {"provider": "anthropic"},
    }
    assert missing_providers(agents, lambda provider: provider == "openai") == ["deepseek"]
    assert missing_providers(agents, lambda provider: True) == []


@pytest.mark.parametrize(
    ("provider", "model", "field", "message"),
    [
        ("deepseek", "deepseek-flash", "deepseek_api_key", "DEEPSEEK_API_KEY"),
        ("typesafe", "jev-1.14.0", "typesafe_api_key", "TYPESAFE_API_KEY"),
        ("openai", "gpt-6-luna", "openai_api_key", "OPENAI_API_KEY"),
        ("anthropic", "claude-opus-5-5", "anthropic_api_key", "ANTHROPIC_API_KEY"),
    ],
)
def test_the_model_clients_follow_the_same_key_rule(provider, model, field, message):
    """What `GET /v1/profiles` reports is what the model factory builds: no key or an empty key is refused."""
    for value in (None, ""):
        settings = Settings(_env_file=None, **{field: None if value is None else SecretStr(value)})
        assert settings.has_provider_key(provider) is False
        with pytest.raises(RuntimeError, match=message):
            model_factory(settings)(provider, model)
    assert Settings(_env_file=None, **{field: SecretStr("synthetic-key")}).has_provider_key(provider) is True
    assert Settings(_env_file=None).has_provider_key("unknown") is False
