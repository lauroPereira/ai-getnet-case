"""Multi-turn behaviour: ownership, history, case state, prefix reuse and technical follow-up (scripted model)."""

import sqlite3

from merchant_assistant.api.schemas import CHALLENGE_EXAMPLES

DEVICE = CHALLENGE_EXAMPLES[4]


def post(client, message, conversation_id=None, user_id="cliente1988", expect=200):
    body = {"message": message, "user_id": user_id}
    if conversation_id:
        body["conversation_id"] = conversation_id
    response = client.post("/messages", json=body)
    assert response.status_code == expect, response.text
    return response.json()


def steps(orchestrator, request_id):
    return orchestrator.trace(request_id)["steps"]


def tool_names(orchestrator, request_id):
    return [s["step"] for s in steps(orchestrator, request_id) if s["step"].startswith("tool:")]


def test_continuation_uses_history_and_reuses_prefix(offline):
    client, orchestrator, llm = offline()
    first = post(client, DEVICE)
    second = post(client, "Já fiz isso e continua sem conexão", first["conversation_id"])
    assert second["conversation_id"] == first["conversation_id"]
    assert second["route"] == "knowledge_and_support"
    router_calls = [c for c in llm.calls if c.spec.agent == "router"]
    assert len(router_calls[-1].spec.context["history"]) == 2
    assert "tool:get_complaint_history" not in tool_names(orchestrator, second["request_id"])
    prefix_step = next(s for s in steps(orchestrator, second["request_id"]) if s["step"] == "support_prefix")
    assert prefix_step["detail"]["reused"] is True


def test_prefix_is_refreshed_when_topic_changes_or_expires(offline, settings):
    client, orchestrator, _ = offline()
    first = post(client, DEVICE)
    other_topic = post(client, CHALLENGE_EXAMPLES[2], first["conversation_id"])
    assert "tool:run_customer_healthcheck" in tool_names(orchestrator, other_topic["request_id"])
    conn = sqlite3.connect(settings.db_path, isolation_level=None)
    conn.execute("UPDATE conversations SET prefix_at = '2026-10-26T08:00:00-03:00'")
    again = post(client, CHALLENGE_EXAMPLES[2], first["conversation_id"])
    assert "tool:run_customer_healthcheck" in tool_names(orchestrator, again["request_id"])


def test_conversation_of_another_merchant_is_refused(offline):
    client, orchestrator, _ = offline()
    mine = post(client, DEVICE)
    response = client.post(
        "/messages", json={"message": "oi", "user_id": "cliente_demo_002", "conversation_id": mine["conversation_id"]}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"
    stored = client.get(f"/conversations/{mine['conversation_id']}").json()
    assert stored["customer_id"] == "cliente1988" and len(stored["messages"]) == 2


def test_client_supplied_id_starts_a_new_conversation(offline):
    client, _, _ = offline()
    body = post(client, CHALLENGE_EXAMPLES[9], conversation_id="conv_clientsupplied01")
    assert body["conversation_id"] == "conv_clientsupplied01"
    assert body["resolution"]["state"] == "awaiting_customer"


def test_confirmation_resolves_with_customer_evidence(offline, settings):
    client, _, _ = offline()
    first = post(client, DEVICE)
    done = post(client, "Voltou a funcionar, obrigado!", first["conversation_id"])
    assert done["route"] == "acknowledgement"
    assert done["resolution"] == {"state": "resolved", "evidence": "customer_confirmed"}
    results = [r[0] for r in sqlite3.connect(settings.db_path).execute("SELECT result FROM case_attempts")]
    assert results and set(results) == {"worked"}


def test_thanks_alone_does_not_resolve(offline):
    client, _, _ = offline()
    first = post(client, CHALLENGE_EXAMPLES[9])
    thanks = post(client, "Obrigado", first["conversation_id"])
    assert thanks["route"] == "acknowledgement"
    assert thanks["resolution"] == {"state": "awaiting_customer", "evidence": None}


def test_confirmation_without_history_is_not_a_resolution(offline):
    client, _, _ = offline()
    body = post(client, "Voltou a funcionar")
    assert body["resolution"]["state"] != "resolved"


def test_two_technical_cycles_then_handoff_with_context(offline, settings):
    client, orchestrator, _ = offline()
    first = post(client, DEVICE)
    second = post(client, "Já tentei e continua sem conexão", first["conversation_id"])
    third = post(client, "Continua igual", first["conversation_id"])
    conn = sqlite3.connect(settings.db_path)
    attempts = conn.execute("SELECT cycle, step, result FROM case_attempts ORDER BY id").fetchall()
    cycle1 = {s for c, s, _ in attempts if c == 1}
    cycle2 = {s for c, s, _ in attempts if c == 2}
    assert cycle1 and cycle2 and not cycle1 & cycle2, "a step must not be repeated"
    assert second["status"] == "answered"
    assert third["status"] == "handoff" and third["handoff"]["reason"] == "technical_cycles_exhausted"
    assert third["resolution"]["state"] == "handoff"
    payload = conn.execute("SELECT payload FROM handoff_cases").fetchone()[0]
    assert "troubleshooting_attempts" in payload and "failed" in payload


def test_success_on_second_cycle(offline):
    client, _, _ = offline()
    first = post(client, DEVICE)
    post(client, "Já fiz isso e continua sem conexão", first["conversation_id"])
    done = post(client, "Agora funcionou!", first["conversation_id"])
    assert done["resolution"]["state"] == "resolved"


def test_human_request_mid_cycle_hands_off_immediately(offline):
    client, _, _ = offline()
    first = post(client, DEVICE)
    human = post(client, "Quero falar com um atendente", first["conversation_id"])
    assert human["status"] == "handoff"
    after = post(client, "Alguma novidade?", first["conversation_id"])
    assert after["resolution"]["state"] == "handoff"


def test_case_already_with_human_reuses_the_protocol(offline, settings):
    client, _, llm = offline()
    first = post(client, DEVICE)
    human = post(client, "Quero falar com um atendente", first["conversation_id"])
    calls_before = len([c for c in llm.calls if c.spec.agent == "customer_support"])
    again = post(client, "Já tentei de novo e continua sem conexão", first["conversation_id"])
    assert again["handoff"]["protocol"] == human["handoff"]["protocol"]
    assert len([c for c in llm.calls if c.spec.agent == "customer_support"]) == calls_before
    assert sqlite3.connect(settings.db_path).execute("SELECT COUNT(*) FROM handoff_cases").fetchone()[0] == 1
