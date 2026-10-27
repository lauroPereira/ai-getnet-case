"""Shared types for the support tools: trusted customer context, environment, errors and money formatting."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Literal

from merchant_assistant.data.clock import Clock

ToolErrorCode = Literal[
    "NOT_FOUND",
    "FORBIDDEN_RESOURCE",
    "INVALID_ARGUMENT",
    "UNAVAILABLE",
    "TIMEOUT",
    "CUSTOMER_NOT_FOUND",
    "LIMIT_REACHED",
]


@dataclass(frozen=True)
class CustomerContext:
    """Built by the server from the request. Tools never receive the customer id from the model."""

    customer_id: str
    known: bool


@dataclass
class ToolEnv:
    conn: sqlite3.Connection
    clock: Clock
    customer: CustomerContext
    faults: dict[str, str] = field(default_factory=dict)  # tool name -> error code, for failure tests
    mock_services: object | None = None


class ToolError(Exception):
    def __init__(self, code: ToolErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def money(minor: int, currency: str = "BRL") -> dict:
    """Amount in minor units plus a Brazilian display string (R$ 1.234,56)."""
    sign = "-" if minor < 0 else ""
    units, cents = divmod(abs(minor), 100)
    display = f"{sign}R$ {units:,}".replace(",", ".") + f",{cents:02d}"
    return {"minor": minor, "currency": currency, "display": display}


def audit(env: ToolEnv, tool: str, resource_id: str | None, outcome: str) -> None:
    env.conn.execute(
        "INSERT INTO audit_events (at, customer_id, tool, resource_id, outcome) VALUES (?,?,?,?,?)",
        (env.clock.now().isoformat(timespec="seconds"), env.customer.customer_id, tool, resource_id, outcome),
    )
