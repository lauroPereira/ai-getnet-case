"""Sale cancellation confirmation and status messages.

Support can only request a cancellation. The conversation flow handles an explicit yes, explicit no, or unanswered turn
in code through the tool registry, with scope checks and audit. Until a yes is confirmed, nothing in the account changes
and the merchant receives a fixed status line. Confirmed cancellations always include their protocol.

Cancellation status in replies is derived from the selected sale records, not from model text. When a status lookup has
several matches, each is listed from its own data. If a request was refused, or the latest request closed without a yes,
the reply states that outcome. A sales question that happens to use the same lookup follows the normal support flow
unless the message or response is about cancellation.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import date

from merchant_assistant.agents.router import explicit_answer
from merchant_assistant.orchestration.run import RunContext
from merchant_assistant.orchestration.state import GraphState
from merchant_assistant.tools.base import money

_MONTHS_EN = (
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
    "December",
)

LINES = {
    "pending_confirmation": {
        "pt": 'Para confirmar o cancelamento da venda de {amount} de {date}, responda "sim". Para manter a venda, '
        'responda "não". Nada foi cancelado ainda.',
        "en": 'To confirm the cancellation of the {amount} sale of {date}, reply "yes". To keep the sale, reply "no". '
        "Nothing has been cancelled yet.",
    },
    "confirmed": {
        "pt": "O cancelamento da venda de {amount} de {date} foi solicitado. Protocolo: {protocol}.",
        "en": "The cancellation of the {amount} sale of {date} was requested. Protocol: {protocol}.",
    },
    "declined": {
        "pt": "Combinado: a venda de {amount} de {date} continua como estava, nada foi cancelado.",
        "en": "All right: the {amount} sale of {date} stays as it was; nothing was cancelled.",
    },
    "expired": {
        "pt": "O pedido de cancelamento da venda de {amount} de {date} expirou sem confirmação, e nada foi "
        "cancelado. Se ainda quiser cancelar essa venda, é só pedir de novo.",
        "en": "The request to cancel the {amount} sale of {date} expired without confirmation, and nothing was "
        "cancelled. If you still want to cancel it, just ask again.",
    },
    "refused": {
        "pt": "Não consegui concluir o cancelamento da venda de {amount} de {date} com esta sessão, e nada foi "
        "alterado na sua conta.",
        "en": "I couldn't complete the cancellation of the {amount} sale of {date} with this session, and nothing "
        "was changed in your account.",
    },

    "declined_late": {
        "pt": "O pedido de cancelamento da venda de {amount} de {date} foi recusado, e nada foi cancelado. Se quiser "
        "cancelar essa venda, é só pedir de novo.",
        "en": "The request to cancel the {amount} sale of {date} was declined, and nothing was cancelled. If you want "
        "to cancel it, just ask again.",
    },
    "not_requested": {
        "pt": "Não registrei nenhum pedido de cancelamento, e nada foi alterado na sua conta. Para eu localizar a "
        "venda, me diga o tipo de pagamento, o valor e a data dela.",
        "en": "I did not record any cancellation request, and nothing was changed in your account. To find the sale, "
        "tell me its payment type, amount and date.",
    },
    "not_requested_scope": {
        "pt": "Não consegui registrar o pedido de cancelamento com esta sessão, e nada foi alterado na sua conta.",
        "en": "I couldn't record the cancellation request with this session, and nothing was changed in your account.",
    },
}
# the status lines of a lookup, written from its data.
STATUS_LINES = {
    "no_sale": {
        "pt": "Não encontrei uma venda com essas condições no período consultado, então não há cancelamento dela.",
        "en": "I couldn't find a sale with those conditions in the period checked, so it has no cancellation.",
    },
    "several": {
        "pt": "Encontrei {n} vendas com essas condições. O status de cancelamento de cada uma:",
        "en": "I found {n} sales with those conditions. The cancellation status of each:",
    },
    "more": {
        "pt": "Há mais {n} vendas no período; me diga o tipo de pagamento, o valor ou a data para eu localizar a "
        "venda.",
        "en": "There are {n} more sales in the period; tell me the payment type, amount or date to find the sale.",
    },
    "none": {
        "pt": "A venda {sale} não tem cancelamento registrado.",
        "en": "The {sale} has no cancellation recorded.",
    },
    "requested": {
        "pt": "O cancelamento da venda {sale} está com status solicitado e ainda não foi processado.",
        "en": "The cancellation of the {sale} has status requested and has not been processed yet.",
    },
    "completed": {
        "pt": "O cancelamento da venda {sale} foi concluído.",
        "en": "The cancellation of the {sale} was completed.",
    },
    "rejected": {
        "pt": "O cancelamento da venda {sale} foi recusado, e a venda não foi cancelada.",
        "en": "The cancellation of the {sale} was rejected, and the sale was not cancelled.",
    },
    "other": {  # any other status of the source: a neutral line, never the raw value
        "pt": "Não consegui confirmar a situação do cancelamento da venda {sale}.",
        "en": "I couldn't confirm the state of the cancellation of the {sale}.",
    },
    "protocol": {"pt": " Protocolo: {protocol}.", "en": " Protocol: {protocol}."},
    "rest": {  # the Support also answered something else: its text is not used in a status turn
        "pt": "Sobre o restante da sua mensagem, envie a pergunta separadamente que eu respondo.",
        "en": "About the rest of your message, send the question separately and I'll answer it.",
    },
    "ask_sale": {  # a turn about a cancellation that looked nothing up, and a model that states a status
        "pt": "Para ver o status do cancelamento, me diga qual venda (tipo, valor ou data) que eu consulto.",
        "en": "To check the cancellation status, tell me which sale (type, amount or date) and I'll look it up.",
    },
}
STATUS_TOOLS = {"get_sale_cancellation_context", "request_sale_cancellation"}
STATUS_LIMIT = 8  # sales listed at most; the rest is counted
_REQUEST_NOTE = {  # the latest request of a sale without a cancellation
    "pending_confirmation": {
        "pt": " Há um pedido de cancelamento dela esperando a sua resposta, e nada foi cancelado.",
        "en": " A request to cancel it is waiting for your answer, and nothing was cancelled.",
    },
    "declined": {
        "pt": " O último pedido de cancelamento dela foi recusado, e nada foi cancelado.",
        "en": " The latest request to cancel it was declined, and nothing was cancelled.",
    },
    "expired": {
        "pt": " O último pedido de cancelamento dela expirou sem resposta, e nada foi cancelado.",
        "en": " The latest request to cancel it expired without an answer, and nothing was cancelled.",
    },
}
_PAYMENT = {
    "pt": {"debit": "de débito", "credit": "de crédito", "pix": "Pix"},
    "en": {"debit": "debit", "credit": "credit", "pix": "Pix"},
}

# A reply to a request still waiting must not say the sale is or will be cancelled. Each clause counts on its own
# (split at ".", "!", "?", ";", ":", a line break and a comma outside a number such as "R$ 150,00"): a clause states
# the cancellation as done or promised when it has one of the `_DONE` words and no negation or condition of its own.
# A qualifier absolves only the clause it is in: "Se precisar, estou aqui; a venda foi cancelada" promises, "Nada foi
# cancelado ainda" and "it will be cancelled only if you reply yes" do not. Words match whole (accents and the curly
# apostrophe folded for `_DONE`); a false positive only swaps the reply for the fixed line, which is safe.
_DONE = re.compile(
    r"(?<!\w)(?:cancelei|cancelamos|cancelo|cancelarei|cancelaremos|vou cancelar|vamos cancelar|cancelad[ao]s?|"
    r"cancelamento (?:ja )?(?:foi |esta )?(?:realizado|concluido|efetuado|confirmado|feito|processado)|"
    r"i(?:'ve| have)? cancell?ed|we(?:'ve| have)? cancell?ed|(?:i|we)(?:'ll| will) cancel|cancell?ed|"
    r"cancellation (?:is|was|has been) (?:done|complete|completed|confirmed|processed))(?!\w)",
)
_QUALIFIED = re.compile(
    r"(?<!\w)(?:n[aã]o|nada|nenhum|nenhuma|nunca|se|caso|quando|depois|ap[oó]s|assim que|somente|só|apenas|"
    r"not|nothing|never|if|once|after|when|only|unless)(?!\w)|n't(?!\w)",
)
_CLAUSES = re.compile(r"[.!?;:\n]|(?<!\d),|,(?!\d)")


def _folded(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold().replace("\u2019", "'"))
    return "".join(c for c in text if not unicodedata.combining(c))


def promises_execution(text: str) -> bool:
    """True when a clause of `text` says the pending cancellation is done or will be done, without a qualifier."""
    return any(
        _DONE.search(_folded(clause)) and not _QUALIFIED.search(clause.casefold().replace("\u2019", "'"))
        for clause in _CLAUSES.split(text)
    )


# in a turn where the code knows the sale has no cancellation in progress (no cancellation, a request refused
# by the tool, or a request already closed), a clause that states one (requested, recorded, in progress, the
# confirmation received, or `_DONE`) without a qualifier of its own is wrong; the reply is replaced by the fixed line.
_STATUS = re.compile(
    r"(?<!\w)(?:solicitad[ao]s?|registrad[ao]s?|em andamento|em cancelamento|em processamento|em analise|"
    r"pendentes?|na fila|abert[ao]s?|processad[ao]s?|aceit[ao]s?|encaminhad[ao]s?|enviad[ao]s?|"
    r"estorn(?:ad[ao]s?|amos|ei|ou|o|arei|aremos)|reembols(?:ad[ao]s?|amos|ei|ou)|devolvid[ao]s?|"
    r"(?:ja )?pedi o cancelamento|(?:ja )?solicitei|(?:ja )?abri|"
    r"recebi (?:a |sua |a sua )?confirmacao|confirmacao (?:foi )?recebida|confirmad[ao]s?|"
    r"requested|recorded|registered|in progress|being processed|under review|pending|queued|submitted|"
    r"processed|accepted|forwarded|refunded|reversed|opened|filed|"
    r"received your confirmation|confirmed)(?!\w)"
)


def claims_status(text: str) -> bool:
    """True when a clause of `text` states that a cancellation exists, was asked for or goes on, without a qualifier."""
    return promises_execution(text) or any(
        _STATUS.search(_folded(clause)) and not _QUALIFIED.search(clause.casefold().replace("\u2019", "'"))
        for clause in _CLAUSES.split(text)
    )


# the state of one specific cancellation or sale ("a venda Pix está com status solicitado", "the
# cancellation was approved"), for a status question the Support did not look up. Narrower than `_STATUS`: no "estorno"
# nor procedure verbs, so the official answer to "how do I cancel or refund a sale" is not taken for a status.
_SALE_STATE = re.compile(
    r"(?<!\w)(?:(?:o|a|seu|sua|esse|essa|este|esta)\s+(?:pedido de\s+)?(?:cancelamento|venda)(?:\s+\S+){0,8}?\s+"
    r"(?:esta|foi|ficou|continua|segue)\s+(?:com\s+(?:o\s+)?status\s+(?:de\s+)?)?"
    r"(?:solicitad|registrad|aprovad|conclu|processad|cancelad|pendente|em andamento|em analise)"
    r"|(?:the|your|this|that)\s+(?:\S+\s+){0,3}(?:cancellation(?:\s+request)?|sale)(?:\s+\S+){0,8}?\s+"
    # "is" before a state ("is pending"), or before a participle only when it closes the clause ("is cancelled"); a
    # participle followed by more words is a procedure ("is processed the same day")
    r"(?:is\s+(?:still\s+|now\s+|currently\s+)?"
    r"(?:(?:in|with)\s+(?:the\s+)?status\s+\S+|pending|in progress|under review)"
    r"|is\s+(?:already\s+|now\s+)?(?:requested|registered|recorded|approved|completed|processed|cancel+ed)\s*$"
    r"|(?:was|has been|remains|stays)\s+(?:(?:in|with)\s+(?:the\s+)?status\s+)?"
    r"(?:requested|registered|recorded|approved|completed|processed|cancel+ed|pending|in progress|under review)))"
)


def states_sale_status(text: str) -> bool:
    """True when a clause of `text` states the state of one specific cancellation or sale, without a qualifier."""
    return any(
        _SALE_STATE.search(_folded(clause)) and not _QUALIFIED.search(clause.casefold().replace("\u2019", "'"))
        for clause in _CLAUSES.split(text)
    )


_QUOTES = str.maketrans(
    {
        **dict.fromkeys("“”„‟″«»‹›＂", '"'),
        **dict.fromkeys("'‘’‚‛′`´＇", '"'),  # single quotes too
        "*": None,
        "_": None,
    }
)


def normalized(text: str) -> str:
    """For comparing a fixed line with the model's text: every quote mark, single or double, as `"`, the
    emphasis marks `*` and `_` dropped and spaces collapsed (the same on both sides, so apostrophes compare too)."""
    return " ".join(text.translate(_QUOTES).split())


def contains_line(draft: str, line: str) -> bool:
    return normalized(line) in normalized(draft)


def _date(value: str, language: str) -> str:
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return value
    return f"{day:%d/%m/%Y}" if language == "pt" else f"{_MONTHS_EN[day.month - 1]} {day.day}, {day.year}"


def _sale_text(sale: dict, language: str) -> str:
    """"de crédito em 2 parcelas de R$ 200,00 de 05/11/2026" or "credit sale in 2 installments of R$ 200,00 on November
    5, 2026"."""
    kind = _PAYMENT[language].get(sale.get("payment_type"), sale.get("payment_type") or "")
    installments = sale.get("installments") or 1
    amount = (sale.get("gross_amount") or {}).get("display")
    day = _date(sale.get("sale_date") or "", language)
    if language == "pt":
        parts = f" em {installments} parcelas" if installments > 1 else ""
        return f"{kind}{parts} de {amount} de {day}"
    parts = f" in {installments} installments" if installments > 1 else ""
    return f"{kind} sale{parts} of {amount} on {day}"


