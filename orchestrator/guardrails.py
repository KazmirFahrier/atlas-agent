"""Runtime guardrails for LLM tool calls.

Three layers, all exercised by the eval suite:
  1. Structured-output validation (JSON schema) on model outputs.
  2. Retry-with-backoff around flaky tool execution.
  3. Tool-result verification to catch hallucinated / malformed results
     before they re-enter the model's context.

Phase-3 TODO: add SQL statement allow-listing here (SELECT-only) and a
numeric grounding check that cross-references model claims against the raw
tool result.
"""
from __future__ import annotations

from typing import Any, Callable

import jsonschema
from tenacity import retry, stop_after_attempt, wait_exponential


class GuardrailError(Exception):
    pass


def validate_json(payload: dict, schema: dict) -> dict:
    """Raise GuardrailError if payload violates schema."""
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except jsonschema.ValidationError as exc:
        raise GuardrailError(f"schema validation failed: {exc.message}") from exc
    return payload


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, max=4), reraise=True)
def call_with_retry(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a tool call with exponential backoff on failure."""
    return fn(*args, **kwargs)


def verify_tool_result(result: Any) -> Any:
    """Reject obviously bad tool results (empty, error markers) before use."""
    if result is None:
        raise GuardrailError("tool returned no result")
    if isinstance(result, str) and result.strip().lower().startswith("error"):
        raise GuardrailError(f"tool signalled an error: {result[:200]}")
    return result


SQL_FORBIDDEN = ("insert", "update", "delete", "drop", "alter", "create", "attach", "copy")


def assert_read_only_sql(sql: str) -> str:
    """SELECT-only guard for the sql-exec tool."""
    lowered = sql.strip().lower()
    if not lowered.startswith(("select", "with")):
        raise GuardrailError("only SELECT/WITH queries are permitted")
    if any(tok in lowered for tok in SQL_FORBIDDEN):
        raise GuardrailError("query contains a forbidden write/DDL keyword")
    return sql
