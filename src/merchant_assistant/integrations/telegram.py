"""Operator on Telegram (spec v0.13.0 D3, CA-69; task 100; ADR 0018).

A small service, off unless `TELEGRAM_BOT_TOKEN` is set (`python -m merchant_assistant.integrations.telegram`; compose
profile `telegram`). It receives the assistant's `handoff.created` at `POST /webhooks/assistant`, signed like every
assistant webhook (`X-Signature: t=<unix>,v1=HMAC-SHA256(TELEGRAM_WEBHOOK_SECRET, "<t>.<body>")`, 300 s window), and
sends the protocol and the masked summary to the one operator chat (`TELEGRAM_OPERATOR_CHAT_ID`). It reads the
operator's commands by long polling (`getUpdates`) and turns them into `/v1/handoffs/{case_id}/claim|actions` calls with
the token of the service operator `operator:telegram` (`client_credentials`, renewed before it expires):

- `/claim`, `/approve`, `/reply <text>` and `/reject <instruction>`, sent as a reply to the case message or followed by
  its protocol (`/reply HO-20261107-A1B2C3 <text>`); the case message also has Claim and Approve buttons.
- Only the configured chat is served: messages and button presses from any other chat are ignored, without an answer.
  A command addressed to another bot (`/approve@other_bot`) is ignored too; the bot's own username comes from `getMe`
  before the first polling round.
- Each update is applied once: its id is recorded before the answer, the polling offset advances only after it, and the
  idempotency key of an action is `telegram-<update_id>`, so an update read again after a crash replays at the API.
- The API's answer becomes a short message (409, 429 and 503 never show their details); a 503 offers a Retry button
  that repeats the action with the same idempotency key.

The bot token is part of every Bot API URL: it never reaches a log (the `httpx` request log is redacted and errors are
logged by type and status) nor a repr."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import sys
import threading
import time
from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from merchant_assistant.api.webhooks import SIGNATURE_TOLERANCE_S, verify_signature
from merchant_assistant.guardrails.input import check_input

log = logging.getLogger("merchant_assistant.telegram")

CLIENT_ID = "telegram-operator"
DEFAULT_ASSISTANT = "http://127.0.0.1:8000"
PROTOCOL = re.compile(r"HO-\d{8}-[0-9A-F]{6}")
CASE_ID = re.compile(r"hc_[0-9a-f]{16}")
BOT_TOKEN = re.compile(r"\d{1,20}:[A-Za-z0-9_-]{20,100}")
COMMANDS = ("claim", "approve", "reply", "reject")
SUMMARY_LIMIT = 1500

HELP = (
    "Comandos do operador (responda à mensagem do caso ou informe o protocolo):\n"
    "/claim — assumir o caso\n"
    "/approve — aprovar o rascunho do assistente\n"
    "/reply <texto> — responder ao lojista\n"
    "/reject <instrução> — devolver ao agente com uma instrução"
)
WHICH_CASE = "Responda à mensagem do caso com o comando ou informe o protocolo, por exemplo: /claim HO-20261107-A1B2C3."
TEXT_REQUIRED = {
    "reply": "Escreva a resposta depois do comando: /reply <texto>.",
    "reject": "Escreva a instrução depois do comando: /reject <instrução>.",
}
NOT_FOUND = "Caso não encontrado."
NOTHING_TO_RETRY = "Não há ação para repetir."
FAILED = "Não foi possível processar o comando."
DONE = {
    "claim": "Caso {protocol} assumido.",
    "approve": "Rascunho aprovado; a resposta segue ao lojista ({protocol}).",
    "reply": "Resposta enviada ao lojista ({protocol}).",
    "reject": "Instrução enviada ao agente; a nova resposta segue ao lojista ({protocol}).",
}
CONFLICTS = {
    "claimed_by_other": "Outro operador já assumiu o caso {protocol}.",
    "already_resumed": "O caso {protocol} já foi respondido.",
    "case_closed": "O caso {protocol} está encerrado.",
}
CONFLICT = "O caso {protocol} não aceita esta ação agora."
REFUSED_TEXT = "O assistente recusou o texto (vazio, longo demais ou bloqueado)."
RATE_LIMITED = "Muitas ações seguidas; tente de novo em instantes."
UNAUTHORIZED = "O adaptador não está autorizado no assistente; avise o responsável."
UNAVAILABLE = "O assistente não conseguiu concluir agora."


# --- settings -----------------------------------------------------------------------------------------------------


class ConfigError(ValueError):
    """The adapter is on (`TELEGRAM_BOT_TOKEN`) but another variable is missing or invalid. Names variables only."""


def _default_db_path(env: Mapping[str, str]) -> Path:
    runtime = env.get("RUNTIME_DIR")
    return Path(runtime) / "telegram.sqlite3" if runtime else Path("data/runtime/telegram.sqlite3")


@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str = field(repr=False)
    operator_chat_id: int
    webhook_secret: str = field(repr=False)  # TELEGRAM_WEBHOOK_SECRET, the same value the assistant signs with
    client_secret: str = field(repr=False)  # TELEGRAM_CLIENT_SECRET of the client `telegram-operator`
    db_path: Path
    assistant_url: str = DEFAULT_ASSISTANT
    client_id: str = CLIENT_ID
    bot_api_url: str = "https://api.telegram.org"
    host: str = "127.0.0.1"
    port: int = 8003
    poll_timeout_s: int = 25
    request_timeout_s: float = 10.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> TelegramSettings | None:
        """None when `TELEGRAM_BOT_TOKEN` is empty: the adapter is off. Raises ConfigError for an invalid setup."""
        env = os.environ if env is None else env
        token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            return None
        if not BOT_TOKEN.fullmatch(token):
            raise ConfigError("TELEGRAM_BOT_TOKEN is not a bot token (<bot id>:<secret>, as given by @BotFather).")
        required = ("TELEGRAM_OPERATOR_CHAT_ID", "TELEGRAM_WEBHOOK_SECRET", "TELEGRAM_CLIENT_SECRET")
        if missing := [name for name in required if not env.get(name, "").strip()]:
            raise ConfigError(f"The Telegram adapter needs {', '.join(missing)}.")
        chat = env["TELEGRAM_OPERATOR_CHAT_ID"].strip()
        if not re.fullmatch(r"-?\d{1,20}", chat):
            raise ConfigError("TELEGRAM_OPERATOR_CHAT_ID must be the numeric id of the operator chat.")
        port = env.get("TELEGRAM_PORT", "").strip() or "8003"
        if not port.isdecimal():
            raise ConfigError("TELEGRAM_PORT must be a port number.")
        return cls(
            bot_token=token,
            operator_chat_id=int(chat),
            webhook_secret=env["TELEGRAM_WEBHOOK_SECRET"].strip(),
            client_secret=env["TELEGRAM_CLIENT_SECRET"].strip(),
            db_path=Path(env["TELEGRAM_DB_PATH"]) if env.get("TELEGRAM_DB_PATH") else _default_db_path(env),
            assistant_url=(env.get("ASSISTANT_URL") or DEFAULT_ASSISTANT).rstrip("/"),
            client_id=env.get("TELEGRAM_CLIENT_ID") or CLIENT_ID,
            host=env.get("TELEGRAM_HOST") or "127.0.0.1",
            port=int(port),
        )


# --- Bot API ------------------------------------------------------------------------------------------------------


class _Redact(logging.Filter):
    """Replaces the bot token in a log record (the `httpx` request log carries the Bot API URL)."""

    def __init__(self, secret: str) -> None:
        super().__init__()
        self.secret = secret

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if self.secret in message:
            record.msg, record.args = message.replace(self.secret, "<bot token>"), ()
        return True


_redacted: set[str] = set()


def _redact(secret: str) -> None:
    if secret in _redacted:
        return
    _redacted.add(secret)
    for name in ("httpx", log.name):
        logging.getLogger(name).addFilter(_Redact(secret))


class BotApiError(Exception):
    """A failed Bot API call. The message names the method and the status, never the URL (it carries the token)."""

    def __init__(self, method: str, status: int | None, retry_after: float | None = None) -> None:
        super().__init__(f"Bot API {method} failed ({'network' if status is None else status})")
        self.method, self.status, self.retry_after = method, status, retry_after


def _json(response: httpx.Response) -> dict | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


class BotApi:
    def __init__(self, settings: TelegramSettings, client: httpx.Client) -> None:
        _redact(settings.bot_token)
        self._base = f"{settings.bot_api_url.rstrip('/')}/bot{settings.bot_token}"
        self.client, self.timeout = client, settings.request_timeout_s

    def call(self, method: str, payload: dict, *, timeout: float | None = None):
        try:
            response = self.client.post(f"{self._base}/{method}", json=payload, timeout=timeout or self.timeout)
        except httpx.HTTPError:
            raise BotApiError(method, None) from None  # the cause would carry the request, and with it the token
        body = _json(response)
        if response.status_code == 200 and body and body.get("ok") is True:
            return body.get("result")
        parameters = (body or {}).get("parameters")
        retry_after = parameters.get("retry_after") if isinstance(parameters, dict) else None
        raise BotApiError(method, response.status_code, retry_after if isinstance(retry_after, int) else None)


# --- assistant ----------------------------------------------------------------------------------------------------


class TokenUnavailable(Exception):
    """The token endpoint could not be reached or answered 5xx/429."""


class TokenRefused(Exception):
    """The token endpoint refused the client (wrong secret or client not registered)."""


class OperatorToken:
    """`client_credentials` token of the service operator, renewed before it expires (a minute early, or halfway
    through a shorter life) and after a 401 of the API."""

    def __init__(self, settings: TelegramSettings, client: httpx.Client, clock: Callable[[], float] = time.time):
        self.settings, self.client, self.clock = settings, client, clock
        self._token: str | None = None
        self._renew_at = 0.0
        self._lock = threading.Lock()

    def invalidate(self) -> None:
        with self._lock:
            self._token = None

    def get(self) -> str:
        with self._lock:
            if self._token and self.clock() < self._renew_at:
                return self._token
            try:
                response = self.client.post(
                    f"{self.settings.assistant_url}/v1/auth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.settings.client_id,
                        "client_secret": self.settings.client_secret,
                    },
                    timeout=self.settings.request_timeout_s,
                )
            except httpx.HTTPError:
                raise TokenUnavailable("token endpoint unreachable") from None
            if response.status_code >= 500 or response.status_code == 429:
                raise TokenUnavailable(f"token endpoint returned {response.status_code}")
            if response.status_code != 200:
                raise TokenRefused(f"token endpoint returned {response.status_code}")
            body = _json(response) or {}
            token, expires_in = body.get("access_token"), body.get("expires_in")
            if not isinstance(token, str) or not token or not isinstance(expires_in, int) or expires_in <= 0:
                raise TokenUnavailable("token endpoint returned an unexpected body")
            self._token = token
            self._renew_at = self.clock() + expires_in - min(60.0, expires_in / 2)
            return token


@dataclass(frozen=True)
class Answer:
    status: int | None  # None: the assistant could not be reached
    code: str | None = None


class Assistant:
    """The operator queue of the assistant (`/v1/handoffs`), called with the service operator's token."""

    def __init__(self, settings: TelegramSettings, client: httpx.Client, token: OperatorToken) -> None:
        self.settings, self.client, self.token = settings, client, token

    def claim(self, case_id: str) -> Answer:
        return self._post(f"/v1/handoffs/{case_id}/claim", None)

    def act(self, case_id: str, action: str, text: str | None, key: str) -> Answer:
        body = {"action": action, "idempotency_key": key} | ({"text": text} if text else {})
        return self._post(f"/v1/handoffs/{case_id}/actions", body)

    def _post(self, path: str, body: dict | None) -> Answer:
        for attempt in (1, 2):
            try:
                token = self.token.get()
            except TokenUnavailable:
                return Answer(None, "token_unavailable")
            except TokenRefused:
                return Answer(401, "token_refused")
            try:
                response = self.client.post(
                    f"{self.settings.assistant_url}{path}",
                    json=body,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self.settings.request_timeout_s * 9,  # a resume runs the agents once
                )
            except httpx.HTTPError:
                return Answer(None, "unreachable")
            if response.status_code == 401 and attempt == 1:  # expired or revoked: renew once
                self.token.invalidate()
                continue
            error = (_json(response) or {}).get("error")
            return Answer(response.status_code, error.get("code") if isinstance(error, dict) else None)
        raise AssertionError("unreachable")


