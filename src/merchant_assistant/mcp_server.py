"""MCP server for the support tools (decision 0010).

Same registry, schemas, validation, scopes, customer isolation, audit and structured errors as the agent path: every
call goes through `tools.registry.execute`. The merchant comes from a merchant access token verified when the server
starts (`MERCHANT_ASSISTANT_TOKEN`, kept out of the process list; spec v0.7.0 D12), never from a tool argument.
Transport: stdio.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from mcp import types
from mcp.server.lowlevel import Server

from merchant_assistant import __version__
from merchant_assistant.api.identity import Identity, InvalidToken, Principal
from merchant_assistant.tools.base import ToolEnv
from merchant_assistant.tools.registry import execute, model_tool_schemas

AGENT = "customer_support"
INSTRUCTIONS = (
    "Read-only tools over the synthetic Getnet demo systems for one merchant, fixed when the server starts. "
    "Errors come back as tool results with is_error=true and a code such as FORBIDDEN_RESOURCE or NOT_FOUND."
)


def build_server(env_factory: Callable[[], ToolEnv]) -> Server:
    """`env_factory` returns a fresh ToolEnv (own SQLite connection) bound to the server's merchant."""
    tools = [
        types.Tool(name=s["name"], description=s["description"], input_schema=s["parameters"])
        for s in model_tool_schemas(AGENT)
    ]

    async def on_list_tools(ctx, params) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tools)

    async def on_call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
        env = env_factory()
        try:
            outcome = execute(params.name, dict(params.arguments or {}), env, agent=AGENT)
        finally:
            env.conn.close()
        payload = outcome.data if outcome.ok else {"error": outcome.error}
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, default=str))],
            structured_content=payload,
            is_error=not outcome.ok,
        )

    return Server(
        "getnet-merchant-support",
        version=__version__,
        instructions=INSTRUCTIONS,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


class AccessRefused(ValueError):
    """The MCP server only starts with a valid merchant access token."""


def principal_for_token(identity: Identity, conn, token: str | None) -> Principal:
    """Verifies the token with the same verifier as the API (signature, issuer, audience, expiry, revocation) and
    accepts only merchant principals: operators and services have no merchant of their own."""
    try:
        principal, _ = identity.verify(token or "", conn)
    except InvalidToken as exc:
        raise AccessRefused("access token is invalid, expired or revoked") from exc
    if principal.role != "merchant" or not principal.customer_id:
        raise AccessRefused("the MCP server accepts only merchant tokens")
    return principal


def env_factory_for(db_path, principal: Principal, clock, mock_services=None) -> Callable[[], ToolEnv]:
    """Tool environments bound to an authenticated merchant principal: scopes and merchant are checked and every call
    is audited with the principal, as on the agent path."""
    from merchant_assistant.data.db import connect
    from merchant_assistant.tools.base import CustomerContext

    if principal.role != "merchant" or not principal.customer_id:
        raise ValueError("the MCP server serves only a merchant principal")
    customer_id = principal.customer_id

    def factory() -> ToolEnv:
        conn = connect(db_path)
        known = conn.execute("SELECT 1 FROM customers WHERE customer_id = ?", (customer_id,)).fetchone() is not None
        context = CustomerContext.for_principal(principal, customer_id, known)
        return ToolEnv(conn, clock, context, mock_services=mock_services)

    return factory


def serve_stdio(server: Server) -> None:
    import anyio
    from mcp.server.stdio import stdio_server

    async def main() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(main)
