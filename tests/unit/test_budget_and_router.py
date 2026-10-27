import contextlib
import threading

import pytest

from merchant_assistant.agents.router import enforce
from merchant_assistant.llm.base import Usage
from merchant_assistant.llm.pricing import PriceUnknown, cost, estimate
from merchant_assistant.orchestration.budget import (
    BudgetExceeded,
    BudgetGuard,
    CombinedBudgetGuard,
    FixedBudgetGuard,
)
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


def test_campaign_cap_is_fixed_and_combined_reservations_are_single_charge(tmp_path):
    primary = BudgetGuard(tmp_path / "existing-ledger.sqlite3", 1.0)
    cap_path = tmp_path / "campaign-cap.sqlite3"
    cap = FixedBudgetGuard(cap_path, 0.25, cap_id="v050-qa")
    guard = CombinedBudgetGuard(primary, cap)
    reservation = guard.reserve(request_id="r1", agent="embed", model="test", amount=0.01)
    guard.settle(reservation, 0.006)
    assert primary.spent() == pytest.approx(0.006)
    assert cap.guard.spent() == pytest.approx(0.006)
    assert guard.remaining() == pytest.approx(0.244)

    reloaded = FixedBudgetGuard(cap_path, 0.25, cap_id="v050-qa")
    assert reloaded.guard.spent() == pytest.approx(0.006)
    with pytest.raises(ValueError):
        FixedBudgetGuard(cap_path, 0.2, cap_id="v050-qa")


def test_primary_guard_denial_cancels_campaign_reservation(tmp_path):
    primary = BudgetGuard(tmp_path / "existing-ledger.sqlite3", 0.005)
    campaign = FixedBudgetGuard(tmp_path / "campaign-cap.sqlite3", 0.25, cap_id="v050-qa")
    combined = CombinedBudgetGuard(primary, campaign)
    with pytest.raises(BudgetExceeded):
        combined.reserve(request_id="r1", agent="embed", model="test", amount=0.01)
    assert campaign.guard.spent() == 0


def _ledger_rows(path):
    import sqlite3

    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT status, reserved_usd, actual_usd FROM ledger ORDER BY id").fetchall()
    finally:
        conn.close()


def test_settle_is_single_shot_and_a_repeat_never_lowers_known_spend(tmp_path):  # R1-04
    path = tmp_path / "b.sqlite3"
    guard = BudgetGuard(path, limit_usd=1)
    rid = guard.reserve(request_id="r", agent="a", model="m", amount=0.05)
    guard.settle(rid, 0.01)
    assert guard.spent() == pytest.approx(0.01)

    guard.settle(rid, 0.01)  # the same value is an idempotent repeat
    assert guard.spent() == pytest.approx(0.01)

    with pytest.raises(ValueError):  # a divergent value must not release balance
        guard.settle(rid, 0.001)
    with pytest.raises(ValueError):  # nor may unknown usage rewrite what is already settled
        guard.settle(rid, None)
    guard.cancel(rid)  # cancel only releases reservations that were never dispatched
    assert guard.spent() == pytest.approx(0.01)
    assert _ledger_rows(path) == [("settled", 0.05, 0.01)]


def test_cancelled_reservation_cannot_be_settled_and_unknown_ids_are_refused(tmp_path):  # R1-04
    guard = BudgetGuard(tmp_path / "b.sqlite3", limit_usd=1)
    rid = guard.reserve(request_id="r", agent="a", model="m", amount=0.05)
    guard.cancel(rid)
    assert guard.spent() == 0
    with pytest.raises(ValueError):
        guard.settle(rid, 0.04)
    with pytest.raises(ValueError):
        guard.settle(rid, None)
    assert guard.spent() == 0
    with pytest.raises(ValueError):
        guard.settle(9999, 0.01)


@pytest.mark.parametrize("bad", [-0.01, float("nan"), float("inf"), float("-inf")])
def test_invalid_monetary_values_are_refused_without_releasing_balance(tmp_path, bad):  # R1-04
    path = tmp_path / "b.sqlite3"
    guard = BudgetGuard(path, limit_usd=1)
    rid = guard.reserve(request_id="r", agent="a", model="m", amount=0.05)
    with pytest.raises(ValueError):
        guard.settle(rid, bad)
    assert guard.spent() == pytest.approx(0.05)
    assert _ledger_rows(path) == [("reserved", 0.05, None)]
    with pytest.raises(ValueError):
        guard.reserve(request_id="r", agent="a", model="m", amount=bad)
    with pytest.raises(ValueError):
        guard.record(request_id="r", agent="a", model="m", actual_usd=bad)
    assert _ledger_rows(path) == [("reserved", 0.05, None)]


