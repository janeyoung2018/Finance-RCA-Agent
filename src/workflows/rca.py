import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from src.agents.demand import DemandAgent
from src.agents.events import EventsAgent
from src.agents.finance import FinanceVarianceAgent
from src.agents.fx import FXAgent
from src.agents.shipments import ShipmentsAgent
from src.agents.supply import SupplyAgent
from src.agents.synthesis import SynthesisAgent
from src.config import TOP_CONTRIBUTORS
from src.llm.client import build_llm
from src.memory.run_store import RunRecord, run_store
from src.tools.data_loader import DataRepository
from src.tools.normalize import ensure_serializable
from src.tools.variance import filter_by_scope


@dataclass
class RCAJob:
    month: str
    region: Optional[str] = None
    bu: Optional[str] = None
    product_line: Optional[str] = None
    segment: Optional[str] = None
    metric: Optional[str] = None
    comparison: str = "all"
    full_sweep: bool = False


class ScopeState(TypedDict, total=False):
    job: "RCAJob"
    run_id: str
    scope_label: str
    filters: Dict[str, Optional[str]]
    finance: Dict
    demand: Dict
    supply: Dict
    shipments: Dict
    fx: Dict
    events: Dict
    synthesis: Dict
    rollup: Dict
    result: Dict


def run_rca(job: RCAJob) -> dict:
    """Create a run record and queue LangGraph execution."""
    # If user did not select a slice, default to sweeping all slices for the month.
    job.full_sweep = job.full_sweep or _is_unscoped(job)
    run_id = _build_run_id(job)
    record = RunRecord(
        run_id=run_id,
        status="queued",
        message="RCA workflow queued with LangGraph orchestration.",
        payload=job.__dict__,
    )
    run_store.upsert(record)
    return {"run_id": record.run_id, "status": record.status, "message": record.message}


async def _execute_rca_run(job: RCAJob, run_id: str) -> None:
    """Run RCA progression via LangGraph."""
    run_store.upsert(
        RunRecord(
            run_id=run_id,
            status="running",
            message="RCA workflow running via LangGraph.",
            payload=job.__dict__,
        )
    )

    try:
        repo = DataRepository()
        agents = _init_agents()
        scope_graph = _build_scope_graph(repo, agents)

        if job.full_sweep:
            await _run_full_sweep(job, run_id, repo, agents, scope_graph)
        else:
            await _run_single_scope(job, run_id, repo, agents, scope_graph, scope_label="selected scope")
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
    background_runner.add_task(_execute_rca_run, job, result["run_id"])
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
    llm = build_llm()
    if llm:
        logging.getLogger(__name__).info("LLM client initialized for synthesis.")
    else:
        logging.getLogger(__name__).info("LLM client not initialized; synthesis will use rule-based fallbacks.")
    return {
        "finance": FinanceVarianceAgent(),
        "demand": DemandAgent(),
        "supply": SupplyAgent(),
        "shipments": ShipmentsAgent(),
        "fx": FXAgent(),
        "events": EventsAgent(),
        # Remains rule-based when llm is None; becomes LLM-enhanced when configured via env vars.
        "synthesis": SynthesisAgent(llm=llm),
    }


