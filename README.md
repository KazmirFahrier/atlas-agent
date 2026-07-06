# Atlas — MCP-Native Agentic Workspace Assistant

An MCP-native, multi-turn agent that runs **sandboxed SQL/Python**, enforces **runtime guardrails**, keeps **persistent session memory**, and generates **PDF/slide deliverables** — deployed on GCP with a **regression eval suite**.

Built to demonstrate the production-AI-engineering skills behind internal LLM agent platforms (tool orchestration, reliability, evaluation, document automation).

## Demo scenario

> "Pull last quarter's spend from the warehouse, flag the 3 worst-performing campaigns, and generate a one-page PDF brief and a 5-slide deck summarizing it."

One request exercises the whole stack: tool calling → SQL execution → Python analysis → memory → guardrails → document/slide generation.

## Architecture

```
TypeScript UI  ──►  Orchestrator (Python, LLM API)  ──►  MCP client
                          │                                  │
                    Session memory                    MCP servers:
                    + context assembly                 • sql-exec   (read-only warehouse)
                          │                             • py-sandbox (resource-limited)
                    Guardrail layer                     • docgen     (PDF / PPTX / tables)
                    (retry, JSON-schema validate,       • greeter    (TypeScript, proves TS)
                     tool-result verification)
                          │
                    Eval harness (multi-turn + regression, CI)
```

## Skills demonstrated (mapped to the AI Engineer JD)

| Skill | Where |
|---|---|
| Python production system | `orchestrator/` |
| LLM APIs, tool calling, structured JSON outputs | `orchestrator/agent.py` |
| MCP-style tool integrations | `mcp_servers/`, `mcp_servers_ts/` |
| Multi-turn context + persistent memory | `orchestrator/memory.py` |
| Sandboxed SQL + Python execution | `mcp_servers/sql_exec`, `mcp_servers/py_sandbox` |
| Guardrails: retry, validation, hallucination mitigation | `orchestrator/guardrails.py` |
| Document / slide / PDF automation | `mcp_servers/docgen` |
| Multi-turn + regression evaluation | `eval/` |
| SQL + data warehouse (DuckDB → BigQuery) | `data/`, `mcp_servers/sql_exec` |
| Cloud deploy (GCP Cloud Run) | `Dockerfile`, `.github/workflows/` |
| TypeScript | `mcp_servers_ts/`, `ui/` |
| Git/GitHub + CI | `.github/workflows/ci.yml` |

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python data/seed.py                 # build the local DuckDB warehouse
cp .env.example .env                # add ANTHROPIC_API_KEY (or OPENAI_API_KEY)
python -m orchestrator.agent "Show me total spend by campaign last quarter"
pytest -q                           # unit tests: guardrails, memory, sandbox
make eval                           # multi-turn regression suite
```

Runs with no API key too — the orchestrator falls back to a deterministic
offline planner, so `pytest` and `make eval` stay green in CI without secrets.

Cloud Run deployment steps: [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Build roadmap

Phased plan lives in [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md). Current status: **Phase 0–1 scaffold** (orchestrator loop, MCP client, guardrail + memory skeletons, seed data, one working tool path). Phases 2–6 are stubbed with `TODO`s.

## License

MIT
