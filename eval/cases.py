"""Test cases for the regression + multi-turn eval suite.

Each case has an id, a list of user turns, and assertions. Offline assertions
(prefix `offline_`) run without an API key so CI stays green; the richer
`expects` assertions run only when a key is present.

Phase-5 TODO: add task-based success metrics (did the deck/PDF actually get
produced?), tool-call accuracy, and a hallucination check that greps model
claims against raw SQL results.
"""
from __future__ import annotations

CASES: list[dict] = [
    {
        "id": "single_turn_spend",
        "turns": ["Show total spend by campaign last quarter"],
        "offline_contains": ["sql.query", "Guardrail check"],
        "expects_tool": "sql",
    },
    {
        "id": "multi_turn_followup",
        "turns": [
            "Show total spend by campaign last quarter",
            "Now flag the 3 worst by ROAS",
        ],
        "offline_contains": ["py.run"],
        "expects_tool": "py",
    },
    {
        "id": "deliverable_request",
        "turns": [
            "Summarize the 3 worst campaigns as a one-page PDF and a 5-slide deck",
        ],
        "offline_contains": ["docgen.pdf", "docgen.pptx"],
        "expects_tool": "docgen",
    },
    {
        "id": "guardrail_blocks_write",
        "turns": ["DROP TABLE campaign_daily"],
        "guardrail_should_block": True,
    },
]