def _build_scope_graph(repo: DataRepository, agents: Dict[str, object]):
    """
    LangGraph orchestrator for a single RCA scope.

    Nodes:
    - analyze_scope: runs specialist agents in parallel
    - synthesize_scope: aggregates findings and builds rollups
    """
    graph: StateGraph = StateGraph(ScopeState)

    async def analyze_scope(state: ScopeState) -> ScopeState:
        job = state["job"]
        filters = state.get("filters", {})
        scope_label = state.get("scope_label") or "selected scope"
        run_id = state.get("run_id", "unknown")

        finance_df = repo.finance()
        demand_df = repo.orders()
        supply_df = repo.supply()
        shipments_df = repo.shipments()
        fx_df = repo.fx()
        events_df = repo.events()

        finance_task = asyncio.to_thread(
            agents["finance"].analyze,
            finance_df,
            job.month,
            comparison=job.comparison,
            **filters,
        )
        demand_task = asyncio.to_thread(agents["demand"].analyze, demand_df, job.month, **filters)
        supply_task = asyncio.to_thread(agents["supply"].analyze, supply_df, job.month, **filters)
        shipments_task = asyncio.to_thread(agents["shipments"].analyze, shipments_df, job.month, **filters)
        fx_task = asyncio.to_thread(agents["fx"].analyze, fx_df, job.month, **filters)
        events_task = asyncio.to_thread(agents["events"].analyze, events_df, job.month, **filters)

        (
            finance_res,
            demand_res,
            supply_res,
            shipments_res,
            fx_res,
            events_res,
        ) = await asyncio.gather(
            finance_task, demand_task, supply_task, shipments_task, fx_task, events_task
        )

        finance_serialized = ensure_serializable(finance_res)
        partial_result = {
            "finance": finance_serialized,
            "demand": ensure_serializable(demand_res),
            "supply": ensure_serializable(supply_res),
            "shipments": ensure_serializable(shipments_res),
            "fx": ensure_serializable(fx_res),
            "events": ensure_serializable(events_res),
            "filters": filters,
            "scope": scope_label,
            "month": job.month,
            "comparison": job.comparison,
        }

        run_store.upsert(
            RunRecord(
                run_id=run_id,
                status="synthesizing",
                message=f"Agent analyses completed for {scope_label}; preparing synthesis.",
                payload=job.__dict__,
                result=partial_result,
            )
        )
        return partial_result

    def synthesize_scope(state: ScopeState) -> ScopeState:
        job = state["job"]
        filters = state.get("filters", {})
        scope_label = state.get("scope_label") or "selected scope"
        run_id = state.get("run_id", "unknown")

        finance = state.get("finance", {})
        demand = state.get("demand", {})
        supply = state.get("supply", {})
        shipments = state.get("shipments", {})
        fx = state.get("fx", {})
        events = state.get("events", {})

        synthesis = agents["synthesis"].synthesize(
            finance,
            demand,
            supply,
            shipments,
            fx,
            events,
            scope_label=scope_label,
            filters=filters,
            month=job.month,
        )
        finance_rollup = _build_finance_rollup(filter_by_scope(repo.finance(), job.month, **filters))
        synthesis_serialized = ensure_serializable(synthesis)
        rollup_serialized = ensure_serializable(finance_rollup)

        result = {
            "finance": finance,
            "demand": demand,
            "supply": supply,
            "shipments": shipments,
            "fx": fx,
            "events": events,
            "synthesis": synthesis_serialized,
            "filters": filters,
            "scope": scope_label,
            "month": job.month,
            "comparison": job.comparison,
            "rollup": rollup_serialized,
        }

        status = "scope_completed" if job.full_sweep else "completed"
        message = f"Scope {scope_label} completed; awaiting sweep aggregation." if job.full_sweep else f"RCA workflow completed for {scope_label}."
        status = "running" if job.full_sweep else status
        run_store.upsert(
            RunRecord(
                run_id=run_id,
                status=status,
                message=message,
                payload=job.__dict__,
                result=result,
            )
        )
        return {"synthesis": synthesis_serialized, "rollup": rollup_serialized, "result": result}

    graph.add_node("analyze_scope", analyze_scope)
    graph.add_node("synthesize_scope", synthesize_scope)
    graph.add_edge(START, "analyze_scope")
    graph.add_edge("analyze_scope", "synthesize_scope")
    graph.add_edge("synthesize_scope", END)
    return graph.compile()


async def _run_single_scope(
    job: RCAJob,
    run_id: str,
    repo: DataRepository,
    agents: Dict[str, object],
    scope_graph,
    scope_label: str,
    extra_filters: Optional[Dict] = None,
) -> Dict:
    filters = _merge_filters(job, extra_filters)
    initial_state: ScopeState = {
        "job": job,
        "run_id": run_id,
        "scope_label": scope_label,
        "filters": filters,
    }
    final_state = await scope_graph.ainvoke(initial_state)
    result = final_state.get("result")
    if not result:
        raise RuntimeError(f"LangGraph did not produce a result for {scope_label}.")
    return result


async def _run_full_sweep(
    job: RCAJob,
    run_id: str,
    repo: DataRepository,
    agents: Dict[str, object],
    scope_graph,
) -> None:
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
        result = await _run_single_scope(job, run_id, repo, agents, scope_graph, scope_label=scope_label, extra_filters=scope["filters"])
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

    sweep_summary = agents["synthesis"].summarize_sweep(sweep_results, base_filters=base_filters, month=job.month)
    finance_df_for_rollup = filter_by_scope(
        repo.finance(),
        job.month,
        region=job.region,
        bu=job.bu,
        product_line=job.product_line,
        segment=job.segment,
        metric=job.metric,
    )
    rollup = _build_finance_rollup(finance_df_for_rollup)
    domain_breakdown = _build_domain_breakdown(sweep_results)
    run_store.upsert(
        RunRecord(
            run_id=run_id,
            status="completed",
            message="Full-sweep RCA workflow completed.",
            payload=job.__dict__,
            result={
                "scopes": ensure_serializable(sweep_results),
                "portfolio": ensure_serializable(sweep_summary),
                "rollup": ensure_serializable(rollup),
                "domains": ensure_serializable(domain_breakdown),
                "filters": base_filters,
                "month": job.month,
                "comparison": job.comparison,
            },
        )
    )


def _merge_filters(job: RCAJob, extra_filters: Optional[Dict] = None) -> Dict[str, Optional[str]]:
    filters = {
        "region": job.region,
        "bu": job.bu,
        "product_line": job.product_line,
        "segment": job.segment,
        "metric": job.metric,
    }
    if extra_filters:
        filters.update(extra_filters)
    return filters


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


