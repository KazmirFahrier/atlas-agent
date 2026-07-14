"""Run Atlas's deterministic MCP demo without an LLM API key.

This is a proof harness, not a replacement for the agent loop: it connects to
the same SQL, Python-sandbox, and document-generation MCP servers and executes
the portfolio demo with a fixed tool sequence.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.mcp_client import McpClient  # noqa: E402


QUERY = """
WITH bounds AS (
    SELECT MAX(day) AS period_end, MAX(day) - INTERVAL 90 DAY AS period_start
    FROM campaign_daily
)
SELECT
    campaign,
    MIN(day)::VARCHAR AS period_start,
    MAX(day)::VARCHAR AS period_end,
    ROUND(SUM(spend), 2) AS spend,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(revenue) / NULLIF(SUM(spend), 0), 2) AS roas
FROM campaign_daily, bounds
WHERE day BETWEEN bounds.period_start AND bounds.period_end
GROUP BY campaign
ORDER BY roas ASC
"""


async def run() -> None:
    mcp = McpClient()
    await mcp.connect(["sql", "py", "docgen"])
    try:
        rows = json.loads(await mcp.call("sql", "query", {"query": QUERY}))
        rank_code = (
            "import json\n"
            f"rows = {rows!r}\n"
            "print(json.dumps(sorted(rows, key=lambda row: row['roas'])[:3]))\n"
        )
        worst = json.loads(await mcp.call("py", "run", {"code": rank_code}))

        total_spend = round(sum(row["spend"] for row in rows), 2)
        total_revenue = round(sum(row["revenue"] for row in rows), 2)
        portfolio_roas = round(total_revenue / total_spend, 2)
        period = f"{rows[0]['period_start']} to {rows[0]['period_end']}"
        bullets = [
            f"{row['campaign']}: {row['roas']:.2f}x ROAS on ${row['spend']:,.2f} spend"
            for row in worst
        ]
        summary = (
            f"Across six campaigns from {period}, Atlas analyzed ${total_spend:,.2f} "
            f"in spend and ${total_revenue:,.2f} in revenue ({portfolio_roas:.2f}x ROAS)."
        )

        pdf_path = await mcp.call(
            "docgen",
            "pdf_brief",
            {
                "title": "Atlas Campaign Performance Brief",
                "summary": summary,
                "bullets": ["Lowest-return campaigns", *bullets],
            },
        )
        deck_path = await mcp.call(
            "docgen",
            "slide_deck",
            {
                "title": "Atlas Campaign Performance Review",
                "slides": [
                    {"heading": "Executive summary", "bullets": [summary]},
                    {
                        "heading": "Portfolio performance",
                        "bullets": [
                            f"Spend: ${total_spend:,.2f}",
                            f"Revenue: ${total_revenue:,.2f}",
                            f"ROAS: {portfolio_roas:.2f}x",
                        ],
                    },
                    {"heading": "Bottom three campaigns", "bullets": bullets},
                    {
                        "heading": "Recommended action",
                        "bullets": [
                            "Review low-ROAS campaign targeting and creative",
                            "Reallocate budget only after validating incrementality",
                        ],
                    },
                ],
            },
        )

        result = {
            "period": period,
            "campaigns_analyzed": len(rows),
            "total_spend": total_spend,
            "total_revenue": total_revenue,
            "portfolio_roas": portfolio_roas,
            "bottom_three": worst,
            "pdf": str(Path(pdf_path).resolve()),
            "deck": str(Path(deck_path).resolve()),
        }
        print(json.dumps(result, indent=2))
    finally:
        await mcp.close()


if __name__ == "__main__":
    asyncio.run(run())
