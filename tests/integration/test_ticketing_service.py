"""Ticketing service against a fake assistant that follows the v0.7.0 contract (spec, "Contrato entre os times").

The fake assistant issues RS256 tokens with a key generated in the test, publishes its JWKS, serves
`client_credentials` and receives `POST /v1/integrations/ticketing/events`. Nothing here imports the assistant."""

from __future__ import annotations

import json
import time
import urllib.parse
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.service import create_app
from merchant_assistant.ticketing.signing import signature, verify

ASSISTANT = "http://assistant.test"
EVENTS = "/v1/integrations/ticketing/events"
TO_TICKETING = "to-ticketing-secret-fictitious"
TO_ASSISTANT = "to-assistant-secret-fictitious"
CLIENT_ID, CLIENT_SECRET = "ticketing-demo", "client-secret-fictitious"
OPERATORS = {"op_ana", "op_bruno"}


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class Clock:
    def __init__(self) -> None:
        self.at = datetime.now(UTC)

    def __call__(self) -> datetime:
        return self.at

    def advance(self, seconds: float) -> None:
        self.at += timedelta(seconds=seconds)


class FakeAssistant:
    def __init__(self) -> None:
        self.keys = {"kid-1": _key()}
        self.outage = False
        self.revoked_tokens: set[str] = set()
        self.tokens_issued = 0
        self.events: list[dict] = []  # every event that passed signature and token checks
        self.claims: dict[str, str] = {}
        self.resumed: dict[str, str] = {}
        self.on_action = None

    # --- tokens --------------------------------------------------------------------------------------------------

    def token(self, *, kid="kid-1", key=None, typ="at+jwt", **claims) -> str:
        now = int(time.time())
        payload = {
            "iss": ASSISTANT,
            "sub": "operator:op_ana",
            "aud": ["merchant-assistant", "ticketing"],
            "iat": now,
            "nbf": now,
            "exp": now + 3600,
            "jti": uuid.uuid4().hex,
            "client_id": "web",
            "role": "operator",
            "scope": "handoff:operate support:read",
        } | claims
        return jwt.encode(payload, key or self.keys[kid], algorithm="RS256", headers={"kid": kid, "typ": typ})

    def operator(self, operator_id="op_ana", **claims) -> dict:
        return {"Authorization": f"Bearer {self.token(sub=f'operator:{operator_id}', **claims)}"}

    def jwks(self) -> dict:
        keys = []
        for kid, key in self.keys.items():
            jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
            keys.append(jwk | {"kid": kid, "alg": "RS256", "use": "sig"})
        return {"keys": keys}

    # --- HTTP ----------------------------------------------------------------------------------------------------

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.outage:
            raise httpx.ConnectError("assistant down", request=request)
        if request.url.path == "/.well-known/jwks.json":
            return httpx.Response(200, json=self.jwks())
        if request.url.path == "/v1/auth/token":
            form = dict(urllib.parse.parse_qsl(request.content.decode()))
            if form != {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}:
                return httpx.Response(401, json={"error": "invalid_client"})
            self.tokens_issued += 1
            token = self.token(
                sub="service:ticketing",
                aud=["merchant-assistant"],
                role="service",
                client_id=CLIENT_ID,
                scope="handoff:integrate",
                exp=int(time.time()) + 600,
            )
            return httpx.Response(
                200,
                json={"access_token": token, "token_type": "Bearer", "expires_in": 600, "scope": "handoff:integrate"},
            )
        if request.url.path == EVENTS:
            return self._event(request)
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    def _event(self, request: httpx.Request) -> httpx.Response:
        if not verify(TO_ASSISTANT, request.headers.get("x-signature"), request.content, time.time(), 300):
            return httpx.Response(401, json={"error": {"code": "invalid_signature"}})
        bearer = request.headers.get("authorization", "").removeprefix("Bearer ")
        try:
            claims = jwt.decode(
                bearer,
                self.keys["kid-1"].public_key(),
                algorithms=["RS256"],
                audience="merchant-assistant",
                issuer=ASSISTANT,
            )
        except jwt.PyJWTError:
            return httpx.Response(401, json={"error": {"code": "invalid_token"}})
        if claims["jti"] in self.revoked_tokens:
            return httpx.Response(401, json={"error": {"code": "invalid_token"}})
        if "handoff:integrate" not in claims["scope"].split():
            return httpx.Response(403, json={"error": {"code": "insufficient_scope"}})
        event = json.loads(request.content)
        assert request.headers["x-webhook-id"] == event["id"]
        assert request.headers["x-webhook-event"] == event["type"]
        data = event["data"]
        case, operator = data["case_id"], data["operator_id"]
        if any(e["id"] == event["id"] for e in self.events):
            return httpx.Response(200, json={"status": "replayed", "case_state": "x", "queue_state": "x"})
        if operator not in OPERATORS:
            return httpx.Response(422, json={"error": {"code": "unknown_operator"}})
        if event["type"] == "ticket.assigned":
            if self.claims.get(case, operator) != operator:
                return httpx.Response(409, json={"error": {"code": "claimed_by_other"}})
            self.claims[case] = operator
            body = {"status": "accepted", "case_state": "handoff", "queue_state": "claimed"}
        elif event["type"] == "ticket.action":
            if case in self.resumed:
                if self.resumed[case] == data["idempotency_key"]:
                    return httpx.Response(
                        200, json={"status": "replayed", "case_state": "awaiting_customer", "queue_state": "answered"}
                    )
                return httpx.Response(409, json={"error": {"code": "already_resumed"}})
            self.resumed[case] = data["idempotency_key"]
            if self.on_action:
                self.on_action(event)
            body = {"status": "accepted", "case_state": "awaiting_customer", "queue_state": "answered"}
        else:
            body = {"status": "accepted", "case_state": "resolved", "queue_state": "closed"}
        self.events.append(event)
        return httpx.Response(200, json=body)


