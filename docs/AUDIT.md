# Self-audit & fixes

A pass over the codebase to close gaps between what the README claims and what
the running code actually wires up. Findings are listed worst-first with the
fix and the regression test that now guards it.

| # | Finding | Fix | Guarded by |
|---|---------|-----|-----------|
| 1 | A failing tool call raised an uncaught `GuardrailError` and crashed the whole request. | `_dispatch_tool` catches guardrail + tool errors and returns an `is_error` tool_result so the model can recover. | `test_agent.py::test_guardrail_error_returns_is_error_not_raise`, `test_tool_crash_returns_is_error_not_raise` |
| 2 | `call_with_retry` was tested but never applied to live tool calls — and it only wrapped coroutine *creation*, so it couldn't retry async calls anyway. | Added `acall_with_retry` (retries the awaited execution) and wired it around `mcp.call`. | `test_async_retry_recovers_after_transient_failures` |
| 3 | `validate_json` (structured-output schema check) was never invoked in the agent loop. | Tool args are validated against each tool's JSON schema before execution. | `test_schema_validation_blocks_bad_args` |
| 4 | `SqliteMemoryStore` was implemented + tested but the live/serve path used the ephemeral in-process store. | Agent uses a durable store by default (`ATLAS_PERSIST_MEMORY`), with a `set_store` DI hook for tests. Sqlite made thread-safe (`check_same_thread=False` + lock) for the threaded HTTP server. | `test_offline_answer_records_and_traces`, `test_memory.py::test_sqlite_persists_across_instances` |
| 5 | The online eval grepped the tool name in the answer text (a real success would be marked FAIL). | The agent returns a tool-invocation trace; eval asserts on the trace, not the prose. | `eval/run.py`, `answer_traced` |

## Still explicitly out of scope (documented, not hidden)

- The Python sandbox uses POSIX rlimits — a single-host boundary, not a
  container escape guarantee. `docs/DEPLOY.md` notes wrapping it in gVisor /
  `--network none` for untrusted multi-tenant use.
- `serve.py` is unauthenticated; the deploy guide uses
  `--allow-unauthenticated` for the demo. Put it behind IAP / an API key for
  real use.
- Durable memory is recency-based; embedding-retrieval over long sessions is a
  noted stretch goal.

## Verification

```
ruff check .      # clean
pytest -q         # 21 passed
python -m eval.run --offline   # 4/4
```
