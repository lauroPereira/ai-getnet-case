# MCP server

External agents and MCP clients use the same Customer Support tools as the assistant. The server runs over
[MCP](https://modelcontextprotocol.io) (stdio), on top of the same domain functions, validation, customer
isolation, audit log and structured errors, and it is read-only. The merchant comes from the token in
`MERCHANT_ASSISTANT_TOKEN`, checked again on every call, never from a tool argument. The summary is in the
[README](../../../README.md#mcp-server).

## Run the server and the demo

```bash
export MERCHANT_ASSISTANT_TOKEN=$(merchant-assistant auth token)   # cliente1988 against a running API
merchant-assistant mcp                            # stdio server (for an MCP client such as Claude Desktop)
merchant-assistant mcp-demo                       # starts the server as a subprocess and calls it as a client
```

The demo lists the support tools, reads yesterday's receivables and recent declines, and shows that a receivable of
another merchant returns `is_error=true` with `FORBIDDEN_RESOURCE`.

## Client configuration

Example client configuration:

```json
{"mcpServers": {"getnet-merchant-support": {"command": "merchant-assistant", "args": ["mcp"], "env": {"MERCHANT_ASSISTANT_TOKEN": "<token>"}}}}
```