def send(client: TestClient, event_type: str, data: dict, *, secret=TO_TICKETING, t=None, event_id=None):
    event = {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "created_at": datetime.now(UTC).isoformat(),
        "data": data,
    }
    body = json.dumps(event).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Id": event["id"],
        "X-Webhook-Event": event_type,
        "X-Signature": signature(secret, body, int(time.time()) if t is None else t),
    }
    return client.post("/webhooks/assistant", content=body, headers=headers)


def created(case_id="case_001") -> dict:
    return {
        "case_id": case_id,
        "protocol": "HO-20261103-ABC123",
        "conversation_id": "conv_1",
        "customer_id": "cliente1988",
        "language": "pt",
        "reason": "customer_request",
        "summary": "Lojista pede atendimento humano.",
        "pending_question": "Quando cai o dinheiro?",
        "draft_reply": "Olá! Vou verificar.",
        "transcript": [{"role": "user", "text": "Quero falar com uma pessoa", "at": "2026-11-03T10:00:00Z"}],
    }


@pytest.fixture
def env(tmp_path):
    fake, clock = FakeAssistant(), Clock()
    settings = TicketingSettings(
        db_path=tmp_path / "ticketing.sqlite3",
        assistant_url=ASSISTANT,
        assistant_issuer=ASSISTANT,
        assistant_jwks_url=f"{ASSISTANT}/.well-known/jwks.json",
        inbound_secret=TO_TICKETING,
        outbound_secret=TO_ASSISTANT,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        jwks_min_refresh_s=0,
        outbox_poll_s=0,
    )
    app = create_app(settings, client=httpx.Client(transport=httpx.MockTransport(fake.handler)), now=clock)
    client = TestClient(app)
    return client, fake, clock, app


def ticket_id(client: TestClient, fake: FakeAssistant, case_id="case_001") -> str:
    response = send(client, "handoff.created", created(case_id))
    assert response.status_code == 200, response.text
    return response.json()["ticket_id"]


# --- CA-47: full cycle ---------------------------------------------------------------------------------------------


