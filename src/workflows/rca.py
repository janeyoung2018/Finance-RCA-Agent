"""
Stubbed RCA workflow orchestrator with simulated background progression.

Replace the simulated run with LangGraph/LangChain orchestration. The stub
creates a run record, then updates status over time in the background.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

from src.agents.demand import DemandAgent
from src.agents.finance import FinanceVarianceAgent
from src.agents.fx import FXAgent
from src.agents.supply import SupplyAgent
from src.agents.synthesis import SynthesisAgent
from src.agents.shipments import ShipmentsAgent
from src.agents.events import EventsAgent
from src.memory.run_store import RunRecord, run_store
from src.tools.data_loader import DataRepository
from src.tools.normalize import ensure_serializable

@dataclass
class RCAJob:
    month: str
    region: Optional[str] = None
    bu: Optional[str] = None
    product_line: Optional[str] = None
    segment: Optional[str] = None
    comparison: str = "plan"


def run_rca(job: RCAJob) -> dict:
    """Create a run record and queue simulated execution."""
    run_id = f"rca-{job.month.replace('-', '')}"
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
        finance_agent = FinanceVarianceAgent()
        demand_agent = DemandAgent()
        supply_agent = SupplyAgent()
        shipments_agent = ShipmentsAgent()
        fx_agent = FXAgent()
        events_agent = EventsAgent()
        synthesis_agent = SynthesisAgent()

        # Finance analysis
        finance_res = finance_agent.analyze(
            repo.finance(),
            job.month,
            comparison=job.comparison,
            region=job.region,
            bu=job.bu,
            product_line=job.product_line,
            segment=job.segment,
        )
        finance_serialized = ensure_serializable(finance_res)
        run_store.upsert(
            RunRecord(
                run_id=run_id,
                status="finance_completed",
                message="Finance analysis completed.",
                payload=job.__dict__,
                result={"finance": finance_serialized},
            )
        )

        # Demand, Supply, FX
        demand_res = demand_agent.analyze(
            repo.orders(),
            job.month,
            region=job.region,
            bu=job.bu,
            product_line=job.product_line,
            segment=job.segment,
        )
        supply_res = supply_agent.analyze(
            repo.supply(),
            job.month,
            region=job.region,
            bu=job.bu,
            product_line=job.product_line,
        )
        shipments_res = shipments_agent.analyze(
            repo.shipments(),
            job.month,
            region=job.region,
            bu=job.bu,
            product_line=job.product_line,
        )
        fx_res = fx_agent.analyze(repo.fx(), job.month, region=job.region)
        events_res = events_agent.analyze(
            repo.events(),
            job.month,
            region=job.region,
            bu=job.bu,
            product_line=job.product_line,
            segment=job.segment,
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
                message="Aggregating findings.",
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

        synthesis = synthesis_agent.synthesize(finance_serialized, demand_serialized, supply_serialized, shipments_serialized, fx_serialized, events_serialized)
        synthesis_serialized = ensure_serializable(synthesis)

        run_store.upsert(
            RunRecord(
                run_id=run_id,
                status="completed",
                message="RCA workflow completed.",
                payload=job.__dict__,
                result={
                    "finance": finance_serialized,
                    "demand": demand_serialized,
                    "supply": supply_serialized,
                    "shipments": shipments_serialized,
                    "fx": fx_serialized,
                    "events": events_serialized,
                    "synthesis": synthesis_serialized,
                },
            )
        )
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
