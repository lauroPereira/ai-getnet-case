import pytest

from merchant_assistant.llm.base import CallSpec, LLMError, NullMeter
from merchant_assistant.llm.jev import JEV_MODEL, JevRouter
from merchant_assistant.orchestration.state import RouterDecision


def jev_body(model=JEV_MODEL):
    return {
        "model": model,
        "answers": {
            "route": {"type": "choice", "choice": "support"},
            "language": {"type": "choice", "choice": "en"},
            "topic": {"type": "choice", "choice": "device"},
            "safety": {"type": "choice", "choice": "none"},
            "case_signal": {"type": "choice", "choice": "none"},
        },
        "usage": {"input_tokens": 120, "output_tokens": 20},
    }


def test_jev_maps_typed_answers_into_router_decision_without_network():
    calls = []
    adapter = JevRouter("synthetic-key", transport=lambda payload: calls.append(payload) or jev_body())
    spec = CallSpec("router", "instructions", "merchant message", context={"message": "hello"})
    result = adapter.parse(spec, RouterDecision, NullMeter())
    assert result.model == JEV_MODEL
    assert result.value.route == "support"
    assert result.value.topic == "device"
    assert result.value.intents == []
    assert calls[0]["model"] == JEV_MODEL
    assert set(calls[0]["questions"]) == {"route", "language", "topic", "safety", "case_signal"}


def test_jev_reservation_limit_is_internal_and_not_an_effective_provider_parameter():
    class MeterSpy:
        def __init__(self):
            self.reservations = []

        def reserve(self, **kwargs):
            self.reservations.append(kwargs)
            return 1

        def settle(self, reservation, usage):
            return None

    requests = []
    meter = MeterSpy()
    adapter = JevRouter("synthetic-key", transport=lambda payload: requests.append(payload) or jev_body())

    adapter.parse(CallSpec("router", "instructions", "message"), RouterDecision, meter)

    assert meter.reservations[0]["max_output_tokens"] == 80
    assert "effective_parameters" not in meter.reservations[0]
    assert set(requests[0]) == {"model", "state", "questions"}


def test_jev_rejects_unknown_or_invalid_model_response_explicitly():
    spec = CallSpec("router", "instructions", "message")
    wrong_model = JevRouter("synthetic-key", transport=lambda _: jev_body("jev-latest"))
    with pytest.raises(LLMError, match="unexpected model"):
        wrong_model.parse(spec, RouterDecision, NullMeter())

    invalid = JevRouter("synthetic-key", transport=lambda _: {"model": JEV_MODEL, "answers": {}, "usage": {}})
    with pytest.raises(LLMError, match="Jev request failed"):
        invalid.parse(spec, RouterDecision, NullMeter())


def test_jev_rejects_non_router_schema_and_never_provides_tools():
    from merchant_assistant.orchestration.state import PersonalityOutput

    adapter = JevRouter("synthetic-key", transport=lambda _: jev_body())
    with pytest.raises(LLMError, match="only for the RouterDecision"):
        adapter.parse(CallSpec("personality", "x", "y"), PersonalityOutput, NullMeter())
    with pytest.raises(LLMError, match="does not support tool calls"):
        adapter.run_tools()