def test_full_ticket_cycle_with_signed_events_and_service_token(env):
    client, fake, _clock, _app = env
    tid = ticket_id(client, fake)
    ticket = client.get(f"/tickets/{tid}", headers=fake.operator()).json()
    assert ticket["status"] == "new" and ticket["protocol"] == "HO-20261103-ABC123"
    assert ticket["draft_reply"] == "Olá! Vou verificar." and ticket["transcript"][0]["role"] == "user"

    def reply_back(event):  # the assistant resumes and sends conversation.replied before answering
        data = event["data"]
        replied = {
            "case_id": data["case_id"],
            "protocol": "HO-20261103-ABC123",
            "conversation_id": "conv_1",
            "action": data["action"],
            "operator_id": data["operator_id"],
            "reply_text": data["text"],
            "via": "operator",
            "request_id": "req_1",
            "delivered_at": "2026-11-03T10:05:00Z",
        }
        assert send(client, "conversation.replied", replied).status_code == 200

    fake.on_action = reply_back
    assigned = client.post(f"/tickets/{tid}/assign", headers=fake.operator())
    assert assigned.status_code == 200 and assigned.json()["ticket"]["status"] == "open"
    acted = client.post(
        f"/tickets/{tid}/actions",
        headers=fake.operator(),
        json={"action": "reply", "text": "Cai amanhã.", "idempotency_key": "act-0001-reply"},
    )
    assert acted.status_code == 200, acted.text
    assert acted.json()["ticket"]["status"] == "pending"
    assert acted.json()["ticket"]["reply_delivered_at"] == "2026-11-03T10:05:00Z"
    solved = client.post(f"/tickets/{tid}/solve", headers=fake.operator())
    assert solved.status_code == 200 and solved.json()["ticket"]["status"] == "solved"
    closed = {
        "case_id": "case_001",
        "protocol": "HO-20261103-ABC123",
        "closed_at": "2026-11-03T10:10:00Z",
        "closed_by": "operator:op_ana",
    }
    assert send(client, "handoff.closed", closed).status_code == 200

    detail = client.get(f"/tickets/{tid}", headers=fake.operator()).json()
    changes = [
        (e["from_status"], e["to_status"]) for e in detail["events"] if e["kind"] in ("created", "status_changed")
    ]
    assert changes == [(None, "new"), ("new", "open"), ("open", "pending"), ("pending", "solved")]
    assert detail["closed_at"] == "2026-11-03T10:10:00Z" and detail["assignee"] == "op_ana"
    assert [d["event_type"] for d in detail["deliveries"]["received"]] == [
        "handoff.created",
        "conversation.replied",
        "handoff.closed",
    ]
    assert [(d["event_type"], d["status"]) for d in detail["deliveries"]["sent"]] == [
        ("ticket.assigned", "delivered"),
        ("ticket.action", "delivered"),
        ("ticket.solved", "delivered"),
    ]
    assert [e["type"] for e in fake.events] == ["ticket.assigned", "ticket.action", "ticket.solved"]
    action = fake.events[1]["data"]
    assert action == {
        "ticket_id": tid,
        "case_id": "case_001",
        "operator_id": "op_ana",
        "action": "reply",
        "text": "Cai amanhã.",
        "idempotency_key": "act-0001-reply",
    }
    assert fake.tokens_issued == 1  # one client_credentials token, reused
    assert client.get("/tickets?status=solved", headers=fake.operator()).json()["tickets"][0]["ticket_id"] == tid


# --- CA-48: idempotency and assistant conflicts ----------------------------------------------------------------------


def test_same_idempotency_key_returns_the_record_without_a_second_event(env):
    client, fake, _clock, _app = env
    tid = ticket_id(client, fake)
    body = {"action": "approve", "text": "", "idempotency_key": "same-key-123"}
    first = client.post(f"/tickets/{tid}/actions", headers=fake.operator(), json=body)
    again = client.post(f"/tickets/{tid}/actions", headers=fake.operator(), json=body)
    assert first.status_code == again.status_code == 200
    assert again.json()["delivery"]["replayed"] is True
    assert again.json()["delivery"]["event_id"] == first.json()["delivery"]["event_id"]
    assert [e["type"] for e in fake.events] == ["ticket.action"]
    other = client.post(f"/tickets/{tid}/actions", headers=fake.operator(), json=body | {"action": "reject"})
    assert other.status_code == 409 and other.json()["error"]["code"] == "idempotency_key_reused"


def test_assistant_409_returns_with_the_same_code_and_leaves_the_ticket_unchanged(env):
    client, fake, _clock, _app = env
    tid = ticket_id(client, fake)
    assert client.post(f"/tickets/{tid}/assign", headers=fake.operator("op_ana")).status_code == 200
    before = client.get(f"/tickets/{tid}", headers=fake.operator()).json()
    response = client.post(f"/tickets/{tid}/assign", headers=fake.operator("op_bruno"))
    assert response.status_code == 409 and response.json() == {"error": {"code": "claimed_by_other"}}
    after = client.get(f"/tickets/{tid}", headers=fake.operator()).json()
    assert (after["status"], after["assignee"]) == (before["status"], before["assignee"]) == ("open", "op_ana")

    ok = {"action": "reply", "text": "Resposta.", "idempotency_key": "first-key-1"}
    assert client.post(f"/tickets/{tid}/actions", headers=fake.operator(), json=ok).status_code == 200
    second = client.post(f"/tickets/{tid}/actions", headers=fake.operator(), json=ok | {"idempotency_key": "other-k-2"})
    assert second.status_code == 409 and second.json()["error"]["code"] == "already_resumed"
    assert client.get(f"/tickets/{tid}", headers=fake.operator()).json()["status"] == "pending"


