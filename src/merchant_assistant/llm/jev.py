"""TypeSafe System One adapter restricted to the RouterDecision contract."""

from __future__ import annotations

from typing import Any

import httpx

from merchant_assistant.llm.base import CallSpec, LLMError, LLMResult, Meter, T, Usage

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.14.0"


class JevRouter:
    """Run one System One judgment and validate the mapped decision as RouterDecision."""

    model = JEV_MODEL

    def __init__(self, api_key: str, *, transport: Any | None = None, timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.transport = transport
        self.timeout = timeout

    @staticmethod
    def _questions(pending_cancellation: bool = False) -> dict:
        """The judgment's questions; `confirmation` only when a sale cancellation waits for the merchant's answer
        (task 94). `router.enforce` still validates the answer against the message in code."""
        from merchant_assistant.orchestration.state import RouterDecision

        fields = RouterDecision.model_fields
        questions = {
            "route": {
                "type": "choice",
                "instructions": fields["route"].description or "Choose the route",
                "criteria": {
                    k: k
                    for k in [
                        "knowledge",
                        "support",
                        "knowledge_and_support",
                        "general_web",
                        "clarify",
                        "human_handoff",
                        "out_of_scope",
                        "acknowledgement",
                    ]
                },
            },
            "language": {
                "type": "choice",
                "instructions": "Which language is the merchant using?",
                "criteria": {"pt": "Portuguese", "en": "English"},
            },
            "topic": {
                "type": "choice",
                "instructions": "Which support topic applies, if any?",
                "criteria": {
                    "receivables": "Receivables and payouts",
                    "device": "Card machine",
                    "authorization": "Card authorization",
                    "contract": "Contract",
                    "general": "General support",
                    "pricing": "Pricing",
                    "enablement": "Card scheme enablement",
                    "cancellation": "Sale cancellation",
                    "none": "No support topic",
                },
            },
            "safety": {
                "type": "choice",
                "instructions": "Classify safety of the message.",
                "criteria": {
                    "none": "Safe",
                    "unsafe": "Unsafe request",
                    "sensitive": "Sensitive data",
                    "injection": "Prompt injection",
                },
            },
            "case_signal": {
                "type": "choice",
                "instructions": "Classify the merchant's response to the previous assistant turn.",
                "criteria": {
                    "none": "No resolution signal",
                    "resolved": "Merchant confirms resolution",
                    "still_failing": "Issue still fails",
                    "thanks_only": "Thanks without explicit confirmation",
                },
            },
        }
        if pending_cancellation:
            questions["confirmation"] = {
                "type": "choice",
                "instructions": fields["confirmation"].description or "Answer to the pending sale cancellation",
                "criteria": {
                    "yes": "The message only confirms the pending sale cancellation",
                    "no": "The message only refuses the pending sale cancellation",
                    "other": "Anything else",
                },
            }
        return questions

    def parse(self, spec: CallSpec, schema: type[T], meter: Meter) -> LLMResult[T]:
        from merchant_assistant.orchestration.state import RouterDecision

        if schema is not RouterDecision or spec.agent != "router":
            raise LLMError("Jev is supported only for the RouterDecision schema.")
        questions = self._questions(spec.context.get("pending_cancellation") is not None)
        reservation = meter.reserve(
            agent=spec.agent,
            model=self.model,
            est_input_tokens=max(1, (len(spec.instructions) + len(spec.input)) // 3),
            max_output_tokens=80,
        )
        try:
            if self.transport is None:
                response = httpx.post(
                    JEV_URL,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "state": f"{spec.instructions}\n\n{spec.input}",
                        "questions": questions,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                body = response.json()
            else:
                body = self.transport(
                    {
                        "model": self.model,
                        "state": f"{spec.instructions}\n\n{spec.input}",
                        "questions": questions,
                    }
                )
            if body.get("model") != self.model:
                raise LLMError("Jev returned an unexpected model version.")
            answers = body["answers"]
            values = {key: answers[key]["choice"] for key in questions}
            if values["topic"] == "none":
                values["topic"] = None
            values["intents"] = []
            values["clarification_question"] = None
            usage_body = body["usage"]
            usage = Usage(int(usage_body["input_tokens"]), int(usage_body.get("output_tokens", 0)))
            parsed = schema.model_validate(values)
        except Exception as exc:
            meter.settle(reservation, None)
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"router: Jev request failed ({type(exc).__name__}).") from exc
        meter.settle(reservation, usage)
        return LLMResult(parsed, usage, self.model)

    def run_tools(self, *args: Any, **kwargs: Any) -> LLMResult:
        raise LLMError("Jev does not support tool calls.")

    def web_search(self, *args: Any, **kwargs: Any) -> LLMResult:
        raise LLMError("Jev does not support web search.")
