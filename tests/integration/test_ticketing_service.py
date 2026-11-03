"""Ticketing service against a fake assistant that follows the v0.7.0 contract (spec, "Contrato entre os times").

The fake assistant issues RS256 tokens with a key generated in the test, publishes its JWKS, serves
`client_credentials` and receives `POST /v1/integrations/ticketing/events`. Nothing here imports the assistant."""

from __future__ import annotations

import base64
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


def err(status: int, code: str, **headers) -> httpx.Response:
    """Assistant error envelope of the contract: {"error": {"code", "message", "request_id"}}."""
    if status in (401, 403):
        headers.setdefault("WWW-Authenticate", "Bearer")
    body = {"error": {"code": code, "message": code.replace("_", " "), "request_id": "req_fake"}}
    return httpx.Response(status, json=body, headers=headers)


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
        self.token_status: int | None = None  # forced status of /v1/auth/token (429 or 401)
        self.events_status: int | None = None  # forced status of the events endpoint (429)
        self.token_raw: bytes | None = None  # forced 200 body of /v1/auth/token (malformed answers)
        self.events_raw: bytes | None = None  # forced 200 body of the events endpoint (malformed answers)
        self.events_delay = 0.0  # a slow assistant, to exercise the outbox lease

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
            if self.token_raw is not None:
                return httpx.Response(200, content=self.token_raw, headers={"Content-Type": "application/json"})
            if self.token_status == 429:
                return httpx.Response(
                    429,
                    json={"error": "invalid_request", "error_description": "slow down"},
                    headers={"Retry-After": "7"},
                )
            form = dict(urllib.parse.parse_qsl(request.content.decode()))
            basic = request.headers.get("authorization", "")
            if basic.startswith("Basic "):  # RFC 6749 2.3.1: secret in the header instead of the form
                client_id, _, secret = base64.b64decode(basic[6:]).decode().partition(":")
                form |= {"client_id": client_id, "client_secret": secret}
            if form.get("grant_type") != "client_credentials":
                return httpx.Response(400, json={"error": "unsupported_grant_type", "error_description": "grant"})
            creds = (form.get("client_id"), form.get("client_secret"))
            if self.token_status == 401 or creds != (CLIENT_ID, CLIENT_SECRET):
                return httpx.Response(
                    401,
                    json={"error": "invalid_client", "error_description": "client"},
                    headers={"WWW-Authenticate": "Basic"},
                )
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
        return err(404, "not_found")

    def _event(self, request: httpx.Request) -> httpx.Response:
        if self.events_delay:
            time.sleep(self.events_delay)
        if self.events_raw is not None:
            self.events.append(json.loads(request.content))
            return httpx.Response(200, content=self.events_raw, headers={"Content-Type": "application/json"})
        if not verify(TO_ASSISTANT, request.headers.get("x-signature"), request.content, time.time(), 300):
            return err(401, "invalid_signature")
        if self.events_status == 429:
            return err(429, "rate_limited", **{"Retry-After": "7"})
        bearer = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not bearer:
            return err(401, "token_required")
        try:
            claims = jwt.decode(
                bearer,
                self.keys["kid-1"].public_key(),
                algorithms=["RS256"],
                audience="merchant-assistant",
                issuer=ASSISTANT,
            )
        except jwt.PyJWTError:
            return err(401, "invalid_token")
        if claims["jti"] in self.revoked_tokens:
            return err(401, "invalid_token")
        if "handoff:integrate" not in claims["scope"].split():
            return err(403, "insufficient_scope")
        event = json.loads(request.content)
        assert request.headers["x-webhook-id"] == event["id"]
        assert request.headers["x-webhook-event"] == event["type"]
        data = event["data"]
        case, operator = data["case_id"], data["operator_id"]
        if any(e["id"] == event["id"] for e in self.events):
            return httpx.Response(200, json={"status": "replayed", "case_state": "x", "queue_state": "x"})
        if operator not in OPERATORS:
            return err(422, "unknown_operator")
        if event["type"] == "ticket.assigned":
            if self.claims.get(case, operator) != operator:
                return err(409, "claimed_by_other")
            self.claims[case] = operator
            body = {"status": "accepted", "case_state": "handoff", "queue_state": "claimed"}
        elif event["type"] == "ticket.action":
            if case in self.resumed:
                if self.resumed[case] == data["idempotency_key"]:
                    return httpx.Response(
                        200, json={"status": "replayed", "case_state": "awaiting_customer", "queue_state": "answered"}
                    )
                return err(409, "already_resumed")
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
    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "claimed_by_other", "message": "claimed by other", "request_id": "req_fake"}
    }
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
    expected = "invalid_token" if status == 401 else "insufficient_scope"
    assert response.json()["error"]["code"] == expected


