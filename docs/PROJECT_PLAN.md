# Project Plan — "Atlas": An MCP-Native Agentic Workspace Assistant

**Target role:** AI Engineer — WITHIN (Long Island City / Queens, NYC), $90.9k–$254.1k
**Source JD:** https://job-boards.greenhouse.io/agencywithin/jobs/5056863007
**Purpose:** Build one portfolio project that demonstrates the JD's required skills *not already covered* by your GitHub, so it complements rather than duplicates your existing work.

---

## 1. Why this project (gap analysis)

WITHIN's role is about "Rai," an internal LLM agent platform: LLMs + tool calling, SQL/Python execution, multi-turn memory, guardrails, evaluation, and document/slide/PDF generation.

Your GitHub already proves a lot of the *adjacent* surface, so building another of the same would be wasted effort:

| Already on your GitHub | Repo | JD area it covers |
|---|---|---|
| LLM analyst for marketing data, semantic layer, sandboxed tools, hallucination eval harness | `campaign-copilot` | LLM agent, tool sandboxing, semantic layer, eval, SQL-over-marketing-data |
| Grounded LLM personalization, taste-graph, embeddings | `kindred` | Embeddings, vector search, RAG-style grounding |
| Leakage-aware ML classification & evaluation | `fmri-motor-classification-thesis` | ML rigor, evaluation discipline |
| Fraud detection ML | `fraudsight` | Applied ML in production framing |

**`campaign-copilot` is close enough to Rai that you should NOT rebuild it.** Instead, target the JD skills your repos do *not* show:

| JD requirement / strong-plus | On your GitHub today? | Atlas covers it |
|---|---|---|
| **MCP-style tool integrations** | ❌ | ✅ Build real MCP servers + client |
| **Multi-turn context & persistent session memory** | ❌ (analysts are mostly single-shot) | ✅ Session memory + context assembly |
| **Stateful / sandboxed code execution (Python + SQL)** | Partial (`campaign-copilot` sandboxed tools) | ✅ Isolated executor w/ resource limits |
| **Guardrails: retry logic, structured validation, hallucination mitigation** | Partial (eval only) | ✅ Runtime guardrail layer |
| **Document / workflow automation (Docs, Slides, PDFs)** | ❌ | ✅ Doc + slide + PDF generation |
| **Multi-turn + regression evaluation** | Partial (hallucination harness) | ✅ Multi-turn regression suite |
| **Cloud deployment (GCP/AWS)** | ❌ (mostly notebooks/local) | ✅ Containerized, deployed to Cloud Run |
| **TypeScript** | ❌ (Python/Verilog/R) | ✅ TS frontend + TS MCP server |

Net: Atlas is deliberately the "productionization + MCP + docgen" half of the JD that `campaign-copilot` doesn't show.

---

## 2. What Atlas is

A multi-turn agent that answers a user's request by orchestrating tools over **MCP**, keeping **session memory** across turns, running **SQL and Python in a sandbox** with **guardrails**, and producing **documents, slide decks, and PDFs** as deliverables — deployed to the cloud with a small TypeScript UI and a regression-tested eval harness.

