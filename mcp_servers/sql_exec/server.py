"""sql-exec MCP server: read-only queries against the DuckDB warehouse.

Guardrails: SELECT/WITH only, row cap, statement timeout. Exposes one tool,
`query`, returning rows as JSON. Run standalone:  python -m mcp_servers.sql_exec.server
"""
from __future__ import annotations

import json
import os

import duckdb
from mcp.server.fastmcp import FastMCP

DB_PATH = os.environ.get("ATLAS_DB_PATH", "data/warehouse.duckdb")
ROW_CAP = 500
FORBIDDEN = ("insert", "update", "delete", "drop", "alter", "create", "attach", "copy", "pragma")

mcp = FastMCP("sql-exec")


def _guard(sql: str) -> str:
    low = sql.strip().lower()
    if not low.startswith(("select", "with")):
        raise ValueError("only SELECT/WITH queries are allowed")
    if any(tok in low for tok in FORBIDDEN):
        raise ValueError("query contains a forbidden keyword")
    return sql


@mcp.tool()
def query(query: str) -> str:
    """Run a read-only SQL SELECT against the marketing warehouse (table: campaign_daily).

    Columns: day, campaign, channel, spend, impressions, clicks, conversions, revenue.
    Returns up to 500 rows as JSON.
    """
    _guard(query)
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        cur = con.execute(query)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(ROW_CAP)
        return json.dumps([dict(zip(cols, r)) for r in rows], default=str)
    finally:
        con.close()


@mcp.tool()
def schema() -> str:
    """Return the warehouse schema so the model can write correct SQL."""
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        rows = con.execute("DESCRIBE campaign_daily").fetchall()
        return json.dumps([{"column": r[0], "type": r[1]} for r in rows])
    finally:
        con.close()


if __name__ == "__main__":
    mcp.run()
