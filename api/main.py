from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.security import rate_limiter, require_api_key
from observability.telemetry import init_telemetry
from src.llm.reasoning import LLMReasoner
from src.memory.run_store import run_store
from src.workflows.rca import RCAJob, enqueue_rca, get_rca_status, list_rca_runs

class RCARequest(BaseModel):
    month: str
    region: Optional[str] = None
    bu: Optional[str] = None
    product_line: Optional[str] = None
    segment: Optional[str] = None
    metric: Optional[str] = None
    comparison: str = "all"  # plan | prior | all
    full_sweep: bool = False


class RCAResponse(BaseModel):
    run_id: str
    status: str
    message: str
    payload: Optional[dict] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    result: Optional[dict] = None


class RCAListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[RCAResponse]


class LLMQueryRequest(BaseModel):
    run_id: str
    question: str
    scope: Optional[str] = None
    compare_run_id: Optional[str] = None


class LLMQueryResponse(BaseModel):
    run_id: str
    question: str
    answer: str
    sources: list[str]
    warnings: list[str] = []
    llm_used: bool = False
    rationale: list[str] = []
    next_questions: list[str] = []
    evidence_refs: list[str] = []
    confidence: Optional[float] = None


class LLMChallengeRequest(BaseModel):
    run_id: str
    scope: Optional[str] = None


class LLMChallengeResponse(BaseModel):
    run_id: str
    answer: str
    sources: list[str]
    warnings: list[str] = []
    llm_used: bool = False
    rationale: list[str] = []
    next_questions: list[str] = []
    evidence_refs: list[str] = []


def create_app() -> FastAPI:
    app = FastAPI(
        title="Finance RCA Agent",
        description="Production-oriented multi-agent system for financial root cause analysis.",
        version="0.1.0",
    )
    security_dependencies = [Depends(require_api_key), Depends(rate_limiter)]

    # Allow local frontend/dev origins; adjust in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_telemetry()
    reasoner = LLMReasoner()

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/rca", response_model=RCAResponse, dependencies=security_dependencies)
    async def start_rca(request: RCARequest, background_tasks: BackgroundTasks) -> RCAResponse:
        job = RCAJob(**request.model_dump())
        try:
            result = enqueue_rca(job, background_tasks)
        except RuntimeError as exc:
            raise HTTPException(status_code=429, detail=str(exc))
        return RCAResponse(**result)

    @app.get("/rca", response_model=RCAListResponse, dependencies=security_dependencies)
    async def list_runs(
        status: Optional[str] = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)
    ) -> RCAListResponse:
        data = list_rca_runs(limit=limit, offset=offset, status=status)
        return RCAListResponse(**data)

    @app.get("/rca/{run_id}", response_model=RCAResponse, dependencies=security_dependencies)
    async def fetch_rca(run_id: str) -> RCAResponse:
        result = get_rca_status(run_id)
        if not result:
            raise HTTPException(status_code=404, detail="run_id not found")
        return RCAResponse(**result)

    @app.post("/llm/query", response_model=LLMQueryResponse, dependencies=security_dependencies)
    async def llm_query(request: LLMQueryRequest) -> LLMQueryResponse:
        record = run_store.get(request.run_id)
        if not record:
            raise HTTPException(status_code=404, detail="run_id not found")
        compare_record = None
        if request.compare_run_id:
            compare_record = run_store.get(request.compare_run_id)
            if not compare_record:
                raise HTTPException(status_code=404, detail="compare_run_id not found")
        try:
            result = reasoner.answer(record, request.question, scope=request.scope, compare_record=compare_record)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return LLMQueryResponse(question=request.question, **result)

    @app.post("/llm/challenge", response_model=LLMChallengeResponse, dependencies=security_dependencies)
    async def llm_challenge(request: LLMChallengeRequest) -> LLMChallengeResponse:
        record = run_store.get(request.run_id)
        if not record:
            raise HTTPException(status_code=404, detail="run_id not found")
        try:
            result = reasoner.challenge(record, scope=request.scope)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return LLMChallengeResponse(**result)

    return app


app = create_app()
