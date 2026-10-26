import threading

import pytest

from merchant_assistant.agents.router import enforce
from merchant_assistant.llm.base import Usage
from merchant_assistant.llm.pricing import PriceUnknown, cost, estimate
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard
from merchant_assistant.orchestration.state import RouterDecision


def test_cost_uses_versioned_prices():
    usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, cached_tokens=0, web_search_calls=1)
    assert cost("gpt-6-luna", usage) == pytest.approx(0.10 + 0.50 + 0.01)
    assert estimate("gpt-6-luna", 1000, 500) == pytest.approx(0.0001 + 0.00025)
    with pytest.raises(PriceUnknown):
        cost("unknown-model", usage)


def test_budget_reserve_settle_and_limit(tmp_path):
    guard = BudgetGuard(tmp_path / "b.sqlite3", limit_usd=0.01)
    rid = guard.reserve(request_id="r1", agent="router", model="m", amount=0.006)
    with pytest.raises(BudgetExceeded):
        guard.reserve(request_id="r2", agent="router", model="m", amount=0.006)
    guard.settle(rid, 0.001)  # real usage was lower: the reservation is released
    guard.reserve(request_id="r2", agent="router", model="m", amount=0.006)
    assert guard.spent() == pytest.approx(0.007)


def test_budget_unknown_usage_keeps_reservation(tmp_path):
    guard = BudgetGuard(tmp_path / "b.sqlite3", limit_usd=1)
    rid = guard.reserve(request_id="r", agent="a", model="m", amount=0.2)
    guard.settle(rid, None)
    assert guard.spent() == pytest.approx(0.2)


def test_budget_is_atomic_under_concurrency(tmp_path):
    guard = BudgetGuard(tmp_path / "b.sqlite3", limit_usd=0.05)
    accepted = []

    def worker():
        try:
            guard.reserve(request_id=None, agent="a", model="m", amount=0.01)
            accepted.append(1)
        except BudgetExceeded:
            pass

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(accepted) == 5
    assert guard.spent() == pytest.approx(0.05)


def decision(**kw):
    base = {
        "route": "knowledge",
        "language": "en",
        "topic": None,
        "intents": ["x"],
        "safety": "none",
        "clarification_question": None,
    }
    return RouterDecision.model_validate(base | kw)


def test_router_rules_after_model():
    assert enforce(decision(safety="sensitive")).route == "out_of_scope"
    assert enforce(decision(route="support")).topic == "general"
    assert enforce(decision(route="knowledge", topic="device")).topic is None
    assert enforce(decision(route="clarify")).clarification_question
