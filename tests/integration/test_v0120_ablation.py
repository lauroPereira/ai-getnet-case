"""v0.12.0 task 93 (RF-117, CA-66; spec D3; ADR 0024): the replanning ablation.

Scripted model, no network, no cost. `REPLAN=off` builds the graph without the `replan` step (the Router's initial
plan and the request limits stay); `eval --replan off` records it in the configuration of the report; `eval-compare`
pairs two reports by case and repetition, by criterion and route, with a bootstrap interval of the difference, counts
the decisions of the `replan` step by origin and splits the paired difference between the pairs with a decision of
origin `model` and those with rule decisions only."""

from __future__ import annotations

import itertools
import json
import tempfile
import uuid

import pytest
from pydantic import ValidationError

from merchant_assistant import cli
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.evaluation import compare
from merchant_assistant.evaluation.runner import CHECK_KEYS, load_cases
from merchant_assistant.orchestration.graph import build_graph

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
CASES = {
    case.id: case
    for case in load_cases([SCENARIOS / "replan.jsonl", SCENARIOS / "challenge_examples.jsonl"])
}
FAULTS = {"REPLAN-TOOL-DOWN": {"simulate_pricing": "UNAVAILABLE"}}


def handle(orchestrator, message: str, user_id: str = "cliente1988"):
    request_id = f"req_t93_{uuid.uuid4().hex[:12]}"
    response = orchestrator.handle(MessageRequest(message=message, user_id=user_id), request_id)
    return response, orchestrator.trace(request_id)


def steps(trace) -> list[str]:
    return [s["step"] for s in trace["steps"]]


# --- REPLAN=on|off ----------------------------------------------------------------------------------------------------


def test_replan_is_on_by_default_and_read_from_replan(monkeypatch):
    monkeypatch.delenv("REPLAN", raising=False)
    assert Settings(_env_file=None).replan == "on"
    monkeypatch.setenv("REPLAN", "off")
    assert Settings(_env_file=None).replan == "off"
    monkeypatch.setenv("REPLAN", "sometimes")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "REPLAN=on" in example


def test_the_graph_without_replanning_has_no_replan_step():
    on, off = set(build_graph().get_graph().nodes), set(build_graph(replan=False).get_graph().nodes)
    assert {"replan", "web"} <= on
    assert not off & {"replan", "web"}
    assert on - off == {"replan", "web"}


@pytest.mark.parametrize(
    ("case_id", "on", "off"),
    [
        # the four replanning scenarios: with off, the specialist of the Router's plan goes straight to the reply
        ("REPLAN-WEB", ["router", "knowledge", "web", "personality"], ["router", "knowledge", "personality"]),
        ("REPLAN-ACCOUNT", ["router", "knowledge", "customer_support", "personality"],
         ["router", "knowledge", "personality"]),
        ("REPLAN-PROCEDURE", ["router", "customer_support", "knowledge", "personality"],
         ["router", "customer_support", "personality"]),
        # a Support that asks for a human still reaches Escalation, as before v0.8.0
        ("REPLAN-TOOL-DOWN", ["router", "customer_support", "escalation", "personality"],
         ["router", "customer_support", "escalation", "personality"]),
        # the initial plan of knowledge_and_support still runs both specialists
        ("EX05", ["router", "knowledge", "customer_support", "personality"],
         ["router", "knowledge", "customer_support", "personality"]),
    ],
)
def test_with_replan_off_each_specialist_goes_to_the_reply_and_the_initial_plan_stays(
    offline, settings, case_id, on, off
):
    case = CASES[case_id]
    _, orchestrator, _ = offline(faults=FAULTS.get(case_id))
    replanned, trace_on = handle(orchestrator, case.message)
    assert replanned.agents == on and "replan" in steps(trace_on)  # the default is unchanged

    settings.replan = "off"
    _, ablated, _ = offline(faults=FAULTS.get(case_id))
    response, trace = handle(ablated, case.message)
    assert response.agents == off and response.answer.strip()
    assert "replan" not in steps(trace) and "web" not in steps(trace)
    assert response.route == replanned.route  # the route is the Router's initial plan in both
    assert trace["detail"]["plan_hops"] == 0


