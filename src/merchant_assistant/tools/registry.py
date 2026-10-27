"""Tool catalog: schemas exposed to the model, per-agent allowlists and a safe executor."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from merchant_assistant.tools import domain
from merchant_assistant.tools.base import ToolEnv, ToolError


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[[ToolEnv, Any], dict]
    phase: Literal["bootstrap", "specialist"]


TOOLS: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in [
        ToolSpec(
            "get_receivables_schedule",
            "List the merchant's receivables (sales to be paid out) for a period, with net amounts, expected "
            "payment dates and original/normalized status. Filter by sale date (default) or expected payment date.",
            domain.ReceivablesArgs,
            domain.get_receivables_schedule,
            "specialist",
        ),
        ToolSpec(
            "get_payout_status",
            "Get the payout stage of receivables and whether the credit is confirmed in the receiving account.",
            domain.PayoutArgs,
            domain.get_payout_status,
            "specialist",
        ),
        ToolSpec(
            "get_device_status",
            "Get the merchant's card machines with model, connectivity, status and last signal time.",
            domain.DeviceArgs,
            domain.get_device_status,
            "specialist",
        ),
        ToolSpec(
            "find_authorization_events",
            "Find the merchant's recent card authorization events (declined by default) with the response code, "
            "documented reason and next step.",
            domain.AuthorizationArgs,
            domain.find_authorization_events,
            "specialist",
        ),
        ToolSpec(
            "get_contract_snapshot",
            "Get the merchant's contracted products, settlement account, settlement plan and pricing context.",
            domain.ContractArgs,
            domain.get_contract_snapshot,
            "specialist",
        ),
        ToolSpec(
            "simulate_pricing",
            "Compare the independent synthetic pricing rule and recorded charge for a sale. Narrow by period, payment "
            "type, installments or sale date; the server discovers the sale from the bound merchant.",
            domain.PricingArgs,
            domain.simulate_pricing,
            "specialist",
        ),
        ToolSpec(
            "get_fee_breakdown",
            "Read the independent recorded charge components for a sale. Narrow by period, payment type, "
            "installments or sale date; the server discovers the sale from the bound merchant.",
            domain.PricingArgs,
            domain.get_fee_breakdown,
            "specialist",
        ),
        ToolSpec(
            "get_enablement_requests",
            "Read existing card-scheme enablement requests and distinguish request state from device availability. "
            "Never creates a request.",
            domain.EnablementArgs,
            domain.get_enablement_requests,
            "specialist",
        ),
        ToolSpec(
            "get_sale_cancellation_context",
            "Read a merchant's existing sale cancellation status. This is a lookup and never executes cancellation "
            "or contract termination.",
            domain.CancellationArgs,
            domain.get_sale_cancellation_context,
            "specialist",
        ),
        ToolSpec(
            "get_complaint_history",
            "Get previous support cases, attempts and pending items for the merchant.",
            domain.HistoryArgs,
            domain.get_complaint_history,
            "bootstrap",
        ),
        ToolSpec(
            "run_customer_healthcheck",
            "Run predefined checks of the systems and products related to a topic.",
            domain.HealthcheckArgs,
            domain.run_customer_healthcheck,
            "bootstrap",
        ),
    ]
}

AGENT_TOOLS: dict[str, tuple[str, ...]] = {
    "customer_support": (
        "get_receivables_schedule",
        "get_payout_status",
        "get_device_status",
        "find_authorization_events",
        "get_contract_snapshot",
        "simulate_pricing",
        "get_fee_breakdown",
        "get_enablement_requests",
        "get_sale_cancellation_context",
    ),
}


def _strip_titles(schema: Any) -> Any:
    if isinstance(schema, dict):
        return {k: _strip_titles(v) for k, v in schema.items() if k != "title"}
    if isinstance(schema, list):
        return [_strip_titles(v) for v in schema]
    return schema


def model_tool_schemas(agent: str) -> list[dict]:
    """Function-tool definitions for the model. No customer identifier is part of any schema."""
    schemas = []
    for name in AGENT_TOOLS.get(agent, ()):
        spec = TOOLS[name]
        parameters = _strip_titles(spec.args_model.model_json_schema())
        parameters.setdefault("properties", {})
        parameters["additionalProperties"] = False
        schemas.append({"type": "function", "name": name, "description": spec.description, "parameters": parameters})
    return schemas


@dataclass
class ToolOutcome:
    name: str
    arguments: dict
    ok: bool
    data: dict | None = None
    error: dict | None = None

    def for_model(self) -> str:
        return json.dumps(self.data if self.ok else {"error": self.error}, ensure_ascii=False, default=str)


def execute(name: str, arguments: dict | str | None, env: ToolEnv, *, agent: str | None = None) -> ToolOutcome:
    """Validates and runs a tool. Never raises: failures become structured error outcomes."""
    raw: dict = {}
    try:
        raw = json.loads(arguments) if isinstance(arguments, str) else dict(arguments or {})
        if name not in TOOLS:
            raise ToolError("INVALID_ARGUMENT", f"Unknown tool: {name}")
        if agent is not None and name not in AGENT_TOOLS.get(agent, ()):
            raise ToolError("INVALID_ARGUMENT", f"Tool {name} is not allowed for {agent}")
        if not env.customer.known:
            raise ToolError("CUSTOMER_NOT_FOUND", "Merchant account not found in the demo environment.")
        if name in env.faults:
            raise ToolError(env.faults[name], f"{name} is unavailable right now.")  # type: ignore[arg-type]
        spec = TOOLS[name]
        args = spec.args_model.model_validate(raw)
        return ToolOutcome(name, raw, True, data=spec.fn(env, args))
    except ToolError as exc:
        return ToolOutcome(name, raw, False, error={"code": exc.code, "message": exc.message})
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
        return ToolOutcome(name, raw, False, error={"code": "INVALID_ARGUMENT", "message": f"Invalid: {fields}"})
    except json.JSONDecodeError:
        return ToolOutcome(name, raw, False, error={"code": "INVALID_ARGUMENT", "message": "Arguments are not JSON."})
