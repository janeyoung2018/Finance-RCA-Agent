# Observability
Logging, tracing, and metrics configuration plus any dashboards/exporters.

## Phoenix + OpenTelemetry
- The app initializes OpenTelemetry with OTLP exporters (HTTP/protobuf) on startup; defaults to `http://localhost:6006/v1` which matches Phoenix.
- Traces:
  - `rca.run` for each workflow execution.
  - `agent.*` spans for every specialist agent invocation (includes run_id, scope, filters, latency, output size).
  - `llm.*` spans for Gemini/OpenAI calls (includes tokens when available, latency, estimated cost).
- Metrics:
  - `agent.latency.ms` histogram.
  - `llm.latency.ms` histogram.
  - `llm.tokens` counter (prompt vs completion).
  - `llm.cost.usd` counter (uses env rates when API does not return usage).

## Running Phoenix locally
1) Install: `pip install arize-phoenix opentelemetry-sdk opentelemetry-exporter-otlp-proto-http`
2) Start the collector/UI (port 6006 default): `phoenix serve`
3) Set env vars (or edit `.env`):
   - `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1`
   - Optionally `SERVICE_VERSION`, `APP_ENV`, and LLM pricing (`LLM_PROMPT_COST_PER_1K`, `LLM_COMPLETION_COST_PER_1K`).
4) Run the API/app; traces and metrics will stream to Phoenix.

Phoenix will show traces for agent calls, LLM calls, and RCA runs so you can inspect latency, token usage, and estimated cost per request/scope.