Concrete demo scenario (mirrors WITHIN's marketing context without copying `campaign-copilot`):
> "Pull last quarter's spend from the warehouse, flag the 3 worst-performing campaigns, and generate a one-page PDF brief and a 5-slide deck summarizing it."

That single request exercises: tool calling → SQL execution → Python analysis → memory → guardrails → doc/slide/PDF generation.

---

## 3. Architecture

```
TypeScript UI  ──►  Orchestrator (Python, LLM API)  ──►  MCP client
                          │                                  │
                    Session memory                    MCP servers:
                    + context assembly                 • sql-exec (read-only warehouse)
                          │                             • py-sandbox (stateful, resource-limited)
                    Guardrail layer                     • docgen (Docs / Slides / PDF)
                    (retry, JSON-schema validate,
                     tool-result verification)
                          │
                    Eval harness (multi-turn + regression, CI)
```

Suggested stack: Python orchestrator (Anthropic or OpenAI API, tool/function calling, JSON-schema structured outputs), official **MCP SDK** for servers/client (one server in **TypeScript** to prove TS), DuckDB or BigQuery sandbox for SQL, a subprocess/`nsjail`/Docker-based Python sandbox, `python-pptx` + `reportlab`/`weasyprint` (or Google Workspace API) for docgen, small **React + TypeScript** front end, containerized and deployed to **GCP Cloud Run** (aligns with WITHIN's GCP/BigQuery/dbt stack).

---

## 4. Build phases (≈4 weeks part-time)

**Phase 0 — Scaffold (Day 1–2)**
Repo, README with the demo scenario, Docker, GCP project, secrets handling, CI skeleton. Deliverable: `hello-agent` that calls an LLM and returns a structured JSON response validated against a schema.

**Phase 1 — MCP tool layer (Week 1)**
Stand up 2–3 MCP servers: `sql-exec` (read-only, parameterized), `py-sandbox` (resource-limited, no network), `docgen`. Write one server in TypeScript. Orchestrator connects as an MCP client and lists/calls tools. Deliverable: agent answers a question by choosing and calling the right MCP tool.

**Phase 2 — Memory & context (Week 2)**
Multi-turn session store, retrieval-driven context assembly (summarize old turns, keep high-signal tokens under a token budget), persistent memory across sessions. Deliverable: agent handles a 5-turn conversation referencing earlier results.

**Phase 3 — Guardrails & reliability (Week 2–3)**
Retry with backoff on tool failure, JSON-schema validation of every structured output, SQL allowlist / statement checks, sandbox timeouts + output caps, and a "verify tool result before trusting it" step to cut hallucinations. Deliverable: a guardrail test showing malformed SQL / oversized output / bad JSON are caught and recovered.

**Phase 4 — Document automation (Week 3)**
`docgen` MCP server produces (a) a formatted PDF brief, (b) a `.pptx` deck, (c) a table export. Optional: Google Slides/Docs API path. Deliverable: the demo scenario end-to-end producing real files.

**Phase 5 — Evaluation harness (Week 4)**
Task-based success metrics, multi-turn test cases, and a regression suite that runs in CI on every commit (does a prompt/model change break prior behavior?). Track pass rate, tool-call accuracy, and hallucination flags over time. Deliverable: `make eval` + CI badge in README.

**Phase 6 — Deploy & document (Week 4)**
Deploy to Cloud Run, add a demo GIF, architecture diagram, "skills demonstrated" table in the README mapped to the JD, and a short write-up. Deliverable: live URL + polished README.

---

## 5. Skills-to-JD checklist (put this in the README)

- Python production system ✔
- LLM APIs, tool/function calling, structured JSON outputs ✔
- **MCP-style integrations** ✔ (gap filled)
- **Multi-turn context + persistent memory** ✔ (gap filled)
- **Sandboxed SQL + Python execution** ✔ (gap filled)
- **Guardrails: retry, validation, hallucination mitigation** ✔ (gap filled)
- **Document/slide/PDF automation** ✔ (gap filled)
- **Multi-turn + regression evaluation** ✔ (gap filled)
- SQL + data warehouse (DuckDB/BigQuery) ✔
- **Cloud deploy (GCP Cloud Run)** ✔ (gap filled)
- **TypeScript** ✔ (gap filled)
- Git/GitHub, CI ✔

---

## 6. Suggested repo name & positioning

Repo: `atlas-agent` (or `mcp-workspace-agent`). One-line description:
> "An MCP-native, multi-turn agent that runs sandboxed SQL/Python, enforces guardrails, and generates PDF/slide deliverables — deployed on GCP with a regression eval suite."

Pin it alongside `campaign-copilot` and `kindred`: together they tell a clean story — *grounded retrieval (kindred) → analytical agent (campaign-copilot) → productionized MCP agent platform (atlas)* — which is exactly WITHIN's Rai.

---

## 7. Scope guardrails (don't over-build)

Keep the warehouse small (a seeded DuckDB/BigQuery dataset of fake ad spend), keep the UI minimal (a chat box + file downloads), and treat MCP + docgen + eval as the three things that must be excellent because they're your gap-fillers. Everything else is supporting cast.
