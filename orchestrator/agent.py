"""Atlas agent loop.

Ties together: LLM (Anthropic tool-calling) + MCP tools + durable session
memory + guardrails. Run from the CLI:

    python -m orchestrator.agent "Total spend by campaign last quarter"

If no API key is configured it falls back to a deterministic offline planner
so the scaffold (and CI) still runs end-to-end without network access.

Every tool call in the live loop goes through the guardrail layer:
  * input args are validated against the tool's JSON schema (validate_json)
  * SQL is checked read-only (assert_read_only_sql)
  * the call is retried with backoff (call_with_retry)
  * failures are caught and returned to the model as an error tool_result
    (is_error=True) so it can recover, instead of crashing the request.
"""
from __future__ import annotations

import asyncio
import sys
import uuid

from .config import CONFIG
from .guardrails import (
    GuardrailError,
    acall_with_retry,
    assert_read_only_sql,
    validate_json,
    verify_tool_result,
)
from .memory import MemoryStore, SqliteMemoryStore

SYSTEM_PROMPT = (
    "You are Atlas, an AI engineer's assistant. You answer questions about a "
    "marketing data warehouse by calling tools: run read-only SQL, run Python "
    "for analysis, and generate PDF/slide deliverables. Prefer tool calls over "
    "guessing. Never fabricate numbers you did not retrieve from a tool."
)

# Durable by default so multi-turn memory survives restarts; override with an
# in-process store in tests. Built lazily so importing the module is side-effect free.
_STORE: MemoryStore | SqliteMemoryStore | None = None


def _store() -> MemoryStore | SqliteMemoryStore:
    global _STORE
    if _STORE is None:
        _STORE = SqliteMemoryStore(CONFIG.sessions_path) if CONFIG.persist_memory else MemoryStore()
    return _STORE


def set_store(store: MemoryStore | SqliteMemoryStore) -> None:
    """Test/DI hook to inject a memory store."""
    global _STORE
    _STORE = store


async def _dispatch_tool(mcp, block, tool_index: dict) -> tuple[dict, str | None]:
    """Validate → guard → retry → verify one tool call.

    Returns (tool_result_block, server_name_on_success). On any failure returns
    an is_error tool_result so the model can recover; never raises.
    """
    server, tool = block.name.split("__", 1)
    args = dict(block.input)
    try:
        schema = tool_index.get(block.name, {}).get("input_schema")
        if schema:
            validate_json(args, schema)
        if server == "sql" and "query" in args:
            assert_read_only_sql(args["query"])
        out = verify_tool_result(await acall_with_retry(mcp.call, server, tool, args))
        return (
            {"type": "tool_result", "tool_use_id": block.id, "content": str(out)},
            server,
        )
    except GuardrailError as exc:
        return (
            {"type": "tool_result", "tool_use_id": block.id,
             "content": f"ERROR (guardrail): {exc}", "is_error": True},
            None,
        )
    except Exception as exc:  # tool crash / transport error, still recoverable
        return (
            {"type": "tool_result", "tool_use_id": block.id,
             "content": f"ERROR (tool failed): {exc}", "is_error": True},
            None,
        )


async def _run_llm(question: str, session_id: str) -> tuple[str, list[str]]:
    """Real path: Anthropic tool-calling over the MCP tool registry."""
    from anthropic import Anthropic

    from .mcp_client import McpClient

    client = Anthropic(api_key=CONFIG.anthropic_api_key)
    mcp = McpClient()
    await mcp.connect(["sql", "py", "docgen"])
    tools = await mcp.list_tools()
    session = _store().get(session_id)
    session.add("user", question)

    anthropic_tools = [
        {"name": f"{t['server']}__{t['name']}", "description": t["description"] or "",
         "input_schema": t["input_schema"]}
        for t in tools
    ]
    tool_index = {t["name"]: t for t in anthropic_tools}
    trace: list[str] = []

    messages = session.assemble(CONFIG.token_budget)
    try:
        for _ in range(CONFIG.max_steps):  # bounded tool-use loop (ATLAS_MAX_STEPS)
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
                return text, trace

            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                result_block, server = await _dispatch_tool(mcp, block, tool_index)
                session.add("tool", str(result_block["content"]), pinned=True)
                tool_results.append(result_block)
                if server:
                    trace.append(server)
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": tool_results})
        return "Stopped after max tool iterations.", trace
    finally:
        await mcp.close()


def _run_offline(question: str, session_id: str) -> tuple[str, list[str]]:
    """No-API fallback: deterministic plan so the scaffold always runs."""
    session = _store().get(session_id)
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
    return plan, ["sql", "py", "docgen"]


def answer_traced(question: str, session_id: str | None = None) -> tuple[str, list[str]]:
    """Return (answer_text, ordered list of tool servers actually invoked)."""
    session_id = session_id or str(uuid.uuid4())
    if CONFIG.has_llm:
        return asyncio.run(_run_llm(question, session_id))
    return _run_offline(question, session_id)


def answer(question: str, session_id: str | None = None) -> str:
    return answer_traced(question, session_id)[0]


def main() -> None:
    question = " ".join(sys.argv[1:]) or "Total spend by campaign last quarter"
    text, trace = answer_traced(question)
    print(text)
    if trace:
        print(f"\n[tools invoked: {', '.join(trace)}]")


if __name__ == "__main__":
    main()
