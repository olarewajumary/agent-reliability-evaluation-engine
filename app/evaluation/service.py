from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationCase,
    EvaluationServiceResult,
)
from app.agent.schemas import AgentExecutionResult
from app.storage.repository import EvaluationHistoryRepository


class EvaluationService:
    """Coordinate evaluation and persistent storage."""

    def __init__(
        self,
        runner: EvaluationRunner,
        repository: EvaluationHistoryRepository,
    ) -> None:
        self.runner = runner
        self.repository = repository

    def run(
        self,
        cases: list[EvaluationCase],
        results_by_case_id: dict[str, AgentExecutionResult],
    ) -> EvaluationServiceResult:
        """Evaluate agent executions and persist the resulting report."""

        report: BatchEvaluationReport = self.runner.run(
            cases=cases,
            results_by_case_id=results_by_case_id,
        )

        run_id = self.repository.save(report)

        return EvaluationServiceResult(
            run_id=run_id,
            report=report,
        )