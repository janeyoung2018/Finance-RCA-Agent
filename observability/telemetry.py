"""
OpenTelemetry + Phoenix wiring for tracing and lightweight metrics.

This module stays optional: if OTLP exporters are not reachable, the system
continues to run while logging a warning.
"""

import json
import logging
import os
import time
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_init_lock = Lock()
_initialized = False

_agent_latency_hist = None
_llm_latency_hist = None
_llm_token_counter = None
_llm_cost_counter = None

_TRACER_NAME = "finance-rca-agent"


def _build_endpoint(base: str, signal: str) -> str:
    base = base.rstrip("/")
    return base if base.endswith(signal) else f"{base}/{signal}"


def init_telemetry(service_name: str = "finance-rca-agent") -> None:
    """
    Initialize OTLP exporters for traces + metrics, targeting Phoenix by default.
    Safe to call multiple times.
    """
    global _initialized, _agent_latency_hist, _llm_latency_hist, _llm_token_counter, _llm_cost_counter
    if _initialized:
        return

    with _init_lock:
        if _initialized:
            return

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:6006/v1")
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
                "deployment.environment": os.getenv("APP_ENV", "dev"),
            }
        )

        try:
            tracer_provider = TracerProvider(resource=resource)
            span_exporter = OTLPSpanExporter(endpoint=_build_endpoint(endpoint, "traces"))
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
            trace.set_tracer_provider(tracer_provider)

            metric_exporter = OTLPMetricExporter(endpoint=_build_endpoint(endpoint, "metrics"))
            metric_reader = PeriodicExportingMetricReader(metric_exporter)
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
            meter = metrics.get_meter(service_name)

            _agent_latency_hist = meter.create_histogram(
                name="agent.latency.ms",
                unit="ms",
                description="Agent execution latency",
            )
            _llm_latency_hist = meter.create_histogram(
                name="llm.latency.ms",
                unit="ms",
                description="LLM call latency",
            )
            _llm_token_counter = meter.create_counter(
                name="llm.tokens",
                unit="1",
                description="LLM tokens consumed (prompt/completion)",
            )
            _llm_cost_counter = meter.create_counter(
                name="llm.cost.usd",
                unit="usd",
                description="Estimated LLM cost in USD",
            )
            _initialized = True
            logging.getLogger(__name__).info("Telemetry initialized with OTLP endpoint %s", endpoint)
        except Exception as exc:  # pragma: no cover - best effort wiring
            logging.getLogger(__name__).warning("Telemetry initialization failed: %s", exc)


def get_tracer(name: str = _TRACER_NAME):
    return trace.get_tracer(name)


@contextmanager
def agent_span(agent_name: str, run_id: Optional[str], scope_label: Optional[str], filters: Optional[Dict[str, Any]], month: Optional[str]):
    tracer = get_tracer()
    start = time.perf_counter()
    attributes = {
        "rca.run_id": run_id or "unknown",
        "rca.scope": scope_label or "unknown",
        "rca.agent": agent_name,
        "rca.month": month or "",
    }
    if filters:
        attributes["rca.filters"] = json.dumps(filters, sort_keys=True)

    with tracer.start_as_current_span(f"agent.{agent_name}", attributes=attributes) as span:
        try:
            yield span
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            span.set_attribute("agent.latency_ms", latency_ms)
            if _agent_latency_hist:
                _agent_latency_hist.record(latency_ms, attributes=attributes)


@contextmanager
def llm_span(provider: str, model: str, run_id: Optional[str] = None, scope_label: Optional[str] = None):
    tracer = get_tracer()
    start = time.perf_counter()
    attributes = {
        "llm.provider": provider,
        "llm.model": model,
    }
    if run_id:
        attributes["rca.run_id"] = run_id
    if scope_label:
        attributes["rca.scope"] = scope_label

    with tracer.start_as_current_span(f"llm.{provider}", attributes=attributes) as span:
        try:
            yield span
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            span.set_attribute("llm.latency_ms", latency_ms)


def record_llm_usage(
    provider: str,
    model: str,
    latency_ms: float,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    run_id: Optional[str] = None,
    scope_label: Optional[str] = None,
    explicit_cost_usd: Optional[float] = None,
):
    attributes = {
        "llm.provider": provider,
        "llm.model": model,
    }
    if run_id:
        attributes["rca.run_id"] = run_id
    if scope_label:
        attributes["rca.scope"] = scope_label

    if _llm_latency_hist:
        _llm_latency_hist.record(latency_ms, attributes=attributes)
    if prompt_tokens is not None and _llm_token_counter:
        _llm_token_counter.add(prompt_tokens, attributes={**attributes, "llm.token_type": "prompt"})
    if completion_tokens is not None and _llm_token_counter:
        _llm_token_counter.add(completion_tokens, attributes={**attributes, "llm.token_type": "completion"})

    cost = explicit_cost_usd
    if cost is None and (prompt_tokens is not None or completion_tokens is not None):
        cost = estimate_cost(prompt_tokens or 0, completion_tokens or 0)
    if cost and _llm_cost_counter:
        _llm_cost_counter.add(cost, attributes=attributes)


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate USD cost based on env vars:
    LLM_PROMPT_COST_PER_1K and LLM_COMPLETION_COST_PER_1K (defaults 0).
    """
    prompt_rate = float(os.getenv("LLM_PROMPT_COST_PER_1K", "0") or 0)
    completion_rate = float(os.getenv("LLM_COMPLETION_COST_PER_1K", "0") or 0)
    return ((prompt_tokens / 1000) * prompt_rate) + ((completion_tokens / 1000) * completion_rate)