def _sale_status(sale: dict, language: str) -> str:
    text = _sale_text(sale, language)
    record = sale.get("cancellation")
    if not record:
        request = (sale.get("cancellation_request") or {}).get("state")
        return STATUS_LINES["none"][language].format(sale=text) + _REQUEST_NOTE.get(request, {}).get(language, "")
    status = record.get("status")
    key = status if status in ("requested", "completed", "rejected") else "other"
    line = STATUS_LINES[key][language].format(sale=text)
    if record.get("protocol"):
        line += STATUS_LINES["protocol"][language].format(protocol=record["protocol"])
    return line


def status_block(ctx: RunContext, language: str) -> str | None:
    """the status of each sale the turn's status lookups selected (all of them, each sale once), from their
    data (every candidate when more than one matches, at most `STATUS_LIMIT`); None when the turn looked nothing up.
    A sale the turn asked to cancel is left out (the request's own line speaks for it), and so is the block when
    nothing else was looked up."""
    language = "pt" if language == "pt" else "en"
    requested = {
        (o.data or {}).get("sale", {}).get("sale_id")
        for o in ctx.outcomes
        if o.ok and o.name == "request_sale_cancellation"
    }
    lookups = [o for o in ctx.outcomes if o.ok and o.name == "get_sale_cancellation_context"]
    if not lookups:
        return None
    found: dict[str, dict] = {}
    for lookup in lookups:
        for sale in (lookup.data or {}).get("sales", []):
            found.setdefault(sale.get("sale_id"), sale)
    sales = [sale for sale_id, sale in found.items() if sale_id not in requested]
    if not sales:
        return None if requested else STATUS_LINES["no_sale"][language]
    lines = [_sale_status(sale, language) for sale in sales[:STATUS_LIMIT]]
    if len(sales) > 1:
        lines.insert(0, STATUS_LINES["several"][language].format(n=len(sales)))
    if len(sales) > STATUS_LIMIT:
        lines.append(STATUS_LINES["more"][language].format(n=len(sales) - STATUS_LIMIT))
    return "\n".join(lines)


