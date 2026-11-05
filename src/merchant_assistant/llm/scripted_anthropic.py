"""Programmed Anthropic provider for tests (zero cost, no network), spec v0.9.0 CA-56.

It is the real SDK client (`anthropic.Anthropic`) over an in-memory transport: the request goes through the SDK's own
serialization and the answer through its own parsing, so a test sees exactly the body the API would receive. A
`handler(body) -> dict | Exception` gives each answer; an exception stands for a network failure."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

Handler = Callable[[dict], "dict | Exception"]


class ScriptedAnthropic:
    """`client` is the SDK client to hand to `AnthropicLLM`; `requests` holds the JSON body of every call."""

    def __init__(self, handler: Handler) -> None:
        import httpx2
        from anthropic import Anthropic

        self.handler = handler
        self.requests: list[dict] = []

        def respond(request: httpx2.Request) -> httpx2.Response:
            body = json.loads(request.content)
            self.requests.append(body)
            answer = self.handler(body)  # read at call time: a test may swap it
            if isinstance(answer, Exception):
                raise httpx2.ConnectError(str(answer), request=request)
            return httpx2.Response(200, json=answer)

        self.client = Anthropic(
            api_key="scripted-not-a-key",
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
        )


def message(
    text: str,
    *,
    model: str = "claude-opus-5-5",
    stop_reason: str = "end_turn",
    input_tokens: int = 3000,
    output_tokens: int = 500,
    cache_read: int = 0,
    cache_creation: int = 0,
    thinking: bool = True,
) -> dict[str, Any]:
    """A Messages API answer: an optional thinking block, then the text block."""
    content: list[dict] = [{"type": "thinking", "thinking": "Scripted reasoning.", "signature": "scripted"}]
    content = (content if thinking else []) + ([{"type": "text", "text": text}] if text else [])
    return {
        "id": "msg_scripted",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_creation,
        },
    }


FIXED_JUDGEMENT = {
    "groundedness": 4,
    "groundedness_reason": "Scripted Claude judge: most facts are in the evidence.",
    "factual_correctness": 4,
    "factual_correctness_reason": "Scripted Claude judge: nothing contradicts the evidence.",
    "relevance": 5,
    "relevance_reason": "Scripted Claude judge: the reply answers the question.",
    "usefulness": 4,
    "usefulness_reason": "Scripted Claude judge: the merchant can act on it.",
    "unsupported_claim": False,
}


def judging(judgement: dict | Callable[[dict], dict] = FIXED_JUDGEMENT, **usage: Any) -> Handler:
    """A handler that answers every call with a judgement: a fixed one, or one computed from the judge's input."""

    def handler(body: dict) -> dict:
        data = json.loads(body["messages"][0]["content"])
        value = judgement(data) if callable(judgement) else judgement
        return message(json.dumps(value), model=body["model"], **usage)

    return handler
