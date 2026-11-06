"""v0.7.0 task 68: the story `docs/historias/identidade-hitl-v070.md` (version 2), moments 1 to 17, programmed.

The assistant, the ticketing service (`merchant_assistant.ticketing`, unchanged) and the synthetic merchant receiver
(`mocks`) run in process and talk only over HTTP through a test transport that routes by host; moment 16 uses two
processes (the first one hands off and exits, the second one acts on the ticket over the saved checkpoint). Moment 18
(Docker) belongs to the QA. Scripted model, no network, no cost. CA-46, CA-47 and CA-48."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import textwrap

import httpx
import jwt
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.llm.scripted import ToolPlan
from merchant_assistant.mocks.service import create_mocks_app
from merchant_assistant.testing import TEST_TICKETING_SECRET, TEST_USER_PASSWORDS, AppTransport, token_headers
from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.service import create_app as create_ticketing_app

ASSISTANT, TICKETING, MERCHANT = "assistant.test", "ticketing.test", "merchant.test"
SECRETS = {
    "ticketing_webhook_secret": "story-ticketing-webhook-secret",
    "assistant_webhook_secret": "story-assistant-webhook-secret",
    "conversation_webhook_secret": "story-conversation-webhook-secret",
}
EVENTS_PATH = "/v1/integrations/ticketing/events"
HANDOFF = "Minha máquina não conecta, quero falar com um atendente"
INSTRUCTION = "verifique o status do dispositivo e responda"


def story_handler(call):
    """The default scripted policy; on an operator's reject, Support checks the device once."""
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


class LosesOneAnswer(AppTransport):
    """The ticketing's link to the assistant: when armed, the next event reaches the assistant but its answer is lost
    on the way back (simulated transport failure)."""

    armed = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = super().handle_request(request)
        if self.armed and request.url.path == EVENTS_PATH:
            self.armed = False
            raise httpx.ReadError("connection reset after the assistant answered", request=request)
        return response


def configure(settings) -> None:
    settings.ticketing_webhook_url = f"http://{TICKETING}/webhooks/assistant"
    settings.conversation_webhook_url = f"http://{MERCHANT}/merchant/events"
    for name, value in SECRETS.items():
        setattr(settings, name, SecretStr(value))


def ticketing_settings(settings, db_path) -> TicketingSettings:
    return TicketingSettings(
        db_path=db_path,
        assistant_url=f"http://{ASSISTANT}",
        assistant_issuer=settings.jwt_issuer,
        assistant_jwks_url=f"http://{ASSISTANT}/.well-known/jwks.json",
        inbound_secret=SECRETS["ticketing_webhook_secret"],
        outbound_secret=SECRETS["assistant_webhook_secret"],
        client_secret=TEST_TICKETING_SECRET,
        retry_waits_s=(0.0,),
        outbox_poll_s=0,  # the test runs the outbox explicitly
    )


def connect_services(assistant: TestClient, settings, ticketing_db, link_cls=AppTransport):
    """Ticketing and merchant receiver wired to the assistant; returns (ticketing, merchant, webhooks, link)."""
    apps: dict[str, TestClient] = {ASSISTANT: assistant}
    link = link_cls(apps)
    ticketing = TestClient(
        create_ticketing_app(ticketing_settings(settings, ticketing_db), client=httpx.Client(transport=link))
    )
    merchant = TestClient(create_mocks_app(conversation_secret=SECRETS["conversation_webhook_secret"]))
    apps |= {TICKETING: ticketing, MERCHANT: merchant}
    webhooks = Webhooks(settings, transport=AppTransport(apps), sleep=lambda _s: None)
    assistant.app.state.webhooks = webhooks
    return ticketing, merchant, webhooks, link


def login(client, username: str) -> dict:
    response = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": username, "password": TEST_USER_PASSWORDS[username]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def db_rows(settings, query, args=()):
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(query, args)]
    finally:
        conn.close()


def operator_turns(client, headers, conversation_id):
    messages = client.get(f"/v1/conversations/{conversation_id}", headers=headers).json()["messages"]
    return [m for m in messages if m.get("via") == "operator"]


