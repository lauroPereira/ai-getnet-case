"""OpenAI Responses API implementation: structured outputs, function-calling loop and web search."""

from __future__ import annotations

import json
from typing import Any

from merchant_assistant.llm.base import (
    CallSpec,
    LLMError,
    LLMResult,
    Meter,
    T,
    ToolCaller,
    Usage,
    WebAnswer,
    estimate_tokens,
)


def _usage(response: Any) -> Usage:
    u = response.usage
    cached = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
    web = sum(1 for o in response.output if getattr(o, "type", "") == "web_search_call")
    return Usage(u.input_tokens, u.output_tokens, cached, web)


CALL_TIMEOUT_S = 30.0


def _call_timeout(meter: Meter | None) -> float:
    remaining = getattr(meter, "remaining_seconds", None)
    if remaining is None:
        return CALL_TIMEOUT_S
    return max(3.0, min(CALL_TIMEOUT_S, remaining() - 2.0))


class OpenAILLM:
    def __init__(self, client: Any, model: str) -> None:
        self.client, self.model = client, model

    def _common(self, spec: CallSpec, meter: Meter | None = None) -> dict:
        kwargs: dict = {
            "model": self.model,
            "instructions": spec.instructions,
            "max_output_tokens": spec.max_output_tokens,
            "store": False,
            "reasoning": {"effort": spec.effort},
            # Never wait longer than what is left of the request's time budget.
            "timeout": _call_timeout(meter),
        }
        if spec.effort != "none":
            kwargs["include"] = ["reasoning.encrypted_content"]
        return kwargs

    def parse(self, spec: CallSpec, schema: type[T], meter: Meter) -> LLMResult[T]:
        reservation = meter.reserve(
            agent=spec.agent,
            model=self.model,
            est_input_tokens=estimate_tokens(spec.instructions, spec.input),
            max_output_tokens=spec.max_output_tokens,
        )
        try:
            response = self.client.responses.parse(input=spec.input, text_format=schema, **self._common(spec, meter))
        except Exception as exc:  # provider errors become LLMError; usage unknown -> settle as reserved
            meter.settle(reservation, None)
            raise LLMError(f"{spec.agent}: {type(exc).__name__}: {exc}") from exc
        usage = _usage(response)
        meter.settle(reservation, usage)
        if response.output_parsed is None:
            raise LLMError(f"{spec.agent}: no structured output (status={getattr(response, 'status', None)})")
        return LLMResult(response.output_parsed, usage, self.model)

    def run_tools(
        self,
        spec: CallSpec,
        schema: type[T],
        meter: Meter,
        *,
        tools: list[dict],
        call_tool: ToolCaller,
        max_tool_calls: int,
    ) -> LLMResult[T]:
        items: list[Any] = [{"role": "user", "content": spec.input}]
        total = Usage()
        executed = 0
        tools_text = json.dumps(tools)
        for _turn in range(max_tool_calls + 2):
            allow_tools = executed < max_tool_calls
            reservation = meter.reserve(
                agent=spec.agent,
                model=self.model,
                est_input_tokens=estimate_tokens(spec.instructions, tools_text, str(items)),
                max_output_tokens=spec.max_output_tokens,
            )
            try:
                response = self.client.responses.parse(
                    input=items,
                    text_format=schema,
                    tools=tools,
                    tool_choice="auto" if allow_tools else "none",
                    **self._common(spec, meter),
                )
            except Exception as exc:
                meter.settle(reservation, None)
                raise LLMError(f"{spec.agent}: {type(exc).__name__}: {exc}") from exc
            usage = _usage(response)
            meter.settle(reservation, usage)
            total.add(usage)
            calls = [o for o in response.output if getattr(o, "type", "") == "function_call"]
            if not calls:
                if response.output_parsed is None:
                    raise LLMError(f"{spec.agent}: no structured output after tools")
                return LLMResult(response.output_parsed, total, self.model)
            for item in response.output:
                if item.type == "reasoning":
                    items.append(item.model_dump(exclude_none=True))
            for call in calls:
                items.append(
                    {"type": "function_call", "call_id": call.call_id, "name": call.name, "arguments": call.arguments}
                )
                if executed >= max_tool_calls:
                    output = json.dumps({"error": {"code": "LIMIT_REACHED", "message": "Tool limit reached."}})
                else:
                    try:
                        args = json.loads(call.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {"__invalid__": call.arguments}
                    output = call_tool(call.name, args)
                    executed += 1
                items.append({"type": "function_call_output", "call_id": call.call_id, "output": output})
        raise LLMError(f"{spec.agent}: tool loop did not finish")

    def web_search(self, spec: CallSpec, meter: Meter, *, max_calls: int = 1) -> LLMResult[WebAnswer]:
        reservation = meter.reserve(
            agent=spec.agent,
            model=self.model,
            est_input_tokens=estimate_tokens(spec.instructions, spec.input),
            max_output_tokens=spec.max_output_tokens,
            web_search_calls=max_calls,
        )
        try:
            kwargs = self._common(spec, meter)
            kwargs["include"] = [*kwargs.get("include", []), "web_search_call.action.sources"]
            response = self.client.responses.create(
                input=spec.input, tools=[{"type": "web_search"}], max_tool_calls=max_calls, **kwargs
            )
        except Exception as exc:
            meter.settle(reservation, None)
            raise LLMError(f"{spec.agent}: {type(exc).__name__}: {exc}") from exc
        usage = _usage(response)
        meter.settle(reservation, usage)
        citations, seen = [], set()
        for item in response.output:
            if getattr(item, "type", "") != "message":
                continue
            for part in item.content:
                for ann in getattr(part, "annotations", None) or []:
                    url = getattr(ann, "url", None)
                    if url and url not in seen:
                        seen.add(url)
                        citations.append({"url": url, "title": getattr(ann, "title", None) or url})
        if not citations:  # no inline annotations: fall back to the sources listed by the search call
            for item in response.output:
                action = getattr(item, "action", None) if getattr(item, "type", "") == "web_search_call" else None
                for source in getattr(action, "sources", None) or []:
                    url, name = getattr(source, "url", None), getattr(source, "name", None)
                    if url and url.startswith("http") and url not in seen:
                        seen.add(url)
                        citations.append({"url": url, "title": url.split("/")[2]})
                    elif name and name not in seen:  # data provider used by the search tool (e.g. weather API)
                        seen.add(name)
                        citations.append({"url": None, "title": f"Web search data provider: {name}"})
            citations = citations[:3]
        text = (response.output_text or "").strip()
        if not text:
            raise LLMError(f"{spec.agent}: empty web search answer")
        return LLMResult(WebAnswer(text=text, citations=citations), usage, self.model)
