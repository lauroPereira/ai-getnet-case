from merchant_assistant.agents.personality import deterministic_answer
from merchant_assistant.llm.openai_llm import CALL_TIMEOUT_S, _call_timeout
from merchant_assistant.orchestration.state import GraphState, KnowledgeResult, RouterDecision


class FakeMeter:
    def __init__(self, remaining):
        self._remaining = remaining

    def remaining_seconds(self):
        return self._remaining


def test_provider_timeout_never_exceeds_the_request_budget():
    assert _call_timeout(None) == CALL_TIMEOUT_S
    assert _call_timeout(FakeMeter(200)) == CALL_TIMEOUT_S
    assert _call_timeout(FakeMeter(12)) == 10
    assert _call_timeout(FakeMeter(1)) == 3.0


def test_fallback_never_shows_internal_procedure_guidance():
    decision = RouterDecision(
        route="knowledge_and_support",
        language="pt",
        topic="authorization",
        intents=["x"],
        safety="none",
        clarification_question=None,
        case_signal="none",
    )
    state = GraphState(
        request_id="r",
        conversation_id="conv_x",
        user_id="u",
        customer_known=True,
        message="m",
        decision=decision,
        knowledge=KnowledgeResult(
            mode="procedure", points=["Só associe códigos documentados"], evidence_sufficient=True
        ),
    )
    assert "códigos documentados" not in deterministic_answer(state, "pt")