def test_missing_tampered_or_foreign_tokens_are_401(env):
    client, fake, _clock, _app = env
    missing = client.get("/tickets")
    assert missing.status_code == 401 and missing.json()["error"]["code"] == "token_required"
    assert missing.headers["www-authenticate"].startswith("Bearer")
    assert missing.json()["error"]["request_id"].startswith("req_")
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


def test_token_endpoint_errors(env):
    """RFC 6749 errors: invalid_client is a configuration error (502); 429 keeps the act pending and honors
    Retry-After."""
    client, fake, clock, app = env
    tid = ticket_id(client, fake)
    client.get("/tickets", headers=fake.operator())
    fake.token_status = 401
    rejected = client.post(f"/tickets/{tid}/assign", headers=fake.operator())
    assert rejected.status_code == 502 and rejected.json()["error"]["code"] == "assistant_rejected"
    assert client.get(f"/tickets/{tid}", headers=fake.operator()).json()["status"] == "new"

    fake.token_status = 429
    pending = client.post(f"/tickets/{tid}/assign", headers=fake.operator())
    assert pending.status_code == 202
    fake.token_status = None
    clock.advance(2)  # more than the 1 s wait, less than Retry-After
    assert app.state.dispatcher.dispatch_due() == []
    clock.advance(5.5)
    assert [d.status for d in app.state.dispatcher.dispatch_due()] == ["delivered"]


def test_assistant_rate_limit_waits_retry_after(env):
    client, fake, clock, app = env
    tid = ticket_id(client, fake)
    fake.events_status = 429
    assert client.post(f"/tickets/{tid}/assign", headers=fake.operator()).status_code == 202
    fake.events_status = None
    clock.advance(2)
    assert app.state.dispatcher.dispatch_due() == []
    clock.advance(5.5)
    assert [d.status for d in app.state.dispatcher.dispatch_due()] == ["delivered"]
    assert fake.tokens_issued == 1  # a 429 does not renew the service token


def test_service_can_obtain_the_token_with_basic_auth_too():
    fake = FakeAssistant()
    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    response = fake.handler(
        httpx.Request(
            "POST",
            f"{ASSISTANT}/v1/auth/token",
            content=b"grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
        )
    )
    assert response.status_code == 200  # the fake follows the contract; the service itself sends the form


# --- round 2 (review of task 66b) ---------------------------------------------------------------------------------


