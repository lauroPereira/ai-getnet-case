"""v0.7.0 task 65 (CA-47, CA-48, CA-46): the handoff interrupts the flow in a SQLite checkpoint; the operator's action
resumes it (approve/reply -> Personality, reject -> Support with the instruction, one cycle), writes an operator
turn and delivers it on the next message without any model call. Scripted model, no network, no cost."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import textwrap

import pytest

from merchant_assistant import handoffs
from merchant_assistant.api.identity import Principal
from merchant_assistant.conversations import ConversationStore
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.llm.scripted import ToolPlan
from merchant_assistant.orchestration.graph import CHECKPOINT_TYPES
from merchant_assistant.testing import merchant_headers, token_headers

HUMAN = "Quero falar com um atendente"
INSTRUCTION = "Verifique o status da maquininha antes de responder."


def operator(client, name="op_ana"):
    return token_headers(client, Principal.operator(name))


def hand_off(client, customer="cliente1988", conversation_id=None) -> dict:
    body = {"message": HUMAN} | ({"conversation_id": conversation_id} if conversation_id else {})
    response = client.post("/messages", json=body, headers=merchant_headers(client, customer))
    assert response.status_code == 200 and response.json()["status"] == "handoff", response.text
    message = response.json()
    cases = client.get("/v1/handoffs", headers=operator(client)).json()["cases"]
    case = next(c for c in cases if c["protocol"] == message["handoff"]["protocol"])
    return {"message": message, "case": case}


def act(client, case_id, action="approve", key="key-resume-01", text=None, name="op_ana"):
    body = {"action": action, "idempotency_key": key} | ({"text": text} if text else {})
    return client.post(f"/v1/handoffs/{case_id}/actions", headers=operator(client, name), json=body)


def turns(client, conversation_id, customer="cliente1988"):
    response = client.get(f"/v1/conversations/{conversation_id}", headers=merchant_headers(client, customer))
    assert response.status_code == 200, response.text
    return response.json()["messages"]


def reject_handler(call):
    """Support follows the operator's instruction with exactly one device lookup; everything else is the default."""
    context = call.spec.context
    if call.spec.agent == "customer_support" and context.get("operator_instruction"):
        return ToolPlan(
            [("get_device_status", {})],
            final=lambda results: {
                "points": ["Sua maquininha está offline desde as 07:00; reinicie-a e verifique o chip."],
                "needs_selection": False,
                "missing": [],
                "escalate": True,  # ignored: an operator's reject never goes back to handoff
                "escalation_reason": "x",
                "steps_given": ["reiniciar"],
                "issue_verified_by_tool": False,
            },
        )
    return default_handler(call)


# --- interruption ---------------------------------------------------------------------------------------------------


def test_handoff_interrupts_with_a_checkpoint_and_no_simulation_text(offline, settings):
    client, orchestrator, _ = offline()
    opened = hand_off(client)
    message, case = opened["message"], opened["case"]
    assert "simula" not in message["answer"].lower() and message["handoff"]["protocol"] in message["answer"]
    assert message["via"] == "agent"
    trace = orchestrator.trace(message["request_id"])
    review = next(s for s in trace["steps"] if s["step"] == "human_review")
    assert review["status"] == "interrupted" and review["detail"]["thread_id"] == message["request_id"]
    snapshot = orchestrator.review_graph().get_state({"configurable": {"thread_id": message["request_id"]}})
    assert snapshot.next == ("human_review",)
    interrupt = snapshot.tasks[0].interrupts[0].value
    assert interrupt["protocol"] == case["protocol"] and interrupt["draft_reply"]
    detail = client.get(f"/v1/handoffs/{case['case_id']}", headers=operator(client)).json()
    assert detail["draft_reply"] == "Nossa equipe analisou o seu caso e vai responder por aqui."  # escalation.v2
    assert any(s.get("detail", {}).get("prompt") == "escalation@2" for s in trace["steps"])
    ready = client.get("/ready").json()
    assert ready["pending_handoffs"] == 1 and ready["checkpoints"]["threads"] == 1


def test_turn_without_handoff_never_touches_checkpoints(offline, settings, monkeypatch):
    from langgraph.checkpoint.sqlite import SqliteSaver

    calls = []
    for method in ("get_tuple", "put", "list", "put_writes"):
        original = getattr(SqliteSaver, method)
        monkeypatch.setattr(
            SqliteSaver, method, lambda self, *a, _m=method, _o=original, **k: calls.append(_m) or _o(self, *a, **k)
        )
    client, orchestrator, _ = offline()
    headers = merchant_headers(client)
    for message in ("When will the money from yesterday's sales be deposited?", "Minha maquininha não conecta"):
        assert client.post("/messages", json={"message": message}, headers=headers).json()["status"] != "handoff"
    assert calls == [] and orchestrator._review_graph is None
    assert not settings.checkpoint_db_path.exists()
    hand_off(client)
    assert calls and settings.checkpoint_db_path.exists()  # the handoff is the only path that writes one


