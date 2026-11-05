"""Support-first procedure and isolated resolution regression tests, without paid calls."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from merchant_assistant.agents import knowledge, personality, router
from merchant_assistant.config import Settings
from merchant_assistant.llm.base import WebAnswer
from merchant_assistant.orchestration.state import GraphState, KnowledgeDraft, KnowledgeResult, RouterDecision
from merchant_assistant.rag.index import Hit


def decision(route="support", signal="resolved", safety="none"):
    return RouterDecision(
        route=route, language="pt", topic="receivables", intents=[], safety=safety,
        clarification_question=None, case_signal=signal,
    )


@pytest.mark.parametrize("message", ["Deu certo, voltou a funcionar!", "Funcionou.", "It worked!", "working again"])
def test_isolated_resolution_becomes_acknowledgement(message):
    result = router.enforce(decision(), message=message, case_state="awaiting_customer")
    assert result.route == "acknowledgement"
    assert result.topic is None
    assert result.case_signal == "resolved"


@pytest.mark.parametrize("message", [
    "Deu certo, mas como vejo minhas vendas?", "Funcionou?", "Funcionou. Quero falar com um atendente.",
    "Funcionou, mas voltou a falhar.", "It worked, how do I check my account?",
])
def test_resolution_with_another_request_or_uncertainty_is_not_overridden(message):
    assert router.enforce(decision(), message=message, case_state="awaiting_customer").route == "support"


def test_resolution_does_not_override_handoff_safety_or_new_conversation():
    assert router.enforce(decision(), message="Funcionou", case_state="handoff").route == "support"
    assert router.enforce(
        decision(route="human_handoff"), message="Funcionou", case_state="awaiting_customer"
    ).route == "human_handoff"
    assert router.enforce(
        decision(safety="unsafe"), message="Funcionou", case_state="awaiting_customer"
    ).route == "out_of_scope"
    assert router.enforce(
        decision(signal="still_failing"), message="Funcionou", case_state="awaiting_customer"
    ).route == "support"
    assert router.enforce(
        decision(), message="Funcionou", case_state="awaiting_customer", new_conversation=True
    ).route == "support"


def state(route="support", plan=None):
    return GraphState(
        request_id="r", conversation_id="c", user_id="u", customer_known=True,
        message="Quando recebo e como faço para antecipar?", decision=decision(route=route), plan=plan or {},
    )


def test_support_first_knowledge_assesses_the_procedure_only():
    hit = Hit(0.9, {"source_kind": "public_official", "title": "Official", "url": "https://example.com",
                    "chunk_id": "a", "text": "Use the app to request an advance."})
    calls = []

    class Index:
        def search(self, query, **kwargs):
            calls.append((query, kwargs))
            return [hit]

    class Model:
        def parse(self, spec, schema, meter):
            calls.append(spec)
            return SimpleNamespace(value=KnowledgeDraft(
                points=["Use the app to request an advance."], used_passages=[1], evidence_sufficient=True, missing=[]
            ))

    ctx = SimpleNamespace(
        settings=Settings(_env_file=None, prompts_dir=Path("prompts")), index=Index(), step_notes={},
        llm_for=lambda _: Model(),
    )
    original = state(plan={"last": "support", "ran": ["support"]})
    result = knowledge.run(original, ctx)["knowledge"]
    assert result.mode == "procedure" and result.evidence_sufficient
    assert "app" in result.points[0]
    assert calls[0][1]["source_kinds"] == ["public_official", "simulated_internal"]
    assert "Assess sufficiency only" in calls[1].instructions
    assert "individual account dates or amounts" in calls[1].instructions
    assert calls[1].input.endswith(f"<<<\n{original.message}\n>>>")


def test_fallback_includes_only_a_procedure_collected_after_support():
    k = KnowledgeResult(mode="procedure", points=["Open the app."], evidence_sufficient=True)
    after = state(plan={"ran": ["support", "knowledge"]}).model_copy(update={"knowledge": k})
    before = state(plan={"ran": ["knowledge", "support"]}).model_copy(update={"knowledge": k})
    assert "Open the app." in personality.deterministic_answer(after, "en")
    assert "Open the app." not in personality.deterministic_answer(before, "en")


@pytest.mark.parametrize(("answer", "citations", "sufficient"), [
    ("The requested device supports the feature.\nEVIDENCE: DIRECT", [{"url": "https://example.com"}], True),
    ("Other devices support the feature.", [{"url": "https://example.com"}], False),
    ("The device was mentioned.\nEVIDENCE: INSUFFICIENT", [{"url": "https://example.com"}], False),
    ("The device supports it.\nEVIDENCE: direct", [{"url": "https://example.com"}], False),
    ("The device supports it.\nEVIDENCE: DIRECT", [], False),
    ("The device supports it.\nEVIDENCE: DIRECT\nEVIDENCE: DIRECT", [{"url": "https://example.com"}], False),
])
def test_web_fallback_requires_explicit_direct_evidence_and_citation(answer, citations, sufficient):
    calls = []

    class Model:
        def web_search(self, spec, meter, **kwargs):
            calls.append(spec)
            return SimpleNamespace(value=WebAnswer(text=answer, citations=citations))

    ctx = SimpleNamespace(
        settings=Settings(_env_file=None, prompts_dir=Path("prompts")),
        clock=SimpleNamespace(now=datetime.now), step_notes={},
        llm_for=lambda _: Model(),
    )
    previous = KnowledgeResult(mode="rag", points=[], evidence_sufficient=False, missing=["specific product feature"])
    original = state(route="knowledge").model_copy(update={"knowledge": previous})
    result = knowledge.run_web(original, ctx)["knowledge"]
    assert result.evidence_sufficient is sufficient
    assert "exact entity and fact" in calls[0].instructions
    assert calls[0].input == original.message
    if sufficient:
        assert result.points == ["The requested device supports the feature."]
    else:
        assert result.points == []
        assert "specific product feature" in result.missing
        assert "web_gap_unconfirmed" in result.missing


def test_direct_web_route_does_not_require_fallback_marker():
    class Model:
        def web_search(self, spec, meter, **kwargs):
            assert "EVIDENCE: DIRECT" not in spec.instructions
            return SimpleNamespace(value=WebAnswer(text="Forecast: sunny.", citations=[]))

    ctx = SimpleNamespace(
        settings=Settings(_env_file=None, prompts_dir=Path("prompts")),
        clock=SimpleNamespace(now=datetime.now), step_notes={},
        llm_for=lambda _: Model(),
    )
    result = knowledge.run(state(route="general_web"), ctx)["knowledge"]
    assert result.evidence_sufficient and result.points == ["Forecast: sunny."]