def test_with_replan_off_the_request_limits_still_hold(offline, settings):
    settings.replan, settings.max_model_calls = "off", 2
    _, orchestrator, _ = offline()
    response, trace = handle(orchestrator, CASES["EX05"].message)  # router + knowledge use the two calls
    assert trace["model_calls"] == 2 and response.answer.strip()
    assert "replan" not in steps(trace)
    personality = next(s for s in trace["steps"] if s["step"] == "personality")
    assert personality["detail"]["source"] == "fallback"


# --- eval --replan and eval-compare through the CLI -------------------------------------------------------------------


@pytest.fixture
def ablation_tree(tmp_path, monkeypatch, settings):
    """A temporary project root with three replanning scenarios and EX05 (TOOL-DOWN needs a fault: tested above); the
    CLI reads these settings, never .env, and each scripted run gets its own runtime inside the test's directory."""
    root = tmp_path / "project"
    scenarios = root / "tests" / "scenarios"
    scenarios.mkdir(parents=True)
    wanted = {"REPLAN-WEB", "REPLAN-ACCOUNT", "REPLAN-PROCEDURE", "EX05"}
    for name in ("replan.jsonl", "challenge_examples.jsonl"):
        lines = (SCENARIOS / name).read_text(encoding="utf-8").splitlines()
        keep = [line for line in lines if line.strip() and json.loads(line)["id"] in wanted]
        (scenarios / name).write_text("\n".join(keep) + "\n", encoding="utf-8")
    for name in ("core_cases.jsonl", "business_journeys.jsonl"):
        (scenarios / name).write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    runs = itertools.count()

    def fresh(prefix=""):
        path = tmp_path / f"scripted-run-{next(runs)}"
        path.mkdir()
        return str(path)

    monkeypatch.setattr(tempfile, "mkdtemp", fresh)
    return root


def scripted_eval(tmp_path, *extra: str) -> int:
    return cli.main(
        ["eval", "--scripted", "--include-replan", "--no-conversations", "--out", str(tmp_path / "out"), *extra]
    )