def test_checkpoint_types_are_registered_for_strict_deserialization():
    names = {name for _, name in CHECKPOINT_TYPES}
    assert {"GraphState", "RouterDecision", "KnowledgeResult", "Citation", "SupportResult", "EscalationResult"} == names


# --- resume (CA-47) -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "text", "expected"),
    [
        ("approve", None, "Nossa equipe analisou o seu caso e vai responder por aqui."),
        ("reply", "Seu repasse foi enviado hoje às 10:00.", "Seu repasse foi enviado hoje às 10:00."),
    ],
)
def test_approve_and_reply_write_an_operator_turn(offline, settings, action, text, expected):
    client, orchestrator, llm = offline()
    case = hand_off(client)["case"]
    response = act(client, case["case_id"], action, f"key-{action}-0001", text)
    assert response.status_code == 200, response.text
    record = response.json()
    assert record["resume_status"] == "done" and record["case_state"] == "awaiting_customer"  # D14
    assert record["queue_state"] == "answered"
    last = turns(client, case["conversation_id"])[-1]
    assert last["via"] == "operator" and last["operator_action"] == action and last["protocol"] == case["protocol"]
    assert last["route"] == "human_reply" and last["text"] == expected
    resume_id = (
        sqlite3.connect(settings.db_path)
        .execute("SELECT resume_request_id FROM handoff_cases WHERE case_id=?", (case["case_id"],))
        .fetchone()[0]
    )
    trace = orchestrator.trace(resume_id)
    assert trace["detail"]["purpose"] == "operator_resume" and trace["detail"]["resumes"]
    assert [s["step"] for s in trace["steps"]] == ["human_review", "personality", "output_guard"]
    assert any(c.spec.agent == "personality" for c in llm.calls)


def test_reject_reruns_support_once_under_the_operator_and_never_hands_off_again(offline, settings):
    client, orchestrator, _ = offline(handler=reject_handler)
    case = hand_off(client)["case"]
    response = act(client, case["case_id"], "reject", "key-reject-0001", INSTRUCTION)
    assert response.status_code == 200, response.text
    assert response.json()["queue_state"] == "rejected" and response.json()["case_state"] == "awaiting_customer"
    conn = sqlite3.connect(settings.db_path)
    resume_id = conn.execute("SELECT resume_request_id FROM handoff_cases").fetchone()[0]
    trace = orchestrator.trace(resume_id)
    steps = [s["step"] for s in trace["steps"]]
    assert steps.count("tool:get_device_status") == 1 and "escalation" not in steps
    assert steps[0] == "human_review" and "support" in steps
    assert conn.execute("SELECT COUNT(*) FROM handoff_cases").fetchone()[0] == 1  # no new case
    rows = conn.execute(  # CA-46: the operator's principal acting for the merchant of the case
        "SELECT principal_id, customer_id, scope, outcome FROM audit_events WHERE tool='get_device_status'"
    ).fetchall()
    assert rows == [("operator:op_ana", "cliente1988", "support:read", "ok")]
    last = turns(client, case["conversation_id"])[-1]
    assert last["via"] == "operator" and last["operator_action"] == "reject" and "offline" in last["text"]


def test_next_message_delivers_the_human_reply_without_a_model_call(offline, settings):
    client, _, llm = offline()
    case = hand_off(client)["case"]
    act(client, case["case_id"], "reply", "key-deliver-01", "Seu repasse foi enviado hoje.")
    calls = len(llm.calls)
    headers = merchant_headers(client)
    delivered = client.post(
        "/messages", json={"message": "E aí?", "conversation_id": case["conversation_id"]}, headers=headers
    ).json()
    assert len(llm.calls) == calls  # no model call
    assert delivered["route"] == "human_reply" and delivered["via"] == "operator"
    assert delivered["answer"] == "Seu repasse foi enviado hoje." and delivered["status"] == "answered"
    assert delivered["resolution"]["state"] == "awaiting_customer"
    following = client.post(
        "/messages", json={"message": "Obrigado", "conversation_id": case["conversation_id"]}, headers=headers
    ).json()
    assert following["route"] != "human_reply" and following["via"] == "agent"
    demo_view = client.get(f"/conversations/{case['conversation_id']}", headers=headers).json()
    assert [t.get("via") for t in demo_view["messages"] if t["role"] == "assistant"] == ["agent", "operator", "agent"]


