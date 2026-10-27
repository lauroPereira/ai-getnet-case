"""MCP transport gives the same results and errors as the domain layer (in-process client, no network)."""

import json

import anyio
from mcp import Client

from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import seed
from merchant_assistant.mcp_server import build_server, env_factory_for
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import AGENT_TOOLS, execute

CLOCK = FixedClock("2026-10-26T10:00:00")


def setup(settings, customer="cliente1988"):
    conn = connect(settings.db_path)
    seed(conn, CLOCK)
    conn.close()
    from merchant_assistant.mocks.clients import in_process_client

    return build_server(env_factory_for(settings.db_path, customer, CLOCK, in_process_client()))


def run(server, calls):
    async def main():
        async with Client(server) as client:
            listed = await client.list_tools()
            results = [await client.call_tool(name, args) for name, args in calls]
            return listed, results

    return anyio.run(main)


def text(result):
    return json.loads(result.content[0].text)


def test_lists_only_the_support_tools(settings):
    listed, _ = run(setup(settings), [])
    assert sorted(t.name for t in listed.tools) == sorted(AGENT_TOOLS["customer_support"])
    assert all("customer" not in json.dumps(t.input_schema) for t in listed.tools)


def test_same_result_as_the_domain_layer(settings):
    _, (result,) = run(setup(settings), [("get_receivables_schedule", {"period": "yesterday"})])
    conn = connect(settings.db_path)
    direct = execute(
        "get_receivables_schedule", {"period": "yesterday"}, ToolEnv(conn, CLOCK, CustomerContext("cliente1988", True))
    )
    assert result.is_error is False
    assert text(result) == json.loads(json.dumps(direct.data, default=str))


def test_pricing_tools_match_the_domain_over_mcp(settings):
    args = {"period": "yesterday", "payment_type": "debit"}
    _, (result,) = run(setup(settings), [("simulate_pricing", args)])
    assert result.is_error is False
    from merchant_assistant.mocks.clients import in_process_client

    conn = connect(settings.db_path)
    direct = execute(
        "simulate_pricing",
        args,
        ToolEnv(conn, CLOCK, CustomerContext("cliente1988", True), mock_services=in_process_client()),
    )
    assert text(result) == json.loads(json.dumps(direct.data, default=str))


def test_all_business_journey_tools_are_available_over_mcp(settings):
    calls = [
        ("get_fee_breakdown", {"period": "yesterday", "payment_type": "debit"}),
        ("get_enablement_requests", {"scheme": "visa"}),
        ("get_sale_cancellation_context", {"period": "yesterday"}),
    ]
    listed, results = run(setup(settings), calls)
    names = {tool.name for tool in listed.tools}
    assert {name for name, _ in calls} <= names
    assert all(not result.is_error for result in results)
    assert "charged_fee_minor" in text(results[0])
    assert text(results[1])["requests"][0]["protocol"] == "SIM-BND-1988-001"
    assert text(results[2])["cancellations"][0]["status"] == "requested"


def test_other_merchant_resource_is_blocked_and_audited(settings):
    _, (result,) = run(setup(settings), [("get_payout_status", {"receivable_ids": ["rcv_002_0001"]})])
    assert result.is_error is True
    assert text(result)["error"]["code"] == "FORBIDDEN_RESOURCE"
    audit = connect(settings.db_path).execute("SELECT tool, resource_id, outcome FROM audit_events").fetchall()
    assert [tuple(r) for r in audit] == [("get_payout_status", "rcv_002_0001", "forbidden")]


def test_invalid_arguments_and_unknown_merchant(settings):
    _, (bad,) = run(setup(settings), [("find_authorization_events", {"limit": 500})])
    assert bad.is_error and text(bad)["error"]["code"] == "INVALID_ARGUMENT"
    _, (unknown,) = run(setup(settings, customer="nobody"), [("get_contract_snapshot", {})])
    assert unknown.is_error and text(unknown)["error"]["code"] == "CUSTOMER_NOT_FOUND"
