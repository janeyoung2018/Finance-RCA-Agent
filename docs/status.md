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
- Gemini-based LLM integration now includes richer response parsing and logging; added live connectivity test (`tests/test_gemini_live.py`) that loads `.env` when available.
- Option values generated from data via `scripts/generate_option_values.py` -> `frontend/src/optionValues.ts`.
- README mentions sweep usage and new rollup/domain fields.
- LangGraph-based orchestration for single scopes and full sweeps with progress updates stored in the run store.
- OpenTelemetry + Phoenix wiring captures RCA runs, per-agent spans, and LLM usage (latency/tokens/cost) with OTLP exporters and optional local Phoenix dashboard.
- Run store now uses durable SQLite storage at `data/run_store.sqlite` to persist run status/results across restarts.

## Not Implemented / Gaps vs README Vision
- No CI/lint/test automation beyond pytest placeholder.
- Synthesis/challenge are rule-based; no real LLM-driven reasoning.
- No auth; metrics beyond traces/tokens/cost still minimal.
- Tests not run in this environment; coverage likely thin.
- Frontend still lacks richer RCA browsing (run detail deep-links, saved views, advanced comparison toggles) beyond the new history table.
