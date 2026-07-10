"""py-sandbox MCP server: run short Python analysis snippets under limits.

Isolation logic lives in `sandbox.run_python` (importable + unit-tested):
CPU/memory/file-size rlimits, throwaway cwd, wall-clock timeout, stdout cap.

Phase-3 TODO (stretch): wrap in gVisor / Docker `--network none` for a true
untrusted-multi-tenant boundary; the rlimits below still compose inside it.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .sandbox import run_python

mcp = FastMCP("py-sandbox")


@mcp.tool()
def run(code: str) -> str:
    """Execute a short Python snippet and return its stdout.

    Use for analysis/ranking over data you already fetched via SQL. No network,
    no file writes, 4 CPU-seconds and 256 MB max. Print what you want back.
    """
    return run_python(code).output


if __name__ == "__main__":
    mcp.run()
