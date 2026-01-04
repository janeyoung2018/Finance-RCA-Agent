# Finance-RCA-Agent
Multi-agent financial root cause analysis (RCA) system that pairs deterministic analytics with LLM decision support.

## Overview

This project is a production-oriented monthly RCA workflow. The goal is to demonstrate how **LLM-powered agents** collaborate with traditional rule-based analyses to deliver accurate financial variance results, surface stakeholder-ready insights, and let humans run RCA and Q&A in plain language with human-in-the-loop control.

The system analyzes **Actual vs Plan vs Prior** performance, identifies what changed, explains why, and attributes impact across regions, business units, product lines, and customer segments.

---

## Current Capabilities

### RCA pipeline
- End-to-end RCA API with background workflow, specialist agents (finance, demand, supply, shipments, FX, events), and a durable SQLite-backed run store.
- LangGraph-based orchestration for single-scope and full-sweep runs with progress persisted per run.
- Finance rollups overall, by region, and by BU with per-metric contributors vs plan and prior; supports `comparison="all"`.
- Domain breakdowns surface dominant demand/supply/pricing/fx/cost drivers per region and BU.
- Full-sweep mode runs all slices (regions/BUs/product_lines/segments/metrics) when unscoped or `full_sweep=true` and returns per-scope syntheses plus a portfolio summary.

### Decision support & LLM usage
- Synthesis produces stakeholder-friendly briefs and sweep hotspot summaries.
- Dual summaries for scopes and sweeps: rule-based reference plus LLM decision-support output with deterministic fallback when no key is set.
- LLM integration (Gemini or OpenAI) with richer response parsing, logging, and a live connectivity test.
- LLM reasoning endpoints `/llm/query` and `/llm/challenge` answer or challenge stored RCA outputs with JSON guardrails (answer/rationale/sources/evidence_refs/next questions/confidence), deterministic fallback when no LLM key is set, and optional compare-run support for delta-aware responses.

### Frontend
- Vite + React UI renders rollup/domain summaries, raw JSON, and scope/filter chips with default `comparison="all"`.
- Dropdowns cover all filters (including metric) with option values generated from data via `scripts/generate_option_values.py`.
- Persistent run history with pagination/filters, clearer `comparison="all"` messaging, shareable run deep-links, and comparison view toggles.
- Frontend surfaces rule-based vs LLM decision-support summaries for scopes and sweeps.
- LLM Reasoning tab lets you ask or challenge runs (with optional scope/compare run) and shows whether answers came from an LLM or deterministic fallback.

### Observability & ops
- OpenTelemetry + Phoenix wiring captures RCA runs, per-agent spans, and LLM usage (latency/tokens/cost) with OTLP exporters and optional local Phoenix dashboard.
- Run store persists to `data/run_store.sqlite` (override with `RUN_STORE_PATH`) so background jobs survive API restarts and backs paginated/status-filtered run listing for the history view.
- GitHub Actions CI runs compile checks and pytest with coverage (XML artifact) on push/PR.
- Dockerfiles for API and frontend plus docker-compose for running both together.

### Security & hardening
- Optional API key guard on all non-health endpoints via `API_KEY` and `X-API-Key` header.
- In-memory request throttling per client (`RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS`); 429 responses on bursts.
- RCA queue/backpressure limits (`MAX_QUEUED_RUNS`, `MAX_CONCURRENT_RUNS`) to avoid unbounded background jobs; excess requests return 429.
- See `docs/security.md` for configuration details and ops guidance.

---

## Gaps vs Vision
- Decision support is heuristic-first: LLM use is limited to summaries/Q&A/challenge over stored outputs (no causal modeling or tool-driven what-ifs).
- Data connectors are limited to the bundled CSV dataset; no warehouse adapters or freshness monitoring.
- Only basic API key auth plus in-memory rate limiting/backpressure are available; no RBAC or production-grade policy enforcement yet.
- Frontend lacks saved presets, side-by-side multi-run comparisons, and deeper drill-down visualizations beyond the current rollups/history toggles.

---

## RCA Flow

1. **Request an RCA** (e.g., “Why did APAC revenue miss plan in Aug 2025?”).
2. **Orchestrator agent** scopes the month/baseline, loads memory, and spawns specialist agents.
3. **Specialist agents** run finance variance, demand, supply/shipments, pricing/FX, and anomaly/event analysis.
4. **Synthesis** aggregates findings, ranks root causes, and drafts stakeholder-ready briefs (rule-based with optional LLM decision support).
5. **Challenge loop** tests alternative explanations, flags conflicts/blind spots, and can request more analysis.
6. **Human-in-the-loop** review gates approval, edits, or drill-down requests; workflows resume afterward.
7. **Final RCA output** includes executive-style summaries, ranked drivers with evidence, assumptions/uncertainty, and follow-ups.

---

## Memory Model

Memory is a first-class component of the system.

### Session Memory (short-term)
- Tracks scope, intermediate tool outputs, agent findings/confidence, drafts, and HITL feedback within a single RCA run.
- Supports pause/resume, avoids recomputation, and keeps steps auditable.

