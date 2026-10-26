"""Support tools as typed domain functions over the synthetic systems.

Every function receives the trusted `ToolEnv` (customer bound by the server) and validated arguments.
Resources of another customer are never returned: the call fails with FORBIDDEN_RESOURCE and is audited.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from merchant_assistant.data.clock import Period, resolve_period
from merchant_assistant.tools.base import ToolEnv, ToolError, audit, money

Topic = Literal["receivables", "device", "authorization", "contract", "general"]


@lru_cache
def glossary() -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "data" / "glossary.json").read_text(encoding="utf-8"))


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _range(env: ToolEnv, period: Period | None, date_from: date | None, date_to: date | None) -> tuple[date, date]:
    if date_from or date_to:
        start, end = date_from or date_to, date_to or date_from
        if start > end:
            raise ToolError("INVALID_ARGUMENT", "date_from must be before date_to")
        if (end - start).days > 92:
            raise ToolError("INVALID_ARGUMENT", "date range is limited to 92 days")
        return start, end
    return resolve_period(period or "yesterday", env.clock)


def _observed(env: ToolEnv) -> str:
    return env.clock.now().isoformat(timespec="seconds")


# --- get_receivables_schedule -------------------------------------------------------------------------------------


class ReceivablesArgs(_Args):
    period: Period | None = Field(default=None, description="Named period resolved by the server clock.")
    date_from: date | None = Field(default=None, description="Explicit start date (YYYY-MM-DD).")
    date_to: date | None = Field(default=None, description="Explicit end date (YYYY-MM-DD).")
    date_field: Literal["sale_date", "expected_payment_date"] = Field(
        default="sale_date", description="Filter by the sale date or by the expected payment date."
    )


def get_receivables_schedule(env: ToolEnv, args: ReceivablesArgs) -> dict:
    start, end = _range(env, args.period, args.date_from, args.date_to)
    column = "substr(s.captured_at,1,10)" if args.date_field == "sale_date" else "r.expected_payment_date"
    rows = env.conn.execute(
        f"""SELECT r.*, s.captured_at, s.payment_type, s.installments, s.gross_minor, s.channel
            FROM receivables r JOIN sales s ON s.sale_id = r.sale_id
            WHERE r.customer_id = ? AND {column} BETWEEN ? AND ?
            ORDER BY s.captured_at""",  # noqa: S608 - column comes from a fixed Literal
        (env.customer.customer_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    statuses = glossary()["receivable_status"]
    items = []
    for r in rows:
        meaning = statuses.get(r["source_status"], {})
        items.append(
            {
                "receivable_id": r["receivable_id"],
                "sale_id": r["sale_id"],
                "sale_captured_at": r["captured_at"],
                "payment_type": r["payment_type"],
                "installments": r["installments"],
                "channel": r["channel"],
                "gross_amount": money(r["gross_minor"], r["currency"]),
                "fee": money(r["fee_minor"], r["currency"]),
                "net_amount": money(r["amount_minor"], r["currency"]),
                "expected_payment_date": r["expected_payment_date"],
                "source_status": r["source_status"],
                "normalized_status": meaning.get("normalized", "unknown"),
                "status_meaning": meaning.get("meaning_en", "Unknown status."),
            }
        )
    return {
        "date_field": args.date_field,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "count": len(items),
        "receivables": items,
        "net_total": money(sum(i["net_amount"]["minor"] for i in items)),
        "note": "Expected dates come from the schedule record. Use get_payout_status to know if credit is confirmed.",
        "source": "ReceivablesMock",
        "observed_at": _observed(env),
    }


# --- get_payout_status --------------------------------------------------------------------------------------------


class PayoutArgs(_Args):
    receivable_ids: list[str] = Field(min_length=1, max_length=10, description="Ids from get_receivables_schedule.")


def get_payout_status(env: ToolEnv, args: PayoutArgs) -> dict:
    ids = list(dict.fromkeys(args.receivable_ids))
    marks = ",".join("?" * len(ids))
    rows = env.conn.execute(
        f"SELECT r.receivable_id, r.customer_id, p.* FROM receivables r LEFT JOIN payouts p "  # noqa: S608
        f"ON p.receivable_id = r.receivable_id WHERE r.receivable_id IN ({marks})",
        ids,
    ).fetchall()
    found = {r["receivable_id"]: r for r in rows}
    for rid in ids:
        if rid in found and found[rid]["customer_id"] != env.customer.customer_id:
            audit(env, "get_payout_status", rid, "forbidden")
            raise ToolError("FORBIDDEN_RESOURCE", "One or more receivables do not belong to this merchant.")
    missing = [rid for rid in ids if rid not in found]
    if missing:
        raise ToolError("NOT_FOUND", f"Unknown receivable ids: {', '.join(missing)}")
    stages = glossary()["payout_stage"]
    items = []
    for rid in ids:
        r = found[rid]
        meaning = stages.get(r["stage"], {})
        items.append(
            {
                "receivable_id": rid,
                "stage": r["stage"],
                "normalized_stage": meaning.get("normalized", "unknown"),
                "credit_confirmed": bool(r["credit_confirmed"]),
                "confirmed_at": r["confirmed_at"],
                "stage_meaning": meaning.get("meaning_en", "Unknown stage."),
            }
        )
    return {"payouts": items, "source": "PayoutMock", "observed_at": _observed(env)}


# --- get_device_status --------------------------------------------------------------------------------------------


class DeviceArgs(_Args):
    device_id: str | None = Field(default=None, description="Omit to list the merchant's devices.")


def get_device_status(env: ToolEnv, args: DeviceArgs) -> dict:
    now = env.clock.now()
    if args.device_id:
        row = env.conn.execute("SELECT * FROM devices WHERE device_id = ?", (args.device_id,)).fetchone()
        if row is None:
            raise ToolError("NOT_FOUND", "Unknown device id.")
        if row["customer_id"] != env.customer.customer_id:
            audit(env, "get_device_status", args.device_id, "forbidden")
            raise ToolError("FORBIDDEN_RESOURCE", "This device does not belong to this merchant.")
        rows = [row]
    else:
        rows = env.conn.execute(
            "SELECT * FROM devices WHERE customer_id = ? ORDER BY device_id", (env.customer.customer_id,)
        ).fetchall()
    devices = []
    for r in rows:
        last_seen = datetime.fromisoformat(r["last_seen_at"]) if r["last_seen_at"] else None
        devices.append(
            {
                "device_id": r["device_id"],
                "model": r["model"],
                "connectivity": r["connectivity"],
                "status": r["status"],
                "last_seen_at": r["last_seen_at"],
                "minutes_since_last_seen": int((now - last_seen).total_seconds() // 60) if last_seen else None,
                "config": json.loads(r["config"]),
            }
        )
    return {
        "devices": devices,
        "needs_selection": args.device_id is None and len(devices) > 1,
        "note": "Signals are the last ones received; no remote command is executed on the device.",
        "source": "DevicesMock",
        "observed_at": _observed(env),
    }


# --- find_authorization_events ------------------------------------------------------------------------------------


class AuthorizationArgs(_Args):
    period: Period = Field(default="last_7_days")
    status: Literal["declined", "approved", "any"] = Field(default="declined")
    limit: int = Field(default=5, ge=1, le=20)


def find_authorization_events(env: ToolEnv, args: AuthorizationArgs) -> dict:
    start, end = resolve_period(args.period, env.clock)
    params: list = [env.customer.customer_id, start.isoformat(), end.isoformat()]
    status_clause = ""
    if args.status != "any":
        status_clause = "AND a.status = ?"
        params.append(args.status)
    rows = env.conn.execute(
        f"""SELECT a.*, c.category, c.customer_message, c.next_step, c.retry_allowed
            FROM authorization_events a LEFT JOIN response_codes c ON c.code = a.response_code
            WHERE a.customer_id = ? AND substr(a.occurred_at,1,10) BETWEEN ? AND ? {status_clause}
            ORDER BY a.occurred_at DESC LIMIT ?""",  # noqa: S608 - fixed clause
        [*params, args.limit],
    ).fetchall()
    events = []
    for r in rows:
        documented = r["category"] is not None
        events.append(
            {
                "transaction_id": r["transaction_id"],
                "occurred_at": r["occurred_at"],
                "device_id": r["device_id"],
                "amount": money(r["amount_minor"], r["currency"]),
                "payment_type": r["payment_type"],
                "status": r["status"],
                "response_code": r["response_code"],
                "reason_category": r["category"]
                if documented
                else ("approved" if r["status"] == "approved" else "unknown"),
                "customer_message": r["customer_message"],
                "next_step": r["next_step"],
                "retry_allowed": bool(r["retry_allowed"]) if documented else None,
            }
        )
    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "events": events,
        "note": "Only codes documented in the demo have a reason; others stay unknown.",
        "source": "AuthorizationsMock",
        "observed_at": _observed(env),
    }


# --- get_contract_snapshot ----------------------------------------------------------------------------------------


class ContractArgs(_Args):
    pass


def get_contract_snapshot(env: ToolEnv, args: ContractArgs) -> dict:
    row = env.conn.execute("SELECT * FROM contracts WHERE customer_id = ?", (env.customer.customer_id,)).fetchone()
    if row is None:
        raise ToolError("NOT_FOUND", "No contract found for this merchant.")
    return {
        "products": json.loads(row["products"]),
        "settlement_account_type": row["settlement_account_type"],
        "settlement_plan": row["settlement_plan"],
        "effective_from": row["effective_from"],
        "source": "ContractsMock",
        "observed_at": _observed(env),
    }


# --- support prefix: history and healthcheck ----------------------------------------------------------------------


class HistoryArgs(_Args):
    topic: Topic | None = None


def get_complaint_history(env: ToolEnv, args: HistoryArgs) -> dict:
    params: list = [env.customer.customer_id]
    clause = ""
    if args.topic and args.topic != "general":
        clause = "AND topic = ?"
        params.append(args.topic)
    rows = env.conn.execute(
        f"SELECT * FROM support_cases WHERE customer_id = ? {clause} ORDER BY created_at DESC LIMIT 5",  # noqa: S608
        params,
    ).fetchall()
    cases = [
        {
            "case_id": r["case_id"],
            "topic": r["topic"],
            "status": r["status"],
            "summary": r["summary"],
            "attempts": json.loads(r["attempts"]),
            "created_at": r["created_at"],
            "closed_at": r["closed_at"],
        }
        for r in rows
    ]
    return {
        "cases": cases,
        "open_cases": sum(c["status"] == "open" for c in cases),
        "source": "SupportHistoryMock",
        "observed_at": _observed(env),
    }


class HealthcheckArgs(_Args):
    topic: Topic


def run_customer_healthcheck(env: ToolEnv, args: HealthcheckArgs) -> dict:
    now = env.clock.now()
    cid = env.customer.customer_id
    checks: list[dict] = []

    def check(name: str, status: str, note: str) -> None:
        checks.append({"check": name, "status": status, "note": note, "observed_at": now.isoformat(timespec="seconds")})

    if args.topic in ("receivables", "general"):
        check("receivables_service", "ok", "Schedule source reachable.")
        scheduled = env.conn.execute(
            "SELECT COUNT(*) FROM payouts p JOIN receivables r USING (receivable_id) "
            "WHERE r.customer_id = ? AND p.stage = 'SCHEDULED'",
            (cid,),
        ).fetchone()[0]
        check(
            "scheduled_payouts",
            "pending" if scheduled else "ok",
            f"{scheduled} payout(s) scheduled; pending is normal before the expected date.",
        )
    if args.topic in ("device", "general"):
        for d in env.conn.execute("SELECT * FROM devices WHERE customer_id = ?", (cid,)):
            status = {"online": "ok", "offline": "attention"}.get(d["status"], "unknown")
            check(f"device:{d['device_id']}", status, f"{d['model']} reported {d['status']}.")
    if args.topic in ("authorization", "general"):
        check("authorization_service", "ok", "Authorization events source reachable.")
        since = (now.date()).isoformat()
        declines = env.conn.execute(
            "SELECT COUNT(*) FROM authorization_events WHERE customer_id = ? AND status='declined' "
            "AND substr(occurred_at,1,10) >= ?",
            (cid, since),
        ).fetchone()[0]
        check("declines_today", "attention" if declines else "ok", f"{declines} declined transaction(s) today.")
    if args.topic in ("contract", "general"):
        check("contracts_service", "ok", "Contract source reachable.")
    return {
        "topic": args.topic,
        "checks": checks,
        "source": "HealthcheckMock",
        "observed_at": now.isoformat(timespec="seconds"),
    }
