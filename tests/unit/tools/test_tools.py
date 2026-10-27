import json

import pytest

from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import MAIN_CUSTOMER, OTHER_CUSTOMER, seed
from merchant_assistant.tools.base import CustomerContext, ToolEnv, money
from merchant_assistant.tools.registry import AGENT_TOOLS, TOOLS, execute, model_tool_schemas


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "db.sqlite3")
    seed(c, FixedClock("2026-10-26T10:00:00"))
    return c


def env(conn, customer=MAIN_CUSTOMER, known=True, faults=None):
    return ToolEnv(conn, FixedClock("2026-10-26T10:00:00"), CustomerContext(customer, known), faults or {})


def test_money_display():
    assert money(116220)["display"] == "R$ 1.162,20"
    assert money(5)["display"] == "R$ 0,05"


def test_receivables_yesterday_by_sale_date(conn):
    out = execute("get_receivables_schedule", {"period": "yesterday"}, env(conn))
    assert out.ok
    ids = [r["receivable_id"] for r in out.data["receivables"]]
    assert ids == ["rcv_1988_0001", "rcv_1988_0002", "rcv_1988_0003"]
    credit = out.data["receivables"][1]
    assert credit["expected_payment_date"] == "2026-10-27"
    assert credit["normalized_status"] == "batch_processed"


def test_receivables_empty_period(conn):
    out = execute("get_receivables_schedule", {"date_from": "2026-01-01", "date_to": "2026-01-31"}, env(conn))
    assert out.ok and out.data["count"] == 0


def test_receivables_invalid_range(conn):
    out = execute("get_receivables_schedule", {"date_from": "2026-10-20", "date_to": "2026-10-01"}, env(conn))
    assert not out.ok and out.error["code"] == "INVALID_ARGUMENT"


def test_payout_status_and_credit_confirmation(conn):
    out = execute("get_payout_status", {"receivable_ids": ["rcv_1988_0002", "rcv_1988_0003"]}, env(conn))
    assert out.ok
    by_id = {p["receivable_id"]: p for p in out.data["payouts"]}
    assert by_id["rcv_1988_0002"]["credit_confirmed"] is False
    assert by_id["rcv_1988_0003"]["credit_confirmed"] is True


def test_payout_of_other_customer_is_forbidden_and_audited(conn):
    out = execute("get_payout_status", {"receivable_ids": ["rcv_002_0001"]}, env(conn))
    assert not out.ok and out.error["code"] == "FORBIDDEN_RESOURCE"
    assert out.data is None
    audit = conn.execute("SELECT * FROM audit_events").fetchone()
    assert audit["customer_id"] == MAIN_CUSTOMER and audit["resource_id"] == "rcv_002_0001"


def test_device_listing_and_selection(conn):
    single = execute("get_device_status", {}, env(conn))
    assert single.ok and not single.data["needs_selection"]
    assert single.data["devices"][0]["status"] == "offline"
    assert single.data["devices"][0]["minutes_since_last_seen"] == 180
    multiple = execute("get_device_status", {}, env(conn, OTHER_CUSTOMER))
    assert multiple.data["needs_selection"] is True


def test_device_of_other_customer_is_forbidden(conn):
    out = execute("get_device_status", {"device_id": "dev_002_gc01"}, env(conn))
    assert out.error["code"] == "FORBIDDEN_RESOURCE"


def test_authorization_events_without_identifier(conn):
    out = execute("find_authorization_events", {}, env(conn))
    assert out.ok
    latest = out.data["events"][0]
    assert latest["transaction_id"] == "txn_1988_0101"
    assert latest["reason_category"] == "insufficient_funds"
    assert len(out.data["events"]) == 2


def test_contract_history_and_healthcheck(conn):
    contract = execute("get_contract_snapshot", {}, env(conn))
    assert "pix" in contract.data["products"] and contract.data["settlement_account_type"] == "get_conta"
    history = execute("get_complaint_history", {"topic": "device"}, env(conn))
    assert history.data["cases"][0]["status"] == "closed"
    health = execute("run_customer_healthcheck", {"topic": "device"}, env(conn))
    assert {c["status"] for c in health.data["checks"]} == {"attention"}


def test_unknown_customer_and_injected_failure(conn):
    unknown = execute("get_contract_snapshot", {}, env(conn, "nobody", known=False))
    assert unknown.error["code"] == "CUSTOMER_NOT_FOUND"
    failed = execute("get_device_status", {}, env(conn, faults={"get_device_status": "UNAVAILABLE"}))
    assert failed.error["code"] == "UNAVAILABLE"


def test_invalid_arguments_and_unknown_tool(conn):
    assert execute("get_payout_status", {"receivable_ids": []}, env(conn)).error["code"] == "INVALID_ARGUMENT"
    assert execute("drop_tables", {}, env(conn)).error["code"] == "INVALID_ARGUMENT"
    assert execute("get_device_status", "{not json", env(conn)).error["code"] == "INVALID_ARGUMENT"


def test_agent_allowlist(conn):
    out = execute("get_complaint_history", {}, env(conn), agent="customer_support")
    assert not out.ok


def test_model_schemas_never_expose_customer_id():
    schemas = model_tool_schemas("customer_support")
    assert {s["name"] for s in schemas} == set(AGENT_TOOLS["customer_support"])
    dumped = json.dumps(schemas)
    assert "customer" not in dumped
    assert set(TOOLS) >= set(AGENT_TOOLS["customer_support"])
