"""`judge.v4` (spec v0.10.0 D1, task 83): the rubric of `judge.v3` plus one sentence, the general claim stated as fact
with no source; the schema, the default (`judge.v3`) and the v3 file do not change. Offline."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import SecretStr

from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.evaluation import calibration as cal
from merchant_assistant.evaluation.judge import (
    RUBRIC_VERSION,
    JudgeRefused,
    resolve_judge,
    rubric_version,
    validate_judge,
)
from merchant_assistant.evaluation.scripted_judge import handler, scripted_judge
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted import ScriptedLLM

PROMPTS = PROJECT_ROOT / "prompts"
AGENT = ("openai", "gpt-6-luna")
# The sentence D1 adds, inside the definition of an unsupported claim. Nothing else of judge.v3 changes.
ADDED = (
    ", or a general claim stated as fact with no source in the evidence (for example 'rates vary by contract' or "
    "'approval depends on analysis' when no passage says so)"
)
ANCHOR = "promise that the evidence does not support or contradicts"
V3_SHA256 = "45d59f0cfebacd6b19cbf7c20532e8d8d409404f77d423e0a2e25216f75152bd"  # judge.v3.md as v0.9.0 shipped it


def flat(text: str) -> str:
    return " ".join(text.split())


def test_v4_is_v3_plus_the_one_sentence_and_v3_is_untouched():
    v3, v4 = load_prompt(PROMPTS, "judge", "3"), load_prompt(PROMPTS, "judge", "4")
    assert (v4.id, v4.version, v4.ref) == ("judge", "4", "judge@4")
    assert flat(v3.template).count(ANCHOR) == 1
    assert flat(v4.template) == flat(v3.template).replace(ANCHOR, ANCHOR + ADDED)
    raw = (PROMPTS / "judge.v3.md").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == V3_SHA256


def test_the_rubric_is_named_v3_or_v4_and_v3_stays_the_default():
    assert RUBRIC_VERSION == "3" and rubric_version(None) == "3"
    assert [rubric_version(name) for name in ("v3", "v4", "3", "4")] == ["3", "4", "3", "4"]
    with pytest.raises(JudgeRefused, match="Unknown rubric 'v5'"):
        rubric_version("v5")
    with pytest.raises(cal.CalibrationError, match="rubrica desconhecida"):
        cal._rubric("v9")


def test_a_v4_judge_sends_the_v4_prompt_and_records_rubric_version_4():
    judge = scripted_judge(PROMPTS, NullMeter(), rubric="v4")
    data = {"merchant_message": "Qual a taxa?", "reply": "As taxas variam conforme o contrato.", "evidence": []}
    record = judge.evaluate(data)
    assert record["state"] == "completed" and record["rubric_version"] == "4"
    assert judge.config()["rubric_version"] == "4" and judge.config()["prompt"] == "judge@4"
    assert ADDED.strip(", ") in flat(judge.llm.calls[0].spec.instructions)
    default = scripted_judge(PROMPTS, NullMeter())
    assert default.config()["prompt"] == "judge@3" and default.evaluate(data)["rubric_version"] == "3"
    assert ADDED.strip(", ") not in flat(default.llm.calls[0].spec.instructions)


def test_the_paid_judge_is_validated_and_built_under_the_rubric_asked_for_without_any_call():
    settings = Settings(_env_file=None, openai_api_key=None, deepseek_api_key=SecretStr("synthetic-deepseek-key"))
    setup = validate_judge(settings, agent=AGENT, rubric="4")
    assert setup.prompt.ref == "judge@4" and validate_judge(settings, agent=AGENT).prompt.ref == "judge@3"
    llm = ScriptedLLM(handler, model="deepseek-flash")
    judge = resolve_judge(settings, agent=AGENT, factory=lambda provider, model: llm, rubric="v4")
    assert judge.config()["rubric_version"] == "4" and llm.calls == []
    with pytest.raises(JudgeRefused, match="Unknown rubric"):
        validate_judge(settings, agent=AGENT, rubric="v7")


def block(verdict: float, within: tuple[float, ...], marked: tuple[str, ...]) -> dict:
    pairs = [
        cal.Pair(cal.Rating(sample_id, "req_" + sample_id, "C", "support", "dev", {}, True, "", 1),
                 {"unsupported_claim": sample_id in marked})
        for sample_id in ("S01", "S02", "S13", "S16", "S21")
    ]
    criteria = {criterion: {"within_one": value} for criterion, value in zip(cal.CRITERIA, within, strict=True)}
    return {"pairs": pairs, "analysis": {"verdict": {"exact": verdict}, "criteria": criteria}}


def test_the_d2_line_computes_the_three_conditions_without_deciding():
    before = block(0.667, (0.833, 0.833, 1.000, 0.917), ())
    # one answer in 24 is 0.0417: one point lost on a criterion is within the tolerance, two are not
    passed = cal.d2_rule(block(0.708, (0.792, 0.833, 1.000, 0.917), ("S01", "S16", "S02")), before)
    assert passed["generic"] == (2, 4) and passed["holds"] == {"verdict": True, "generic": True, "within_one": True}
    assert passed["all"] is True
    failed = cal.d2_rule(block(0.625, (0.750, 0.833, 1.000, 0.917), ("S13",)), before)
    assert failed["holds"] == {"verdict": False, "generic": False, "within_one": False} and failed["all"] is False
    same = cal.d2_rule(block(0.667, (0.833, 0.833, 1.000, 0.917), ("S13", "S21")), before)
    assert same["all"] is True  # a verdict that does not drop is enough; it need not rise
