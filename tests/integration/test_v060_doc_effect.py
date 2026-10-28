"""v0.6.0 block D: editing the fictional devices document changes observable behaviour, and rollback restores it.

Expected difference (fixed before any edit, task 57): with V1 the device procedure only diagnoses connectivity; with
V2 the procedure requires `get_contract_snapshot` before offering Payment Link as an alternative, and the reply only
offers it when the product is in the contract facts. Zero cost: a programmed policy stands in for the models (it
follows whatever procedure the Knowledge step retrieved) and the hashing embedder replaces paid embeddings. It proves
the data path (document -> retrieved passage -> procedure -> tool -> facts -> reply, with the version in the trace);
real model behaviour is checked by the QA run described in docs/evidence/v060-qa-preparacao.md."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.llm.scripted import ToolPlan
from merchant_assistant.tools.registry import AGENT_TOOLS

ADMIN_KEY = "synthetic-admin-access-key-v060-d"
DOCUMENT = "demo:KB-DEMO-DEVICES-001"
MARKER = "get_contract_snapshot"
V2_TEXT = (PROJECT_ROOT / "data" / "scenarios" / "kb-demo-devices-v2.md").read_text(encoding="utf-8")


def programmed_policy(call):
    """Deterministic stand-in for the models: it applies the procedure text that retrieval actually returned."""
    context = call.spec.context
    if call.spec.agent == "knowledge" and context.get("mode") == "procedure":
        draft = default_handler(call)
        rule = next((p for p in context.get("passages", []) if MARKER in p["text"]), None)
        if rule:
            sentence = next(s for s in rule["text"].split(". ") if MARKER in s)
            draft["points"] = [*draft["points"], sentence.strip()]
            draft["used_passages"] = sorted({*draft["used_passages"], rule["n"]})
        return draft
    if call.spec.agent == "customer_support" and context.get("topic") == "device" and MARKER in context["procedure"]:

        def final(results):
            import json

            device = json.loads(results[0])["devices"][0]
            products = json.loads(results[1]).get("products", [])
            points = [f"{device['model']}: {device['status']}"]
            if "link_de_pagamento" in products:
                points.append("O Link de Pagamento consta no seu contrato e pode ser usado enquanto isso.")
            return {
                "points": points,
                "needs_selection": False,
                "missing": [],
                "escalate": False,
                "escalation_reason": None,
                "steps_given": [],
                "issue_verified_by_tool": False,
            }

        return ToolPlan([("get_device_status", {}), (MARKER, {})], final=final)
    return default_handler(call)


@pytest.fixture
def system(settings, offline):
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    client, orchestrator, _ = offline(handler=programmed_policy)
    response = client.post("/v1/sessions", json={"access_key": ADMIN_KEY})
    return client, orchestrator, {"Authorization": f"Bearer {response.json()['access_token']}"}


def ask(client, headers) -> dict:
    scenario = next(
        item
        for item in client.get("/v1/scenarios", headers=headers).json()["scenarios"]
        if item["scenario_id"] == "SC-DOC-EFFECT"
    )
    sent = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "message": scenario["message"],
            "scenario_id": "SC-DOC-EFFECT",
            "profile_id": "reference",
            "profile_version": 1,
            "router_mechanism": "llm",
        },
    )
    assert sent.status_code == 200, sent.json()
    body = sent.json()
    run = client.get(f"/v1/runs/{body['message']['request_id']}", headers=headers).json()
    return {"message": body["message"], "run": run}


def tools(result) -> list[str]:
    return [step["step"].removeprefix("tool:") for step in result["run"]["steps"] if step["step"].startswith("tool:")]


def retrieved_marker(result) -> bool:
    knowledge = next(step for step in result["run"]["steps"] if step["step"] == "knowledge")
    return any(MARKER in hit["excerpt"] for hit in knowledge["hits"])


def test_document_edit_changes_tool_use_and_rollback_restores_it(system):
    client, orchestrator, admin = system
    tools_before = dict(AGENT_TOOLS)

    v1 = ask(client, admin)
    assert v1["message"]["route"] == "knowledge_and_support"
    assert MARKER not in tools(v1) and "get_device_status" in tools(v1)  # the difference does not occur yet
    assert not retrieved_marker(v1)
    assert "Link de Pagamento consta" not in v1["message"]["answer"]
    assert v1["run"]["knowledge_base_version_id"] == "kb_initial"

    assert client.get(f"/v1/kb/documents/{DOCUMENT}", headers=admin).json()["source_kind"] == "simulated_internal"
    saved = client.put(f"/v1/kb/drafts/{DOCUMENT}", headers=admin, json={"content": V2_TEXT, "expected_revision": 0})
    assert saved.status_code == 200
    diff = client.get(f"/v1/kb/drafts/{DOCUMENT}/diff", headers=admin).json()["diff"]
    added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    assert removed == [] and any(MARKER in line for line in added)  # pure addition, no rule removed
    estimate = client.post("/v1/kb/versions/estimate", headers=admin, json={"revisions": {DOCUMENT: 1}}).json()
    built = client.post(
        "/v1/kb/versions",
        headers=admin,
        json={
            "revisions": {DOCUMENT: 1},
            "expected_active_version_id": "kb_initial",
            "expected_digest": estimate["digest"],
            "confirmed": True,
            "max_cost_usd": 0.0,
        },
    ).json()
    version_id = built["version_id"]
    assert client.post(
        f"/v1/kb/versions/{version_id}/test", headers=admin, json={"confirmed": True, "max_cost_usd": 0.0}
    ).json()["passed"]
    activated = client.post(
        f"/v1/kb/versions/{version_id}/activate",
        headers=admin,
        json={"expected_active_version_id": "kb_initial", "confirmed": True},
    )
    assert activated.status_code == 200

    v2 = ask(client, admin)
    assert v2["run"]["knowledge_base_version_id"] == version_id
    assert retrieved_marker(v2)  # the edited passage reached the Knowledge step
    assert tools(v2)[-2:] == ["get_device_status", MARKER]
    assert "Link de Pagamento consta" in v2["message"]["answer"]  # offered only because the contract lists it
    assert any(source["title"] == "Contracted products (your account)" for source in v2["run"]["sources"])

    restored = client.post(
        "/v1/kb/versions/kb_initial/rollback",
        headers=admin,
        json={"expected_active_version_id": version_id, "confirmed": True},
    )
    assert restored.status_code == 200
    v1_again = ask(client, admin)
    assert v1_again["run"]["knowledge_base_version_id"] == "kb_initial"
    assert MARKER not in tools(v1_again) and not retrieved_marker(v1_again)
    assert "Link de Pagamento consta" not in v1_again["message"]["answer"]

    runs = [v1["run"], v2["run"], v1_again["run"]]
    assert len({item["message"]["conversation_id"] for item in (v1, v2, v1_again)}) == 3  # independent
    for key in ("scenario_id", "profile_id", "profile_version", "profile_digest", "router_mechanism", "prompt_set"):
        assert len({str(run[key]) for run in runs}) == 1, key
    assert dict(AGENT_TOOLS) == tools_before  # the document never grants a tool


def test_v2_text_adds_no_deadline_amount_or_new_tool():
    import re

    from merchant_assistant.tools.registry import TOOLS

    added = V2_TEXT.split("## Alternativa de venda com a maquininha sem conexão", 1)[1].split("## Parada", 1)[0]
    assert not re.search(r"\d", added)  # no deadline, fee, amount or percentage
    named_tools = set(re.findall(r"\b(get_[a-z_]+|find_[a-z_]+|simulate_[a-z_]+|run_[a-z_]+)\b", added))
    assert named_tools == {MARKER} and MARKER in TOOLS and MARKER in AGENT_TOOLS["customer_support"]


def test_v2_does_not_offer_payment_link_when_the_contract_does_not_list_it(settings, system):
    """P3-09b: negative branch of the expected difference, for the synthetic merchant without link_de_pagamento."""
    client, orchestrator, admin = system
    settings.api_demo_customer_id = "cliente_demo_002"
    other = {
        "Authorization": f"Bearer {client.post('/v1/sessions', json={'access_key': ADMIN_KEY}).json()['access_token']}"
    }
    assert client.get("/v1/kb/documents", headers=other).status_code == 200  # registers the knowledge base
    saved = client.put(f"/v1/kb/drafts/{DOCUMENT}", headers=admin, json={"content": V2_TEXT, "expected_revision": 0})
    assert saved.status_code == 200
    estimate = client.post("/v1/kb/versions/estimate", headers=admin, json={"revisions": {DOCUMENT: 1}}).json()
    version_id = client.post(
        "/v1/kb/versions",
        headers=admin,
        json={
            "revisions": {DOCUMENT: 1},
            "expected_active_version_id": "kb_initial",
            "expected_digest": estimate["digest"],
            "confirmed": True,
            "max_cost_usd": 0.0,
        },
    ).json()["version_id"]
    client.post(f"/v1/kb/versions/{version_id}/test", headers=admin, json={"confirmed": True, "max_cost_usd": 0.0})
    client.post(
        f"/v1/kb/versions/{version_id}/activate",
        headers=admin,
        json={"expected_active_version_id": "kb_initial", "confirmed": True},
    )
    result = ask(client, other)
    assert result["run"]["knowledge_base_version_id"] == version_id and retrieved_marker(result)
    assert MARKER in tools(result)  # the contract is checked first ...
    assert "Link de Pagamento consta" not in result["message"]["answer"]  # ... and the alternative is not offered
