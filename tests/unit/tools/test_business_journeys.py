import json
from datetime import date

from fastapi.testclient import TestClient

from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import seed
from merchant_assistant.evaluation.scripted_policy import route_for
from merchant_assistant.guardrails.output import unsupported
from merchant_assistant.mocks.clients import MockServiceClient
from merchant_assistant.mocks.service import create_mocks_app
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.domain import (
    AuthorizationArgs,
    CancellationArgs,
    EnablementArgs,
    PricingArgs,
    find_authorization_events,
    get_enablement_requests,
    get_sale_cancellation_context,
    simulate_pricing,
)


def environment(tmp_path, customer="cliente1988"):
    clock = FixedClock("2026-10-26T10:00:00")
    conn = connect(tmp_path / "synthetic.sqlite3")
    seed(conn, clock)
    test_client = TestClient(create_mocks_app())

    def dispatch(request):
        response = test_client.request(
            request.method, str(request.url), content=request.content, headers=request.headers
        )
        import httpx

        return httpx.Response(response.status_code, headers=response.headers, json=response.json())

    import httpx

    services = MockServiceClient("http://mocks", transport=httpx.MockTransport(dispatch))
    return conn, ToolEnv(conn, clock, CustomerContext(customer, True), mock_services=services)


def test_price_comparison_reports_four_distinct_results(tmp_path):
    conn, env = environment(tmp_path)
    results = [
        simulate_pricing(env, PricingArgs(period="yesterday", payment_type="debit")),
        simulate_pricing(env, PricingArgs(period="yesterday", payment_type="credit")),
        simulate_pricing(env, PricingArgs(period="yesterday", payment_type="pix")),
        simulate_pricing(env, PricingArgs(period="latest", payment_type="credit", installments=2)),
    ]
    assert [item["comparison"]["result"] for item in results] == [
        "consistent",
        "different_conditions",
        "divergence",
        "insufficient_evidence",
    ]
    assert results[2]["comparison"]["difference_minor"] == 75
    assert results[2]["comparison"]["comparison_method"] == "integer_minor_units"
    assert results[0]["pricing"]["transaction_id"] == results[0]["charge"]["transaction_id"]
    assert results[2]["financial_evidence"]["sale"]["gross_amount"]["display"] == "R$ 80,00"
    assert results[2]["financial_evidence"]["charge"]["installments"][0]["net_amount"]["display"] == "R$ 79,25"
    assert results[2]["charge"]["installments"][0]["net_minor"] == 7925

    evidence = [json.dumps(results[2], ensure_ascii=False)]
    known_amounts = "The sale was R$ 80,00 gross and R$ 79,25 net."
    assert unsupported(known_amounts, evidence, date(2026, 10, 26)) == []
    unsupported_amounts = unsupported("The sale was R$ 99,99 net.", evidence, date(2026, 10, 26))
    assert {violation.value for violation in unsupported_amounts} == {"9999"}

    insufficient = json.dumps(results[3], ensure_ascii=False)
    assert unsupported("The recorded net amount was R$ 79,25.", [insufficient], date(2026, 10, 26))
    conn.close()


