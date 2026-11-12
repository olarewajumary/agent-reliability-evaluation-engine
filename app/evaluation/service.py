from app.agent.schemas import AgentExecutionResult
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationCase,
    EvaluationServiceResult,
)
from app.monitoring.schemas import ExecutionTrace
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
        """Evaluate executions and persist reports with their traces."""

        report: BatchEvaluationReport = self.runner.run(
            cases=cases,
            results_by_case_id=results_by_case_id,
        )

        traces_by_case_id: dict[str, list[ExecutionTrace]] = {}

        for case_id, result in results_by_case_id.items():
            case_traces = []

            for tool_entry in result.tool_results:
                if not isinstance(tool_entry, dict):
                    continue

                trace_data = tool_entry.get("trace")

                if trace_data is None:
                    continue

                trace = ExecutionTrace.model_validate(trace_data)
                case_traces.append(trace)

            traces_by_case_id[case_id] = case_traces

        run_id = self.repository.save(
            report,
            traces_by_case_id=traces_by_case_id,
        )

        return EvaluationServiceResult(
            run_id=run_id,
            report=report,
        )