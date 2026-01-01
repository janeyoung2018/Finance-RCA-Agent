"""
Stubbed RCA workflow orchestrator with simulated background progression.

Replace the simulated run with LangGraph/LangChain orchestration. The stub
creates a run record, then updates status over time in the background.
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.agents.demand import DemandAgent
from src.agents.finance import FinanceVarianceAgent
from src.agents.fx import FXAgent
from src.agents.supply import SupplyAgent
from src.agents.synthesis import SynthesisAgent
from src.agents.shipments import ShipmentsAgent
from src.agents.events import EventsAgent
from src.memory.run_store import RunRecord, run_store
from src.tools.data_loader import DataRepository
from src.tools.variance import filter_by_scope
from src.tools.normalize import ensure_serializable

@dataclass
class RCAJob:
    month: str
    region: Optional[str] = None
    bu: Optional[str] = None
    product_line: Optional[str] = None
    segment: Optional[str] = None
    metric: Optional[str] = None
    comparison: str = "plan"
    full_sweep: bool = False


def run_rca(job: RCAJob) -> dict:
    """Create a run record and queue simulated execution."""
    # If user did not select a slice, default to sweeping all slices for the month.
    job.full_sweep = job.full_sweep or _is_unscoped(job)
    run_id = _build_run_id(job)
    record = RunRecord(
        run_id=run_id,
        status="queued",
        message="RCA workflow queued (stub). Replace with LangGraph orchestration.",
        payload=job.__dict__,
    )
    run_store.upsert(record)
    return {"run_id": record.run_id, "status": record.status, "message": record.message}


async def _simulate_rca_run(job: RCAJob, run_id: str) -> None:
    """Run RCA progression; replace with actual LangGraph orchestration."""
    run_store.upsert(
        RunRecord(
            run_id=run_id,
            status="running",
            message="RCA workflow running.",
            payload=job.__dict__,
        )
    )

    try:
        repo = DataRepository()
        agents = _init_agents()

        if job.full_sweep:
            await _run_full_sweep(job, run_id, repo, agents)
        else:
            await _run_single_scope(job, run_id, repo, agents, scope_label="selected scope")
    except Exception as exc:
        run_store.upsert(
            RunRecord(
                run_id=run_id,
                status="failed",
                message=f"RCA workflow failed: {exc}",
                payload=job.__dict__,
            )
        )


def enqueue_rca(job: RCAJob, background_runner) -> dict:
    """
    Create a run and enqueue background execution.

    `background_runner` should support `.add_task(callable, *args)`, e.g. FastAPI BackgroundTasks.
    """
    result = run_rca(job)
    background_runner.add_task(_simulate_rca_run, job, result["run_id"])
    return result


def get_rca_status(run_id: str) -> Optional[dict]:
    record = run_store.get(run_id)
    if not record:
        return None
    return {
        "run_id": record.run_id,
        "status": record.status,
        "message": record.message,
        "result": record.result,
    }


def _build_run_id(job: RCAJob) -> str:
    scope_bits = [job.region, job.bu, job.product_line, job.segment, job.metric]
    scope = "-".join([bit for bit in scope_bits if bit]) or "all"
    base = f"rca-{job.month.replace('-', '')}-{scope}"
    return f"{base}-sweep" if job.full_sweep else base


def _is_unscoped(job: RCAJob) -> bool:
    return not any([job.region, job.bu, job.product_line, job.segment, job.metric])


def _init_agents() -> Dict[str, object]:
    return {
        "finance": FinanceVarianceAgent(),
        "demand": DemandAgent(),
        "supply": SupplyAgent(),
        "shipments": ShipmentsAgent(),
        "fx": FXAgent(),
        "events": EventsAgent(),
        "synthesis": SynthesisAgent(),
    }


async def _run_single_scope(job: RCAJob, run_id: str, repo: DataRepository, agents: Dict[str, object], scope_label: str, extra_filters: Optional[Dict] = None) -> Dict:
    filters = {
        "region": job.region,
        "bu": job.bu,
        "product_line": job.product_line,
        "segment": job.segment,
        "metric": job.metric,
    }
    if extra_filters:
        filters.update(extra_filters)

    finance_res = agents["finance"].analyze(
        repo.finance(),
        job.month,
        comparison=job.comparison,
        **filters,
    )
    finance_serialized = ensure_serializable(finance_res)
    run_store.upsert(
        RunRecord(
            run_id=run_id,
            status="finance_completed",
            message=f"Finance analysis completed for {scope_label}.",
            payload=job.__dict__,
            result={"finance": finance_serialized},
        )
    )

    demand_res = agents["demand"].analyze(
        repo.orders(),
        job.month,
        **filters,
    )
    supply_res = agents["supply"].analyze(
        repo.supply(),
        job.month,
        **filters,
    )
    shipments_res = agents["shipments"].analyze(
        repo.shipments(),
        job.month,
        **filters,
    )
    fx_res = agents["fx"].analyze(repo.fx(), job.month, **filters)
    events_res = agents["events"].analyze(
        repo.events(),
        job.month,
        **filters,
    )

    demand_serialized = ensure_serializable(demand_res)
    supply_serialized = ensure_serializable(supply_res)
    shipments_serialized = ensure_serializable(shipments_res)
    fx_serialized = ensure_serializable(fx_res)
    events_serialized = ensure_serializable(events_res)

    run_store.upsert(
        RunRecord(
            run_id=run_id,
            status="synthesizing",
            message=f"Aggregating findings for {scope_label}.",
            payload=job.__dict__,
            result={
                "finance": finance_serialized,
                "demand": demand_serialized,
                "supply": supply_serialized,
                "shipments": shipments_serialized,
                "fx": fx_serialized,
                "events": events_serialized,
            },
        )
    )

    synthesis = agents["synthesis"].synthesize(
        finance_serialized,
        demand_serialized,
        supply_serialized,
        shipments_serialized,
        fx_serialized,
        events_serialized,
        scope_label=scope_label,
    )
    synthesis_serialized = ensure_serializable(synthesis)

    result = {
        "finance": finance_serialized,
        "demand": demand_serialized,
        "supply": supply_serialized,
        "shipments": shipments_serialized,
        "fx": fx_serialized,
        "events": events_serialized,
        "synthesis": synthesis_serialized,
        "filters": filters,
        "scope": scope_label,
    }

    run_store.upsert(
        RunRecord(
            run_id=run_id,
            status="completed",
            message=f"RCA workflow completed for {scope_label}.",
            payload=job.__dict__,
            result=result,
        )
    )
    return result


async def _run_full_sweep(job: RCAJob, run_id: str, repo: DataRepository, agents: Dict[str, object]) -> None:
    base_filters = {k: v for k, v in {
        "region": job.region,
        "bu": job.bu,
        "product_line": job.product_line,
        "segment": job.segment,
        "metric": job.metric,
    }.items() if v}

    scopes = _discover_scopes(repo, job.month, base_filters)
    sweep_results: Dict[str, Dict] = {}

    for idx, scope in enumerate(scopes, start=1):
        scope_label = scope["label"]
        result = await _run_single_scope(job, run_id, repo, agents, scope_label=scope_label, extra_filters=scope["filters"])
        sweep_results[scope_label] = result
        run_store.upsert(
            RunRecord(
                run_id=run_id,
                status="running",
                message=f"Processed {idx}/{len(scopes)} scopes.",
                payload=job.__dict__,
                result={"scopes": ensure_serializable(sweep_results)},
            )
        )

    sweep_summary = agents["synthesis"].summarize_sweep(sweep_results)
    run_store.upsert(
        RunRecord(
            run_id=run_id,
            status="completed",
            message="Full-sweep RCA workflow completed.",
            payload=job.__dict__,
            result={"scopes": ensure_serializable(sweep_results), "portfolio": ensure_serializable(sweep_summary)},
        )
    )


def _discover_scopes(repo: DataRepository, month: str, base_filters: Dict[str, str]) -> List[Dict[str, Dict]]:
    """Build a list of scopes (overall + each dimension) for sweep runs."""
    finance_df = filter_by_scope(repo.finance(), month, **base_filters)
    scopes: List[Dict[str, Dict]] = [{"label": "overall", "filters": base_filters}]
    seen_labels = set(["overall"])

    for column, prefix in [
        ("region", "region"),
        ("bu", "bu"),
        ("product_line", "product_line"),
        ("segment", "segment"),
        ("metric", "metric"),
    ]:
        if column not in finance_df.columns:
            continue
        values = _unique_non_null(finance_df, column)
        for value in values:
            label = f"{prefix}:{value}"
            if label in seen_labels:
                continue
            seen_labels.add(label)
            filters = dict(base_filters)
            filters[column] = value
            scopes.append({"label": label, "filters": filters})
    return scopes


def _unique_non_null(df, column: str) -> List[str]:
    values = (
        df[column]
        .dropna()
        .unique()
        .tolist()
    )
    return [str(v) for v in values if str(v).strip() != ""]