def view(event: dict | None, language: str) -> dict | None:
    """What the Personality receives about the cancellation in this turn: status, sale, protocol and the fixed line."""
    if not event:
        return None
    language = "pt" if language == "pt" else "en"
    status = event["status"]
    if status == "not_requested":
        line = LINES["not_requested_scope" if event.get("code") == "FORBIDDEN_SCOPE" else "not_requested"][language]
        return {
            "status": status,
            "sale_date": None,
            "amount": None,
            "protocol": None,
            "executed": False,
            "replaces_reply": True,
            "message": line,
            "note": "Keep the wording of `message`. Never describe a sale or say a cancellation was requested.",
        }
    sale = event.get("sale") or {}
    amount = (sale.get("amount") or {}).get("display") or event.get("amount")
    sale_date = sale.get("sale_date") or event.get("sale_date")
    key = "declined_late" if status == "declined" and event.get("late") else status
    line = LINES[key][language].format(
        amount=amount, date=_date(sale_date or "", language), protocol=event.get("protocol")
    )
    return {
        "status": status,
        "sale_date": sale_date,
        "amount": amount,
        "protocol": event.get("protocol"),
        "executed": status == "confirmed",
        "replaces_reply": bool(event.get("late")),  # a bare yes or no to a request already closed
        "message": line,
        "note": "Keep the wording of `message`. Never say the sale was or will be cancelled unless status is "
        "confirmed." if status != "confirmed" else "Give the protocol exactly as written.",
    }


