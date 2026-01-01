# RCA Implementation Status

## Implemented
- End-to-end RCA API with background workflow, specialist agents (finance, demand, supply, shipments, FX, events), and in-memory run store.
- Full-sweep mode runs all slices (regions/BUs/product_lines/segments/metrics) when unscoped or `full_sweep=true`; returns per-scope syntheses plus portfolio summary.
- Synthesis produces stakeholder-friendly briefs and sweep hotspot summaries.
- Synthesis now emits dual summaries: a rule-based reference and an LLM decision-support summary with deterministic fallback; LLM calls wire up automatically when `GOOGLE_API_KEY` (Gemini) or `OPENAI_API_KEY` is set.
- Finance rollups: overall, by region, by BU with per-metric contributors vs plan and prior; supports `comparison="all"`.
- Domain breakdowns: dominant demand/supply/pricing/fx/cost drivers per region and BU.
- Frontend dropdowns for all filters (including metric), default comparison `all`, and rendering for rollup/domain summaries plus raw JSON.
- Frontend surfaces rule-based vs LLM decision-support summaries for scopes and sweeps.
- Gemini-based LLM integration now includes richer response parsing and logging; added live connectivity test (`tests/test_gemini_live.py`) that loads `.env` when available.
- Option values generated from data via `scripts/generate_option_values.py` -> `frontend/src/optionValues.ts`.
- README mentions sweep usage and new rollup/domain fields.

## Not Implemented / Gaps vs README Vision
- Orchestration still a stubbed background task (no LangGraph/LangChain, challenge agent, or HITL loop).
- No durable storage (still in-memory run store); no CI/lint/test automation beyond pytest placeholder.
- Synthesis/challenge are rule-based; no real LLM-driven reasoning.
- No auth, tracing, or cost/latency metrics on the API.
- Tests not run in this environment; coverage likely thin.
- Frontend remains minimal (no run history, pagination, richer UX); `comparison="all"` handling is basic display only.