def test_authorizations_default_to_recent_history_and_respect_explicit_period(tmp_path):
    conn, env = environment(tmp_path)
    conn.execute(
        """INSERT INTO authorization_events
           (transaction_id, customer_id, device_id, occurred_at, amount_minor, currency,
            payment_type, status, response_code)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "txn_test_yesterday_230",
            "cliente1988",
            "dev_1988_gs01",
            "2026-10-25T13:00:00-03:00",
            23000,
            "BRL",
            "credit",
            "declined",
            "51",
        ),
    )
    conn.commit()

    recent = find_authorization_events(env, AuthorizationArgs())
    today = find_authorization_events(env, AuthorizationArgs(period="today"))
    yesterday = find_authorization_events(env, AuthorizationArgs(period="yesterday"))

    assert any(event["transaction_id"] == "txn_test_yesterday_230" for event in recent["events"])
    assert all(event["transaction_id"] != "txn_test_yesterday_230" for event in today["events"])
    assert any(event["transaction_id"] == "txn_test_yesterday_230" for event in yesterday["events"])
    conn.close()


def test_enablement_distinguishes_request_activation_and_device(tmp_path):
    conn, env = environment(tmp_path)
    pending = get_enablement_requests(env, EnablementArgs(scheme="visa"))["requests"][0]
    active = get_enablement_requests(env, EnablementArgs(scheme="mastercard"))["requests"][0]
    assert pending["status"] == "pending" and pending["protocol"] == "SIM-BND-1988-001"
    assert active["status"] == "active" and active["device_availability"]["available"] is False
    assert conn.execute("SELECT COUNT(*) FROM enablement_requests WHERE customer_id='cliente1988'").fetchone()[0] == 2
    conn.close()


def test_cancellation_lookup_is_read_only_and_customer_scoped(tmp_path):
    conn, env = environment(tmp_path)
    conn.execute(
        """INSERT INTO sale_cancellations
           (transaction_id, customer_id, status, requested_at, processed_at, reason_code)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "sale_002_0002",
            "cliente1988",
            "completed",
            "2026-10-25T15:21:00",
            None,
            "synthetic_inconsistent_link",
        ),
    )
    conn.commit()

    data = get_sale_cancellation_context(env, CancellationArgs(period="yesterday"))
    assert data["cancellations"] == [
        {
            "transaction_id": "sale_1988_0002",
            "customer_id": "cliente1988",
            "status": "requested",
            "requested_at": "2026-10-25T13:10:00-03:00",
            "processed_at": None,
            "reason_code": "merchant_request",
        }
    ]
    rendered = str(data["cancellations"])
    assert "sale_002_0002" not in rendered
    assert "completed" not in rendered
    conn.close()


def test_internal_http_services_enforce_ownership_and_contract(tmp_path):
    client = TestClient(create_mocks_app())
    response = client.get("/charges/sale_1988_0001", params={"customer_id": "cliente_demo_002"})
    assert response.status_code == 403
    invalid = client.post(
        "/pricing/simulations", json={"customer_id": "cliente1988", "transaction_id": "sale_1988_0001"}
    )
    assert invalid.status_code == 422
    missing = client.get("/charges/unknown", params={"customer_id": "cliente1988"})
    assert missing.status_code == 404


def test_mock_service_reads_fixtures_from_runtime_data_directory(tmp_path, monkeypatch):
    import json

    from merchant_assistant.mocks.service import _load

    data_dir = tmp_path / "runtime-data"
    fixture_dir = data_dir / "mock-services"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "pricing-v1.json").write_text(json.dumps({"synthetic": {"customer_id": "c1"}}))
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.delenv("MOCK_SERVICES_DIR", raising=False)
    assert _load("pricing-v1.json") == {"synthetic": {"customer_id": "c1"}}
    monkeypatch.setenv("MOCK_SERVICES_DIR", str(fixture_dir))
    assert _load("pricing-v1.json") == {"synthetic": {"customer_id": "c1"}}


def test_http_client_controls_timeout_and_invalid_responses():
    import httpx
    import pytest

    from merchant_assistant.tools.base import ToolError

    timed = MockServiceClient(
        "http://mocks",
        transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("late"))),
    )
    with pytest.raises(ToolError, match="timed out"):
        timed.charge("sale_1988_0001", "cliente1988")
    invalid = MockServiceClient(
        "http://mocks", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"unexpected": True}))
    )
    with pytest.raises(ToolError, match="invalid response"):
        invalid.charge("sale_1988_0001", "cliente1988")


def test_product_interest_question_is_not_routed_to_fee_contestation():
    assert route_for("Qual é a taxa de juros da maquininha Get Ultra Pro 9000?") == ("knowledge", None)
    assert route_for("A taxa da venda de débito de ontem está coerente?") == ("support", "pricing")