def new_ticket(ticketing, ana, protocol) -> dict:
    tickets = ticketing.get("/tickets", params={"status": "new"}, headers=ana).json()["tickets"]
    return next(t for t in tickets if t["protocol"] == protocol)


def test_story_moments_1_to_15_and_17(offline, settings, tmp_path):
    configure(settings)
    client, orchestrator, llm = offline(handler=story_handler)
    ticketing, merchant, webhooks, link = connect_services(
        client, settings, tmp_path / "ticketing" / "ticketing.sqlite3", LosesOneAnswer
    )
    ana, bruno = (
        token_headers(client, Principal.operator("op_ana")),
        token_headers(client, Principal.operator("op_bruno")),
    )

    # 1. No token: 401, no model call.
    unauthenticated = client.post("/messages", json={"message": "Olá"})
    assert unauthenticated.status_code == 401 and unauthenticated.json()["error"]["code"] == "token_required"
    assert llm.calls == []

    # 2. Merchant login; the published JWKS validates the token.
    issued = login(client, "cliente1988")
    token = issued["access_token"]
    keys = jwt.PyJWKSet.from_dict(client.get("/.well-known/jwks.json").json())
    kid = jwt.get_unverified_header(token)["kid"]
    claims = jwt.decode(
        token,
        next(k for k in keys.keys if k.key_id == kid).key,
        algorithms=["RS256"],
        audience="merchant-assistant",
        issuer=settings.jwt_issuer,
    )
    assert claims["sub"] == "merchant:cliente1988" and claims["customer_id"] == "cliente1988"
    assert set(claims["scope"].split()) == {"support:read", "handoff:create", "conversation:read"}
    assert issued["token_type"] == "Bearer" and 0 < issued["expires_in"] <= 3600

    # 3. Tampered token, then a revoked one: 401 for both; a new login works.
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}{'A' if signature[-2] != 'A' else 'B'}{signature[-1]}"
    assert client.post("/messages", json={"message": "Olá"}, headers=bearer(tampered)).status_code == 401
    assert client.post("/v1/auth/revoke", headers=bearer(token)).status_code == 200
    assert client.post("/messages", json={"message": "Olá"}, headers=bearer(token)).status_code == 401
    merchant_a = bearer(login(client, "cliente1988")["access_token"])
    assert llm.calls == []

    # 4. Forged identity: 403 identity_mismatch, nothing of cliente_demo_002.
    forged = client.post("/messages", json={"message": "Olá", "user_id": "cliente_demo_002"}, headers=merchant_a)
    assert forged.status_code == 403 and forged.json()["error"]["code"] == "identity_mismatch"
    assert "Loja Demo 002" not in forged.text and llm.calls == []

    # 5. Normal question: the merchant's data, one audit row per tool call with principal, scope and outcome.
    # The scripted policy routes by keywords: the story's "Quando cai meu próximo recebimento?" is asked as below.
    normal = client.post(
        "/messages", json={"message": "Quando cai o dinheiro das vendas de ontem?"}, headers=merchant_a
    )
    assert normal.status_code == 200 and normal.json()["via"] == "agent", normal.text
    trace = orchestrator.trace(normal.json()["request_id"])
    audit = db_rows(
        settings, "SELECT principal_id, scope, outcome, customer_id FROM audit_events WHERE tool NOT LIKE 'handoff%'"
    )
    assert trace["tool_calls"] > 0 and len(audit) == trace["tool_calls"]
    assert all(a["principal_id"] == "merchant:cliente1988" and a["scope"] and a["outcome"] for a in audit)
    assert {a["customer_id"] for a in audit} == {"cliente1988"}

    # 6. The merchant asks for an attendant: handoff with HO-…, no simulation text, case open in the queue.
    handed = client.post(
        "/messages", json={"message": HANDOFF, "conversation_id": normal.json()["conversation_id"]}, headers=merchant_a
    )
    body = handed.json()
    assert body["status"] == "handoff" and body["handoff"]["protocol"].startswith("HO-"), handed.text
    assert "simula" not in body["answer"].lower()
    conversation_id, protocol = body["conversation_id"], body["handoff"]["protocol"]
    queue = client.get("/v1/handoffs", params={"state": "open"}, headers=ana).json()["cases"]
    case_id = next(c["case_id"] for c in queue if c["protocol"] == protocol)
    webhooks.wait()

    # 7. Reception in the ticketing: ticket `new` with the case; handoff.created recorded on both sides.
    ticket = new_ticket(ticketing, ana, protocol)
    assert ticket["case_id"] == case_id and ticket["summary"] and ticket["pending_question"] and ticket["draft_reply"]
    assert ticket["transcript"] and all({"role", "text", "at"} == set(t) for t in ticket["transcript"])
    ticket_id = ticket["ticket_id"]
    detail = client.get(f"/v1/handoffs/{case_id}", headers=ana).json()
    assert [(d["event"], d["status"]) for d in detail["deliveries"]] == [("handoff.created", "delivered")]
    received = ticketing.get(f"/tickets/{ticket_id}", headers=ana).json()["deliveries"]["received"]
    assert [d["event_type"] for d in received] == ["handoff.created"]

    # 8. The merchant insists before the human answer: the pending interruption is kept.
    insisted = client.post(
        "/messages", json={"message": "Alguma novidade?", "conversation_id": conversation_id}, headers=merchant_a
    )
    assert insisted.json()["resolution"]["state"] == "handoff" and insisted.json()["route"] != "human_reply"
    assert client.get("/ready").json()["checkpoints"]["threads"] == 1
    assert db_rows(
        settings,
        "SELECT queue_state, resume_status, resume_count, ticket_id FROM handoff_cases WHERE case_id=?",
        (case_id,),
    ) == [{"queue_state": "open", "resume_status": None, "resume_count": 0, "ticket_id": None}]  # nobody acted yet

    # 9. op_ana takes the ticket; op_bruno gets 409 claimed_by_other.
    assigned = ticketing.post(f"/tickets/{ticket_id}/assign", headers=ana)
    assert assigned.status_code == 200 and assigned.json()["ticket"]["status"] == "open", assigned.text
    conflict = ticketing.post(f"/tickets/{ticket_id}/assign", headers=bruno)
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "claimed_by_other"

    # 10 and 11. op_ana replies; the assistant's answer is lost once on the way back, the outbox repeats the same
    # event (same key), the assistant answers `replayed` without resuming twice; then a new act is 409.
    reply = {
        "action": "reply",
        "text": "Reinicie a maquininha e ela volta a conectar.",
        "idempotency_key": "story-reply-01",
    }
    link.armed = True
    pending = ticketing.post(f"/tickets/{ticket_id}/actions", headers=ana, json=reply)
    assert pending.status_code == 202 and pending.json()["delivery"]["status"] == "pending"  # "envio pendente"
    [redelivered] = ticketing.app.state.dispatcher.dispatch_due()
    assert redelivered.status == "delivered" and redelivered.response["status"] == "replayed"
    webhooks.wait()
    assert db_rows(settings, "SELECT resume_count, queue_state FROM handoff_cases WHERE case_id=?", (case_id,)) == [
        {"resume_count": 1, "queue_state": "answered"}
    ]
    [turn] = operator_turns(client, merchant_a, conversation_id)
    assert turn["text"] == reply["text"] and turn["operator_action"] == "reply" and turn["protocol"] == protocol
    ticket = ticketing.get(f"/tickets/{ticket_id}", headers=ana).json()
    assert ticket["status"] == "pending" and ticket["reply_text"] == reply["text"] and ticket["reply_delivered_at"]
    to_merchant = merchant.get("/merchant/events", params={"conversation_id": conversation_id}).json()["events"]
    assert [e["type"] for e in to_merchant] == ["conversation.replied"] and "operator_id" not in to_merchant[0]["data"]
    again = ticketing.post(f"/tickets/{ticket_id}/actions", headers=ana, json=reply)
    assert again.status_code == 200 and again.json()["delivery"]["replayed"] is True
    other = ticketing.post(
        f"/tickets/{ticket_id}/actions", headers=ana, json=reply | {"idempotency_key": "story-reply-02"}
    )
    assert other.status_code == 409 and other.json()["error"]["code"] == "already_resumed"

    # 12. The merchant comes back: human_reply, via operator, no model call.
    calls = len(llm.calls)
    back = client.post(
        "/messages", json={"message": "Obrigado", "conversation_id": conversation_id}, headers=merchant_a
    )
    assert back.json()["route"] == "human_reply" and back.json()["via"] == "operator"
    assert back.json()["answer"] == reply["text"] and len(llm.calls) == calls

    # 13. op_ana solves the ticket: case closed, handoff.closed received by the ticketing.
    solved = ticketing.post(f"/tickets/{ticket_id}/solve", headers=ana)
    assert solved.status_code == 200 and solved.json()["ticket"]["status"] == "solved"
    webhooks.wait()
    assert client.get(f"/v1/handoffs/{case_id}", headers=ana).json()["queue_state"] == "closed"
    ticket = ticketing.get(f"/tickets/{ticket_id}", headers=ana).json()
    assert ticket["closed_by"] == "op_ana" and ticket["deliveries"]["received"][-1]["event_type"] == "handoff.closed"

    # 14. approve on a new handoff: the draft is released, marked as the attendant's and delivered.
    second = client.post("/messages", json={"message": HANDOFF}, headers=merchant_a).json()
    webhooks.wait()
    approve_ticket = new_ticket(ticketing, ana, second["handoff"]["protocol"])
    approve = {"action": "approve", "text": "", "idempotency_key": "story-approve-01"}
    approved = ticketing.post(f"/tickets/{approve_ticket['ticket_id']}/actions", headers=ana, json=approve)
    assert approved.status_code == 200 and approved.json()["delivery"]["assistant"]["queue_state"] == "answered"
    webhooks.wait()
    [turn] = operator_turns(client, merchant_a, second["conversation_id"])
    assert turn["operator_action"] == "approve" and turn["text"] == approve_ticket["draft_reply"]
    events = merchant.get("/merchant/events", params={"conversation_id": second["conversation_id"]}).json()["events"]
    assert [e["data"]["action"] for e in events] == ["approve"]

    # 15. reject on a new handoff: Support runs once with the instruction, as the operator for the case's merchant.
    third = client.post("/messages", json={"message": HANDOFF}, headers=merchant_a).json()
    webhooks.wait()
    reject_ticket = new_ticket(ticketing, ana, third["handoff"]["protocol"])
    reject = {"action": "reject", "text": INSTRUCTION, "idempotency_key": "story-reject-01"}
    rejected = ticketing.post(f"/tickets/{reject_ticket['ticket_id']}/actions", headers=ana, json=reject)
    answer = rejected.json()["delivery"]["assistant"]
    assert rejected.status_code == 200 and answer["queue_state"] == "rejected" and answer["case_state"] != "handoff"
    lookups = db_rows(
        settings, "SELECT principal_id, customer_id, scope FROM audit_events WHERE tool='get_device_status'"
    )
    assert lookups == [{"principal_id": "operator:op_ana", "customer_id": "cliente1988", "scope": "support:read"}]
    [turn] = operator_turns(client, merchant_a, third["conversation_id"])
    assert turn["operator_action"] == "reject" and "offline" in turn["text"]
    cases = db_rows(settings, "SELECT COUNT(*) AS n FROM handoff_cases")
    assert cases == [{"n": 3}]  # no new intervention after the reject

    # 17. Another merchant: nothing of cliente1988 through the assistant or the ticketing.
    merchant_b = bearer(login(client, "cliente_demo_002")["access_token"])
    refusals = [
        client.get(f"/v1/conversations/{conversation_id}", headers=merchant_b),
        client.get(f"/conversations/{conversation_id}", headers=merchant_b),
        client.get(f"/traces/{handed.json()['request_id']}", headers=merchant_b),
        client.get("/v1/handoffs", headers=merchant_b),
        ticketing.get("/tickets", headers=merchant_b),
        ticketing.get(f"/tickets/{ticket_id}", headers=merchant_b),
    ]
    assert [r.status_code for r in refusals] == [404, 404, 404, 403, 401, 401]
    assert all("cliente1988" not in r.text and protocol not in r.text for r in refusals)

    # The whole story, at the end. The durable outbox (0010) delivered every intention once, in the order of the
    # events, and the ticketing has nothing left to send.
    webhooks.wait()
    outbox = db_rows(
        settings,
        "SELECT event, target, status, attempts, COUNT(*) AS n FROM webhook_outbox "
        "GROUP BY event, target, status, attempts ORDER BY event, target",
    )
    assert [(o["event"], o["target"], o["status"], o["attempts"], o["n"]) for o in outbox] == [
        ("conversation.replied", "merchant", "delivered", 1, 3),
        ("conversation.replied", "ticketing", "delivered", 1, 3),
        ("handoff.closed", "ticketing", "delivered", 1, 1),
        ("handoff.created", "ticketing", "delivered", 1, 3),
    ]
    assert db_rows(settings, "SELECT COUNT(*) AS n FROM webhook_deliveries WHERE status != 'delivered'") == [{"n": 0}]
    sent = [
        d
        for each in ticketing.get("/tickets", headers=ana).json()["tickets"]
        for d in ticketing.get(f"/tickets/{each['ticket_id']}", headers=ana).json()["deliveries"]["sent"]
    ]
    refused = sorted(
        (d["event_type"], d["operator_id"], d["status"], d["response_status"])
        for d in sent
        if d["status"] != "delivered"
    )
    assert len(sent) == 7 and refused == [  # the two refusals of the story, both final: moments 9 and 11
        ("ticket.action", "op_ana", "rejected", 409),
        ("ticket.assigned", "op_bruno", "rejected", 409),
    ]
    [lost] = [d for d in sent if d["idempotency_key"] == reply["idempotency_key"]]  # moment 11: answer lost once
    assert [a["outcome"] for a in lost["attempts"]] == ["network_error", "delivered"]
    # CA-46: one audit row per tool call in every request of the story (the operator's reject included).
    traced = sqlite3.connect(settings.runtime_path / "traces.sqlite3").execute(
        "SELECT SUM(tool_calls) FROM requests"
    ).fetchone()[0]
    audited = db_rows(settings, "SELECT COUNT(*) AS n FROM audit_events WHERE tool NOT LIKE 'handoff%'")[0]["n"]
    assert traced > 1 and audited == traced
    versions = client.get("/ready").json()["versions"]
    assert versions["schema"] == 12 and versions["app"] == "0.9.0"


