from app.agent.schemas import AgentExecutionResult
from app.evaluation.evaluator import AgentEvaluator
from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationCase,
)


class EvaluationRunner:
    """Run evaluations across a collection of agent tasks."""

    def __init__(self, evaluator: AgentEvaluator) -> None:
        self.evaluator = evaluator

    def run(
        self,
        cases: list[EvaluationCase],
        results_by_case_id: dict[str, AgentExecutionResult],
    ) -> BatchEvaluationReport:
        """Evaluate all cases and calculate aggregate metrics."""

        case_ids = [case.case_id for case in cases]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError(
                "Evaluation cases contain duplicate case IDs."
            )

        expected_ids = set(case_ids)
        actual_ids = set(results_by_case_id)

        missing_ids = expected_ids - actual_ids
        unexpected_ids = actual_ids - expected_ids

        errors = []

        if missing_ids:
            errors.append(
                f"Missing execution results for cases: "
                f"{sorted(missing_ids)}"
            )

        if unexpected_ids:
            errors.append(
                f"Unexpected execution results for cases: "
                f"{sorted(unexpected_ids)}"
            )

        if errors:
            raise ValueError(" | ".join(errors))

        reports = [
            self.evaluator.evaluate(
                case,
                results_by_case_id[case.case_id],
            )
            for case in cases
        ]

        total_cases = len(reports)

        passed_cases = sum(
            report.passed for report in reports
        )

        failed_cases = total_cases - passed_cases

        pass_rate = (
            (passed_cases / total_cases) * 100
            if total_cases
            else 0.0
        )

        average_score = (
            sum(report.score for report in reports) / total_cases
            if total_cases
            else 0.0
        )

        failure_counts = {
            "tool_selection": sum(
                not report.tool_selection_correct
                for report in reports
            ),
            "execution_sequence": sum(
                not report.execution_sequence_correct
                for report in reports
            ),
            "task_status": sum(
                not report.task_status_correct
                for report in reports
            ),
            "policy_compliance": sum(
                not report.policy_compliant
                for report in reports
            ),
        }

        return BatchEvaluationReport(
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            pass_rate=pass_rate,
            average_score=average_score,
            failure_counts=failure_counts,
            reports=reports,
        )