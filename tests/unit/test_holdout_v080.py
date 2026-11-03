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
    raw = HOLDOUT.read_bytes()
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


def test_tool_backed_amounts_come_from_the_seed(tmp_path):
    """Every amount labeled on a case that expects tools is returned by those tools over the synthetic seed."""
    clock = FixedClock(DEFAULT_CLOCK)
    conn = connect(tmp_path / "holdout.sqlite3")
    seed(conn, clock)
    env = ToolEnv(conn, clock, CustomerContext(MAIN_CUSTOMER, True), mock_services=in_process_client())
    calls = [
        ("get_receivables_schedule", {"period": "last_7_days"}),
        ("get_payout_status", {"receivable_ids": ["rcv_1988_0003", "rcv_1988_0004"]}),
        ("find_authorization_events", {}),
        ("simulate_pricing", {"payment_type": "credit", "sale_date": "2026-10-20"}),
        ("simulate_pricing", {"period": "yesterday", "payment_type": "credit"}),
    ]
    available: set[int] = set()
    for name, args in calls:
        outcome = execute(name, args, env)
        assert outcome.ok, (name, outcome.error)
        available |= _minor_values(outcome.data)
    conn.close()
    for case in load_cases([HOLDOUT]):
        if case.expected_tools:
            assert set(case.must_include_amounts) <= available, case.id