def test_another_merchant_never_receives_or_sees_the_operator_turn(offline):
    client, _, _ = offline()
    case = hand_off(client)["case"]
    act(client, case["case_id"], "reply", "key-isolate-1", "Resposta para o lojista A.")
    other = merchant_headers(client, "cliente_demo_002")
    assert client.get(f"/v1/conversations/{case['conversation_id']}", headers=other).status_code == 404
    assert client.get(f"/conversations/{case['conversation_id']}", headers=other).status_code == 404
    mine = client.post("/messages", json={"message": "Oi"}, headers=other).json()
    assert mine["route"] != "human_reply" and "lojista A" not in mine["answer"]
    stolen = client.post("/messages", json={"message": "Oi", "conversation_id": case["conversation_id"]}, headers=other)
    assert stolen.status_code == 404


def test_new_message_with_the_case_open_does_not_collide_with_the_interruption(offline, settings):
    client, orchestrator, _ = offline()
    opened = hand_off(client)
    case, thread = opened["case"], opened["message"]["request_id"]
    again = client.post(
        "/messages",
        json={"message": "Alguma novidade?", "conversation_id": case["conversation_id"]},
        headers=merchant_headers(client),
    ).json()
    assert again["resolution"]["state"] == "handoff"
    assert client.get("/ready").json()["checkpoints"]["threads"] == 1  # no second interruption
    snapshot = orchestrator.review_graph().get_state({"configurable": {"thread_id": thread}})
    assert snapshot.next == ("human_review",)
    assert act(client, case["case_id"], "approve", "key-collide-1").json()["resume_status"] == "done"


# --- double resume and failures (CA-48) -------------------------------------------------------------------------------


def test_second_action_is_refused_without_touching_the_graph(offline, settings):
    client, orchestrator, _ = offline()
    case = hand_off(client)["case"]
    resumes = []
    real = orchestrator.resume_handoff
    orchestrator.resume_handoff = lambda c, r: resumes.append(r["event_id"]) or real(c, r)
    assert act(client, case["case_id"], "approve", "key-double-01").status_code == 200
    thread = sqlite3.connect(settings.db_path).execute("SELECT thread_id FROM handoff_cases").fetchone()[0]
    before = orchestrator.review_graph().get_state({"configurable": {"thread_id": thread}}).config
    second = act(client, case["case_id"], "reply", "key-double-02", "outro texto")
    assert second.status_code == 409 and second.json()["error"]["code"] == "already_resumed"
    replay = act(client, case["case_id"], "approve", "key-double-01")
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    after = orchestrator.review_graph().get_state({"configurable": {"thread_id": thread}}).config
    assert len(resumes) == 1 and before == after
    operator_turns = [t for t in turns(client, case["conversation_id"]) if t.get("via") == "operator"]
    assert len(operator_turns) == 1


def test_failed_resume_is_visible_and_recovers_with_the_same_key(offline, settings):
    client, orchestrator, _ = offline()
    case = hand_off(client)["case"]
    real, attempts = orchestrator.resume_handoff, []

    def flaky(c, r):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("disk full")
        return real(c, r)

    orchestrator.resume_handoff = flaky
    failed = act(client, case["case_id"], "reply", "key-flaky-001", "Já resolvemos.")
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "resume_failed"
    listed = client.get("/v1/handoffs", headers=operator(client)).json()["cases"][0]
    assert (listed["queue_state"], listed["resume_status"], listed["resume_error"]) == (
        "answered",
        "failed",
        "RuntimeError",
    )
    assert act(client, case["case_id"], "approve", "key-flaky-002").json()["error"]["code"] == "already_resumed"
    retried = act(client, case["case_id"], "reply", "key-flaky-001", "Já resolvemos.")
    assert retried.status_code == 200 and retried.json()["replayed"] is True
    assert retried.json()["resume_status"] == "done" and retried.json()["case_state"] == "awaiting_customer"
    assert act(client, case["case_id"], "reply", "key-flaky-001", "Já resolvemos.").json()["resume_status"] == "done"
    assert len(attempts) == 2  # a done resume is never repeated
    operator_turns = [t for t in turns(client, case["conversation_id"]) if t.get("via") == "operator"]
    assert [t["text"] for t in operator_turns] == ["Já resolvemos."]


def test_failure_after_the_graph_finished_writes_the_turn_once_on_retry(offline, settings, monkeypatch):
    client, _, _ = offline()
    case = hand_off(client)["case"]
    real_save, failures = ConversationStore.save, []

    def save_once_failing(self, *args, **kwargs):
        if not failures:
            failures.append(1)
            raise sqlite3.OperationalError("database is locked")
        return real_save(self, *args, **kwargs)

    monkeypatch.setattr(ConversationStore, "save", save_once_failing)
    assert act(client, case["case_id"], "reply", "key-late-0001", "Tudo certo.").status_code == 503
    retried = act(client, case["case_id"], "reply", "key-late-0001", "Tudo certo.")
    assert retried.status_code == 200 and retried.json()["resume_status"] == "done"
    operator_turns = [t for t in turns(client, case["conversation_id"]) if t.get("via") == "operator"]
    assert [t["text"] for t in operator_turns] == ["Tudo certo."]


