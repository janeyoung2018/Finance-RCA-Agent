# RCA Implementation Status

## Implemented
- End-to-end RCA API with background workflow, specialist agents (finance, demand, supply, shipments, FX, events), and durable SQLite-backed run store.
- Full-sweep mode runs all slices (regions/BUs/product_lines/segments/metrics) when unscoped or `full_sweep=true`; returns per-scope syntheses plus portfolio summary.
- Synthesis produces stakeholder-friendly briefs and sweep hotspot summaries.
- Synthesis now emits dual summaries: a rule-based reference and an LLM decision-support summary with deterministic fallback; LLM calls wire up automatically when `GOOGLE_API_KEY` (Gemini) or `OPENAI_API_KEY` is set.
- Finance rollups: overall, by region, by BU with per-metric contributors vs plan and prior; supports `comparison="all"`.
- Domain breakdowns: dominant demand/supply/pricing/fx/cost drivers per region and BU.
- Frontend dropdowns for all filters (including metric), default comparison `all`, and rendering for rollup/domain summaries plus raw JSON.
- Rollups and decision-support summaries honor the active filters (including metric/comparison), surface scope/filter chips in the UI, and LLM prompts/output are reformatted to avoid markdown bolding.
- Frontend surfaces rule-based vs LLM decision-support summaries for scopes and sweeps.
- Frontend now includes persistent run history with pagination/filters and clearer `comparison="all"` context messaging.
- Frontend browsing adds shareable run deep-links and comparison view toggles for rollups/history.
- LLM reasoning endpoint `/llm/query` plus frontend Q&A page that answers questions from stored RCA outputs; prompt is guardrailed to JSON (answer/rationale/sources/evidence_refs/next questions/confidence) with deterministic fallback when no LLM key is set.
- LLM challenge endpoint `/llm/challenge` highlights conflicts/blind spots; Q&A supports optional comparison against a second run for delta-aware reasoning.
- Gemini-based LLM integration now includes richer response parsing and logging; added live connectivity test (`tests/test_gemini_live.py`) that loads `.env` when available.
- Option values generated from data via `scripts/generate_option_values.py` -> `frontend/src/optionValues.ts`.
- README mentions sweep usage and new rollup/domain fields.
- LangGraph-based orchestration for single scopes and full sweeps with progress updates stored in the run store.
- OpenTelemetry + Phoenix wiring captures RCA runs, per-agent spans, and LLM usage (latency/tokens/cost) with OTLP exporters and optional local Phoenix dashboard.
- Run store uses durable SQLite storage at `data/run_store.sqlite` to persist run status/results across restarts and supports paginated/status-filtered run listing for the frontend history view.
- GitHub Actions CI runs compile checks and pytest with coverage (xml artifact) on push/PR.
- Dockerfiles added for API and frontend plus docker-compose for running both.
- Coverage configured via pytest-cov (`pytest.ini`) producing terminal and XML reports.

## Not Implemented / Gaps vs README Vision
- Decision support remains heuristic-first: LLM usage is limited to summaries/Q&A/challenge over stored outputs (no tool-using or causal modeling).
- Data connectors are limited to the bundled CSV dataset; no warehouse adapters or freshness monitoring.
- No auth or RBAC; operational hardening is light (no rate limiting/backpressure on background jobs).
- Frontend still lacks saved presets, side-by-side multi-run comparisons, and deeper drill-down visualizations beyond the current rollups/history toggles.
