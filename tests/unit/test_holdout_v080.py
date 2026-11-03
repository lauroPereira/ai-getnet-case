"""Seal and shape of the v0.8.0 answer holdout (RF-92): written before any v0.8.0 prompt change, never tuned on.

The SHA-256 is computed over the UTF-8 content with line breaks normalized to LF, so a checkout with CRLF still
matches and any edit to a case breaks the seal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import MAIN_CUSTOMER, seed
from merchant_assistant.evaluation.runner import load_cases
from merchant_assistant.guardrails.output import amounts
from merchant_assistant.mocks.clients import in_process_client
from merchant_assistant.testing import DEFAULT_CLOCK
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import execute

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"
HOLDOUT = SCENARIOS / "holdout_v080.jsonl"
SEAL = SCENARIOS / "holdout_v080.sha256"
REQUIRED_ROUTES = {"knowledge", "support", "knowledge_and_support", "general_web", "human_handoff", "out_of_scope"}


def normalized_digest(raw: bytes) -> str:
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sealed_digest() -> str:
    return SEAL.read_text(encoding="utf-8").split()[0]


def other_scenario_rows() -> list[dict]:
    rows = []
    for path in sorted(SCENARIOS.glob("*.jsonl")):
        if path != HOLDOUT:
            rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows


def test_seal_matches_content():
    assert normalized_digest(HOLDOUT.read_bytes()) == sealed_digest()


def test_seal_ignores_line_endings_but_not_content():
    raw = HOLDOUT.read_bytes().replace(b"\r\n", b"\n")  # the checkout may already be CRLF (text=auto)
    assert normalized_digest(raw) == sealed_digest()
    assert normalized_digest(raw.replace(b"\n", b"\r\n")) == sealed_digest()
    tampered = bytearray(raw)
    tampered[10] = ord("x") if tampered[10] != ord("x") else ord("y")
    assert normalized_digest(bytes(tampered)) != sealed_digest()


def test_cases_load_with_the_runner_and_have_the_agreed_shape():
    cases = load_cases([HOLDOUT])
    assert len(cases) >= 20
    assert sum(c.language == "pt" for c in cases) * 2 >= len(cases)
    assert {c.language for c in cases} == {"pt", "en"}
    assert {c.split for c in cases} == {"holdout_v080"}
    assert {route for c in cases for route in c.accepted_routes} >= REQUIRED_ROUTES
    assert sum(c.id.endswith("-HARD") for c in cases) >= 3
    assert all(c.user_id == MAIN_CUSTOMER for c in cases)


def test_ids_are_unique_and_do_not_collide_with_other_sets():
    ids = [c.id for c in load_cases([HOLDOUT])]
    assert len(ids) == len(set(ids))
    assert not set(ids) & {row["id"] for row in other_scenario_rows()}


def test_messages_are_new():
    def norm(text: str) -> str:
        return " ".join(text.casefold().split())

    seen = set()
    for row in other_scenario_rows():
        seen |= {norm(row[key]) for key in ("message", "question") if key in row}
        seen |= {norm(turn["message"]) for turn in row.get("turns", [])}
    messages = [norm(c.message) for c in load_cases([HOLDOUT])]
    assert len(messages) == len(set(messages))
    assert not set(messages) & seen


def _minor_values(node) -> set[int]:
    if isinstance(node, dict):
        found = {v for k, v in node.items() if (k == "minor" or k.endswith("_minor")) and isinstance(v, int)}
        return found.union(*(_minor_values(v) for v in node.values()))
    if isinstance(node, list):
        return set().union(*(_minor_values(v) for v in node)) if node else set()
    return set()


# Where each labeled amount comes from: the calls of that case over the seed, or the official page and excerpt.
TOOL_DERIVATION = {
    "HV080-EN-SUP-RECEIVABLE-DEBIT-NET": [("get_receivables_schedule", {"period": "yesterday"})],
    "HV080-EN-SUP-PAYOUT-LINK-SALE": [
        ("get_receivables_schedule", {"period": "last_7_days"}),
        ("get_payout_status", {"receivable_ids": ["rcv_1988_0004"]}),
    ],
    "HV080-EN-SUP-DEBIT-DECLINE-ISSUER": [("find_authorization_events", {})],
    "HV080-PT-SUP-PRICE-LINK-CONSISTENT": [("simulate_pricing", {"payment_type": "credit", "sale_date": "2026-10-20"})],
    "HV080-EN-SUP-PRICE-CREDIT-CONDITIONS": [("simulate_pricing", {"period": "yesterday", "payment_type": "credit"})],
    "HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE": [("find_authorization_events", {})],
    "HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD": [
        ("get_receivables_schedule", {"period": "yesterday"}),
        ("get_payout_status", {"receivable_ids": ["rcv_1988_0003"]}),
    ],
}
SOURCE_DERIVATION = {
    "HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD": (
        "site-getnet-com-br-get-ajuda-antecipacao-de-venda-como-antecipar-sua-vendas-pelo-app",
        "o valor mínimo para antecipação é de R$50,00",
    ),
    "HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION": (
        "site-getnet-com-br-get-ajuda-whatsapp-business-descontinuacao-whatsapp-business",
        "R$1,00 por link pago",
    ),
}
PAGES = Path(__file__).resolve().parents[2] / "data" / "snapshots" / "public" / "pages"


def test_every_labeled_amount_has_a_derivation():
    labeled = {c.id for c in load_cases([HOLDOUT]) if c.must_include_amounts}
    assert labeled == set(TOOL_DERIVATION) | set(SOURCE_DERIVATION)


def test_tool_backed_amounts_come_from_the_calls_of_each_case(tmp_path):
    """Each case's amounts are returned by that case's own calls over the synthetic seed (fixed seed clock)."""
    clock = FixedClock(DEFAULT_CLOCK)
    conn = connect(tmp_path / "holdout.sqlite3")
    seed(conn, clock)
    env = ToolEnv(conn, clock, CustomerContext(MAIN_CUSTOMER, True), mock_services=in_process_client())
    cases = {c.id: c for c in load_cases([HOLDOUT])}
    try:
        for case_id, calls in TOOL_DERIVATION.items():
            available: set[int] = set()
            for name, args in calls:
                outcome = execute(name, args, env)
                assert outcome.ok, (case_id, name, outcome.error)
                available |= _minor_values(outcome.data)
            assert set(cases[case_id].must_include_amounts) <= available, case_id
    finally:
        conn.close()


def test_official_amounts_come_from_the_versioned_pages():
    cases = {c.id: c for c in load_cases([HOLDOUT])}
    for case_id, (page, excerpt) in SOURCE_DERIVATION.items():
        text = json.loads((PAGES / f"{page}.json").read_text(encoding="utf-8"))["text"]
        assert excerpt in text, case_id
        assert amounts(excerpt) == set(cases[case_id].must_include_amounts), case_id
