from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from src.workflows.rca import RCAJob, enqueue_rca, get_rca_status

class RCARequest(BaseModel):
    month: str
    region: Optional[str] = None
    bu: Optional[str] = None
    product_line: Optional[str] = None
    segment: Optional[str] = None
    comparison: str = "plan"  # plan | prior


class RCAResponse(BaseModel):
    run_id: str
    status: str
    message: str
    result: Optional[dict] = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Finance RCA Agent",
        description="Production-oriented multi-agent system for financial root cause analysis.",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/rca", response_model=RCAResponse)
    async def start_rca(request: RCARequest, background_tasks: BackgroundTasks) -> RCAResponse:
        job = RCAJob(**request.model_dump())
        result = enqueue_rca(job, background_tasks)
        return RCAResponse(**result)

    @app.get("/rca/{run_id}", response_model=RCAResponse)
    async def fetch_rca(run_id: str) -> RCAResponse:
        result = get_rca_status(run_id)
        if not result:
            raise HTTPException(status_code=404, detail="run_id not found")
        return RCAResponse(**result)

    return app


app = create_app()
