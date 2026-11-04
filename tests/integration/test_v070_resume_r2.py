"""v0.7.0 task 65, round 2 (review of 2026-11-03, `d55ce35`; spec D28): isolation of the operator's turn in another
merchant's open conversation, an operator's amount and date kept intact by the guard, a thread stopped half-way
continues without repeating Support, a turn already written is not written again, and a handoff whose checkpoint
could not be saved is marked from the start. Scripted model, no network, no cost."""

from __future__ import annotations

import sqlite3

import pytest

from merchant_assistant import handoffs
from merchant_assistant.api.identity import Principal
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.llm.scripted import ToolPlan
from merchant_assistant.testing import merchant_headers, token_headers

HUMAN = "Quero falar com um atendente"
INSTRUCTION = "Verifique o status da maquininha antes de responder."
AMOUNT_AND_DATE = "Seu repasse de R$ 1.234,56 cai em 28/10/2026."


class Crash(BaseException):
    """Stands for the process dying inside a node: not an Exception, so nothing on the way catches it."""


def operator(client, name="op_ana"):
    return token_headers(client, Principal.operator(name))


def hand_off(client, customer="cliente1988") -> dict:
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client, customer))
    assert response.status_code == 200 and response.json()["status"] == "handoff", response.text
    cases = client.get("/v1/handoffs", headers=operator(client)).json()["cases"]
    return next(c for c in cases if c["protocol"] == response.json()["handoff"]["protocol"])


def act(client, case_id, action="approve", key="key-r2-000001", text=None):
    body = {"action": action, "idempotency_key": key} | ({"text": text} if text else {})
    return client.post(f"/v1/handoffs/{case_id}/actions", headers=operator(client), json=body)


def operator_turns(client, conversation_id, customer="cliente1988"):
    response = client.get(f"/v1/conversations/{conversation_id}", headers=merchant_headers(client, customer))
    return [t for t in response.json()["messages"] if t.get("via") == "operator"]


def reject_handler(call):
    """Support follows the operator's instruction with one device lookup; everything else is the default."""
    if call.spec.agent == "customer_support" and call.spec.context.get("operator_instruction"):
        return ToolPlan(
            [("get_device_status", {})],
            final=lambda results: {
                "points": ["Sua maquininha está offline desde as 07:00; reinicie-a e verifique o chip."],
                "needs_selection": False,
                "missing": [],
                "escalate": False,
                "escalation_reason": None,
                "steps_given": ["reiniciar"],
                "issue_verified_by_tool": False,
            },
        )
    return default_handler(call)


# --- P2-2: the operator's turn never reaches another merchant's open conversation -----------------------------------


def test_operator_turn_is_not_delivered_in_another_merchants_open_conversation(offline):
    client, _, _ = offline()
    other = merchant_headers(client, "cliente_demo_002")
    opened = client.post("/messages", json={"message": "Olá"}, headers=other).json()  # B's conversation, open first
    case = hand_off(client)
    assert act(client, case["case_id"], "reply", "key-r2-isolate", "Resposta para o lojista A.").status_code == 200
    again = client.post(
        "/messages", json={"message": "Oi", "conversation_id": opened["conversation_id"]}, headers=other
    )
    assert again.status_code == 200
    assert again.json()["route"] != "human_reply" and "lojista A" not in again.json()["answer"]
    mine = client.post(
        "/messages",
        json={"message": "Oi", "conversation_id": case["conversation_id"]},
        headers=merchant_headers(client),
    )
    assert mine.json()["route"] == "human_reply" and mine.json()["answer"] == "Resposta para o lojista A."


# --- P2-3: an operator's amount and date pass the output guard intact -----------------------------------------------


def test_reply_with_an_amount_and_a_date_passes_the_guard_intact(offline):
    client, _, _ = offline()
    case = hand_off(client)
    response = act(client, case["case_id"], "reply", "key-r2-amount", AMOUNT_AND_DATE)
    assert response.status_code == 200 and response.json()["resume_status"] == "done", response.text
    assert [t["text"] for t in operator_turns(client, case["conversation_id"])] == [AMOUNT_AND_DATE]
    delivered = client.post(
        "/messages",
        json={"message": "Ok", "conversation_id": case["conversation_id"]},
        headers=merchant_headers(client),
    )
    assert delivered.json()["answer"] == AMOUNT_AND_DATE