def test_concurrent_settlements_keep_exactly_one_value(tmp_path):  # R1-04
    path = tmp_path / "b.sqlite3"
    guard = BudgetGuard(path, limit_usd=1)
    rid = guard.reserve(request_id="r", agent="a", model="m", amount=0.5)
    values = [0.001 * (i + 1) for i in range(12)]
    outcomes: list[tuple[float, bool]] = []
    start = threading.Barrier(len(values))

    def worker(value):
        start.wait()
        try:
            guard.settle(rid, value)
            outcomes.append((value, True))
        except ValueError:
            outcomes.append((value, False))

    threads = [threading.Thread(target=worker, args=(v,)) for v in values]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    winners = [value for value, accepted in outcomes if accepted]
    assert len(winners) == 1 and len(outcomes) == len(values)
    assert guard.spent() == pytest.approx(winners[0])


def test_combined_guard_repeat_and_divergent_settlement_never_lower_either_ledger(tmp_path):  # R1-04
    primary = BudgetGuard(tmp_path / "primary.sqlite3", 1.0)
    campaign = FixedBudgetGuard(tmp_path / "campaign.sqlite3", 0.25, cap_id="v050-qa")
    guard = CombinedBudgetGuard(primary, campaign)
    ids = guard.reserve(request_id="r", agent="a", model="m", amount=0.05)
    guard.settle(ids, 0.02)
    guard.settle(ids, 0.02)  # idempotent
    with pytest.raises(ValueError):
        guard.settle(ids, 0.001)
    with pytest.raises(ValueError):
        guard.settle(ids, None)
    with pytest.raises(ValueError):
        guard.settle(ids, float("nan"))
    assert primary.spent() == pytest.approx(0.02)
    assert campaign.guard.spent() == pytest.approx(0.02)


def test_combined_guard_unknown_usage_keeps_the_conservative_reservation_in_both_ledgers(tmp_path):  # R1-04
    primary = BudgetGuard(tmp_path / "primary.sqlite3", 1.0)
    campaign = FixedBudgetGuard(tmp_path / "campaign.sqlite3", 0.25, cap_id="v050-qa")
    guard = CombinedBudgetGuard(primary, campaign)
    ids = guard.reserve(request_id="r", agent="a", model="m", amount=0.05)
    guard.settle(ids, None)
    assert primary.spent() == pytest.approx(0.05)
    assert campaign.guard.spent() == pytest.approx(0.05)
    guard.settle(ids, None)  # repeating the unknown usage is idempotent as well
    assert primary.spent() == pytest.approx(0.05)


def test_combined_guard_partial_failure_stays_conservative_and_a_retry_completes(tmp_path, monkeypatch):  # R1-04
    primary = BudgetGuard(tmp_path / "primary.sqlite3", 1.0)
    campaign = FixedBudgetGuard(tmp_path / "campaign.sqlite3", 0.25, cap_id="v050-qa")
    guard = CombinedBudgetGuard(primary, campaign)
    ids = guard.reserve(request_id="r", agent="a", model="m", amount=0.05)

    original = FixedBudgetGuard.settle
    calls = {"n": 0}

    def flaky(self, reservation_id, actual_usd):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("synthetic campaign ledger failure")
        return original(self, reservation_id, actual_usd)

    monkeypatch.setattr(FixedBudgetGuard, "settle", flaky)
    with pytest.raises(RuntimeError):
        guard.settle(ids, 0.02)
    assert primary.spent() == pytest.approx(0.02)  # primary already settled the known cost
    assert campaign.guard.spent() == pytest.approx(0.05)  # campaign keeps the conservative reservation
    with pytest.raises(ValueError):  # a divergent retry is refused and does not lower anything
        guard.settle(ids, 0.001)
    assert primary.spent() == pytest.approx(0.02)
    assert campaign.guard.spent() == pytest.approx(0.05)

    guard.settle(ids, 0.02)  # the same value retries safely and completes the pair
    assert primary.spent() == pytest.approx(0.02)
    assert campaign.guard.spent() == pytest.approx(0.02)


def test_combined_guard_primary_failure_leaves_both_reservations_conservative(tmp_path, monkeypatch):  # R1-04
    primary = BudgetGuard(tmp_path / "primary.sqlite3", 1.0)
    campaign = FixedBudgetGuard(tmp_path / "campaign.sqlite3", 0.25, cap_id="v050-qa")
    guard = CombinedBudgetGuard(primary, campaign)
    ids = guard.reserve(request_id="r", agent="a", model="m", amount=0.05)
    original = BudgetGuard.settle
    calls = {"n": 0}

    def flaky(self, reservation_id, actual_usd):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("synthetic primary ledger failure")
        return original(self, reservation_id, actual_usd)

    monkeypatch.setattr(BudgetGuard, "settle", flaky)
    with pytest.raises(RuntimeError):
        guard.settle(ids, 0.02)
    assert primary.spent() == pytest.approx(0.05) and campaign.guard.spent() == pytest.approx(0.05)
    guard.settle(ids, 0.02)
    assert primary.spent() == pytest.approx(0.02) and campaign.guard.spent() == pytest.approx(0.02)


