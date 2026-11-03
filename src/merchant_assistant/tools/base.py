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
    "FORBIDDEN_SCOPE",
    "FORBIDDEN_CUSTOMER",
    "INVALID_TOKEN",
]


@dataclass(frozen=True)
class CustomerContext:
    """Built by the server from the authenticated principal. Tools never receive the customer id from the model.

    `authorized_customer_id` is the merchant the principal may act for in this call: its own merchant for merchant,
    demo and admin sessions; for an operator, the merchant of the case it acts on, read from the case by the server.
    Without a principal the context has no scopes, so every tool call is refused (fail closed)."""

    customer_id: str
    known: bool
    principal_id: str | None = None
    role: str | None = None
    scopes: tuple[str, ...] = ()
    authorized_customer_id: str | None = None
    on_behalf_of: str | None = None  # principal a service acts for (ticketing on behalf of an operator)

    @classmethod
    def for_principal(
        cls,
        principal,
        customer_id: str,
        known: bool,
        *,
        authorized_customer_id: str | None = None,
        on_behalf_of: str | None = None,
    ) -> CustomerContext:
        """`principal` is an `api.identity.Principal` (any object with the same attributes)."""
        return cls(
            customer_id,
            known,
            principal.principal_id,
            principal.role,
            tuple(principal.scopes),
            authorized_customer_id if authorized_customer_id is not None else principal.customer_id,
            on_behalf_of,
        )


@dataclass
class ToolEnv:
    conn: sqlite3.Connection
    clock: Clock
    customer: CustomerContext
    faults: dict[str, str] = field(default_factory=dict)  # tool name -> error code, for failure tests
    mock_services: object | None = None
    resource_id: str | None = None  # resource the current tool call touched, written to its audit row


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


def note_resource(env: ToolEnv, resource_id: str) -> None:
    """Records the resource a tool call touched; the registry writes it in the single audit row of the call."""
    env.resource_id = resource_id


def access_error(customer: CustomerContext, scope: str) -> ToolError | None:
    """Scope and merchant check done before any tool or case write runs (ADR 0017)."""
    if scope not in customer.scopes:
        return ToolError("FORBIDDEN_SCOPE", f"This session is not allowed to use {scope}.")
    if customer.authorized_customer_id is None or customer.authorized_customer_id != customer.customer_id:
        return ToolError("FORBIDDEN_CUSTOMER", "This session cannot act for this merchant.")
    return None


def write_audit(env: ToolEnv, tool: str, scope: str | None, outcome: str, resource_id: str | None = None) -> None:
    """One row per tool call or case write, accepted or refused, with the acting principal and the scope."""
    env.conn.execute(
        "INSERT INTO audit_events (at, customer_id, tool, resource_id, outcome, principal_id, scope, on_behalf_of) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            env.clock.now().isoformat(timespec="seconds"),
            env.customer.customer_id,
            tool,
            resource_id,
            outcome,
            env.customer.principal_id,
            scope,
            env.customer.on_behalf_of,
        ),
    )