# --- P3-1: a thread stopped half-way continues; a turn already written is not written again --------------------------


def test_thread_stopped_half_way_continues_without_repeating_support(offline, settings):
    armed = {"on": False}

    def handler(call):
        if armed["on"] and call.spec.agent == "personality":
            armed["on"] = False
            raise Crash("the process dies inside Personality, after Support")
        return reject_handler(call)

    client, orchestrator, _ = offline(handler=handler)
    case = hand_off(client)
    armed["on"] = True
    conn = connect(settings.db_path)
    try:
        with pytest.raises(Crash):
            handoffs.act(
                conn,
                case["case_id"],
                "op_ana",
                "reject",
                INSTRUCTION,
                "key-r2-halfway",
                actor="operator:op_ana",
                resume=orchestrator.resume_handoff,
            )
        thread = conn.execute("SELECT thread_id FROM handoff_cases").fetchone()["thread_id"]
        snapshot = orchestrator.review_graph().get_state({"configurable": {"thread_id": thread}})
        assert snapshot.next and not any(task.interrupts for task in snapshot.tasks)  # stopped after human_review
        assert operator_turns(client, case["conversation_id"]) == []
        conn.execute("UPDATE handoff_cases SET resume_started_at='2000-01-01T00:00:00+00:00'")  # the attempt is stale
        record = handoffs.act(
            conn,
            case["case_id"],
            "op_ana",
            "reject",
            INSTRUCTION,
            "key-r2-halfway",
            actor="operator:op_ana",
            resume=orchestrator.resume_handoff,
        )
        assert record["replayed"] is True and record["resume_status"] == "done"
        lookups = conn.execute("SELECT COUNT(*) FROM audit_events WHERE tool='get_device_status'").fetchone()[0]
        assert lookups == 1  # Support ran once, before the crash; the retry continued from the checkpoint
    finally:
        conn.close()
    [turn] = operator_turns(client, case["conversation_id"])
    assert turn["operator_action"] == "reject" and "offline" in turn["text"]


def test_turn_written_before_a_failure_is_not_written_again_on_retry(offline, monkeypatch):
    client, orchestrator, _ = offline()
    case = hand_off(client)
    real_record, failures = orchestrator._record, []

    def record_once_failing(*args, **kwargs):  # runs after the operator turn is stored
        if not failures:
            failures.append(1)
            raise RuntimeError("trace store unavailable")
        return real_record(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "_record", record_once_failing)
    failed = act(client, case["case_id"], "reply", "key-r2-written", "Tudo certo.")
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "resume_failed"
    assert [t["text"] for t in operator_turns(client, case["conversation_id"])] == ["Tudo certo."]
    retried = act(client, case["case_id"], "reply", "key-r2-written", "Tudo certo.")
    assert retried.status_code == 200 and retried.json()["resume_status"] == "done"
    assert [t["text"] for t in operator_turns(client, case["conversation_id"])] == ["Tudo certo."]


# --- D28: a checkpoint that was not saved marks the case from the start ----------------------------------------------


def test_checkpoint_failure_marks_the_case_and_refuses_actions(offline, settings, monkeypatch):
    client, orchestrator, _ = offline()

    def broken():
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(orchestrator, "review_graph", broken)
    case = hand_off(client)  # the merchant's reply is not affected
    assert case["resume_status"] == "checkpoint_failed" and case["queue_state"] == "open"
    detail = client.get(f"/v1/handoffs/{case['case_id']}", headers=operator(client)).json()
    assert detail["resume_status"] == "checkpoint_failed" and detail["resume_error"]
    refused = act(client, case["case_id"], "approve", "key-r2-nockpt")
    assert refused.status_code == 503 and refused.json()["error"]["code"] == "checkpoint_missing"
    conn = sqlite3.connect(settings.db_path)
    row = conn.execute("SELECT queue_state, claimed_by, resume_count FROM handoff_cases").fetchone()
    assert row == ("open", None, 0)
    assert conn.execute("SELECT COUNT(*) FROM handoff_events").fetchone()[0] == 0
    audit = conn.execute("SELECT outcome FROM audit_events WHERE tool='handoff.approve'").fetchall()
    assert audit == [("checkpoint_missing",)]
    assert client.get("/ready").json()["pending_handoffs"] == 1  # still waiting in the queue, visibly
