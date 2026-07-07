"""Atlas agent loop.

Ties together: LLM (Anthropic tool-calling) + MCP tools + session memory +
guardrails. Run from the CLI:

    python -m orchestrator.agent "Total spend by campaign last quarter"

If no API key is configured it falls back to a deterministic offline planner
so the scaffold (and CI) still runs end-to-end without network access.
"""
from __future__ import annotations

import asyncio
import sys
import uuid

from .config import CONFIG
from .guardrails import GuardrailError, assert_read_only_sql, verify_tool_result
from .memory import MemoryStore

SYSTEM_PROMPT = (
    "You are Atlas, an AI engineer's assistant. You answer questions about a "
    "marketing data warehouse by calling tools: run read-only SQL, run Python "
    "for analysis, and generate PDF/slide deliverables. Prefer tool calls over "
    "guessing. Never fabricate numbers you did not retrieve from a tool."
)

_MEMORY = MemoryStore()


async def _run_llm(question: str, session_id: str) -> str:
    """Real path: Anthropic tool-calling over the MCP tool registry."""
    from anthropic import Anthropic

    from .mcp_client import McpClient

    client = Anthropic(api_key=CONFIG.anthropic_api_key)
    mcp = McpClient()
    await mcp.connect(["sql", "py", "docgen"])
    tools = await mcp.list_tools()
    session = _MEMORY.get(session_id)
    session.add("user", question)

    # Convert MCP tool descriptors to Anthropic tool schema.
    anthropic_tools = [
        {"name": f"{t['server']}__{t['name']}", "description": t["description"] or "",
         "input_schema": t["input_schema"]}
        for t in tools
    ]

    messages = session.assemble(CONFIG.token_budget)
    for _ in range(6):  # bounded tool-use loop
        resp = client.messages.create(
            model=CONFIG.model,
            max_tokens=CONFIG.max_tokens,
            system=SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=messages,
        )
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            session.add("assistant", text)
            await mcp.close()
            return text
        # Execute each requested tool call through the guardrail layer.
        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            server, tool = block.name.split("__", 1)
            args = dict(block.input)
            if server == "sql" and "query" in args:
                assert_read_only_sql(args["query"])
            out = verify_tool_result(await mcp.call(server, tool, args))
            session.add("tool", str(out), pinned=True)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(out)})
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": tool_results})
    await mcp.close()
    return "Stopped after max tool iterations."


def _run_offline(question: str, session_id: str) -> str:
    """No-API fallback: deterministic plan so the scaffold always runs."""
    session = _MEMORY.get(session_id)
    session.add("user", question)
    try:
        assert_read_only_sql("SELECT campaign, SUM(spend) FROM campaign_daily GROUP BY 1")
        guard = "guardrails OK (read-only SQL accepted)"
    except GuardrailError as exc:  # pragma: no cover
        guard = f"guardrail blocked: {exc}"
    plan = (
        "[offline mode — no ANTHROPIC_API_KEY set]\n"
        f"Question: {question}\n"
        "Planned tool calls:\n"
        "  1. sql.query  -> aggregate spend/revenue by campaign\n"
        "  2. py.run     -> rank campaigns by ROAS, pick bottom 3\n"
        "  3. docgen.pdf -> one-page brief;  docgen.pptx -> 5-slide deck\n"
        f"Guardrail check: {guard}"
    )
    session.add("assistant", plan)
    return plan


def answer(question: str, session_id: str | None = None) -> str:
    session_id = session_id or str(uuid.uuid4())
    if CONFIG.has_llm:
        return asyncio.run(_run_llm(question, session_id))
    return _run_offline(question, session_id)


def main() -> None:
    question = " ".join(sys.argv[1:]) or "Total spend by campaign last quarter"
    print(answer(question))


if __name__ == "__main__":
    main()