def turn_event(state: GraphState, ctx: RunContext) -> dict | None:
    """The cancellation of this turn: the request the Support asked for in it, else what this node did (or the closed
    request a late yes or no answered), else a request the tool refused."""
    for outcome in reversed(ctx.outcomes):
        if outcome.ok and outcome.name == "request_sale_cancellation":
            return outcome.data
    if state.cancellation_event:
        return state.cancellation_event
    for outcome in reversed(ctx.outcomes):
        if not outcome.ok and outcome.name == "request_sale_cancellation":
            return {"status": "not_requested", "code": (outcome.error or {}).get("code")}
    return None


def requested_in_conversation(conn: sqlite3.Connection, conversation_id: str, customer_id: str) -> bool:
    """this merchant asked for a cancellation in this conversation (the request waiting or closed)."""
    return conn.execute(
        "SELECT 1 FROM sale_cancellation_requests WHERE conversation_id = ? AND customer_id = ? LIMIT 1",
        (conversation_id, customer_id),
    ).fetchone() is not None


# a mention of a cancellation (unaccented, lowercase): `cancel*`, `estorn*`, `refund*`, `chargeback*`
_MENTION = re.compile(r"(?<!\w)(?:cancel\w*|estorn\w*|refund\w*|chargeback\w*)")