def test_outbox_lease_lets_one_worker_send_while_the_assistant_is_slow(env):
    """P3-1: two workers on the same pending event while the assistant takes 0.4 s: one POST only."""
    import threading

    from merchant_assistant.ticketing.outbox import envelope

    client, fake, clock, app = env
    tid = ticket_id(client, fake)
    store, dispatcher = app.state.store, app.state.dispatcher
    data = {"ticket_id": tid, "case_id": "case_001", "operator_id": "op_ana"}
    outcome, row = store.enqueue(tid, envelope("ticket.assigned", data, clock()), "op_ana", clock())
    assert outcome == "created"
    dispatcher.token.get()  # token fetched before the race, so both workers race only for the event
    fake.events_delay = 0.4
    barrier, results = threading.Barrier(2), []

    def work():
        barrier.wait()
        results.append(dispatcher.deliver(row["event_id"]).status)

    threads = [threading.Thread(target=work) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert sorted(results) == ["delivered", "pending"]  # the loser sees the event still pending (in flight)
    assert [e["type"] for e in fake.events] == ["ticket.assigned"]
    assert store.get_outbox(row["event_id"])["attempts"] == 1


def _hand_made_token(header: dict, payload: dict, signer=None) -> str:
    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    signing_input = f"{b64(json.dumps(header).encode())}.{b64(json.dumps(payload).encode())}"
    return f"{signing_input}.{b64(signer(signing_input.encode())) if signer else ''}"


def test_alg_none_and_hs256_with_the_public_key_are_rejected(env):
    """P3-2: algorithm confusion never reaches the claims."""
    import hashlib
    import hmac

    from cryptography.hazmat.primitives import serialization

    client, fake, _clock, _app = env
    claims = jwt.decode(fake.token(), options={"verify_signature": False})
    none_token = _hand_made_token({"alg": "none", "typ": "at+jwt", "kid": "kid-1"}, claims)
    public_pem = (
        fake.keys["kid-1"]
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    hs_token = _hand_made_token(
        {"alg": "HS256", "typ": "at+jwt", "kid": "kid-1"},
        claims,
        lambda data: hmac.new(public_pem, data, hashlib.sha256).digest(),
    )
    for token in (none_token, hs_token):
        response = client.get("/tickets", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_token"


@pytest.mark.parametrize("raw", [b"not json", b"[1, 2]", b'{"token_type": "Bearer"}'], ids=["text", "list", "no-token"])
def test_malformed_token_answer_is_a_recorded_failure(env, raw):
    """P3-3: no 500, no lease left behind, the next act is not blocked."""
    client, fake, clock, app = env
    tid = ticket_id(client, fake)
    client.get("/tickets", headers=fake.operator())
    fake.token_raw = raw
    response = client.post(f"/tickets/{tid}/assign", headers=fake.operator())
    assert response.status_code == 502 and response.json()["error"]["code"] == "service_token_malformed"
    sent = client.get(f"/tickets/{tid}", headers=fake.operator()).json()["deliveries"]["sent"][0]
    assert sent["status"] == "rejected" and [a["outcome"] for a in sent["attempts"]] == ["rejected"]
    clock.advance(60)
    assert app.state.dispatcher.dispatch_due() == []  # no resend loop
    fake.token_raw = None
    assert client.post(f"/tickets/{tid}/assign", headers=fake.operator()).status_code == 200


@pytest.mark.parametrize("raw", [b"[]", b"not json", b'{"ok": true}'], ids=["list", "text", "no-status"])
def test_malformed_event_answer_is_a_recorded_failure(env, raw):
    """P3-3: a 200 without the contract body is recorded as rejected, the ticket does not move, no resend."""
    client, fake, clock, app = env
    tid = ticket_id(client, fake)
    fake.events_raw = raw
    response = client.post(f"/tickets/{tid}/assign", headers=fake.operator())
    assert response.status_code == 502 and response.json()["error"]["code"] == "assistant_malformed_response"
    detail = client.get(f"/tickets/{tid}", headers=fake.operator()).json()
    assert detail["status"] == "new" and detail["deliveries"]["sent"][0]["status"] == "rejected"
    clock.advance(60)
    assert app.state.dispatcher.dispatch_due() == [] and len(fake.events) == 1  # sent once, never again


def test_missing_credential_challenge_has_no_error_code(env):
    """P3-4: RFC 6750 section 3.1, as the assistant does."""
    client, _fake, _clock, _app = env
    missing = client.get("/tickets")
    assert missing.status_code == 401 and missing.headers["www-authenticate"] == "Bearer"
    invalid = client.get("/tickets", headers={"Authorization": "Bearer garbage"})
    assert invalid.headers["www-authenticate"] == 'Bearer error="invalid_token"'


def test_another_operator_cannot_replay_a_key(env):
    """P3-6: the idempotency fingerprint includes the operator."""
    client, fake, _clock, _app = env
    tid = ticket_id(client, fake)
    body = {"action": "approve", "text": "", "idempotency_key": "shared-key-01"}
    assert client.post(f"/tickets/{tid}/actions", headers=fake.operator("op_ana"), json=body).status_code == 200
    other = client.post(f"/tickets/{tid}/actions", headers=fake.operator("op_bruno"), json=body)
    assert other.status_code == 409 and other.json()["error"]["code"] == "idempotency_key_reused"
    assert [e["type"] for e in fake.events] == ["ticket.action"]