# --- moment 16: restart between handing off and acting (two processes) ------------------------------------------------

FIRST_PROCESS = textwrap.dedent(
    """
    import json, sys
    from pathlib import Path
    from pydantic import SecretStr
    from fastapi.testclient import TestClient
    from merchant_assistant.api.app import create_app
    from merchant_assistant.api.identity import Principal
    from merchant_assistant.config import Settings
    from merchant_assistant.testing import (TEST_TICKETING_SECRET, TEST_USER_PASSWORDS, offline_orchestrator,
                                            passwords_setting, token_headers)

    sys.path.insert(0, sys.argv[4])
    from story_services import configure, connect_services

    runtime, key_path, ticketing_db = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    settings = Settings(_env_file=None, openai_api_key=None, runtime_dir=runtime, qdrant_url=":memory:",
                        jwt_private_key_path=key_path, demo_mode=True, password_hash_iterations=1000,
                        demo_user_passwords=SecretStr(passwords_setting(TEST_USER_PASSWORDS)),
                        ticketing_client_secret=SecretStr(TEST_TICKETING_SECRET))
    configure(settings)
    orchestrator, _ = offline_orchestrator(settings, with_index=False)
    client = TestClient(create_app(orchestrator, settings))
    ticketing, merchant, webhooks, _ = connect_services(client, settings, ticketing_db)
    response = client.post("/messages", json={"message": "Quero falar com um atendente"},
                           headers=token_headers(client, Principal.merchant("cliente1988"))).json()
    webhooks.wait()
    ana = token_headers(client, Principal.operator("op_ana"))
    [ticket] = ticketing.get("/tickets", params={"status": "new"}, headers=ana).json()["tickets"]
    orchestrator.close()
    print(json.dumps({"protocol": response["handoff"]["protocol"], "conversation_id": response["conversation_id"],
                      "ticket_id": ticket["ticket_id"], "case_id": ticket["case_id"]}))
    """
)