def mentions_cancellation(text: str) -> bool:
    return bool(_MENTION.search(_folded(text)))


def asked_about_cancellation(state: GraphState) -> bool:
    """the current question is about a cancellation: the Router's topic `cancellation` (validated in code) or
    a merchant's message that mentions one; a request earlier in the conversation does not count here."""
    return bool((state.decision and state.decision.topic == "cancellation") or mentions_cancellation(state.message))


def about_cancellation(state: GraphState, model_text: str = "") -> bool:
    """the turn is about a cancellation, so a status lookup gets the status block written by code: the
    Router's topic `cancellation` (validated in code), a request of this merchant waiting or closed in the
    conversation, a cancellation event of this turn (a request asked for in it, too), an operator's "reject" (no
    merchant question was routed; the operator's instruction drove the lookup, and no human reads the rerun's text
    before the merchant does), a merchant's message that mentions a cancellation, or a model's text (`model_text`)
    that mentions one (the block itself exists only when the Support looked the status up in the turn). Otherwise
    the lookup is one more Support tool and the reply follows the normal flow (output guard and promise detector)."""
    return bool(
        asked_about_cancellation(state)
        or state.cancellation_in_conversation
        or state.cancellation_event
        or (state.operator or {}).get("action") == "reject"
        or mentions_cancellation(model_text)
    )