def read(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_eval_replan_off_records_it_and_never_overwrites_the_report_of_the_on_run(tmp_path, ablation_tree):
    assert scripted_eval(tmp_path) == 0
    assert scripted_eval(tmp_path, "--replan", "off") == 0
    on, off = read(tmp_path / "out" / "avaliacao.json"), read(tmp_path / "out" / "avaliacao-replan-off.json")
    assert on["config"]["replan"] == "on" and off["config"]["replan"] == "off"
    assert [r["id"] for r in on["cases"]] == [r["id"] for r in off["cases"]] == [
        "REPLAN-WEB", "REPLAN-PROCEDURE", "REPLAN-ACCOUNT", "EX05"
    ]
    # the decisions of the replan step come from the traces: none with off
    assert all(r["replan"] == [] for r in off["cases"])
    web = next(r for r in on["cases"] if r["id"] == "REPLAN-WEB")["replan"]
    assert [(d["next"], d["origin"]) for d in web] == [
        ("web", "rule:evidence_insufficient_web"),
        ("finish", "rule:complete"),
    ]
    assert {"next", "origin", "reason", "review", "hops", "observed"} <= set(web[0])


def test_the_default_name_reads_replan_from_the_settings(tmp_path, ablation_tree, settings):
    """REPLAN=off in the environment selects the matching report name without replacing the on report."""
    settings.replan = "off"
    assert scripted_eval(tmp_path) == 0
    assert read(tmp_path / "out" / "avaliacao-replan-off.json")["config"]["replan"] == "off"
    assert not (tmp_path / "out" / "avaliacao.json").exists()


def test_eval_compare_pairs_the_ablation_and_its_report_repeats_byte_for_byte(tmp_path, ablation_tree, monkeypatch):
    # the repository of this run is the temporary project, so the reports in `out` are outside it wherever pytest puts
    # its temporary directories even when pytest uses a basetemp inside the repository
    monkeypatch.setattr(compare, "PROJECT_ROOT", ablation_tree)
    assert scripted_eval(tmp_path, "--replan", "off", "--name", "off") == 0
    assert scripted_eval(tmp_path, "--name", "on") == 0
    out = tmp_path / "out"
    given = ["eval-compare", "--a", str(out / "off.json"), "--b", str(out / "on.json"), "--out", str(out)]
    assert cli.main([*given, "--name", "first"]) == 0
    assert cli.main([*given, "--name", "second"]) == 0
    assert (out / "first.md").read_bytes() == (out / "second.md").read_bytes()
    assert (out / "first.json").read_bytes() == (out / "second.json").read_bytes()

    data, on = read(out / "first.json"), read(out / "on.json")
    assert data["pairs"] == 4 and data["unpaired"] == {"a_only": [], "b_only": []}
    assert data["config"]["a"]["replan"] == "off" and data["config"]["b"]["replan"] == "on"
    assert set(data["by_criterion"]) == {"passed", *CHECK_KEYS}  # no judge in this run
    assert set(data["by_route"]) == {r["route"] for r in on["cases"]}
    # every decision of the on run is counted by its origin; the off run has none
    recorded: dict[str, int] = {}
    for case_row in on["cases"]:
        for recorded_decision in case_row["replan"]:
            recorded[recorded_decision["origin"]] = recorded.get(recorded_decision["origin"], 0) + 1
    assert data["origins"] == {
        "a": {}, "b": recorded, "model_share": {"a": None, "b": 0.0}, "refused_model": {"a": 0, "b": 0}
    }
    # Input paths outside the repository are represented by their file names.
    assert data["sources"] == ["off.json", "on.json"]
    assert str(tmp_path) not in (out / "first.md").read_text(encoding="utf-8")
    assert data["model_decisions"] == []  # the scripted policy settles these four by rule
    assert data["by_decision_group"]["rule"]["pairs"] == 4 and data["by_decision_group"]["model"]["pairs"] == 0
    # the web search and the account lookup the replanning adds: the off run misses them
    tools = data["by_criterion"]["tools_ok"]
    assert tools["b"] > tools["a"] and tools["diff"] > 0
    text = (out / "first.md").read_text(encoding="utf-8")
    headings = (
        "## Por critério",
        "## Por rota",
        "## Decisões do replanejamento por origem",
        "## Diferença pareada por origem das decisões",
        "## Decisões de origem `model`",
        "## Casos sem par",
    )
    assert all(heading in text for heading in headings)


@pytest.mark.parametrize(
    ("mode_a", "mode_b", "description_a", "description_b"),
    [
        ("off", "on", "replanning disabled (`REPLAN=off`)", "replanning enabled (`REPLAN=on`)"),
        ("on", "off", "replanning enabled (`REPLAN=on`)", "replanning disabled (`REPLAN=off`)"),
        ("off", "off", "replanning disabled (`REPLAN=off`)", "replanning disabled (`REPLAN=off`)"),
        ("on", "on", "replanning enabled (`REPLAN=on`)", "replanning enabled (`REPLAN=on`)"),
        (None, None, "replanning mode unspecified", "replanning mode unspecified"),
    ],
)
def test_eval_compare_describes_each_input_replan_mode(mode_a, mode_b, description_a, description_b):
    report_a = {**OFF, "config": {"replan": mode_a, "mode": "scripted"}}
    report_b = {**ON, "config": {"replan": mode_b, "mode": "scripted"}}
    data = compare.compare(report_a, report_b)
    text = "\n".join(compare.render(data, ("a.json", "b.json")))

    assert f"A usa {description_a} e B usa {description_b}." in text
    assert "Uma diferença positiva indica que B teve pontuação maior que A" in text
    assert "ganho do replanejamento" not in text


# --- the two measures of ADR 0024, by hand ----------------------------------------------------------------------------


def decision(origin: str, next_: str = "finish", hops: int = 0, **extra) -> dict:
    return {"next": next_, "origin": origin, "reason": f"because {origin}", "review": "complete", "hops": hops,
            "observed": {"just_ran": "knowledge"}, **extra}


def row(case_id: str, route: str, passed: bool, replan: list[dict], repetition: int = 1, **extra) -> dict:
    return {"id": case_id, "repetition": repetition, "route": route, "passed": passed, "replan": replan,
            **dict.fromkeys(CHECK_KEYS, True), **extra}


def judged(factual_correctness: int) -> dict:
    return {"state": "completed", "scores": {"groundedness": 4, "factual_correctness": factual_correctness,
                                             "relevance": 4, "usefulness": 4}, "unsupported_claim": False}


MODEL_1 = decision("model", "web", 1, candidates=["finish", "web"], observed={"just_ran": "knowledge", "hops": 0})
MODEL_2 = decision("model", "support", 1, candidates=[], observed={"just_ran": "web", "hops": 1})
MODEL_A = decision("model", "finish", candidates=["clarify", "finish"], observed={"just_ran": "support", "hops": 0})
# A choice refused by the guard counts by its final origin and is listed separately.
REFUSED = decision("rule:hop_budget", refused="web", refused_origin="model", candidates=["finish", "web"],
                   observed={"just_ran": "knowledge", "hops": 3})
# Factual correctness varies between pairs, so its interval depends on the seed.
OFF = {"config": {"replan": "off", "mode": "scripted"}, "cases": [
    row("C1", "knowledge", False, [], judge=judged(2)),
    row("C2", "knowledge", False, [], judge=judged(3)),
    row("C3", "support", True, [], judge=judged(3)),
    row("C4", "support", True, [], judge=judged(4)),
    row("C5", "support", False, [], judge=judged(1)),
    row("C6", "acknowledgement", True, [MODEL_A], judge=judged(5)),  # a model decision on side A
    row("C1", "knowledge", True, [], repetition=2),  # no pair: only in A
]}
ON = {"config": {"replan": "on", "mode": "scripted"}, "cases": [
    row("C1", "knowledge", True, [MODEL_1, decision("rule:complete", hops=1)], judge=judged(5)),
    row("C2", "knowledge", True, [decision("rule:evidence_insufficient_web", "web", 1), MODEL_2], judge=judged(3)),
    row("C3", "support", True, [decision("rule:complete")], judge=judged(5)),
    row("C4", "support", False, [REFUSED], judge=judged(2)),
    row("C5", "support", True, [decision("rule:procedure_gap", "knowledge", 1), decision("rule:complete", hops=1)],
        judge=judged(4)),
    row("C6", "acknowledgement", True, [], judge=judged(4)),
    row("C7", "support", True, [decision("rule:complete")]),  # no pair: only in B, its decision still counted
]}


def test_the_two_measures_of_adr_0024_match_the_hand_count(tmp_path, monkeypatch):
    monkeypatch.setattr(compare, "PROJECT_ROOT", tmp_path / "repository")  # the inputs stay outside it (O1)
    md, js, data = compare.write(_dump(tmp_path, "off", OFF), _dump(tmp_path, "on", ON), tmp_path / "out", "hand")
    # measure 1: every decision of the replan step by its final origin; the refused choice of the model is a rule
    assert data["origins"]["a"] == {"model": 1}
    assert data["origins"]["b"] == {
        "model": 2, "rule:complete": 4, "rule:evidence_insufficient_web": 1, "rule:hop_budget": 1,
        "rule:procedure_gap": 1,
    }
    assert data["origins"]["model_share"] == {"a": 1.0, "b": round(2 / 9, 3)}
    assert data["origins"]["refused_model"] == {"a": 0, "b": 1}

    # pairing: 6 pairs; C1 rep 2 only in A, C7 only in B
    assert data["pairs"] == 6 and data["unpaired"] == {"a_only": [["C1", 2]], "b_only": [["C7", 1]]}
    passed = data["by_criterion"]["passed"]
    assert (passed["n"], passed["a"], passed["b"], passed["diff"]) == (6, 0.5, 0.833, 0.333)
    assert data["by_criterion"]["route_ok"] == {
        "n": 6, "a": 1.0, "b": 1.0, "diff": 0.0, "interval": [0.0, 0.0], "excludes_zero": False
    }
    by_route = {route: r["passed"]["diff"] for route, r in data["by_route"].items()}
    assert by_route == {"acknowledgement": 0.0, "knowledge": 1.0, "support": 0.0}

    # the judge's scores with spread: the mean by hand, the interval fixed by the seed and the resamples
    factual = data["by_criterion"]["judge:factual_correctness"]
    assert (factual["n"], factual["a"], factual["b"], factual["diff"]) == (6, 3.0, 3.833, 0.833)
    assert factual["interval"] == [-0.667, 2.333] and not factual["excludes_zero"]  # 2.5% and 97.5% of 2000 means
    assert data["by_criterion"]["judge:relevance"]["interval"] == [0.0, 0.0]

    # measure 2: C1, C2 (B) and C6 (A) have a model decision (+1, +1, 0); C3, C4, C5 rule only (0, -1, +1): C4's only
    # decision is the refused choice of the model, a rule decision by its final origin
    groups = data["by_decision_group"]
    assert [groups[g]["pairs"] for g in ("model", "rule", "none")] == [3, 3, 0]
    model = groups["model"]["by_criterion"]["passed"]
    assert (model["n"], model["a"], model["b"], model["diff"]) == (3, 0.333, 1.0, 0.667)
    rule = groups["rule"]["by_criterion"]["passed"]
    assert (rule["n"], rule["a"], rule["b"], rule["diff"], rule["excludes_zero"]) == (3, 0.667, 0.667, 0.0, False)
    assert -1.0 <= rule["interval"][0] <= 0.0 <= rule["interval"][1] <= 1.0
    assert groups["none"]["by_criterion"] == {}

    # C1, C2 and C5 have a decision with hops > 0, all in the same direction.
    changed = data["changed_plan"]
    assert changed["pairs"] == 3
    assert changed["by_criterion"]["passed"] == {
        "n": 3, "a": 0.0, "b": 1.0, "diff": 1.0, "interval": [1.0, 1.0], "excludes_zero": True
    }

    # the decisions of origin model, both sides: observation, candidates and choice
    assert [(d["side"], d["case_id"], d["candidates"], d["next"], d["observed"]) for d in data["model_decisions"]] == [
        ("a", "C6", ["clarify", "finish"], "finish", {"just_ran": "support", "hops": 0}),
        ("b", "C1", ["finish", "web"], "web", {"just_ran": "knowledge", "hops": 0}),
        ("b", "C2", [], "support", {"just_ran": "web", "hops": 1}),
    ]
    # the model consulted and refused by the guard: listed apart with what it chose and the final origin
    assert [(d["side"], d["case_id"], d["candidates"], d["refused"], d["origin"]) for d in data["refused_model"]] == [
        ("b", "C4", ["finish", "web"], "web", "rule:hop_budget"),
    ]
    text = md.read_text(encoding="utf-8")
    assert "| `model` | 1 | 2 |" in text and "| `rule:hop_budget` | 0 | 1 |" in text and "| total | 1 | 9 |" in text
    assert "Modelo consultado e recusado pela guarda: A 0; B 1." in text
    assert "### Pares com pelo menos uma decisão `model`: 3" in text and "### Pares só decisões por regra: 3" in text
    assert "### Pares com mudança de plano (`hops > 0` em algum lado): 3" in text
    assert "| passed | 3 | 0.000 | 1.000 | +1.000 | [+1.000, +1.000] | sim |" in text
    assert '`{"hops": 0, "just_ran": "knowledge"}` | finish, web | web (complete) |' in text
    assert '`{"hops": 3, "just_ran": "knowledge"}` | finish, web | web | `rule:hop_budget` |' in text
    assert "- Só em A: C1 (rep 2)." in text and "- Só em B: C7 (rep 1)." in text
    # The inputs are outside the repository: only their names are written.
    assert data["sources"] == ["off.json", "on.json"] and str(tmp_path) not in text
    assert tmp_path.as_posix() not in text and "- **A:** `off.json`" in text


def test_the_inputs_are_named_relative_to_the_repository_or_by_their_file_name(tmp_path, monkeypatch):
    inside = PROJECT_ROOT / "docs" / "evidence" / "ablation-off.json"
    assert compare.display_path(inside) == "docs/evidence/ablation-off.json"
    elsewhere = tmp_path / "repository"  # a repository that does not hold the test's directory, wherever that is (O1)
    assert compare.display_path(tmp_path / "x" / "report.json", root=elsewhere) == "report.json"
    assert compare.display_path(tmp_path / "x" / "report.json", root=tmp_path) == "x/report.json"
    monkeypatch.setattr(compare, "PROJECT_ROOT", elsewhere)  # the default root is the one in force at the call
    assert compare.display_path(tmp_path / "x" / "report.json") == "report.json"
    assert compare.display_path(elsewhere / "docs" / "a.json") == "docs/a.json"


def test_the_runner_records_the_candidates_and_the_refused_choice_of_the_model(offline, settings, monkeypatch):
    """The model picks `web` between two disagreeing rules; with a budget of zero plan changes the
    guard refuses it, and the row of the report keeps the candidates, the refused choice and its origin."""
    from merchant_assistant.agents import replanner
    from merchant_assistant.evaluation.runner import run
    from merchant_assistant.evaluation.scripted_policy import handler as default_handler

    disagree = [replanner.Match("a", "finish", "complete", "done"), replanner.Match("b", "web", "incomplete", "more")]
    monkeypatch.setattr(replanner, "apply_rules", lambda o: disagree)

    def handler(call):
        if call.spec.agent == "replan":
            return {"next": "web", "review": "incomplete", "reason": "the web may have it"}
        return default_handler(call)

    case = CASES["REPLAN-WEB"]
    settings.max_plan_hops = 0
    _, refused_run, _ = offline(handler=handler)
    [refused] = run(refused_run, [case])
    [decided] = refused["replan"]
    assert (decided["origin"], decided["refused"], decided["refused_origin"]) == ("rule:hop_budget", "web", "model")
    assert decided["candidates"] == ["finish", "web"] and decided["next"] == "finish"

    settings.max_plan_hops = 3
    _, accepted_run, _ = offline(handler=handler)
    [accepted] = run(accepted_run, [case])
    first = accepted["replan"][0]
    assert (first["origin"], first["next"], first["candidates"]) == ("model", "web", ["finish", "web"])
    assert "refused_origin" not in first and first["observed"]["just_ran"] == "knowledge"


def test_the_bootstrap_interval_is_fixed_by_the_seed_and_the_number_of_resamples():
    """Real-valued differences make the seed, the 2000 resamples and the percentiles each affect the
    interval."""
    diffs = [0.13, -0.7, 1.9, 0.42, -1.3, 2.2, 0.05, -0.33]
    assert (compare.RESAMPLES, compare.DEFAULT_SEED) == (2000, 93)
    assert compare.bootstrap(diffs, 93) == pytest.approx((-0.47, 1.095), abs=1e-9)
    assert compare.bootstrap(diffs, 7) == pytest.approx((-0.44125, 1.1125), abs=1e-9)
    data = compare.compare(*(
        {"cases": [row(f"R{i}", "knowledge", True, [], judge=judged(3)) for i in range(8)]} for _ in range(2)
    ))
    assert data["seed"] == 93 and data["resamples"] == 2000


def test_the_bootstrap_is_seeded_and_resamples_the_pairs():
    diffs = [1.0, 0.0, -1.0, 1.0, 0.0, 1.0]
    first, second = compare.bootstrap(diffs, 93), compare.bootstrap(diffs, 93)
    assert first == second and min(diffs) <= first[0] <= sum(diffs) / len(diffs) <= first[1] <= max(diffs)
    assert first[0] < first[1]  # the pairs disagree: the interval is not a point
    assert compare.bootstrap([0.5, 0.5, 0.5], 93) == (0.5, 0.5)  # every resample of equal differences is the same
    assert compare.bootstrap([1.0], 93) is None


def test_old_reports_without_recorded_decisions_are_compared_and_flagged(tmp_path):
    old = {"config": {}, "cases": [{k: v for k, v in r.items() if k != "replan"} for r in OFF["cases"]]}
    md, _, data = compare.write(_dump(tmp_path, "old", old), _dump(tmp_path, "on", ON), tmp_path / "out", "old")
    assert data["unrecorded_decisions"] == {"a": 7, "b": 0} and data["pairs"] == 6
    note = "Linhas sem as decisões gravadas (relatório anterior à tarefa 93): A 7; B 0."
    assert note in md.read_text(encoding="utf-8")


def _dump(tmp_path, name: str, report: dict):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path