def outcome(answer: Answer, action: str, protocol: str) -> tuple[str, bool]:
    """The operator's message for an answer of the API, and whether repeating the same action may succeed."""
    status = answer.status
    if status is not None and 200 <= status < 300:
        return DONE[action].format(protocol=protocol), False
    if status == 404:
        return NOT_FOUND, False
    if status == 409:
        return CONFLICTS.get(answer.code or "", CONFLICT).format(protocol=protocol), False
    if status == 422:
        return REFUSED_TEXT, False
    if status == 429:
        return RATE_LIMITED, False
    if status in (401, 403):
        return UNAUTHORIZED, False
    return UNAVAILABLE, True


def case_text(protocol: str, summary) -> str:
    """The case message: the protocol and the summary, masked again here and then shortened."""
    text = check_input(summary).masked.strip() if isinstance(summary, str) else ""
    text = text or "(sem resumo)"
    if len(text) > SUMMARY_LIMIT:
        text = text[: SUMMARY_LIMIT - 1] + "…"
    return (
        f"Novo caso encaminhado: {protocol}\n\nResumo: {text}\n\n"
        "Responda a esta mensagem com /claim, /approve, /reply <texto> ou /reject <instrução>."
    )


# --- store --------------------------------------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY, protocol TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE, message_id INTEGER,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS cases_message ON cases(message_id);
CREATE TABLE IF NOT EXISTS updates (update_id INTEGER PRIMARY KEY, outcome TEXT NOT NULL, processed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS retries (
    update_id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, action TEXT NOT NULL, text TEXT, idempotency_key TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    """The adapter's own SQLite database: the cases it showed, the updates it applied, the polling offset and the
    actions waiting for a retry. A restart reads it back, so no command is applied twice."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _one(self, sql: str, args: tuple) -> sqlite3.Row | None:
        with closing(self._connect()) as conn:
            return conn.execute(sql, args).fetchone()

    def _run(self, sql: str, args: tuple) -> None:
        with closing(self._connect()) as conn:
            conn.execute(sql, args)

    def event_seen(self, event_id: str) -> bool:
        return self._one("SELECT 1 FROM cases WHERE event_id=?", (event_id,)) is not None

    def record_case(self, event_id: str, case_id: str, protocol: str, message_id: int | None) -> None:
        self._run(
            "INSERT OR REPLACE INTO cases (case_id,protocol,event_id,message_id,created_at) VALUES (?,?,?,?,?)",
            (case_id, protocol, event_id, message_id, _now()),
        )

    def case(self, reference: str) -> tuple[str, str] | None:
        row = self._one("SELECT case_id, protocol FROM cases WHERE case_id=? OR protocol=?", (reference, reference))
        return (row["case_id"], row["protocol"]) if row else None

    def case_by_message(self, message_id) -> tuple[str, str] | None:
        if not isinstance(message_id, int):
            return None
        row = self._one("SELECT case_id, protocol FROM cases WHERE message_id=?", (message_id,))
        return (row["case_id"], row["protocol"]) if row else None

    def update_seen(self, update_id: int) -> bool:
        return self._one("SELECT 1 FROM updates WHERE update_id=?", (update_id,)) is not None

    def mark_update(self, update_id: int, result: str) -> None:
        self._run(
            "INSERT OR IGNORE INTO updates (update_id,outcome,processed_at) VALUES (?,?,?)", (update_id, result, _now())
        )

    def offset(self) -> int | None:
        row = self._one("SELECT value FROM state WHERE key='offset'", ())
        return int(row["value"]) if row else None

    def set_offset(self, offset: int) -> None:
        self._run("INSERT OR REPLACE INTO state (key,value) VALUES ('offset',?)", (str(offset),))

    def save_retry(self, update_id: int, case_id: str, action: str, text: str | None, key: str) -> None:
        self._run(
            "INSERT OR REPLACE INTO retries (update_id,case_id,action,text,idempotency_key) VALUES (?,?,?,?,?)",
            (update_id, case_id, action, text, key),
        )

    def retry(self, update_id: int) -> sqlite3.Row | None:
        return self._one("SELECT * FROM retries WHERE update_id=?", (update_id,))

    def drop_retry(self, update_id: int) -> None:
        self._run("DELETE FROM retries WHERE update_id=?", (update_id,))


# --- the adapter --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Reply:
    text: str
    reply_to: int | None = None
    buttons: tuple[tuple[str, str], ...] = ()


class TelegramOperator:
    def __init__(
        self,
        settings: TelegramSettings,
        bot: BotApi,
        assistant: Assistant,
        store: Store,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.settings, self.bot, self.assistant, self.store, self.clock = settings, bot, assistant, store, clock
        self._lock = threading.Lock()
        self.username: str | None = None  # the bot's own, from `getMe` before the first polling round

    # --- handoff.created ------------------------------------------------------------------------------------------

    def receive(self, body: bytes, signature_header: str | None) -> tuple[int, dict]:
        """A signed `handoff.created`: the case goes to the operator chat once per event id. 401 bad signature or
        timestamp; 400 malformed; 422 another event or invalid case; 503 Telegram unavailable (the assistant retries);
        200 accepted or replayed."""
        secret = self.settings.webhook_secret
        if not verify_signature(secret, signature_header, body, self.clock(), SIGNATURE_TOLERANCE_S):
            return 401, _error("invalid_signature", "Missing, invalid or expired X-Signature.")
        try:
            event = json.loads(body)
        except ValueError:
            event = None
        data = event.get("data") if isinstance(event, dict) else None
        event_id = event.get("id") if isinstance(event, dict) else None
        if not isinstance(data, dict) or not isinstance(event_id, str) or not 0 < len(event_id) <= 100:
            return 400, _error("invalid_event", "The body is not an event envelope.")
        if event.get("type") != "handoff.created":
            return 422, _error("unsupported_event", "Only handoff.created is accepted.")
        case_id, protocol = data.get("case_id"), data.get("protocol")
        if not (isinstance(case_id, str) and CASE_ID.fullmatch(case_id)) or not (
            isinstance(protocol, str) and PROTOCOL.fullmatch(protocol)
        ):
            return 422, _error("invalid_event", "The event has no valid case id and protocol.")
        with self._lock:
            if self.store.event_seen(event_id):
                return 200, {"status": "replayed"}
            reply = Reply(case_text(protocol, data.get("summary")), buttons=_case_buttons(case_id))
            try:
                message_id = self._send(reply)
            except BotApiError as exc:
                log.warning("case not sent to telegram", extra={"event": {"case_id": case_id, "status": exc.status}})
                return 503, _error("telegram_unavailable", "The case could not be sent to Telegram; retry later.")
            self.store.record_case(event_id, case_id, protocol, message_id)
        log.info("case sent to telegram", extra={"event": {"case_id": case_id}})
        return 200, {"status": "accepted"}

    # --- long polling ---------------------------------------------------------------------------------------------

    def poll_once(self) -> int:
        """One `getUpdates` round. Each update is processed and only then the stored offset passes it. The first round
        asks `getMe` for the bot's username; no update is read before it is known."""
        if self.username is None:
            self.username = self._bot_username()
        payload: dict = {"timeout": self.settings.poll_timeout_s, "allowed_updates": ["message", "callback_query"]}
        if (offset := self.store.offset()) is not None:
            payload["offset"] = offset
        updates = self.bot.call("getUpdates", payload, timeout=self.settings.poll_timeout_s + 10)
        valid = [u for u in updates or [] if isinstance(u, dict) and isinstance(u.get("update_id"), int)]
        for update in sorted(valid, key=lambda u: u["update_id"]):
            self.process(update)
            self.store.set_offset(update["update_id"] + 1)
        return len(valid)

    def _bot_username(self) -> str:
        me = self.bot.call("getMe", {})
        username = me.get("username") if isinstance(me, dict) else None
        if not isinstance(username, str) or not username:
            raise BotApiError("getMe", None)
        return username

    def run(self, stop: threading.Event) -> None:
        failures = 0
        while not stop.is_set():
            try:
                self.poll_once()
                failures = 0
            except BotApiError as exc:
                failures += 1
                if exc.status == 409:
                    log.warning("another client is reading this bot's updates, or a webhook is set on the bot")
                elif exc.status == 401:
                    log.error("the Bot API refused TELEGRAM_BOT_TOKEN")
                else:
                    log.warning("telegram polling failed", extra={"event": {"status": exc.status}})
                stop.wait(exc.retry_after or min(30, 2 ** min(failures, 5)))
            except Exception as exc:  # the loop outlives any single failure
                log.warning("telegram polling failed", extra={"event": {"error": type(exc).__name__}})
                stop.wait(5)

    def process(self, update: dict) -> None:
        update_id = update.get("update_id")
        if not isinstance(update_id, int) or self.store.update_seen(update_id):
            return
        message, button = update.get("message"), update.get("callback_query")
        button = button if isinstance(button, dict) else None
        source = button.get("message") if button else message
        chat = source.get("chat") if isinstance(source, dict) else None
        if not isinstance(chat, dict) or chat.get("id") != self.settings.operator_chat_id:
            self.store.mark_update(update_id, "ignored")  # another chat: no call, no answer
            if source is not None:
                log.info("update from another chat ignored", extra={"event": {"update_id": update_id}})
            return
        try:
            result, reply = self._on_button(update_id, button) if button else self._on_message(update_id, source)
        except Exception as exc:
            log.warning("telegram command failed", extra={"event": {"error": type(exc).__name__}})
            result, reply = "error", Reply(FAILED, source.get("message_id"))
        self.store.mark_update(update_id, result)
        if button:
            self._quietly("answerCallbackQuery", {"callback_query_id": button.get("id")})
        if reply:
            try:
                self._send(reply)
            except BotApiError as exc:
                log.warning("answer not sent to telegram", extra={"event": {"status": exc.status}})

    def _on_message(self, update_id: int, message: dict) -> tuple[str, Reply | None]:
        text = message.get("text")
        if not isinstance(text, str) or not text.startswith("/"):
            return "ignored", None
        message_id = message.get("message_id")
        head, *rest = text.strip().split(maxsplit=1)
        argument = rest[0] if rest else ""
        name, _, mention = head[1:].partition("@")
        if mention and (self.username is None or mention.lower() != self.username.lower()):
            return "ignored", None  # addressed to another bot of the chat
        command = name.lower()
        if command not in COMMANDS:
            return "help", Reply(HELP, message_id)
        quoted = message.get("reply_to_message")
        case = self.store.case_by_message(quoted.get("message_id")) if isinstance(quoted, dict) else None
        if case is None:
            first, *remainder = argument.split(maxsplit=1) or [""]
            if not (PROTOCOL.fullmatch(first) or CASE_ID.fullmatch(first)):
                return "no_case", Reply(WHICH_CASE, message_id)
            case = self.store.case(first)
            if case is None:
                return "unknown_case", Reply(NOT_FOUND, message_id)
            argument = remainder[0] if remainder else ""
        argument = argument.strip()
        if command in TEXT_REQUIRED and not argument:
            return "text_required", Reply(TEXT_REQUIRED[command], message_id)
        return self._act(update_id, case, command, argument or None, f"telegram-{update_id}", message_id)

    def _on_button(self, update_id: int, button: dict) -> tuple[str, Reply | None]:
        data = button.get("data")
        message_id = button["message"].get("message_id")
        action, _, value = (data if isinstance(data, str) else "").partition(":")
        if action == "retry" and value.isascii() and value.isdecimal():
            row = self.store.retry(int(value))
            case = self.store.case(row["case_id"]) if row else None
            if row is None or case is None:
                return "nothing_to_retry", Reply(NOTHING_TO_RETRY, message_id)
            return self._act(int(value), case, row["action"], row["text"], row["idempotency_key"], message_id)
        if action in ("claim", "approve") and CASE_ID.fullmatch(value):
            case = self.store.case(value)
            if case is None:
                return "unknown_case", Reply(NOT_FOUND, message_id)
            return self._act(update_id, case, action, None, f"telegram-{update_id}", message_id)
        return "ignored", None

    def _act(
        self, retry_id: int, case: tuple[str, str], action: str, text: str | None, key: str, reply_to: int | None
    ) -> tuple[str, Reply]:
        """Calls the API; `retry_id` names the action for the Retry button (the update that first asked for it)."""
        case_id, protocol = case
        answer = self.assistant.claim(case_id) if action == "claim" else self.assistant.act(case_id, action, text, key)
        message, retryable = outcome(answer, action, protocol)
        log.info(
            "operator command", extra={"event": {"case_id": case_id, "action": action, "status": answer.status}}
        )
        if retryable:
            self.store.save_retry(retry_id, case_id, action, text, key)
            return "retryable", Reply(message, reply_to, (("Tentar de novo", f"retry:{retry_id}"),))
        self.store.drop_retry(retry_id)
        return f"{action}:{answer.status}", Reply(message, reply_to)

    # --- sending --------------------------------------------------------------------------------------------------

    def _send(self, reply: Reply) -> int | None:
        payload: dict = {
            "chat_id": self.settings.operator_chat_id,
            "text": reply.text,  # plain text: nothing in it is read as markup
            "link_preview_options": {"is_disabled": True},
        }
        if reply.reply_to is not None:
            payload["reply_parameters"] = {"message_id": reply.reply_to, "allow_sending_without_reply": True}
        if reply.buttons:
            payload["reply_markup"] = {
                "inline_keyboard": [[{"text": label, "callback_data": data} for label, data in reply.buttons]]
            }
        result = self.bot.call("sendMessage", payload)
        message_id = result.get("message_id") if isinstance(result, dict) else None
        return message_id if isinstance(message_id, int) else None

    def _quietly(self, method: str, payload: dict) -> None:
        try:
            self.bot.call(method, payload)
        except BotApiError as exc:
            log.info("telegram call failed", extra={"event": {"method": method, "status": exc.status}})


def _case_buttons(case_id: str) -> tuple[tuple[str, str], ...]:
    return (("Assumir", f"claim:{case_id}"), ("Aprovar rascunho", f"approve:{case_id}"))


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


# --- service ------------------------------------------------------------------------------------------------------


def create_app(
    settings: TelegramSettings | None = None,
    *,
    bot_client: httpx.Client | None = None,
    api_client: httpx.Client | None = None,
    poll: bool = True,
    clock: Callable[[], float] = time.time,
) -> FastAPI:
    settings = settings or TelegramSettings.from_env()
    if settings is None:
        raise ConfigError("TELEGRAM_BOT_TOKEN is empty: the Telegram adapter is off.")
    api_client = api_client or httpx.Client()
    operator = TelegramOperator(
        settings,
        BotApi(settings, bot_client or httpx.Client()),
        Assistant(settings, api_client, OperatorToken(settings, api_client, clock)),
        Store(settings.db_path),
        clock=clock,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        stop = threading.Event()
        thread = threading.Thread(target=operator.run, args=(stop,), name="telegram-poll", daemon=True)
        if poll:
            thread.start()
        yield
        stop.set()
        if poll:
            thread.join(timeout=1)  # a long poll still waiting ends with the process

    app = FastAPI(title="Telegram operator adapter", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.operator = operator

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/webhooks/assistant")
    async def assistant_event(request: Request) -> JSONResponse:
        body = await request.body()
        status, content = await run_in_threadpool(operator.receive, body, request.headers.get("x-signature"))
        return JSONResponse(status_code=status, content=content)

    return app


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    try:
        settings = TelegramSettings.from_env()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    if settings is None:
        print("TELEGRAM_BOT_TOKEN is empty: the Telegram adapter is off.", file=sys.stderr)
        return 0
    import uvicorn

    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
