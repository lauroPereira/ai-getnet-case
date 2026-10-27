"""Support tools as typed domain functions over the synthetic systems.

Every function receives the trusted `ToolEnv` (customer bound by the server) and validated arguments.
Resources of another customer are never returned: the call fails with FORBIDDEN_RESOURCE and is audited.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from merchant_assistant.data.clock import Period, resolve_period
from merchant_assistant.tools.base import ToolEnv, ToolError, audit, money

Topic = Literal[
    "receivables", "device", "authorization", "contract", "general", "pricing", "enablement", "cancellation"
]


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
    row = env.conn.execute(
        """SELECT c.*, p.pricing_plan, p.pricing_version FROM contracts c
           LEFT JOIN contract_pricing_context p USING (customer_id) WHERE c.customer_id = ?""",
        (env.customer.customer_id,),
    ).fetchone()
    if row is None:
        raise ToolError("NOT_FOUND", "No contract found for this merchant.")
    return {
        "products": json.loads(row["products"]),
        "settlement_account_type": row["settlement_account_type"],
        "settlement_plan": row["settlement_plan"],
        "effective_from": row["effective_from"],
        "pricing_context": {
            "plan": row["pricing_plan"],
            "version": row["pricing_version"],
            "source": "ContractPricingContextMock",
        },
        "source": "ContractsMock",
        "observed_at": _observed(env),
    }


# --- pricing, enablement and cancellation journeys --------------------------------------------------------------


class PricingArgs(_Args):
    period: Literal["latest", "today", "yesterday", "last_7_days"] = "latest"
    payment_type: Literal["debit", "credit", "pix"] | None = None
    installments: int | None = Field(default=None, ge=1, le=24)
    sale_date: date | None = None


def _select_sale(env: ToolEnv, args: PricingArgs) -> sqlite3.Row:
    cid = env.customer.customer_id
    rows = env.conn.execute(
        "SELECT * FROM sales WHERE customer_id = ? ORDER BY captured_at DESC, sale_id", (cid,)
    ).fetchall()
    if args.period != "latest":
        start = args.sale_date or resolve_period(args.period, env.clock)[0]
        end = start if args.sale_date else resolve_period(args.period, env.clock)[1]
        rows = [r for r in rows if start.isoformat() <= r["captured_at"][:10] <= end.isoformat()]
    elif args.sale_date:
        rows = [r for r in rows if r["captured_at"][:10] == args.sale_date.isoformat()]
    if args.payment_type:
        rows = [r for r in rows if r["payment_type"] == args.payment_type]
    if args.installments:
        rows = [r for r in rows if r["installments"] == args.installments]
    if not rows:
        raise ToolError("NOT_FOUND", "No sale matches the selected period and conditions.")
    if args.period == "latest" and not args.sale_date and not args.payment_type and not args.installments:
        return rows[0]
    if len(rows) > 1:
        raise ToolError("INVALID_ARGUMENT", "Several sales match. Add a payment type, installment count, or sale date.")
    return rows[0]


def _sale_conditions(env: ToolEnv, row: sqlite3.Row) -> dict:
    plan = env.conn.execute(
        "SELECT pricing_plan, pricing_version FROM contract_pricing_context WHERE customer_id = ?",
        (env.customer.customer_id,),
    ).fetchone()
    return {
        "payment_type": row["payment_type"],
        "installments": row["installments"],
        "channel": row["channel"],
        "pricing_plan": plan["pricing_plan"] if plan else "unknown",
    }


def _service(env: ToolEnv):
    if env.mock_services is None:
        raise ToolError("UNAVAILABLE", "Synthetic pricing and charges services are unavailable.")
    return env.mock_services


def _compare_pricing(
    pricing: dict, charge: dict, *, customer_id: str, transaction_id: str, gross_minor: int, currency: str
) -> dict:
    def valid_evidence(item: dict, amount_field: str, recorded: bool = True) -> bool:
        amount = item.get(amount_field)
        if not recorded or amount is None or not item.get("transaction_id") or not item.get("customer_id"):
            return False
        if sum(c["amount_minor"] for c in item["components"]) != amount:
            return False
        if item["installments"]:
            if sum(i["fee_minor"] for i in item["installments"]) != amount:
                return False
            if any(i["gross_minor"] != i["fee_minor"] + i["net_minor"] for i in item["installments"]):
                return False
        return True

    valid = (
        pricing["applicable"]
        and charge["recorded"]
        and pricing["customer_id"] == charge["customer_id"]
        and pricing["customer_id"] == customer_id
        and pricing["transaction_id"] == charge["transaction_id"]
        and pricing["transaction_id"] == transaction_id
        and pricing["currency"] == charge["currency"]
        and pricing["currency"] == currency
        and valid_evidence(pricing, "expected_fee_minor")
        and valid_evidence(charge, "charged_fee_minor")
        and sum(i["gross_minor"] for i in pricing["installments"]) == gross_minor
        and sum(i["gross_minor"] for i in charge["installments"]) == gross_minor
    )
    if not valid:
        result, delta = "insufficient_evidence", None
    elif pricing["conditions"] != charge["conditions"]:
        result, delta = "different_conditions", None
    else:
        delta = charge["charged_fee_minor"] - pricing["expected_fee_minor"]
        result = "consistent" if delta == 0 else "divergence"
    return {
        "result": result,
        "expected_fee_minor": pricing["expected_fee_minor"],
        "charged_fee_minor": charge["charged_fee_minor"],
        "difference_minor": delta,
        "currency": pricing["currency"],
        "expected_fee_display": money(pricing["expected_fee_minor"], pricing["currency"])["display"]
        if pricing["expected_fee_minor"] is not None
        else None,
        "charged_fee_display": money(charge["charged_fee_minor"], charge["currency"])["display"]
        if charge["charged_fee_minor"] is not None
        else None,
        "difference_display": money(delta, pricing["currency"])["display"] if delta is not None else None,
        "comparison_method": "integer_minor_units",
    }


def _normalized_source_amounts(item: dict, fee_field: str) -> dict:
    currency = item["currency"]
    amount = item[fee_field]
    return {
        "fee": money(amount, currency) if amount is not None else None,
        "components": [
            {"name": component["name"], "amount": money(component["amount_minor"], currency)}
            for component in item["components"]
        ],
        "installments": [
            {
                "number": installment["number"],
                "gross_amount": money(installment["gross_minor"], currency),
                "fee_amount": money(installment["fee_minor"], currency),
                "net_amount": money(installment["net_minor"], currency),
            }
            for installment in item["installments"]
        ],
    }


def simulate_pricing(env: ToolEnv, args: PricingArgs) -> dict:
    row = _select_sale(env, args)
    cond = _sale_conditions(env, row)
    request = {
        "customer_id": env.customer.customer_id,
        "transaction_id": row["sale_id"],
        "operation": "sale_fee",
        "gross_amount_minor": row["gross_minor"],
        "currency": row["currency"],
        "conditions": cond,
        "pricing_version": env.conn.execute(
            "SELECT pricing_version FROM contract_pricing_context WHERE customer_id = ?",
            (env.customer.customer_id,),
        ).fetchone()["pricing_version"],
    }
    pricing = _service(env).simulate(request)
    charge = _service(env).charge(row["sale_id"], env.customer.customer_id)
    if pricing["customer_id"] != env.customer.customer_id or charge["customer_id"] != env.customer.customer_id:
        audit(env, "simulate_pricing", row["sale_id"], "forbidden")
        raise ToolError("FORBIDDEN_RESOURCE", "Pricing or charge evidence does not belong to this merchant.")
    comparison = _compare_pricing(
        pricing,
        charge,
        customer_id=env.customer.customer_id,
        transaction_id=row["sale_id"],
        gross_minor=row["gross_minor"],
        currency=row["currency"],
    )
    financial_evidence = {
        "sale": {
            "gross_amount": money(row["gross_minor"], row["currency"])
            if row["currency"] == "BRL"
            else None
        },
        "pricing": None,
        "charge": None,
    }
    if comparison["result"] != "insufficient_evidence" and row["currency"] == "BRL":
        financial_evidence["pricing"] = _normalized_source_amounts(pricing, "expected_fee_minor")
        financial_evidence["charge"] = _normalized_source_amounts(charge, "charged_fee_minor")
    audit(env, "simulate_pricing", row["sale_id"], "ok")
    return {
        "sale": {"sale_date": row["captured_at"][:10], "gross_amount_minor": row["gross_minor"], **cond},
        "pricing": pricing,
        "charge": charge,
        "comparison": comparison,
        "financial_evidence": financial_evidence,
        "source": "independent_synthetic_pricing_and_charge_services",
        "observed_at": _observed(env),
        "note": "A comparison does not execute a correction, refund, or financial action.",
    }


def get_fee_breakdown(env: ToolEnv, args: PricingArgs) -> dict:
    row = _select_sale(env, args)
    record = _service(env).charge(row["sale_id"], env.customer.customer_id)
    if record["customer_id"] != env.customer.customer_id:
        audit(env, "get_fee_breakdown", row["sale_id"], "forbidden")
        raise ToolError("FORBIDDEN_RESOURCE", "Charge evidence does not belong to this merchant.")
    audit(env, "get_fee_breakdown", row["sale_id"], "ok")
    return {**record, "source": "independent_synthetic_charge_service", "observed_at": _observed(env)}


class EnablementArgs(_Args):
    scheme: str | None = Field(default=None, min_length=2, max_length=32)


def get_enablement_requests(env: ToolEnv, args: EnablementArgs) -> dict:
    params: list = [env.customer.customer_id]
    clause = ""
    if args.scheme:
        clause = "AND scheme = ?"
        params.append(args.scheme.casefold())
    rows = env.conn.execute(
        f"SELECT * FROM enablement_requests WHERE customer_id = ? {clause} ORDER BY requested_at DESC",
        params,
    ).fetchall()
    devices = env.conn.execute(
        "SELECT device_id, config FROM devices WHERE customer_id = ?", (env.customer.customer_id,)
    ).fetchall()
    availability = {}
    for device in devices:
        config = json.loads(device["config"])
        for scheme in config.get("card_schemes", []):
            availability[scheme.casefold()] = {"device_id": device["device_id"], "available": True}
    return {
        "requests": [
            {
                "request_id": r["request_id"],
                "scheme": r["scheme"],
                "status": r["status"],
                "protocol": r["protocol"],
                "requested_at": r["requested_at"],
                "activated_at": r["activated_at"],
                "device_availability": availability.get(r["scheme"].casefold(), {"available": False}),
            }
            for r in rows
        ],
        "source": "EnablementRequestsMock",
        "observed_at": _observed(env),
        "note": "Read-only status; no new request or terminal configuration is created.",
    }


class CancellationArgs(_Args):
    period: Literal["today", "yesterday", "last_7_days"] = "last_7_days"


def get_sale_cancellation_context(env: ToolEnv, args: CancellationArgs) -> dict:
    start, end = resolve_period(args.period, env.clock)
    rows = env.conn.execute(
        """SELECT c.* FROM sale_cancellations c JOIN sales s ON s.sale_id = c.transaction_id
           WHERE c.customer_id = ? AND s.customer_id = ?
             AND substr(s.captured_at,1,10) BETWEEN ? AND ?
           ORDER BY c.requested_at DESC""",
        (env.customer.customer_id, env.customer.customer_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    return {
        "cancellations": [dict(r) for r in rows],
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "source": "SaleCancellationMock",
        "observed_at": _observed(env),
        "note": "Read-only lookup. No sale cancellation or contract termination is executed.",
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
