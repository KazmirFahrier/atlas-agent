"""Regression tests for the audit fixes (#1-#5)."""
import asyncio
from dataclasses import dataclass

import pytest

from orchestrator import agent
from orchestrator.guardrails import acall_with_retry
from orchestrator.memory import MemoryStore


@dataclass
class FakeBlock:
    name: str
    input: dict
    id: str = "tu_1"
    type: str = "tool_use"


class FakeMcp:
    """Records calls and can be told to fail N times before succeeding."""

    def __init__(self, fail_times: int = 0, result: str = "[]"):
        self.calls = 0
        self.fail_times = fail_times
        self.result = result

    async def call(self, server, tool, args):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient transport error")
        return self.result


TOOL_INDEX = {
    "sql__query": {"input_schema": {"type": "object", "required": ["query"],
                                    "properties": {"query": {"type": "string"}}}},
    "py__run": {"input_schema": {"type": "object", "properties": {"code": {"type": "string"}}}},
}


def _dispatch(mcp, block):
    return asyncio.run(agent._dispatch_tool(mcp, block, TOOL_INDEX))


# --- Fix #1: tool errors are recoverable, never raise ------------------------

def test_guardrail_error_returns_is_error_not_raise():
    block = FakeBlock("sql__query", {"query": "DROP TABLE campaign_daily"})
    result, server = _dispatch(FakeMcp(), block)
    assert result["is_error"] is True and server is None
    assert "guardrail" in result["content"].lower()


def test_tool_crash_returns_is_error_not_raise():
    block = FakeBlock("py__run", {"code": "x"})
    result, server = _dispatch(FakeMcp(fail_times=99), block)  # always fails
    assert result["is_error"] is True and server is None
    assert "tool failed" in result["content"].lower()


def test_success_path_returns_content_and_server():
    block = FakeBlock("sql__query", {"query": "SELECT 1"})
    result, server = _dispatch(FakeMcp(result='[{"x":1}]'), block)
    assert server == "sql" and result.get("is_error") is None
    assert result["content"] == '[{"x":1}]'


# --- Fix #2: async retry actually retries the awaited call -------------------

def test_async_retry_recovers_after_transient_failures():
    mcp = FakeMcp(fail_times=2, result="ok")
    out = asyncio.run(acall_with_retry(mcp.call, "sql", "query", {"query": "SELECT 1"}))
    assert out == "ok" and mcp.calls == 3  # 2 failures + 1 success


# --- Fix #3: bad tool args are rejected by schema validation -----------------

def test_schema_validation_blocks_bad_args():
    block = FakeBlock("sql__query", {"query": 123})  # query must be a string
    result, server = _dispatch(FakeMcp(), block)
    assert result["is_error"] is True and server is None


# --- Fix #4: durable memory is used by the live path ------------------------

def test_offline_answer_records_and_traces(tmp_path):
    agent.set_store(MemoryStore())
    text, trace = agent.answer_traced("Total spend by campaign", "sess-1")
    assert trace == ["sql", "py", "docgen"]
    assert "offline mode" in text
    # second turn on same session should see the first turn in memory
    store = agent._store()
    assert len(store.get("sess-1").turns) >= 2


@pytest.fixture(autouse=True)
def _reset_store():
    yield
    agent.set_store(MemoryStore())  # isolate tests from the durable default