def test_assistant_422_unknown_operator_returns_with_the_same_code(env):
    client, fake, _clock, _app = env
    tid = ticket_id(client, fake)
    response = client.post(f"/tickets/{tid}/assign", headers=fake.operator("op_carla"))
    assert response.status_code == 422 and response.json()["error"]["code"] == "unknown_operator"
    assert client.get(f"/tickets/{tid}", headers=fake.operator()).json()["status"] == "new"


def test_unknown_ticket_and_local_validation(env):
    client, fake, _clock, _app = env
    assert client.post("/tickets/tkt_missing/assign", headers=fake.operator()).status_code == 404
    tid = ticket_id(client, fake)
    short = client.post(
        f"/tickets/{tid}/actions",
        headers=fake.operator(),
        json={"action": "reply", "text": "x", "idempotency_key": "short"},
    )
    assert short.status_code == 422
    assert client.get("/tickets?status=closed", headers=fake.operator()).status_code == 422
    assert fake.events == []


# --- webhooks received from the assistant -----------------------------------------------------------------------------


def test_repeated_webhook_id_has_no_new_effect(env):
    client, fake, _clock, _app = env
    first = send(client, "handoff.created", created(), event_id="evt_fixed")
    again = send(client, "handoff.created", created(), event_id="evt_fixed")
    assert first.status_code == again.status_code == 200
    assert again.json()["status"] == "duplicate"
    assert len(client.get("/tickets", headers=fake.operator()).json()["tickets"]) == 1


@pytest.mark.parametrize(
    "kwargs",
    [{"secret": "wrong-secret"}, {"offset": -330}, {"offset": 330}],
    ids=["wrong-secret", "too-old", "too-new"],
)
def test_bad_webhook_signature_is_rejected_without_effect(env, kwargs):
    client, fake, _clock, _app = env
    if "offset" in kwargs:
        kwargs = {"t": int(time.time()) + kwargs["offset"]}
    response = send(client, "handoff.created", created(), **kwargs)
    assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_signature"
    assert client.get("/tickets", headers=fake.operator()).json()["tickets"] == []


def test_replied_for_unknown_case_is_not_recorded(env):
    client, _fake, _clock, _app = env
    response = send(client, "conversation.replied", {"case_id": "case_none"}, event_id="evt_early")
    assert response.status_code == 404
    send(client, "handoff.created", created("case_none"))
    assert send(client, "conversation.replied", {"case_id": "case_none"}, event_id="evt_early").status_code == 200


# --- operator JWT --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("claims", "status"),
    [
        ({"aud": ["merchant-assistant"]}, 401),
        ({"iss": "http://other-issuer.test"}, 401),
        ({"exp": -120, "iat": -3720, "nbf": -3720}, 401),
        ({"scope": "support:read"}, 403),
        ({"role": "merchant", "sub": "merchant:cliente1988", "customer_id": "cliente1988"}, 403),
    ],
    ids=["no-ticketing-audience", "other-issuer", "expired", "no-operate-scope", "merchant"],
)
def test_operator_token_rules(env, claims, status):
    client, fake, _clock, _app = env
    claims = {k: int(time.time()) + v if k in ("exp", "iat", "nbf") else v for k, v in claims.items()}
    response = client.get("/tickets", headers={"Authorization": f"Bearer {fake.token(**claims)}"})
    assert response.status_code == status
    assert response.headers["www-authenticate"].startswith("Bearer")


def test_missing_tampered_or_foreign_tokens_are_401(env):
    client, fake, _clock, _app = env
    assert client.get("/tickets").status_code == 401
    token = fake.token()
    head, payload, sig = token.split(".")
    assert client.get("/tickets", headers={"Authorization": f"Bearer {head}.{payload}.{sig[::-1]}"}).status_code == 401
    foreign = fake.token(key=_key())  # right kid, wrong private key
    assert client.get("/tickets", headers={"Authorization": f"Bearer {foreign}"}).status_code == 401
    unknown_kid = fake.token(kid="kid-x", key=_key())
    assert client.get("/tickets", headers={"Authorization": f"Bearer {unknown_kid}"}).status_code == 401
    wrong_typ = fake.token(typ="JWT")
    assert client.get("/tickets", headers={"Authorization": f"Bearer {wrong_typ}"}).status_code == 401


def test_unknown_kid_reloads_the_jwks(env):
    client, fake, _clock, _app = env
    assert client.get("/tickets", headers=fake.operator()).status_code == 200
    fake.keys["kid-2"] = _key()  # key rotation on the assistant
    assert client.get("/tickets", headers={"Authorization": f"Bearer {fake.token(kid='kid-2')}"}).status_code == 200


