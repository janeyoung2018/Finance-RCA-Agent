# Finance-RCA-Agent
An agent for financial root cause analyses
# Multi-Agent Financial Root Cause Analysis (RCA) System

## Overview

This project is a **production-oriented multi-agent system** for performing **monthly financial root cause analysis (RCA)**.

The system analyzes **Actual vs Plan vs Prior** performance, identifies **what changed**, explains **why it changed**, and attributes impact across:
- Regions
- Business Units
- Product Lines
- Customer Segments
- Demand, Supply, Pricing, FX, and Cost drivers

The goal is **not** to build a BI dashboard or chatbot, but to demonstrate how **LLM-powered agents** can collaborate, reason over structured data, retain context over time, and produce **auditable, explainable analyses** with **human-in-the-loop control**.

---

## Project Goals

This repository is a **reference implementation** focused on real-world agent system concerns:

- Multi-agent orchestration (parallel, sequential, looped agents)
- Tool-augmented reasoning over structured data
- Long-running workflows with pause/resume
- Session and state management
- **Short-term and long-term memory**
- Context engineering and compaction
- Observability (logging, tracing, metrics)
- Agent evaluation and regression testing
- Human-in-the-loop (HITL) review and approval
- Cloud-ready, containerized deployment

The emphasis is **system reliability and design**, not prompt engineering.

---

## High-Level Workflow

1. **User requests an RCA**
   - Example:  
     *“Why did APAC revenue miss plan in Aug 2025?”*

2. **Orchestrator Agent**
   - Defines scope (month, comparison baseline)
   - Loads relevant memory
   - Creates an investigation plan
   - Spawns specialist agents

3. **Specialist Agents (parallel)**
   - Finance Variance Agent
   - Demand Agent
   - Supply Chain Agent
   - Pricing / FX Agent
   - Anomaly Detection Agent

4. **Synthesis Agent**
   - Aggregates findings
   - Ranks root causes by quantified impact
   - Generates a draft narrative with evidence

5. **Challenge Agent (loop)**
   - Tests alternative explanations
   - Detects conflicting signals
   - Requests additional analysis if needed

6. **Human-in-the-Loop Gate**
   - Review, edit, approve, or request drill-downs
   - System resumes after feedback

7. **Final RCA Report**
   - Executive summary
   - Ranked drivers with evidence
   - Assumptions and uncertainty
   - Actionable follow-ups

---

## Memory Model

Memory is a **first-class component** of the system.

### 1. Session Memory (Short-Term)

Used **within a single RCA run**.

Stores:
- Scope (month, baseline, filters)
- Intermediate tool outputs
- Agent findings and confidence scores
- Draft narratives and revisions
- Human feedback and decisions

Purpose:
- Enable pause/resume
- Avoid recomputation
- Maintain traceability across agent steps

Typical implementations:
- In-memory (development)
- Redis or database-backed (production)

---

### 2. Long-Term Memory (Cross-Session)

Used **across multiple RCA runs** to improve analysis quality over time.

Stores:
- Recurring seasonal patterns by region or BU
- Known structural drivers (e.g., recurring supply constraints)
- Previously validated RCA explanations
- Human reviewer corrections and preferences
- Known data quality issues

Purpose:
- Reduce repeated false hypotheses
- Improve consistency across months
- Incorporate human judgment into future analyses

Memory is retrieved **selectively** and injected into agent context in compact form.

---

### 3. Context Engineering

Because RCA sessions can grow large:
- Raw tables are never placed directly into prompts
- Only aggregates, summaries, and evidence references are included
- Memory is compacted into short, decision-relevant snippets

This keeps agents:
- Cost-efficient
- Deterministic
- Auditable

---

## Dataset (Example Only)

This repository includes a **synthetic financial and operational dataset** in the `data/` folder.

The dataset:
- Is fully synthetic and safe to share
- Mimics real enterprise finance and operations data
- Contains planted RCA scenarios (supply delays, promotions, FX swings, churn)

The dataset exists solely to **exercise the system design**.  
The architecture is **data-source agnostic** and can be adapted to real data warehouses or APIs.

---

## Tools & Technologies

### Core Stack
- **Python**
- **LangGraph (LangChain)** for agent orchestration
- **Pydantic** for contracts and state
- **FastAPI** (or CLI) for execution
- **Docker / containers** for deployment

### Tooling Concepts Demonstrated
- Custom analytical tools (variance decomposition, anomaly detection)
- CSV-backed “warehouse-like” query tools
- OpenAPI tools (e.g., ticketing or CRM — optional)
- MCP-style tool discovery (optional)
- Code execution tools for validation and chart generation

---

## Observability

The system is instrumented for:
- Structured logging
- Distributed tracing
- Cost and latency metrics
- Evidence coverage metrics
- HITL escalation and rejection rates

Observability is treated as **part of correctness**, not an afterthought.

---

## Repository Structure (scaffold)

Current layout with intended roles:
- `src/agents` — orchestrator, specialist agents, and synthesis/challenge loops.
- `src/tools` — analytical tools (variance decomposition, anomaly detection, charting, CSV/SQL loaders).
- `src/memory` — session + long-term stores, compaction utilities, and retrieval logic.
- `src/workflows` — LangGraph/LangChain graphs and orchestration definitions.
- `src/schemas` — Pydantic contracts for state, tool IO, and HITL payloads.
- `api/` — FastAPI or CLI entrypoints, routing, auth hooks.
- `config/` — environment settings, data paths, and routing config (add `.env.example` here).
- `observability/` — logging, tracing, metrics config.
- `docs/` — architecture notes, runbooks, HITL/observability guides.
- `tests/` — unit/integration/e2e tests and planted-scenario evaluations.
- `scripts/` — setup, lint/test runners, data/evaluation helpers.
- `data/` — synthetic dataset, dictionary, and examples (see `data_readme.md` and `datadict.md`).

---

## Getting Started (FastAPI)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the API locally:
   ```bash
   uvicorn api.main:app --reload
   ```
3. Check health:
   ```bash
   curl http://127.0.0.1:8000/health
   ```
4. Start an RCA:
   ```bash
   curl -X POST http://127.0.0.1:8000/rca \\
     -H "Content-Type: application/json" \\
     -d '{"month":"2025-08","region":"APAC","bu":"Growth"}'
   ```
5. Poll run status and results:
   ```bash
   curl http://127.0.0.1:8000/rca/rca-202508
   ```

### Tests
```bash
pytest
```

### React Frontend
Located in `frontend/` (Vite + React + TypeScript).
1. Install deps (from `frontend/`):
   ```bash
   npm install
   ```
2. Run dev server:
   ```bash
   npm run dev
   ```
3. Open the URL printed by Vite (default http://localhost:5173) and trigger RCA runs.
4. To point at a different API base URL, set `VITE_API_BASE_URL` in `frontend/.env` (defaults to `http://127.0.0.1:8000`).
