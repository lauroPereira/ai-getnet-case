from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import CHECK_KEYS, load_cases, run, summarize, write_report
from merchant_assistant.testing import offline_orchestrator

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"


def test_labeled_scenarios_are_valid():
    cases = load_cases([SCENARIOS / "challenge_examples.jsonl", SCENARIOS / "core_cases.jsonl"])
    assert len(cases) == 27
    assert sum(c.split == "dev" for c in cases) == 10
    assert len({c.id for c in cases}) == 27


def test_runner_scripted_mode_produces_report(settings, tmp_path):
    orchestrator, _ = offline_orchestrator(settings)
    cases = [c for c in load_cases([SCENARIOS / "core_cases.jsonl"]) if c.id in {"UC12", "UC14", "UC16", "UC18"}]
    rows = run(orchestrator, cases)
    assert all(r["route_ok"] and r["status_ok"] for r in rows)
    summary = summarize(rows)
    assert summary["overall"]["n"] == 4 and set(CHECK_KEYS) <= set(summary["overall"])
    md, js = write_report(rows, summary, tmp_path, "test", {"mode": "scripted"})
    assert md.exists() and js.exists()


def test_multi_turn_scenarios_scripted(settings):
    from merchant_assistant.evaluation.runner import run_conversations

    orchestrator, _ = offline_orchestrator(settings)
    rows = run_conversations(orchestrator, SCENARIOS / "followup.jsonl")
    assert len(rows) == 4
    assert all(r["passed"] for r in rows), [(r["id"], [t for t in r["turns"] if not t["passed"]]) for r in rows]
