"""v0.13.0 task 100 (spec D3, CA-69): the operator works a handed-off case from Telegram.

The assistant (scripted model) delivers `handoff.created` to the adapter over the signed webhook; the adapter talks to a
fake Bot API in process (`httpx.MockTransport`) and calls the assistant's `/v1/handoffs` through a test transport. The
token endpoint of that transport answers the `client_credentials` grant of `telegram-operator` with an operator token
the assistant's own issuer signs. No network, no Telegram, no cost."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks, signature
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.webhook_outbox import webhook_targets
from merchant_assistant.integrations import telegram
from merchant_assistant.integrations.telegram import (
    ConfigError,
    OperatorToken,
    TelegramSettings,
    create_app,
)
from merchant_assistant.testing import AppTransport, merchant_headers, token_headers

ASSISTANT, TELEGRAM = "assistant.test", "telegram.test"
BOT_TOKEN = "123456789:AAH-fake_bot_token_for_tests_0123456789"
CHAT, OTHER_CHAT = -1001234567890, 4242
BOT_USERNAME = "getnet_operator_bot"
WEBHOOK_SECRET = "it-telegram-webhook-secret"
CLIENT_SECRET = "it-telegram-client-secret"
HUMAN = "Quero falar com um atendente"
CARD, CPF = "4111 1111 1111 1111", "123.456.789-09"


class Crash(BaseException):
    """A process dying in the middle of a command (not an Exception: nothing in the adapter catches it)."""


class FakeBot:
    """The Bot API methods the adapter uses. `getUpdates` forgets what an offset confirmed, as Telegram does."""

    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.sent: list[dict] = []
        self.calls: list[tuple[str, dict]] = []
        self.fail: dict[str, object] = {}
        self._message_id = 500

    def handler(self, request: httpx.Request) -> httpx.Response:
        prefix = f"/bot{BOT_TOKEN}/"
        assert request.url.host == "api.telegram.org" and request.url.path.startswith(prefix)
        method = request.url.path[len(prefix):]
        payload = json.loads(request.content or b"{}")
        self.calls.append((method, payload))
        failure = self.fail.get(method)
        if isinstance(failure, Exception):
            raise failure
        if failure:
            return httpx.Response(failure, json={"ok": False, "error_code": failure, "description": "fake failure"})
        if method == "sendMessage":
            self._message_id += 1
            self.sent.append(payload | {"message_id": self._message_id})
            return httpx.Response(200, json={"ok": True, "result": {"message_id": self._message_id}})
        if method == "getUpdates":
            offset = payload.get("offset", 0)
            pending = [u for u in self.updates if u["update_id"] >= offset]
            return httpx.Response(200, json={"ok": True, "result": pending})
        if method == "answerCallbackQuery":
            return httpx.Response(200, json={"ok": True, "result": True})
        if method == "getMe":
            bot = {"id": 123456789, "is_bot": True, "first_name": "Operador", "username": BOT_USERNAME}
            return httpx.Response(200, json={"ok": True, "result": bot})
        return httpx.Response(404, json={"ok": False, "error_code": 404})


class OperatorApi(httpx.BaseTransport):
    """The adapter's view of the assistant: `/v1/auth/token` issues the operator token of `telegram-operator` (checking
    its secret), every other request goes to the assistant app. `before`/`after` let a test fail or crash a call."""

    def __init__(self, assistant: TestClient) -> None:
        self.assistant = assistant
        self.requests: list[httpx.Request] = []
        self.tokens = 0
        self.before = None
        self.after = None
        self.real_tokens = False  # True: the assistant's own `/v1/auth/token` issues the token (client registered)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/auth/token" and not self.real_tokens:
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            if form != {
                "grant_type": "client_credentials", "client_id": "telegram-operator", "client_secret": CLIENT_SECRET
            }:
                return httpx.Response(401, json={"error": "invalid_client"}, request=request)
            self.tokens += 1
            issued = self.assistant.app.state.identity.issue(Principal.operator("telegram"), "telegram-operator")
            return httpx.Response(200, json=issued, request=request)
        self.requests.append(request)
        if self.before and (early := self.before(request)) is not None:
            return early
        response = self.assistant._transport.handle_request(request)
        content = response.read()
        if self.after:
            self.after(request)
        return httpx.Response(response.status_code, headers=response.headers, content=content, request=request)

    def actions(self) -> list[dict]:
        return [json.loads(r.content) for r in self.requests if r.url.path.endswith("/actions")]


def adapter_settings(tmp_path, **overrides) -> TelegramSettings:
    values = {
        "bot_token": BOT_TOKEN,
        "operator_chat_id": CHAT,
        "webhook_secret": WEBHOOK_SECRET,
        "client_secret": CLIENT_SECRET,
        "db_path": tmp_path / "telegram" / "telegram.sqlite3",
        "assistant_url": f"http://{ASSISTANT}",
        "poll_timeout_s": 0,
    } | overrides
    return TelegramSettings(**values)


@pytest.fixture
def system(offline, settings, tmp_path):
    settings.telegram_webhook_url = f"http://{TELEGRAM}/webhooks/assistant"
    settings.telegram_webhook_secret = SecretStr(WEBHOOK_SECRET)
    assistant, _, _ = offline()
    bot, api = FakeBot(), OperatorApi(assistant)

    def start():
        """A (re)started adapter over the same database, Bot API and assistant."""
        app = create_app(
            adapter_settings(tmp_path),
            bot_client=httpx.Client(transport=httpx.MockTransport(bot.handler)),
            api_client=httpx.Client(transport=api),
            poll=False,
        )
        client = TestClient(app)
        apps[TELEGRAM] = client
        return app.state.operator

    apps: dict[str, TestClient] = {}
    operator = start()
    webhooks = Webhooks(settings, transport=AppTransport(apps), sleep=lambda _s: None)
    assistant.app.state.webhooks = webhooks
    return SimpleNamespace(
        assistant=assistant, settings=settings, bot=bot, api=api, operator=operator, webhooks=webhooks, start=start,
        apps=apps, tmp_path=tmp_path,
    )


def open_case(s, message: str = HUMAN) -> dict:
    """A merchant asks for a human; the case reaches the operator chat. Returns the turn and the case message."""
    response = s.assistant.post("/messages", json={"message": message}, headers=merchant_headers(s.assistant))
    assert response.status_code == 200 and response.json()["status"] == "handoff", response.text
    assert s.webhooks.wait()
    turn = response.json()
    case_message = next(m for m in s.bot.sent if turn["handoff"]["protocol"] in m["text"])
    return {"turn": turn, "message": case_message, "protocol": turn["handoff"]["protocol"]}


def case_row(s, protocol: str) -> sqlite3.Row:
    conn = sqlite3.connect(s.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM handoff_cases WHERE protocol=?", (protocol,)).fetchone()
    finally:
        conn.close()


def command(update_id: int, text: str, reply_to: int | None = None, chat: int = CHAT) -> dict:
    message = {"message_id": 9000 + update_id, "date": 0, "chat": {"id": chat, "type": "group"}, "text": text}
    if reply_to is not None:
        message["reply_to_message"] = {"message_id": reply_to, "chat": {"id": chat}}
    return {"update_id": update_id, "message": message}


def press(update_id: int, data: str, message_id: int, chat: int = CHAT) -> dict:
    message = {"message_id": message_id, "chat": {"id": chat}}
    return {"update_id": update_id, "callback_query": {"id": f"cb-{update_id}", "data": data, "message": message}}


def deliver(s, *updates: dict) -> list[dict]:
    """The operator sends the updates; one polling round reads them. Returns the messages sent in that round."""
    before = len(s.bot.sent)
    s.bot.updates.extend(updates)
    s.operator.poll_once()
    return s.bot.sent[before:]


def signed(body: dict, at: float | None = None) -> tuple[bytes, dict]:
    raw = json.dumps(body).encode()
    return raw, {"X-Signature": signature(WEBHOOK_SECRET, raw, int(time.time() if at is None else at))}


def created(case_id="hc_0123456789abcdef", protocol="HO-20261107-A1B2C3", summary="Repasse atrasado.", event="evt_1"):
    return {"id": event, "type": "handoff.created", "created_at": "2026-11-07T10:00:00+00:00",
            "data": {"case_id": case_id, "protocol": protocol, "summary": summary}}


# --- the case reaches the operator chat ------------------------------------------------------------------------------


def test_case_reaches_the_operator_chat_with_protocol_and_masked_summary_only(system):
    s = system
    opened = open_case(s, f"{HUMAN}. Meu cartão é {CARD}, CPF {CPF}, senha: abc12345")
    sent = opened["message"]
    assert sent["chat_id"] == CHAT and sent["text"].startswith(f"Novo caso encaminhado: {opened['protocol']}")
    buttons = [b["callback_data"] for b in sent["reply_markup"]["inline_keyboard"][0]]
    case_id = case_row(s, opened["protocol"])["case_id"]
    assert buttons == [f"claim:{case_id}", f"approve:{case_id}"]
    every_text = " ".join(m["text"] for m in s.bot.sent)
    for leaked in (CARD, CARD.replace(" ", ""), CPF, "abc12345", "cliente1988", BOT_TOKEN):
        assert leaked not in every_text
    conn = sqlite3.connect(s.settings.db_path)
    body = json.loads(conn.execute("SELECT body FROM webhook_outbox WHERE target='telegram'").fetchone()[0])
    conn.close()
    assert set(body["data"]) == {"case_id", "protocol", "summary"}  # no transcript, merchant or draft leaves


def test_adapter_masks_again_and_never_shows_more_than_the_summary(system):
    s = system
    summary = f"Cartão {CARD}, CPF {CPF}, CNPJ 12.345.678/0001-90, token: sk-abcdefghijklmnopqrstu, e-mail a@b.com"
    event = created(summary=summary) | {"data": created()["data"] | {
        "summary": summary, "transcript": [{"text": CARD}], "customer_id": "cliente1988", "draft_reply": "rascunho"
    }}
    raw, headers = signed(event)
    response = adapter(s).post("/webhooks/assistant", content=raw, headers=headers)
    assert response.status_code == 200 and response.json() == {"status": "accepted"}
    [sent] = s.bot.sent
    for leaked in (CARD, CPF, "12.345.678/0001-90", "sk-abcdefghijklmnopqrstu", "a@b.com", "cliente1988", "rascunho"):
        assert leaked not in sent["text"]
    assert "[card number removed]" in sent["text"] and "[CPF removed]" in sent["text"]


def adapter(s) -> TestClient:
    """The adapter's HTTP side, as the assistant's webhook dispatcher reaches it."""
    return s.apps[TELEGRAM]


def test_webhook_signature_window_and_event_id_are_checked(system):
    s = system
    client = adapter(s)
    raw, headers = signed(created())
    forged = {"X-Signature": f"t={int(time.time())},v1=" + "0" * 64}
    assert client.post("/webhooks/assistant", content=raw, headers=forged).status_code == 401
    assert client.post("/webhooks/assistant", content=raw).status_code == 401
    stale_raw, stale = signed(created(), at=time.time() - 301)
    assert client.post("/webhooks/assistant", content=stale_raw, headers=stale).status_code == 401
    other_raw, other = signed(created() | {"type": "conversation.replied"})
    assert client.post("/webhooks/assistant", content=other_raw, headers=other).status_code == 422
    tampered = raw.replace(b"A1B2C3", b"A1B2C4")
    assert client.post("/webhooks/assistant", content=tampered, headers=headers).status_code == 401
    assert s.bot.sent == []
    assert client.post("/webhooks/assistant", content=raw, headers=headers).json() == {"status": "accepted"}
    assert client.post("/webhooks/assistant", content=raw, headers=headers).json() == {"status": "replayed"}
    assert len(s.bot.sent) == 1  # the same event id never reaches the chat twice


def test_telegram_down_answers_503_and_the_assistant_retry_sends_the_case_once(system):
    s = system
    client = adapter(s)
    s.bot.fail["sendMessage"] = 502
    raw, headers = signed(created())
    refused = client.post("/webhooks/assistant", content=raw, headers=headers)
    assert refused.status_code == 503 and refused.json()["error"]["code"] == "telegram_unavailable"
    del s.bot.fail["sendMessage"]
    assert client.post("/webhooks/assistant", content=raw, headers=headers).json() == {"status": "accepted"}
    assert len(s.bot.sent) == 1


# --- commands --------------------------------------------------------------------------------------------------------


def test_claim_approve_reply_and_reject_reach_the_queue_with_keys_from_the_update(system):
    s = system
    first = open_case(s)
    [claimed] = deliver(s, command(1, "/claim", reply_to=first["message"]["message_id"]))
    assert claimed["text"] == f"Caso {first['protocol']} assumido."
    row = case_row(s, first["protocol"])
    assert row["claimed_by"] == "telegram" and row["queue_state"] == "claimed"
    [approved] = deliver(s, command(2, "/approve@getnet_operator_bot", reply_to=first["message"]["message_id"]))
    assert approved["text"] == f"Rascunho aprovado; a resposta segue ao lojista ({first['protocol']})."
    assert case_row(s, first["protocol"])["queue_state"] == "answered"

    second = open_case(s)
    [replied] = deliver(s, command(3, f"/reply {second['protocol']} Seu repasse foi enviado hoje."))
    assert replied["text"] == f"Resposta enviada ao lojista ({second['protocol']})."

    third = open_case(s)
    [rejected] = deliver(
        s, command(4, "/reject Verifique o status da maquininha.", reply_to=third["message"]["message_id"])
    )
    assert rejected["text"] == f"Instrução enviada ao agente; a nova resposta segue ao lojista ({third['protocol']})."
    assert case_row(s, third["protocol"])["queue_state"] == "rejected"
    assert s.api.actions() == [
        {"action": "approve", "idempotency_key": "telegram-2"},
        {"action": "reply", "idempotency_key": "telegram-3", "text": "Seu repasse foi enviado hoje."},
        {"action": "reject", "idempotency_key": "telegram-4", "text": "Verifique o status da maquininha."},
    ]
    assert s.api.tokens == 1  # one operator token serves every call while it is valid
    assert s.operator.store.offset() == 5


def test_operator_reply_reaches_the_merchant_in_the_same_conversation_via_operator(system):
    s = system
    opened = open_case(s)
    deliver(s, command(10, "/reply Seu repasse foi enviado hoje às 10:00.", reply_to=opened["message"]["message_id"]))
    conversation_id = opened["turn"]["conversation_id"]
    headers = merchant_headers(s.assistant)
    messages = s.assistant.get(f"/v1/conversations/{conversation_id}", headers=headers).json()["messages"]
    assert messages[-1]["via"] == "operator" and messages[-1]["operator_action"] == "reply"
    assert messages[-1]["text"] == "Seu repasse foi enviado hoje às 10:00."
    following = s.assistant.post(
        "/messages", json={"message": "E aí?", "conversation_id": conversation_id}, headers=headers
    ).json()
    assert following["route"] == "human_reply" and following["via"] == "operator"
    assert following["answer"] == "Seu repasse foi enviado hoje às 10:00."


def test_buttons_claim_and_approve_and_answer_the_press(system):
    s = system
    opened = open_case(s)
    case_id = case_row(s, opened["protocol"])["case_id"]
    message_id = opened["message"]["message_id"]
    [claimed] = deliver(s, press(20, f"claim:{case_id}", message_id))
    [approved] = deliver(s, press(21, f"approve:{case_id}", message_id))
    assert claimed["text"] == f"Caso {opened['protocol']} assumido."
    assert approved["text"].startswith("Rascunho aprovado")
    assert s.api.actions() == [{"action": "approve", "idempotency_key": "telegram-21"}]
    assert [p["callback_query_id"] for m, p in s.bot.calls if m == "answerCallbackQuery"] == ["cb-20", "cb-21"]


def test_reply_and_reject_require_text_and_unknown_cases_get_a_neutral_answer(system):
    s = system
    opened = open_case(s)
    message_id = opened["message"]["message_id"]
    answers = deliver(
        s,
        command(30, "/reply", reply_to=message_id),
        command(31, "/reject   ", reply_to=message_id),
        command(32, "/claim HO-20200101-ABCDEF"),
        command(33, "/approve"),
        command(34, "/status"),
        command(35, "bom dia"),
        press(36, "approve:hc_ffffffffffffffff", message_id),
    )
    assert [a["text"] for a in answers] == [
        telegram.TEXT_REQUIRED["reply"],
        telegram.TEXT_REQUIRED["reject"],
        telegram.NOT_FOUND,
        telegram.WHICH_CASE,
        telegram.HELP,
        telegram.NOT_FOUND,
    ]
    assert s.api.requests == []  # nothing reached the assistant
    assert case_row(s, opened["protocol"])["queue_state"] == "open"


# --- only the operator chat ------------------------------------------------------------------------------------------


def test_commands_and_buttons_from_another_chat_are_ignored_without_answer(system):
    s = system
    opened = open_case(s)
    case_id = case_row(s, opened["protocol"])["case_id"]
    sent_before = len(s.bot.sent)
    deliver(
        s,
        command(40, f"/approve {opened['protocol']}", chat=OTHER_CHAT),
        command(41, "/reply Oi", reply_to=opened["message"]["message_id"], chat=OTHER_CHAT),
        press(42, f"claim:{case_id}", opened["message"]["message_id"], chat=OTHER_CHAT),
    )
    assert s.api.requests == [] and len(s.bot.sent) == sent_before
    assert not any(m == "answerCallbackQuery" for m, _ in s.bot.calls)
    assert case_row(s, opened["protocol"])["queue_state"] == "open"
    assert s.operator.store.offset() == 43  # read and confirmed, never applied


def test_commands_addressed_to_another_bot_are_ignored(system):
    s = system
    opened = open_case(s)
    message_id = opened["message"]["message_id"]
    sent_before = len(s.bot.sent)
    deliver(
        s,
        command(45, "/approve@outro_bot", reply_to=message_id),
        command(46, f"/claim@outro_bot {opened['protocol']}"),
        command(47, "/help@outro_bot"),
    )
    assert s.api.requests == [] and len(s.bot.sent) == sent_before  # no call, no answer
    assert case_row(s, opened["protocol"])["queue_state"] == "open"
    assert s.operator.store.offset() == 48  # read and confirmed, never applied
    [claimed] = deliver(s, command(48, "/claim@Getnet_Operator_Bot", reply_to=message_id))  # usernames ignore case
    assert claimed["text"] == f"Caso {opened['protocol']} assumido."
    assert [m for m, _ in s.bot.calls].count("getMe") == 1  # asked once, before the first round


def test_no_update_is_read_before_the_bot_username_is_known(system):
    s = system
    s.bot.fail["getMe"] = 502
    with pytest.raises(telegram.BotApiError):
        s.operator.poll_once()
    assert not any(m == "getUpdates" for m, _ in s.bot.calls) and s.operator.username is None
    del s.bot.fail["getMe"]
    s.operator.poll_once()
    assert s.operator.username == BOT_USERNAME
    assert [m for m, _ in s.bot.calls] == ["getMe", "getMe", "getUpdates"]


# --- idempotency ----------------------------------------------------------------------------------------------------


def test_an_update_is_applied_once_even_after_a_restart(system):
    s = system
    opened = open_case(s)
    update = command(50, "/reply Pronto.", reply_to=opened["message"]["message_id"])
    deliver(s, update)
    s.operator.process(update)  # the same update again in the same process
    restarted = s.start()
    restarted.process(update)  # and after a restart
    restarted.poll_once()  # the stored offset keeps Telegram from sending it again
    assert s.bot.calls[-1] == ("getUpdates", {"timeout": 0, "allowed_updates": ["message", "callback_query"],
                                              "offset": 51})
    assert len(s.api.actions()) == 1
    conn = sqlite3.connect(s.settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM handoff_events WHERE action='reply'").fetchone()[0] == 1
    conn.close()


def test_offset_advances_only_after_processing_and_a_crash_replays_with_the_same_key(system):
    s = system
    opened = open_case(s)
    update = command(60, "/reply Pronto.", reply_to=opened["message"]["message_id"])

    def crash(request):
        if request.url.path.endswith("/actions"):
            raise Crash()

    s.api.after = crash  # the API applied the action; the adapter dies before recording the update
    s.bot.updates.append(update)
    with pytest.raises(Crash):
        s.operator.poll_once()
    assert s.operator.store.offset() is None and not s.operator.store.update_seen(60)
    s.api.after = None
    restarted = s.start()
    restarted.poll_once()
    answer = s.bot.sent[-1]
    assert answer["text"] == f"Resposta enviada ao lojista ({opened['protocol']})."
    assert [a["idempotency_key"] for a in s.api.actions()] == ["telegram-60", "telegram-60"]
    row = case_row(s, opened["protocol"])
    assert row["resume_count"] == 1 and row["queue_state"] == "answered"
    assert restarted.store.offset() == 61


# --- answers of the API ----------------------------------------------------------------------------------------------


def test_conflicts_rate_limit_and_outage_become_short_messages(system):
    s = system
    opened = open_case(s)
    case_id = case_row(s, opened["protocol"])["case_id"]
    message_id = opened["message"]["message_id"]
    claim = s.assistant.post(
        f"/v1/handoffs/{case_id}/claim", headers=token_headers(s.assistant, Principal.operator("op_ana"))
    )
    assert claim.status_code == 200
    [other] = deliver(s, command(70, "/claim", reply_to=message_id))
    assert other["text"] == f"Outro operador já assumiu o caso {opened['protocol']}."

    def limited(request):
        error = {"code": "rate_limited", "message": "Too many", "request_id": "r1"}
        return httpx.Response(429, json={"error": error})

    s.api.before = limited
    [slow] = deliver(s, command(71, "/approve", reply_to=message_id))
    assert slow["text"] == telegram.RATE_LIMITED
    for text in (other["text"], slow["text"]):
        assert "request_id" not in text and "Another" not in text and "r1" not in text


def test_outage_offers_a_retry_that_repeats_the_action_with_the_same_key(system):
    s = system
    opened = open_case(s)
    message_id = opened["message"]["message_id"]
    s.api.before = lambda request: httpx.Response(
        503, json={"error": {"code": "resume_failed", "message": "provider down", "request_id": "r2"}}
    )
    [down] = deliver(s, command(80, "/reply Pronto.", reply_to=message_id))
    assert down["text"] == telegram.UNAVAILABLE and "provider" not in down["text"]
    [[retry]] = down["reply_markup"]["inline_keyboard"]
    assert retry["callback_data"] == "retry:80"
    s.api.before = None
    [done] = deliver(s, press(81, retry["callback_data"], down["message_id"]))
    assert done["text"] == f"Resposta enviada ao lojista ({opened['protocol']})."
    assert [a["idempotency_key"] for a in s.api.actions()] == ["telegram-80", "telegram-80"]
    [again] = deliver(s, press(82, retry["callback_data"], down["message_id"]))
    assert again["text"] == telegram.NOTHING_TO_RETRY
    assert len(s.api.actions()) == 2


def test_expired_operator_token_is_renewed_after_a_401(system):
    s = system
    opened = open_case(s)
    refused = []

    def once(request):
        if not refused:
            refused.append(request)
            return httpx.Response(401, json={"error": {"code": "invalid_token", "message": "expired"}})
        return None

    s.api.before = once
    [claimed] = deliver(s, command(90, "/claim", reply_to=opened["message"]["message_id"]))
    assert claimed["text"] == f"Caso {opened['protocol']} assumido."
    assert s.api.tokens == 2


def test_registered_client_gets_its_operator_token_from_the_real_token_endpoint(system):
    """The `telegram-operator` client of the assistant's issuer (client credentials, role operator): a wrong secret is
    refused with 401 and a short message; the right one claims the case as `telegram`."""
    s = system
    s.api.real_tokens = True
    s.settings.telegram_client_secret = SecretStr("another-secret")
    opened = open_case(s)
    message_id = opened["message"]["message_id"]
    [refused] = deliver(s, command(95, "/claim", reply_to=message_id))
    assert refused["text"] == telegram.UNAUTHORIZED
    token_calls = [r for r in s.api.requests if r.url.path == "/v1/auth/token"]
    assert token_calls and case_row(s, opened["protocol"])["queue_state"] == "open"
    s.settings.telegram_client_secret = SecretStr(CLIENT_SECRET)
    [claimed] = deliver(s, command(96, "/claim", reply_to=message_id))
    assert claimed["text"] == f"Caso {opened['protocol']} assumido."
    row = case_row(s, opened["protocol"])
    assert row["claimed_by"] == "telegram" and row["queue_state"] == "claimed"
    direct = s.assistant.post(
        "/v1/auth/token",
        data={"grant_type": "client_credentials", "client_id": "telegram-operator", "client_secret": "wrong"},
    )
    assert direct.status_code == 401 and direct.json()["error"] == "invalid_client"
    issued = s.assistant.post(
        "/v1/auth/token",
        data={"grant_type": "client_credentials", "client_id": "telegram-operator", "client_secret": CLIENT_SECRET},
    ).json()
    assert set(issued["scope"].split()) == {"handoff:operate", "support:read"}


def test_telegram_client_is_off_without_its_secret(offline, settings):
    settings.telegram_client_secret = None
    client, _, _ = offline()
    response = client.post(
        "/v1/auth/token",
        data={"grant_type": "client_credentials", "client_id": "telegram-operator", "client_secret": CLIENT_SECRET},
    )
    assert response.status_code == 401 and response.json()["error"] == "invalid_client"


def test_operator_token_is_renewed_before_it_expires(tmp_path):
    issued = []

    def endpoint(request):
        issued.append(dict(parse_qs(request.content.decode())))
        return httpx.Response(200, json={"access_token": f"token-{len(issued)}", "expires_in": 300})

    now = [1000.0]
    token = OperatorToken(
        adapter_settings(tmp_path), httpx.Client(transport=httpx.MockTransport(endpoint)), clock=lambda: now[0]
    )
    assert token.get() == "token-1"
    now[0] += 239
    assert token.get() == "token-1"
    now[0] += 2  # within the last minute of its life
    assert token.get() == "token-2"
    assert issued[0] == {
        "grant_type": ["client_credentials"], "client_id": ["telegram-operator"], "client_secret": [CLIENT_SECRET]
    }


# --- the bot token never leaves ---------------------------------------------------------------------------------------


def test_bot_token_never_reaches_a_log_or_a_repr(system, caplog):
    s = system
    caplog.set_level(logging.DEBUG)
    s.operator.poll_once()  # the httpx request log names the Bot API URL
    s.bot.fail["getUpdates"] = httpx.ConnectError("connection refused")

    class OneRound(threading.Event):
        def wait(self, timeout=None):
            self.set()
            return True

    s.operator.run(OneRound())
    s.bot.fail["getUpdates"] = 409
    s.operator.run(OneRound())
    s.bot.fail["sendMessage"] = 500
    raw, headers = signed(created())
    assert adapter(s).post("/webhooks/assistant", content=raw, headers=headers).status_code == 503
    logged = caplog.text + " ".join(str(r.args) + str(r.exc_text) for r in caplog.records)
    assert "<bot token>" in caplog.text  # the request log was there, redacted
    assert BOT_TOKEN not in logged and BOT_TOKEN.split(":")[1] not in logged
    settings = adapter_settings(s.tmp_path)
    for secret in (BOT_TOKEN, WEBHOOK_SECRET, CLIENT_SECRET):
        assert secret not in repr(settings)


# --- off by default --------------------------------------------------------------------------------------------------


def test_adapter_is_off_without_a_bot_token_and_the_api_does_not_change(offline, settings, monkeypatch):
    assert TelegramSettings.from_env({}) is None
    assert TelegramSettings.from_env({"TELEGRAM_BOT_TOKEN": "  ", "TELEGRAM_OPERATOR_CHAT_ID": "1"}) is None
    for name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_OPERATOR_CHAT_ID", "TELEGRAM_WEBHOOK_SECRET"):
        monkeypatch.delenv(name, raising=False)
    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: pytest.fail("the adapter started without a bot token"))
    assert telegram.main() == 0
    with pytest.raises(ConfigError):
        create_app()
    assert "telegram" not in webhook_targets(settings)
    client, _, _ = offline()
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    assert response.json()["status"] == "handoff"
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM webhook_outbox WHERE target='telegram'").fetchone()[0] == 0
    conn.close()


def test_incomplete_configuration_names_the_variables_never_their_values():
    with pytest.raises(ConfigError) as missing:
        TelegramSettings.from_env({"TELEGRAM_BOT_TOKEN": BOT_TOKEN, "TELEGRAM_WEBHOOK_SECRET": WEBHOOK_SECRET})
    assert "TELEGRAM_OPERATOR_CHAT_ID" in str(missing.value) and "TELEGRAM_CLIENT_SECRET" in str(missing.value)
    assert BOT_TOKEN not in str(missing.value) and WEBHOOK_SECRET not in str(missing.value)
    complete = {
        "TELEGRAM_BOT_TOKEN": BOT_TOKEN, "TELEGRAM_OPERATOR_CHAT_ID": "@operadores",
        "TELEGRAM_WEBHOOK_SECRET": WEBHOOK_SECRET, "TELEGRAM_CLIENT_SECRET": CLIENT_SECRET,
    }
    with pytest.raises(ConfigError, match="numeric id"):
        TelegramSettings.from_env(complete)
    with pytest.raises(ConfigError, match="not a bot token"):
        TelegramSettings.from_env(complete | {"TELEGRAM_BOT_TOKEN": "not-a-token"})
    loaded = TelegramSettings.from_env(complete | {"TELEGRAM_OPERATOR_CHAT_ID": str(CHAT), "RUNTIME_DIR": "/rt"})
    assert loaded.operator_chat_id == CHAT and loaded.db_path.as_posix() == "/rt/telegram.sqlite3"
    assert loaded.client_id == "telegram-operator" and loaded.assistant_url == "http://127.0.0.1:8000"


def test_compose_runs_the_adapter_only_in_its_profile_and_env_example_leaves_it_off():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = compose["services"]["telegram"]
    assert service["profiles"] == ["telegram"] and "ports" not in service
    assert "env_file" not in service  # the adapter never sees the provider keys of .env
    environment = service["environment"]
    assert environment["TELEGRAM_BOT_TOKEN"] == "${TELEGRAM_BOT_TOKEN:-}"
    assert environment["ASSISTANT_URL"] == "http://api:8000"
    assert not any("OPENAI" in name or "API_KEY" in name for name in environment)
    api = compose["services"]["api"]["environment"]
    assert api["TELEGRAM_WEBHOOK_URL"] == "${TELEGRAM_WEBHOOK_URL:-}"  # off unless configured
    assert api["TELEGRAM_WEBHOOK_SECRET"] == environment["TELEGRAM_WEBHOOK_SECRET"]
    assert api["TELEGRAM_BOT_TOKEN"] == ""  # blanks the token the api's env_file (.env) would pass
    example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    for name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_OPERATOR_CHAT_ID", "TELEGRAM_WEBHOOK_URL", "TELEGRAM_WEBHOOK_SECRET",
                 "TELEGRAM_CLIENT_SECRET"):
        assert f"{name}=" in example
