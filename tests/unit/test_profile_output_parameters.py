from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from merchant_assistant.llm.base import CallSpec, OutputTokenLimitLLM
from merchant_assistant.llm.openai_llm import OpenAILLM
from merchant_assistant.orchestration.state import PersonalityOutput


class RecordingMeter:
    def __init__(self):
        self.reserved = []
        self.settled = []

    def reserve(self, **kwargs):
        self.reserved.append(kwargs)
        return len(self.reserved)

    def settle(self, reservation, usage):
        self.settled.append((reservation, usage))

    def remaining_seconds(self):
        return 20.0


class FakeResponses:
    def __init__(self):
        self.payloads = []

    def parse(self, *, input, text_format, **kwargs):
        self.payloads.append({"input": input, **kwargs})
        return SimpleNamespace(
            usage=SimpleNamespace(input_tokens=10, output_tokens=5, input_tokens_details=None),
            output=[],
            output_parsed=text_format(answer="synthetic"),
        )


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_profile_output_cap_reaches_provider_and_never_exceeds_reserved_tokens():
    client = FakeOpenAIClient()
    meter = RecordingMeter()
    llm = OutputTokenLimitLLM(OpenAILLM(client, "gpt-6-luna"), max_output_tokens=128)
    spec = CallSpec(agent="personality", instructions="instructions", input="input", max_output_tokens=600)

    result = llm.parse(spec, PersonalityOutput, meter)

    assert result.value.answer == "synthetic"
    assert meter.reserved[0]["max_output_tokens"] == 128
    assert meter.reserved[0]["effective_parameters"] == {"max_output_tokens": 128}
    assert client.responses.payloads[0]["max_output_tokens"] == 128
    assert client.responses.payloads[0]["max_output_tokens"] == meter.reserved[0]["max_output_tokens"]

    # A profile limit can only lower the caller's existing cap; it cannot enlarge it.
    llm.parse(replace(spec, max_output_tokens=64), PersonalityOutput, meter)
    assert meter.reserved[1]["max_output_tokens"] == 64
    assert meter.reserved[1]["effective_parameters"] == {"max_output_tokens": 64}
    assert client.responses.payloads[1]["max_output_tokens"] == 64
    assert client.responses.payloads[1]["max_output_tokens"] == meter.reserved[1]["max_output_tokens"]
