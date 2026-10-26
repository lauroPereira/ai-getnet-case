"""Versioned price table and cost estimation. Unknown prices block paid calls."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from merchant_assistant.llm.base import Usage

PRICES_PATH = Path(__file__).with_name("prices.json")


class PriceUnknown(Exception):
    pass


@lru_cache
def prices() -> dict:
    return json.loads(PRICES_PATH.read_text(encoding="utf-8"))


def model_price(model: str) -> dict:
    entry = prices()["models"].get(model)
    if entry is None:
        if model.startswith("scripted"):
            return {"input_per_mtok": 0.0, "output_per_mtok": 0.0, "cached_input_per_mtok": 0.0}
        raise PriceUnknown(f"No price registered for model {model}")
    return entry


def web_search_price() -> float:
    return prices()["tools"]["web_search"]["per_call"]


def cost(model: str, usage: Usage) -> float:
    p = model_price(model)
    uncached = max(usage.input_tokens - usage.cached_tokens, 0)
    total = uncached * p["input_per_mtok"] / 1e6
    total += usage.cached_tokens * p.get("cached_input_per_mtok", p["input_per_mtok"]) / 1e6
    total += usage.output_tokens * p["output_per_mtok"] / 1e6
    total += usage.web_search_calls * web_search_price() if not model.startswith("scripted") else 0.0
    return round(total, 8)


def estimate(model: str, est_input_tokens: int, max_output_tokens: int, web_search_calls: int = 0) -> float:
    # Web search adds retrieved content as input; observed ~8k tokens per call (tarefa 02).
    extra_input = 9000 * web_search_calls
    return cost(model, Usage(est_input_tokens + extra_input, max_output_tokens, 0, web_search_calls))