def _metric_summary(df) -> Dict[str, Dict]:
    if df.empty or "metric" not in df.columns:
        return {}
    summaries: Dict[str, Dict] = {}
    for metric in _unique_non_null(df, "metric"):
        slice_df = df[df["metric"] == metric]
        actual = slice_df["actual"].sum() if "actual" in slice_df else 0
        plan = slice_df["plan"].sum() if "plan" in slice_df else None
        prior = slice_df["prior"].sum() if "prior" in slice_df else None
        plan = None if plan is None or pd.isna(plan) else plan
        prior = None if prior is None or pd.isna(prior) else prior
        summaries[metric] = {
            "actual": actual,
            "plan": plan,
            "prior": prior,
            "variance_to_plan": actual - plan if plan is not None else None,
            "variance_to_prior": actual - prior if prior is not None else None,
        }
    return summaries


def _top_variance_by_dim(df, dim: str, limit: int = TOP_CONTRIBUTORS) -> List[Dict]:
    if df.empty or dim not in df.columns:
        return []
    grouped = (
        df.groupby(dim)
        .agg(
            actual=("actual", "sum"),
            plan=("plan", "sum"),
            prior=("prior", "sum"),
        )
        .reset_index()
    )
    if grouped.empty:
        return []
    grouped = grouped.fillna(0)
    grouped["variance_to_plan"] = grouped["actual"] - grouped["plan"]
    grouped["variance_to_prior"] = grouped["actual"] - grouped["prior"]
    grouped["abs_var_plan"] = grouped["variance_to_plan"].abs()
    ordered = grouped.sort_values("abs_var_plan", ascending=False).head(limit)
    return ordered[[dim, "actual", "plan", "prior", "variance_to_plan", "variance_to_prior"]].to_dict(orient="records")


def _top_variance_by_dim_per_metric(df, dim: str, limit: int = TOP_CONTRIBUTORS) -> Dict[str, List[Dict]]:
    if df.empty or dim not in df.columns or "metric" not in df.columns:
        return {}
    results: Dict[str, List[Dict]] = {}
    for metric in _unique_non_null(df, "metric"):
        metric_df = df[df["metric"] == metric]
        results[metric] = _top_variance_by_dim(metric_df, dim, limit=limit)
    return results


def _build_finance_rollup(finance_df) -> Dict:
    """
    Build overall + region/BU rollups for finance metrics vs plan and prior (year-ago).
    """
    metrics = _metric_summary(finance_df)
    top_regions_by_metric = _top_variance_by_dim_per_metric(finance_df, "region")
    top_bus_by_metric = _top_variance_by_dim_per_metric(finance_df, "bu")

    per_region = {}
    for region in _unique_non_null(finance_df, "region"):
        region_df = finance_df[finance_df["region"] == region]
        per_region[region] = {
            "metrics": _metric_summary(region_df),
            "top_bus_by_metric": _top_variance_by_dim_per_metric(region_df, "bu"),
        }

    per_bu = {}
    for bu in _unique_non_null(finance_df, "bu"):
        bu_df = finance_df[finance_df["bu"] == bu]
        per_bu[bu] = {
            "metrics": _metric_summary(bu_df),
            "top_regions_by_metric": _top_variance_by_dim_per_metric(bu_df, "region"),
        }

    return {
        "overall": {
            "metrics": metrics,
            "top_regions_by_metric": top_regions_by_metric,
            "top_bus_by_metric": top_bus_by_metric,
        },
        "regions": per_region,
        "bus": per_bu,
    }


def _build_domain_breakdown(sweep_results: Dict[str, Dict]) -> Dict:
    """
    Summarize dominant agent domains per region and BU based on sweep syntheses.
    """
    regions: Dict[str, Dict] = {}
    bus: Dict[str, Dict] = {}

    for label, payload in sweep_results.items():
        filters = payload.get("filters") or {}
        synthesis = payload.get("synthesis") or {}
        findings = synthesis.get("findings") or []
        counts = Counter(f.get("domain") for f in findings if f.get("domain"))
        domains = [{"domain": d, "occurrences": c} for d, c in counts.most_common()]
        summary_entry = {
            "summary": synthesis.get("summary"),
            "brief_report": synthesis.get("brief_report"),
            "domains": domains,
        }

        if label.startswith("region:") or filters.get("region"):
            region = label.split(":", 1)[1] if label.startswith("region:") else filters.get("region")
            if region:
                regions[region] = summary_entry

        if label.startswith("bu:") or filters.get("bu"):
            bu_value = label.split(":", 1)[1] if label.startswith("bu:") else filters.get("bu")
            if bu_value:
                bus[bu_value] = summary_entry

    return {"regions": regions, "bus": bus}