def test_story_moment_16_restart_between_handoff_and_action(offline, settings, tmp_path, jwt_signing_key_path):
    """Process 1 hands off (the ticket is born) and ends; process 2, a new API over the same runtime and the same
    ticketing database, acts on the ticket and resumes the saved checkpoint."""
    module_dir = tmp_path / "story_module"
    module_dir.mkdir()
    shutil.copy(__file__, module_dir / "story_services.py")  # the same wiring helpers, importable by process 1
    ticketing_db = tmp_path / "ticketing" / "ticketing.sqlite3"
    env = os.environ | {"LANGGRAPH_STRICT_MSGPACK": "true", "PYTHONUTF8": "1"}
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            FIRST_PROCESS,
            str(settings.runtime_path),
            str(jwt_signing_key_path),
            str(ticketing_db),
            str(module_dir),
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    first = json.loads(done.stdout.strip().splitlines()[-1])

    configure(settings)
    client, _, _ = offline()  # process 2: a new API over the same runtime (database and checkpoints)
    ticketing, merchant, webhooks, _ = connect_services(client, settings, ticketing_db)
    ana = token_headers(client, Principal.operator("op_ana"))
    assert ticketing.post(f"/tickets/{first['ticket_id']}/assign", headers=ana).status_code == 200
    body = {"action": "reply", "text": "Resposta depois do reinício.", "idempotency_key": "story-restart-01"}
    acted = ticketing.post(f"/tickets/{first['ticket_id']}/actions", headers=ana, json=body)
    assert acted.status_code == 200, acted.text
    assert acted.json()["delivery"]["assistant"]["queue_state"] == "answered"
    webhooks.wait()
    record = client.get(f"/v1/handoffs/{first['case_id']}", headers=ana).json()
    assert record["resume_status"] == "done" and record["resume_count"] == 1 and record["protocol"] == first["protocol"]
    merchant_a = token_headers(client, Principal.merchant("cliente1988"))
    [turn] = operator_turns(client, merchant_a, first["conversation_id"])
    assert turn["text"] == body["text"] and turn["protocol"] == first["protocol"]
    assert ticketing.get(f"/tickets/{first['ticket_id']}", headers=ana).json()["reply_delivered_at"]
    assert merchant.get("/merchant/events", params={"conversation_id": first["conversation_id"]}).json()["events"]
    # The same key after the restart: the record, no second resume, still one operator turn (CA-48).
    again = ticketing.post(f"/tickets/{first['ticket_id']}/actions", headers=ana, json=body)
    assert again.status_code == 200 and again.json()["delivery"]["replayed"] is True
    assert len(operator_turns(client, merchant_a, first["conversation_id"])) == 1
    # The outbox written by the first process (handoff.created) and the second (the reply) is all delivered.
    outbox = db_rows(settings, "SELECT event, target, status, attempts FROM webhook_outbox ORDER BY rowid")
    assert [(o["event"], o["target"], o["status"], o["attempts"]) for o in outbox] == [
        ("handoff.created", "ticketing", "delivered", 1),
        ("conversation.replied", "ticketing", "delivered", 1),
        ("conversation.replied", "merchant", "delivered", 1),
    ]
    assert client.get("/ready").json()["checkpoints"]["threads"] == 1