def closed_request(conn: sqlite3.Connection, conversation_id: str, customer_id: str, message: str) -> dict | None:
    """when no request waits and the latest request of this merchant in this conversation was closed without
    a yes (declined or expired), that request as the reply must describe it (closed, nothing cancelled), for a message
    that is only a yes (in any later turn) or only a no (in the turn right after the one that closed it; after that, a
    bare no answers whatever was asked since)."""
    answer = explicit_answer(message)
    if answer is None:
        return None
    row = conn.execute(
        "SELECT * FROM sale_cancellation_requests WHERE conversation_id = ? AND customer_id = ? "
        "ORDER BY updated_at DESC, rowid DESC LIMIT 1",
        (conversation_id, customer_id),
    ).fetchone()
    if row is None or row["state"] not in ("declined", "expired"):
        return None
    if answer == "no":
        closed_in = conn.execute(  # the register keeps the message of the turn that recorded this status first
            "SELECT source_message_id FROM conversation_facts WHERE conversation_id = ? AND kind = 'status' "
            "AND value = ?",
            (conversation_id, f"{row['request_id']}: {row['state']}"),
        ).fetchone()
        last = conn.execute(
            "SELECT MAX(id) FROM messages WHERE conversation_id = ? AND role = 'merchant'", (conversation_id,)
        ).fetchone()
        if closed_in is None or last is None or closed_in[0] != last[0]:
            return None
    return {
        "request_id": row["request_id"],
        "status": row["state"],
        "sale": {"sale_id": row["sale_id"], "sale_date": row["sale_date"], "amount": money(row["amount"])},
        "protocol": None,
        "executed": False,
        "late": True,
    }


def run(state: GraphState, ctx: RunContext) -> dict:
    pending = state.cancellation or {}
    label = state.decision.confirmation if state.decision else "other"
    if label in ("yes", "no"):
        tool = "confirm_sale_cancellation" if label == "yes" else "decline_sale_cancellation"
        outcome = ctx.run_tool(tool, {"request_id": pending["request_id"]}, agent=None)
        ctx.step_notes.update(confirmation=label, tool=tool, ok=outcome.ok)
        if not outcome.ok:  # refused (scope, merchant or state): an answer to give, nothing changed
            ctx.step_notes["refused"] = (outcome.error or {}).get("code")
        event = (
            outcome.data
            if outcome.ok
            else {"status": "refused", "amount": pending["amount"], "sale_date": pending["sale_date"]}
        )
        return {
            "cancellation_event": event,
            "status": "answered",
            "policy": None,
            "agents": [*state.agents, "confirmation"],
        }
    # a turn without an answer: counted through the registry (scope `support:write`, merchant and audit); a session
    # without the scope leaves the request as it was
    outcome = ctx.run_tool("count_unanswered_cancellation_turn", {"request_id": pending["request_id"]}, agent=None)
    if not outcome.ok:
        ctx.step_notes.update(confirmation="other", refused=(outcome.error or {}).get("code"))
        return {}
    event = outcome.data
    ctx.step_notes.update(confirmation="other", turns_waited=pending["turns_waited"] + 1, state=event["status"])
    return {"cancellation_event": event}


def decided(state: GraphState) -> bool:
    """The turn answered the pending request (yes or no, executed or refused): it goes straight to the reply."""
    confirmation = state.decision.confirmation if state.decision else "other"
    return state.cancellation is not None and confirmation in ("yes", "no")
