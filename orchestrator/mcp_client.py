"""Thin MCP client wrapper.

Connects to the local MCP servers over stdio, lists their tools, and exposes
a uniform `call(tool_name, args)` used by the agent loop. Keeping this behind
one interface means the agent doesn't care whether a tool is the Python
sql-exec server or the TypeScript greeter server.

Phase-1 note: server registry is static below; Phase-4 will add the docgen
server and (optionally) a remote HTTP transport.
"""
from __future__ import annotations

import os
import sys
from contextlib import AsyncExitStack
from typing import Any

# The `mcp` package provides the client session + stdio transport.
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _HAS_MCP = True
except Exception:  # allow import without the dependency installed (offline eval)
    _HAS_MCP = False


SERVERS: dict[str, list[str]] = {
    "sql": [sys.executable, "-m", "mcp_servers.sql_exec.server"],
    "py": [sys.executable, "-m", "mcp_servers.py_sandbox.server"],
    "docgen": [sys.executable, "-m", "mcp_servers.docgen.server"],
    # TypeScript server (build first: cd mcp_servers_ts && npm i && npm run build)
    "greeter": ["node", "mcp_servers_ts/dist/server.js"],
}


class McpClient:
    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._sessions: dict[str, "ClientSession"] = {}

    async def connect(self, names: list[str]) -> None:
        if not _HAS_MCP:
            raise RuntimeError("mcp package not installed")
        for name in names:
            cmd, *args = SERVERS[name]
            params = StdioServerParameters(command=cmd, args=args, env=os.environ.copy())
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[name] = session

    async def list_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for name, session in self._sessions.items():
            resp = await session.list_tools()
            for tool in resp.tools:
                tools.append(
                    {
                        "server": name,
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                    }
                )
        return tools

    async def call(self, server: str, tool: str, args: dict[str, Any]) -> Any:
        result = await self._sessions[server].call_tool(tool, args)
        # MCP returns content parts; join text parts for the agent.
        return "".join(part.text for part in result.content if getattr(part, "type", "") == "text")

    async def close(self) -> None:
        await self._stack.aclose()