def test_combined_guard_concurrent_settlements_leave_both_ledgers_equal(tmp_path):  # R1-04
    primary = BudgetGuard(tmp_path / "primary.sqlite3", 1.0)
    campaign = FixedBudgetGuard(tmp_path / "campaign.sqlite3", 0.25, cap_id="v050-qa")
    guard = CombinedBudgetGuard(primary, campaign)
    for round_number in range(15):  # many rounds: an unsynchronised settle would eventually interleave
        before = primary.spent()
        ids = guard.reserve(request_id="r", agent="a", model="m", amount=0.01)
        values = [0.0001 * (i + 1) for i in range(6)]
        start = threading.Barrier(len(values))

        def worker(value, ids=ids, start=start):
            start.wait()
            with contextlib.suppress(ValueError):
                guard.settle(ids, value)

        threads = [threading.Thread(target=worker, args=(v,)) for v in values]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        settled = primary.spent() - before
        assert any(settled == pytest.approx(v) for v in values), round_number
    assert primary.spent() == pytest.approx(campaign.guard.spent())
    primary_rows, campaign_rows = (_ledger_rows(guard_path) for guard_path in (primary.path, campaign.guard.path))
    assert [row[2] for row in primary_rows] == pytest.approx([row[2] for row in campaign_rows])


@pytest.mark.parametrize("bad", [5.01, 6.0, 1000.0, -0.01, float("nan"), float("inf")])
def test_absolute_ceiling_applies_to_settings_and_to_the_guard(tmp_path, bad):  # R1-06
    from pydantic import ValidationError

    from merchant_assistant.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, budget_limit_usd=bad)
    with pytest.raises(ValueError):
        BudgetGuard(tmp_path / "b.sqlite3", bad)
    assert not (tmp_path / "b.sqlite3").exists()


def test_absolute_ceiling_is_exactly_five_dollars(tmp_path):  # R1-06
    from merchant_assistant.config import Settings

    assert Settings(_env_file=None, budget_limit_usd=5).budget_limit_usd == 5.0
    guard = BudgetGuard(tmp_path / "b.sqlite3", 5.0)
    guard.reserve(request_id="r", agent="a", model="m", amount=5.0)
    with pytest.raises(BudgetExceeded):
        guard.reserve(request_id="r", agent="a", model="m", amount=0.01)
    assert guard.spent() == pytest.approx(5.0)


def test_persisted_ceiling_cannot_be_raised_by_remounting(tmp_path):  # R1-06
    path = tmp_path / "b.sqlite3"
    guard = BudgetGuard(path, 0.5)
    guard.reserve(request_id="r", agent="a", model="m", amount=0.4)
    with pytest.raises(ValueError):
        BudgetGuard(path, 1.0)
    with pytest.raises(ValueError):
        BudgetGuard(path, 5.0)
    stricter = BudgetGuard(path, 0.3)  # a stricter limit is allowed and keeps the recorded spend
    assert stricter.spent() == pytest.approx(0.4) and stricter.remaining() == 0
    with pytest.raises(ValueError):
        BudgetGuard(path, 0.6)


def test_legacy_ledger_without_a_recorded_ceiling_stays_at_the_native_one_dollar(tmp_path):  # R1-06
    import sqlite3

    from merchant_assistant.orchestration.budget import LEDGER_SCHEMA

    path = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(LEDGER_SCHEMA)
    conn.close()
    with pytest.raises(ValueError):
        BudgetGuard(path, 5.0)
    assert BudgetGuard(path, 1.0).limit_usd == 1.0


@pytest.mark.parametrize("bad", [0, 0.2500001, 0.26, 5.0, -0.1, float("nan"), float("inf")])
def test_campaign_cap_stays_within_the_fixed_quarter_dollar(tmp_path, bad):  # R1-06
    with pytest.raises(ValueError):
        FixedBudgetGuard(tmp_path / "campaign.sqlite3", bad, cap_id="v050-qa")


def test_campaign_cap_cannot_be_changed_in_either_direction_by_remounting(tmp_path):  # R1-06
    path = tmp_path / "campaign.sqlite3"
    first = FixedBudgetGuard(path, 0.15, cap_id="v050-qa")
    first.reserve(request_id="r", agent="a", model="m", amount=0.1)
    for amount in (0.25, 0.2, 0.1):
        with pytest.raises(ValueError):
            FixedBudgetGuard(path, amount, cap_id="v050-qa")
    with pytest.raises(ValueError):
        FixedBudgetGuard(path, 0.15, cap_id="another-campaign")
    again = FixedBudgetGuard(path, 0.15, cap_id="v050-qa")
    assert again.guard.spent() == pytest.approx(0.1) and again.guard.limit_usd == 0.15


def decision(**kw):
    base = {
        "route": "knowledge",
        "language": "en",
        "topic": None,
        "intents": ["x"],
        "safety": "none",
        "clarification_question": None,
        "case_signal": "none",
    }
    return RouterDecision.model_validate(base | kw)


def test_router_rules_after_model():
    assert enforce(decision(safety="sensitive")).route == "out_of_scope"
    assert enforce(decision(route="support")).topic == "general"
    assert enforce(decision(route="knowledge", topic="device")).topic is None
    assert enforce(decision(route="clarify")).clarification_question
