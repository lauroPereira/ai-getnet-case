from __future__ import annotations

import hashlib
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.data.migrations import current_version, migrate

DEMO_KEY = "synthetic-demo-access-key-v040"
ADMIN_KEY = "synthetic-admin-access-key-v040"


def test_openapi_declares_bearer_on_protected_routes_and_preserves_legacy():
    from merchant_assistant.api.app import create_app
    from merchant_assistant.config import Settings

    schema = create_app(settings=Settings(_env_file=None)).openapi()
    assert schema["components"]["securitySchemes"]["SessionBearer"] == {"type": "http", "scheme": "bearer"}
    assert schema["paths"]["/v1/profiles"]["get"]["security"] == [{"SessionBearer": []}]
    assert "security" not in schema["paths"]["/v1/sessions"]["post"]
    assert "429" in schema["paths"]["/v1/router/compare"]["post"]["responses"]
    assert "/messages" in schema["paths"]


def test_revocation_followed_by_unauthenticated_request_has_a_complete_response(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, _, _ = offline()
    headers = {"Authorization": f"Bearer {login(client)}"}
    revoked = client.delete("/v1/sessions/current", headers=headers)
    assert revoked.status_code == 204 and revoked.content == b""
    response = client.get("/v1/profiles")
    assert response.status_code == 401
    assert len(response.content) == int(response.headers["content-length"])


def login(client: TestClient, key: str = DEMO_KEY) -> str:
    response = client.post("/v1/sessions", json={"access_key": key})
    assert response.status_code == 201
    return response.json()["access_token"]


def test_v1_authentication_is_closed_by_default_and_legacy_stays_public(settings, offline):
    client, _, _ = offline()
    assert client.post("/v1/sessions", json={"access_key": "anything"}).status_code == 401
    assert client.get("/v1/catalog/models").status_code == 401
    assert client.post("/messages", json={"message": "oi", "user_id": "cliente1988"}).status_code == 200


def test_session_digest_expiry_revocation_and_role_boundaries(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    client, orchestrator, _ = offline()

    raw_key = DEMO_KEY
    token = login(client, raw_key)
    assert raw_key not in token
    conn = sqlite3.connect(settings.db_path)
    session_digest = conn.execute("SELECT token_digest FROM api_sessions").fetchone()[0]
    assert session_digest == hashlib.sha256(token.encode()).hexdigest()
    assert token not in session_digest
    conn.close()

    demo_headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/v1/profiles", headers=demo_headers).status_code == 200
    assert (
        client.post("/v1/profiles/reference/publish", json={"expected_version": 1}, headers=demo_headers).status_code
        == 403
    )

    conn = sqlite3.connect(settings.db_path)
    conn.execute("UPDATE api_sessions SET expires_at='2000-01-01T00:00:00+00:00'")
    conn.commit()
    conn.close()
    assert client.get("/v1/profiles", headers=demo_headers).status_code == 401

    admin_token = login(client, ADMIN_KEY)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    assert (
        client.post("/v1/profiles/reference/publish", json={"expected_version": 1}, headers=admin_headers).status_code
        == 409
    )
    assert client.delete("/v1/sessions/current", headers=admin_headers).status_code == 204
    assert client.get("/v1/profiles", headers=admin_headers).status_code == 401


def test_profiles_are_versioned_and_published_versions_are_immutable(settings, offline):
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    client, _, _ = offline()
    headers = {"Authorization": f"Bearer {login(client, ADMIN_KEY)}"}
    profile = client.get("/v1/profiles", headers=headers).json()["profiles"]
    agents = next(item["agents"] for item in profile if item["profile_id"] == "reference")

    created = client.post(
        "/v1/profiles", headers=headers, json={"name": "Test draft", "agents": agents, "demo_allowed": True}
    )
    assert created.status_code == 201
    profile_id = created.json()["profile_id"]
    updated = client.put(
        f"/v1/profiles/{profile_id}/draft", headers=headers, json={"expected_version": 1, "agents": agents}
    )
    assert updated.status_code == 200 and updated.json()["version"] == 2
    published = client.post(f"/v1/profiles/{profile_id}/publish", headers=headers, json={"expected_version": 2})
    assert published.status_code == 200 and published.json()["state"] == "published"
    immutable = client.put(
        f"/v1/profiles/{profile_id}/draft", headers=headers, json={"expected_version": 2, "agents": agents}
    )
    assert immutable.status_code == 409


def test_output_token_parameter_is_catalogued_published_and_effective_in_snapshot(settings, offline):
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, _, llm = offline()
    admin_headers = {"Authorization": f"Bearer {login(client, ADMIN_KEY)}"}
    agents = next(
        item["agents"]
        for item in client.get("/v1/profiles", headers=admin_headers).json()["profiles"]
        if item["profile_id"] == "reference"
    )

    created = client.post(
        "/v1/profiles",
        headers=admin_headers,
        json={"name": "Bounded personality", "agents": agents, "demo_allowed": True},
    )
    assert created.status_code == 201
    profile_id = created.json()["profile_id"]
    invalid_agents = {name: dict(config, parameters=dict(config["parameters"])) for name, config in agents.items()}
    invalid_agents["personality"]["parameters"] = {"max_output_tokens": 601}
    invalid = client.put(
        f"/v1/profiles/{profile_id}/draft",
        headers=admin_headers,
        json={"expected_version": 1, "agents": invalid_agents},
    )
    assert invalid.status_code == 422
    draft = next(
        item
        for item in client.get("/v1/profiles", headers=admin_headers).json()["profiles"]
        if item["profile_id"] == profile_id
    )
    assert draft["version"] == 1 and draft["state"] == "draft"
    agents["personality"]["parameters"] = {"max_output_tokens": 128}
    updated = client.put(
        f"/v1/profiles/{profile_id}/draft",
        headers=admin_headers,
        json={"expected_version": 1, "agents": agents},
    )
    assert updated.status_code == 200 and updated.json()["version"] == 2
    assert updated.json()["agents"]["personality"]["parameters"] == {"max_output_tokens": 128}
    published = client.post(f"/v1/profiles/{profile_id}/publish", headers=admin_headers, json={"expected_version": 2})
    assert published.status_code == 200 and published.json()["state"] == "published"

    demo_headers = {"Authorization": f"Bearer {login(client)}"}
    response = client.post(
        "/v1/messages",
        headers=demo_headers,
        json={
            "message": "Hello, I need help.",
            "profile_id": profile_id,
            "profile_version": 2,
            "router_mechanism": "llm",
        },
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["profile_version"] == 2
    assert run["agents"]["personality"]["parameters"] == {"max_output_tokens": 128}
    assert run["effective_parameters_by_agent"]["personality"] == {"max_output_tokens": 128}
    personality_call = next(call for call in llm.calls if call.spec.agent == "personality")
    assert personality_call.spec.max_output_tokens == 128
    stored = client.get(f"/v1/runs/{response.json()['message']['request_id']}", headers=demo_headers)
    assert stored.status_code == 200
    assert stored.json()["effective_parameters_by_agent"]["personality"] == {"max_output_tokens": 128}


@pytest.mark.parametrize(
    ("agent", "parameters", "message"),
    [
        ("personality", {"temperature": 0}, "unsupported parameter"),
        ("personality", {"max_output_tokens": True}, "must be an integer"),
        ("personality", {"max_output_tokens": 15}, "between 16 and 600"),
        ("router", {"max_output_tokens": 301}, "between 16 and 300"),
        ("evaluation", {"max_output_tokens": 128}, "unavailable for agent evaluation"),
    ],
)
def test_profile_rejects_unknown_or_unsafe_output_token_parameters(settings, offline, agent, parameters, message):
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    client, _, llm = offline()
    headers = {"Authorization": f"Bearer {login(client, ADMIN_KEY)}"}
    agents = next(
        item["agents"]
        for item in client.get("/v1/profiles", headers=headers).json()["profiles"]
        if item["profile_id"] == "reference"
    )
    agents[agent]["parameters"] = parameters

    response = client.post("/v1/profiles", headers=headers, json={"name": "Rejected config", "agents": agents})

    assert response.status_code == 422
    assert message in response.json()["error"]["message"]
    assert llm.calls == []


def test_router_comparison_is_router_only_and_consumed_once(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, _, llm = offline()
    headers = {"Authorization": f"Bearer {login(client)}"}
    payload = {
        "message": "My card machine won't connect",
        "profile_id": "hybrid",
        "profile_version": 1,
        "selected_mechanism": "jev",
    }
    compared = client.post("/v1/router/compare", headers=headers, json=payload)
    assert compared.status_code == 201
    body = compared.json()
    assert body["execution_mode"] == "simulated"
    assert {call.spec.agent for call in llm.calls} == {"router"}
    assert len(llm.calls) == 2

    message_payload = {key: payload[key] for key in ("message", "profile_id", "profile_version")}
    message_payload |= {"router_mechanism": "jev", "comparison_id": body["comparison_id"]}
    handled = client.post("/v1/messages", headers=headers, json=message_payload)
    assert handled.status_code == 200
    result = handled.json()
    assert result["run"]["execution_mode"] == "simulated"
    assert result["run"]["models"]["router"] == "typesafe:jev-1.14.0"
    assert len([call for call in llm.calls if call.spec.agent == "router"]) == 2
    assert client.get(f"/v1/runs/{result['message']['request_id']}", headers=headers).status_code == 200

    repeated = client.post("/v1/messages", headers=headers, json=message_payload)
    assert repeated.status_code == 409


def test_comparison_and_reused_run_report_only_provider_applied_router_parameters(settings, offline):
    from types import SimpleNamespace

    from merchant_assistant.llm.jev import JEV_MODEL, JevRouter
    from merchant_assistant.llm.openai_llm import OpenAILLM

    class FakeResponses:
        def __init__(self):
            self.payloads = []

        def parse(self, *, input, text_format, **kwargs):
            self.payloads.append({"input": input, **kwargs})
            decision = text_format(
                route="support",
                language="en",
                topic="device",
                intents=[],
                safety="none",
                clarification_question=None,
                case_signal="none",
            )
            return SimpleNamespace(
                usage=SimpleNamespace(input_tokens=12, output_tokens=5, input_tokens_details=None),
                output=[],
                output_parsed=decision,
            )

    class FakeOpenAIClient:
        def __init__(self):
            self.responses = FakeResponses()

    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, orchestrator, scripted = offline()
    openai_client = FakeOpenAIClient()
    jev_payloads = []

    def factory(provider, model):
        if provider == "typesafe":
            return JevRouter(
                "synthetic-key",
                transport=lambda payload: (
                    jev_payloads.append(payload)
                    or {
                        "model": JEV_MODEL,
                        "answers": {
                            "route": {"choice": "support"},
                            "language": {"choice": "en"},
                            "topic": {"choice": "device"},
                            "safety": {"choice": "none"},
                            "case_signal": {"choice": "none"},
                        },
                        "usage": {"input_tokens": 12, "output_tokens": 5},
                    }
                ),
            )
        if provider == "deepseek":
            return OpenAILLM(openai_client, model)
        return scripted

    orchestrator.llm_factory = factory
    headers = {"Authorization": f"Bearer {login(client)}"}

    for selected_mechanism in ("jev", "llm"):
        payload = {
            "message": "My card machine won't connect",
            "profile_id": "hybrid",
            "profile_version": 1,
            "selected_mechanism": selected_mechanism,
        }
        compared = client.post("/v1/router/compare", headers=headers, json=payload)
        assert compared.status_code == 201
        body = compared.json()
        assert body["decisions"]["jev"]["effective_parameters"] == {}
        assert body["decisions"]["llm"]["effective_parameters"] == {"max_output_tokens": 300}
        assert all("max_output_tokens" not in item for item in jev_payloads)
        assert openai_client.responses.payloads[-1]["max_output_tokens"] == 300

        handled = client.post(
            "/v1/messages",
            headers=headers,
            json={
                "message": payload["message"],
                "profile_id": payload["profile_id"],
                "profile_version": payload["profile_version"],
                "router_mechanism": selected_mechanism,
                "comparison_id": body["comparison_id"],
            },
        )
        assert handled.status_code == 200
        expected = {"max_output_tokens": 300} if selected_mechanism == "llm" else {}
        request_id = handled.json()["message"]["request_id"]
        run = client.get(f"/v1/runs/{request_id}", headers=headers)
        assert run.status_code == 200
        assert run.json()["effective_parameters_by_agent"].get("router", {}) == expected

    assert len(jev_payloads) == 2
    assert len(openai_client.responses.payloads) == 2


@pytest.mark.parametrize(
    ("scope", "stage", "request_limit", "installation_limit", "expected_code"),
    [
        ("request", "first", 0.03, 1.0, "request_budget_exceeded"),
        ("installation", "first", 1.0, 0.03, "installation_budget_exceeded"),
        ("request", "second", 0.065, 1.0, "request_budget_exceeded"),
        ("installation", "second", 1.0, 0.065, "installation_budget_exceeded"),
    ],
)
def test_router_comparison_budget_rejection_is_explicit_and_preserves_prior_cost(
    settings, offline, monkeypatch, scope, stage, request_limit, installation_limit, expected_code
):
    from merchant_assistant.llm import pricing

    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    settings.max_request_cost_usd = request_limit
    settings.budget_limit_usd = installation_limit
    monkeypatch.setattr(pricing, "estimate", lambda *args, **kwargs: 0.04)
    monkeypatch.setattr(pricing, "cost", lambda *args, **kwargs: 0.03)
    client, orchestrator, llm = offline()
    headers = {"Authorization": f"Bearer {login(client)}"}
    payload = {
        "message": "My card machine won't connect",
        "profile_id": "hybrid",
        "profile_version": 1,
        "selected_mechanism": "jev",
    }

    response = client.post("/v1/router/compare", headers=headers, json=payload)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["request_id"]
    assert "no incomplete comparison was saved" in response.json()["error"]["message"]
    assert len(llm.calls) == (1 if stage == "second" else 0)

    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM router_comparisons").fetchone()[0] == 0
    conn.close()

    budget = orchestrator.budget
    if stage == "first":
        assert budget.spent() == 0
        assert budget.remaining() == installation_limit
    else:
        assert budget.spent() == pytest.approx(0.03)
        assert budget.remaining() == pytest.approx(installation_limit - 0.03)
        ledger = sqlite3.connect(settings.runtime_path / "budget.sqlite3")
        rows = ledger.execute("SELECT status, reserved_usd, actual_usd FROM ledger ORDER BY id").fetchall()
        ledger.close()
        assert rows == [("settled", 0.04, 0.03)]


def test_catalog_contains_only_priced_verified_models(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, _, _ = offline()
    headers = {"Authorization": f"Bearer {login(client)}"}
    response = client.get("/v1/catalog/models", headers=headers)
    assert response.status_code == 200
    models = {item["model"] for item in response.json()["models"]}
    assert models == {"gpt-6-luna", "deepseek-flash", "jev-1.14.0"}


def test_catalog_publishes_only_documented_output_parameter_compatibility(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, _, _ = offline()
    headers = {"Authorization": f"Bearer {login(client)}"}
    response = client.get("/v1/catalog/models", headers=headers)
    assert response.status_code == 200
    models = {item["provider"]: item for item in response.json()["models"]}
    openai_parameter = models["openai"]["parameters"]["max_output_tokens"]
    deepseek_parameter = models["deepseek"]["parameters"]["max_output_tokens"]
    assert openai_parameter["minimum"] == 16
    assert openai_parameter["maximum_by_agent"]["personality"] == 600
    assert "evaluation" not in openai_parameter["maximum_by_agent"]
    assert deepseek_parameter["maximum_by_agent"] == {
        "router": 300,
        "support": 1200,
        "escalation": 400,
        "personality": 600,
    }
    assert models["typesafe"]["parameters"] == {}
    assert openai_parameter["documentation_url"].startswith("https://developers.openai.com/")


def test_migration_0006_round_trip_preserves_legacy_synthetic_records(settings):
    from merchant_assistant.data.clock import FixedClock
    from merchant_assistant.data.db import connect
    from merchant_assistant.data.seed import seed

    conn = connect(settings.db_path)
    assert migrate(conn, 6) == ["down 0007_kb_versions"]
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    before = conn.execute("SELECT customer_id, display_name FROM customers ORDER BY customer_id").fetchall()
    assert current_version(conn) == 6
    assert migrate(conn, 5) == ["down 0006_profiles_api"]
    assert conn.execute("SELECT customer_id, display_name FROM customers ORDER BY customer_id").fetchall() == before
    assert migrate(conn, 6) == ["up 0006_profiles_api"]
    assert current_version(conn) == 6
    assert migrate(conn, 7) == ["up 0007_kb_versions"]
    assert current_version(conn) == 7
    conn.close()


def test_kb_draft_build_test_activate_and_rollback_stay_isolated(settings, offline):
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, orchestrator, _ = offline()
    admin = {"Authorization": f"Bearer {login(client, ADMIN_KEY)}"}
    demo = {"Authorization": f"Bearer {login(client, DEMO_KEY)}"}

    docs = client.get("/v1/kb/documents", headers=admin).json()["documents"]
    fictional = next(item for item in docs if item["source_kind"] == "simulated_internal")
    official = next(item for item in docs if item["source_kind"] == "public_official")
    assert client.get(f"/v1/kb/documents/{official['document_id']}", headers=demo).status_code == 200
    assert (
        client.put(
            f"/v1/kb/drafts/{official['document_id']}",
            headers=admin,
            json={"content": "attempt", "expected_revision": 0},
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/v1/kb/drafts/{fictional['document_id']}",
            headers=demo,
            json={"content": "attempt", "expected_revision": 0},
        ).status_code
        == 403
    )

    original = client.get(f"/v1/kb/documents/{fictional['document_id']}", headers=admin).json()["content"]
    edited = original + "\n\n## Synthetic note\nThis is a fictional operational note for the demo."
    saved = client.put(
        f"/v1/kb/drafts/{fictional['document_id']}", headers=admin, json={"content": edited, "expected_revision": 0}
    )
    assert saved.status_code == 200 and saved.json()["revision"] == 1
    assert client.get(f"/v1/kb/drafts/{fictional['document_id']}/diff", headers=admin).json()["diff"]
    assert (
        client.put(
            f"/v1/kb/drafts/{fictional['document_id']}", headers=admin, json={"content": edited, "expected_revision": 0}
        ).status_code
        == 409
    )

    estimated = client.post(
        "/v1/kb/versions/estimate", headers=admin, json={"revisions": {fictional["document_id"]: 1}}
    )
    assert estimated.status_code == 200
    estimate = estimated.json()
    before = orchestrator.knowledge_base.capture_active()
    built = client.post(
        "/v1/kb/versions",
        headers=admin,
        json={
            "revisions": {fictional["document_id"]: 1},
            "expected_active_version_id": estimate["active_version_id"],
            "expected_digest": estimate["digest"],
            "confirmed": True,
            "max_cost_usd": 0.0,
        },
    )
    assert built.status_code == 201 and built.json()["state"] == "testing"
    assert orchestrator.knowledge_base.capture_active()[1] == before[1]
    assert (
        client.post(
            f"/v1/kb/versions/{built.json()['version_id']}/activate",
            headers=demo,
            json={"expected_active_version_id": before[1], "confirmed": True},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/kb/versions/{built.json()['version_id']}/test",
            headers=admin,
            json={"confirmed": False, "max_cost_usd": 0.0},
        ).status_code
        == 422
    )
    tested = client.post(
        f"/v1/kb/versions/{built.json()['version_id']}/test",
        headers=admin,
        json={"confirmed": True, "max_cost_usd": 0.0},
    )
    assert tested.status_code == 200 and tested.json()["passed"]
    activated = client.post(
        f"/v1/kb/versions/{built.json()['version_id']}/activate",
        headers=admin,
        json={"expected_active_version_id": before[1], "confirmed": True},
    )
    assert activated.status_code == 200
    captured, captured_version = orchestrator.knowledge_base.capture_active()
    assert captured_version == built.json()["version_id"]
    assert captured.collection != before[0].collection
    from merchant_assistant.api.schemas import MessageRequest

    orchestrator.handle(
        MessageRequest(message="Olá, preciso de orientação.", user_id=settings.api_demo_customer_id),
        "req_kb_version_capture",
    )
    assert orchestrator.trace("req_kb_version_capture")["detail"]["knowledge_base_version_id"] == captured_version
    assert before[0].count() > 0
    stale_activate = client.post(
        f"/v1/kb/versions/{built.json()['version_id']}/activate",
        headers=admin,
        json={"expected_active_version_id": before[1], "confirmed": True},
    )
    assert stale_activate.status_code == 409
    rollback = client.post(
        f"/v1/kb/versions/{before[1]}/rollback",
        headers=admin,
        json={"expected_active_version_id": captured_version, "confirmed": True},
    )
    assert rollback.status_code == 200
    assert orchestrator.knowledge_base.capture_active()[1] == before[1]