### Long-Term Memory (cross-session)
- Stores recurring patterns, validated explanations, reviewer corrections, and known data quality issues to improve future analyses.
- Retrieved selectively and compacted before entering prompts to keep runs cost-efficient and deterministic.

### Context Engineering
- Raw tables stay out of prompts; only aggregates, summaries, and evidence references are injected.
- Memory is compacted into short, decision-relevant snippets to maintain traceability.

---

## Dataset (example only)

The `data/` folder contains a synthetic financial/operational dataset with planted scenarios (supply delays, promotions, FX swings, churn) to exercise the system design. The architecture is data-source agnostic and can be pointed at real warehouses or APIs.

---

## Tools & Technologies

- Python, LangGraph (LangChain), Pydantic, FastAPI/CLI
- Custom analytical tools (variance decomposition, anomaly detection), CSV-backed query tools
- Optional OpenAPI/MCP-style tool discovery and code execution for validation/charting
- Docker/containerized deployment

---

## Repository Structure

- `src/agents` — orchestrator, specialist agents, synthesis/challenge loops.
- `src/tools` — analytical tools (variance, anomaly detection, charting, CSV/SQL loaders).
- `src/memory` — session + long-term stores, compaction utilities, retrieval logic.
- `src/workflows` — LangGraph/LangChain graphs and orchestration definitions.
- `src/schemas` — Pydantic contracts for state, tool IO, and HITL payloads.
- `api/` — FastAPI or CLI entrypoints, routing, auth hooks.
- `config/` — environment settings, data paths, routing config.
- `observability/` — logging, tracing, metrics config.
- `docs/` — architecture notes, runbooks, HITL/observability guides.
- `tests/` — unit/integration/e2e tests and planted-scenario evaluations.
- `scripts/` — setup, lint/test runners, data/evaluation helpers.
- `data/` — synthetic dataset, dictionary, and examples (see `data_readme.md` and `datadict.md`).

---

## Getting Started (FastAPI API)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the API locally:
   ```bash
   uvicorn api.main:app --reload
   ```
3. Health check (health endpoint is unauthenticated):
   ```bash
   curl http://127.0.0.1:8000/health
   ```
   If you set `API_KEY`, include `-H "X-API-Key: $API_KEY"` on all other requests.
4. Start an RCA (defaults to `comparison="all"`):
   ```bash
   curl -X POST http://127.0.0.1:8000/rca \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $API_KEY" \
     -d '{"month":"2025-08","region":"APAC","bu":"Growth"}'
   ```
   Full sweep across regions/BUs/product_lines/segments/metrics:
   ```bash
   curl -X POST http://127.0.0.1:8000/rca \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $API_KEY" \
     -d '{"month":"2025-08","full_sweep":true}'
   ```
5. Poll run status/results:
   ```bash
   curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8000/rca/rca-202508-APAC-Growth
   ```
   Full-sweep runs return IDs like `rca-202508-all-sweep` and include:
   - `rollup`: month-level finance metrics vs plan/prior with top region/BU contributors
   - `portfolio`: sweep summary across scopes
   - `domains`: dominant demand/supply/pricing/fx/cost drivers per region and BU
6. List runs (powers the frontend history view) with optional status/limit/offset filters:
   ```bash
   curl -H "X-API-Key: $API_KEY" "http://127.0.0.1:8000/rca?status=completed&limit=10&offset=0"
   ```

### LLM decision support (optional)
- Prefer Gemini free tier: set `GOOGLE_API_KEY` (default model `gemini-1.5-flash`).
- Or set `OPENAI_API_KEY` (and optionally `OPENAI_BASE_URL`) to use OpenAI chat models.
- Optional envs: `LLM_MODEL`, `LLM_MAX_TOKENS` (default `256`), `LLM_TEMPERATURE` (default `0.2`).
- Use `/llm/query` for natural-language Q&A over stored RCA outputs and `/llm/challenge` for conflict/blind-spot checks (both fall back to deterministic responses without keys).

### React frontend

Located in `frontend/` (Vite + React + TypeScript).

1. Install deps:
   ```bash
   npm install
   ```
2. Run dev server:
   ```bash
   npm run dev
   ```
3. Open the URL printed by Vite (default http://localhost:5173) and trigger RCA runs.
4. Point to a different API base URL with `VITE_API_BASE_URL` in `frontend/.env` (defaults to `http://127.0.0.1:8000`).
5. Regenerate dropdown values:
   ```bash
   python scripts/generate_option_values.py
   ```

### Tests
```bash
pytest
```

### CI
- GitHub Actions workflow (`.github/workflows/ci.yml`) runs compile checks and pytest with coverage (XML artifact) on push/PR.

### Docker
- Backend: `docker build -t rca-api . && docker run -p 8000:8000 rca-api`
- Frontend: `docker build -f frontend/Dockerfile -t rca-frontend . && docker run -p 5173:80 rca-frontend`
- Compose both: `docker-compose up --build` (frontend built with `VITE_API_BASE_URL=http://api:8000`; mounts `./data` into the API).