# --- assistant unavailable -----------------------------------------------------------------------------------------


def test_assistant_down_keeps_the_act_pending_and_records_retries(env):
    client, fake, clock, app = env
    tid = ticket_id(client, fake)
    assert client.get("/tickets", headers=fake.operator()).status_code == 200  # JWKS cached before the outage
    fake.outage = True
    response = client.post(f"/tickets/{tid}/assign", headers=fake.operator())
    assert response.status_code == 202
    assert response.json()["delivery"]["status"] == "pending"
    assert response.json()["ticket"]["status"] == "new"
    assert response.json()["ticket"]["delivery"]["status"] == "pending"
    busy = client.post(f"/tickets/{tid}/solve", headers=fake.operator())
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "delivery_pending"

    dispatcher = app.state.dispatcher
    assert dispatcher.dispatch_due() == []  # the 1 s wait has not passed
    clock.advance(1.1)
    assert [d.status for d in dispatcher.dispatch_due()] == ["pending"]
    clock.advance(2.1)
    assert [d.status for d in dispatcher.dispatch_due()] == ["failed"]
    sent = client.get(f"/tickets/{tid}", headers=fake.operator()).json()["deliveries"]["sent"][0]
    assert [a["outcome"] for a in sent["attempts"]] == ["network_error"] * 3 and sent["status"] == "failed"

    fake.outage = False
    retried = client.post(f"/tickets/{tid}/assign", headers=fake.operator())
    assert retried.status_code == 200 and retried.json()["ticket"]["status"] == "open"


def test_pending_act_is_delivered_when_the_assistant_returns(env):
    client, fake, clock, app = env
    tid = ticket_id(client, fake)
    client.get("/tickets", headers=fake.operator())
    fake.outage = True
    body = {"action": "approve", "text": "", "idempotency_key": "retry-key-01"}
    assert client.post(f"/tickets/{tid}/actions", headers=fake.operator(), json=body).status_code == 202
    fake.outage = False
    clock.advance(1.1)
    assert [d.status for d in app.state.dispatcher.dispatch_due()] == ["delivered"]
    again = client.post(f"/tickets/{tid}/actions", headers=fake.operator(), json=body)
    assert again.status_code == 200 and again.json()["ticket"]["status"] == "pending"
    assert [e["type"] for e in fake.events] == ["ticket.action"]


def test_revoked_service_token_is_renewed_once(env):
    client, fake, _clock, _app = env
    tid = ticket_id(client, fake)
    assert client.post(f"/tickets/{tid}/assign", headers=fake.operator()).status_code == 200
    fake.revoked_tokens.add(jwt.decode(_app.state.dispatcher.token.get(), options={"verify_signature": False})["jti"])
    assert client.post(f"/tickets/{tid}/solve", headers=fake.operator()).status_code == 200
    assert fake.tokens_issued == 2


def test_background_loop_delivers_a_pending_act(tmp_path):
    fake = FakeAssistant()
    settings = TicketingSettings(
        db_path=tmp_path / "ticketing.sqlite3",
        assistant_url=ASSISTANT,
        assistant_issuer=ASSISTANT,
        assistant_jwks_url=f"{ASSISTANT}/.well-known/jwks.json",
        inbound_secret=TO_TICKETING,
        outbound_secret=TO_ASSISTANT,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        retry_waits_s=(0.05, 0.05),
        outbox_poll_s=0.05,
    )
    app = create_app(settings, client=httpx.Client(transport=httpx.MockTransport(fake.handler)))
    with TestClient(app) as client:
        tid = ticket_id(client, fake)
        client.get("/tickets", headers=fake.operator())
        fake.outage = True
        assert client.post(f"/tickets/{tid}/assign", headers=fake.operator()).status_code == 202
        fake.outage = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not fake.events:
            time.sleep(0.05)
        assert [e["type"] for e in fake.events] == ["ticket.assigned"]
        assert client.get(f"/tickets/{tid}", headers=fake.operator()).json()["status"] == "open"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/tickets"),
        ("get", "/tickets/{tid}"),
        ("post", "/tickets/{tid}/assign"),
        ("post", "/tickets/{tid}/actions"),
        ("post", "/tickets/{tid}/solve"),
    ],
)
def test_every_operator_endpoint_requires_the_token(env, method, path):
    client, fake, _clock, _app = env
    tid = ticket_id(client, fake)
    kwargs = {"json": {"action": "approve", "text": "", "idempotency_key": "no-token-key"}} if "actions" in path else {}
    response = getattr(client, method)(path.format(tid=tid), **kwargs)
    assert response.status_code == 401
    assert fake.events == []