def test_stale_pending_resume_is_retried(offline, settings):
    client, orchestrator, _ = offline()
    case = hand_off(client)["case"]
    conn = connect(settings.db_path)
    handoffs.act(conn, case["case_id"], "op_ana", "approve", None, "key-stale-001", actor="operator:op_ana")
    fresh = handoffs.act(
        conn,
        case["case_id"],
        "op_ana",
        "approve",
        None,
        "key-stale-001",
        actor="operator:op_ana",
        resume=orchestrator.resume_handoff,
    )
    assert fresh["resume_status"] == "pending"  # another attempt may still be running
    conn.execute("UPDATE handoff_cases SET resume_started_at='2000-01-01T00:00:00+00:00'")
    stale = handoffs.act(
        conn,
        case["case_id"],
        "op_ana",
        "approve",
        None,
        "key-stale-001",
        actor="operator:op_ana",
        resume=orchestrator.resume_handoff,
    )
    assert stale["resume_status"] == "done"


def test_case_from_before_0009_is_refused_clearly(offline, settings):
    client, _, _ = offline()
    case = hand_off(client)["case"]
    sqlite3.connect(settings.db_path, isolation_level=None).execute(
        "UPDATE handoff_cases SET thread_id=NULL WHERE case_id=?", (case["case_id"],)
    )
    refused = act(client, case["case_id"], "approve", "key-legacy-01")
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "not_resumable"
    detail = client.get(f"/v1/handoffs/{case['case_id']}", headers=operator(client)).json()
    assert detail["queue_state"] == "open" and detail["resume_count"] == 0 and detail["events"] == []


# --- restart (CA-48) ----------------------------------------------------------------------------------------------

SCRIPT = textwrap.dedent(
    """
    import json, sys
    from merchant_assistant.config import Settings
    from merchant_assistant.testing import offline_orchestrator
    from merchant_assistant.api.schemas import MessageRequest
    from merchant_assistant.data.db import connect
    from merchant_assistant import handoffs

    runtime, key_path, step = sys.argv[1], sys.argv[2], sys.argv[3]
    settings = Settings(_env_file=None, openai_api_key=None, runtime_dir=runtime, qdrant_url=":memory:",
                        jwt_private_key_path=key_path)
    orchestrator, _ = offline_orchestrator(settings, with_index=False)
    if step == "handoff":
        response = orchestrator.handle(
            MessageRequest(message="Quero falar com um atendente", user_id="cliente1988"), "req_restart_00001",
            channel="api",
        )
        print(json.dumps({"protocol": response.handoff.protocol, "conversation_id": response.conversation_id}))
    else:
        conn = connect(settings.db_path)
        case_id = conn.execute("SELECT case_id FROM handoff_cases").fetchone()[0]
        record = handoffs.act(conn, case_id, "op_bruno", "reply", "Resposta depois do reinicio.", "key-restart-1",
                              actor="operator:op_bruno", resume=orchestrator.resume_handoff)
        print(json.dumps(record))
    orchestrator.close()
    """
)


def test_resume_after_restart_in_a_new_process(tmp_path, jwt_signing_key_path):
    runtime = tmp_path / "runtime"
    env = os.environ | {"LANGGRAPH_STRICT_MSGPACK": "true", "PYTHONUTF8": "1"}  # unregistered types would fail

    def run(step: str) -> dict:
        done = subprocess.run(
            [sys.executable, "-c", SCRIPT, str(runtime), str(jwt_signing_key_path), step],
            capture_output=True,
            text=True,
            env=env,
            timeout=180,
            check=False,
        )
        assert done.returncode == 0, done.stderr[-2000:]
        return json.loads(done.stdout.strip().splitlines()[-1])

    first = run("handoff")  # this process ends here: the flow lives only in the checkpoint
    record = run("resume")
    assert record["resume_status"] == "done" and record["queue_state"] == "answered"
    assert record["case_state"] == "awaiting_customer" and record["operator_id"] == "op_bruno"
    conn = sqlite3.connect(runtime / "merchant.sqlite3")
    via, text, meta = conn.execute(
        "SELECT via, text, meta FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 1",
        (first["conversation_id"],),
    ).fetchone()
    assert via == "operator" and text == "Resposta depois do reinicio."
    assert json.loads(meta)["protocol"] == first["protocol"]
