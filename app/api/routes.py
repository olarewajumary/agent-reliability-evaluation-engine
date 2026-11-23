from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agent.orchestrator import AgentOrchestrator
from app.agent.planner import PlanningError
from app.agent.schemas import AgentExecutionResult, AgentTask, AgentTaskRequest
from app.api.dependencies import get_agent_orchestrator

from app.api.dependencies import (
    get_evaluation_repository,
    get_evaluation_service,
    get_retrieval_evaluator,
    get_scenario_runner,
)
from app.api.schemas import (
    EvaluationRunRequest,
    RetrievalEvaluationRunRequest,
    ScenarioEvaluationRunRequest,
)
from app.evaluation.analysis import FailureAnalyzer
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.retrieval_schemas import RetrievalBatchReport
from app.evaluation.scenario_runner import ScenarioRunner
from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationServiceResult,
    FailureAnalysisReport,
)
from app.evaluation.service import EvaluationService
from app.monitoring.diagnostics import (
    AgentReliabilityDiagnostics,
    RunDiagnosticsReport,
)
from app.storage.repository import EvaluationHistoryRepository
from app.storage.schemas import (
    StoredEvaluationRun,
    StoredExecutionTrace,
)


router = APIRouter(
    prefix="/evaluations",
    tags=["Evaluations"],
)


@router.post(
    "/run",
    response_model=EvaluationServiceResult,
    status_code=201,
)
def run_evaluation(
    request: EvaluationRunRequest,
    service: Annotated[
        EvaluationService,
        Depends(get_evaluation_service),
    ],
):
    """Evaluate agent executions and persist the results."""

    try:
        return service.run(
            cases=request.cases,
            results_by_case_id=request.results_by_case_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[StoredEvaluationRun],
)
def list_evaluation_runs(
    repository: Annotated[
        EvaluationHistoryRepository,
        Depends(get_evaluation_repository),
    ],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return historical evaluation runs."""

    return repository.list_runs(
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{run_id}",
    response_model=StoredEvaluationRun,
)
def get_evaluation_run(
    run_id: str,
    repository: Annotated[
        EvaluationHistoryRepository,
        Depends(get_evaluation_repository),
    ],
):
    """Retrieve a specific evaluation run."""

    run = repository.get(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found.",
        )

    return run


@router.get(
    "/{run_id}/analysis",
    response_model=FailureAnalysisReport,
)
def analyze_evaluation_run(
    run_id: str,
    repository: Annotated[
        EvaluationHistoryRepository,
        Depends(get_evaluation_repository),
    ],
):
    """Analyze failures from a previously stored evaluation run."""

    stored_run = repository.get(run_id)

    if stored_run is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found.",
        )

    batch_report = BatchEvaluationReport(
        total_cases=stored_run.total_cases,
        passed_cases=stored_run.passed_cases,
        failed_cases=stored_run.failed_cases,
        pass_rate=stored_run.pass_rate,
        average_score=stored_run.average_score,
        failure_counts=stored_run.failure_counts,
        reports=stored_run.reports,
    )

    return FailureAnalyzer().analyze(batch_report)


@router.post(
    "/scenarios/run",
    response_model=EvaluationServiceResult,
    status_code=201,
)
def run_scenario_evaluation(
    request: ScenarioEvaluationRunRequest,
    service: Annotated[
        EvaluationService,
        Depends(get_evaluation_service),
    ],
    scenario_runner: Annotated[
        ScenarioRunner,
        Depends(get_scenario_runner),
    ],
):
    """Execute scenarios, evaluate results, and persist the report."""

    try:
        results_by_case_id = scenario_runner.run(
            request.scenarios
        )

        cases = [
            scenario.case
            for scenario in request.scenarios
        ]

        return service.run(
            cases=cases,
            results_by_case_id=results_by_case_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post(
    "/retrieval/run",
    response_model=RetrievalBatchReport,
)
def run_retrieval_evaluation(
    request: RetrievalEvaluationRunRequest,
    scenario_runner: Annotated[
        ScenarioRunner,
        Depends(get_scenario_runner),
    ],
    evaluator: Annotated[
        RetrievalEvaluator,
        Depends(get_retrieval_evaluator),
    ],
):
    """Execute scenarios and evaluate their retrieved evidence."""

    try:
        results_by_case_id = scenario_runner.run(
            request.scenarios
        )

        return evaluator.evaluate_batch(
            scenarios=request.scenarios,
            results_by_case_id=results_by_case_id,
            k=request.k,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get(
    "/{run_id}/traces",
    response_model=list[StoredExecutionTrace],
)
def list_execution_traces(
    run_id: str,
    repository: Annotated[
        EvaluationHistoryRepository,
        Depends(get_evaluation_repository),
    ],
    case_id: str | None = Query(default=None),
):
    """Retrieve persisted execution traces for an evaluation run."""

    run = repository.get(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found.",
        )

    return repository.list_traces(
        run_id=run_id,
        case_id=case_id,
    )


@router.get(
    "/{run_id}/diagnostics",
    response_model=RunDiagnosticsReport,
)
def get_evaluation_diagnostics(
    run_id: str,
    slow_threshold_ms: float = Query(default=1000.0, gt=0),
    repository: EvaluationHistoryRepository = Depends(
        get_evaluation_repository
    ),
):
    """Analyze execution reliability for a stored evaluation run."""

    run = repository.get(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found.",
        )

    traces = repository.list_traces(run_id)

    return AgentReliabilityDiagnostics().analyze(
        run_id=run_id,
        traces=traces,
        slow_threshold_ms=slow_threshold_ms,
    )


@router.post(
    "/agent/run",
    response_model=AgentExecutionResult,
)
def run_agent_task(
    request: AgentTaskRequest,
    orchestrator: Annotated[
        AgentOrchestrator,
        Depends(get_agent_orchestrator),
    ],
):
    """Plan and execute an agent task using the configured LLM."""

    task = AgentTask(
        objective=request.objective,
        context=request.context,
    )

    try:
        return orchestrator.execute(task)

    except PlanningError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc