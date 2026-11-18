
from app.agent.schemas import AgentExecutionResult
from app.evaluation.retrieval_schemas import (
    RetrievalBatchReport,
    RetrievalCaseReport,
)
from app.evaluation.scenarios import EvaluationScenario
from app.tools.schemas import ToolStatus


class RetrievalEvaluator:
    """Evaluate evidence retrieval from actual tool execution results."""

    @staticmethod
    def _extract_evidence_ids(
        result: AgentExecutionResult,
    ) -> list[str]:
        """Extract stable evidence IDs from successful tool outputs."""

        evidence_ids: list[str] = []
        seen: set[str] = set()

        for entry in result.tool_results:
            tool_result = entry.get("result", {})

            if tool_result.get("status") != ToolStatus.SUCCESS.value:
                continue

            tool_name = tool_result.get("tool_name")
            output = tool_result.get("output", {})

            if not isinstance(output, dict):
                continue

            records = []

            if tool_name == "slack_search":
                messages = output.get("messages", [])

                if isinstance(messages, list):
                    records = [
                        (
                            f"slack:{message['message_id']}"
                        )
                        for message in messages
                        if isinstance(message, dict)
                        and isinstance(
                            message.get("message_id"),
                            str,
                        )
                        and message["message_id"].strip()
                    ]

            elif tool_name == "github_search":
                issues = output.get("issues", [])

                if isinstance(issues, list):
                    records = [
                        f"github:{issue['issue_number']}"
                        for issue in issues
                        if isinstance(issue, dict)
                        and isinstance(
                            issue.get("issue_number"),
                            int,
                        )
                        and not isinstance(
                            issue.get("issue_number"),
                            bool,
                        )
                    ]

            for evidence_id in records:
                if evidence_id not in seen:
                    evidence_ids.append(evidence_id)
                    seen.add(evidence_id)

        return evidence_ids

    def evaluate(
        self,
        scenario: EvaluationScenario,
        result: AgentExecutionResult,
        k: int = 10,
    ) -> RetrievalCaseReport:
        """Compare retrieved evidence against expected evidence."""

        if k < 1:
            raise ValueError("k must be at least 1.")

        expected = scenario.expected_evidence_ids

        if not expected:
            raise ValueError(
                f"Scenario '{scenario.case.case_id}' has no "
                "expected evidence IDs."
            )

        retrieved = self._extract_evidence_ids(result)
        retrieved_at_k = retrieved[:k]

        expected_set = set(expected)

        relevant_at_k = [
            evidence_id
            for evidence_id in retrieved_at_k
            if evidence_id in expected_set
        ]

        relevant_anywhere = [
            evidence_id
            for evidence_id in retrieved
            if evidence_id in expected_set
        ]

        precision = len(relevant_at_k) / k

        recall = len(relevant_at_k) / len(expected)

        coverage = len(relevant_anywhere) / len(expected)

        reciprocal_rank = 0.0

        for rank, evidence_id in enumerate(
            retrieved_at_k,
            start=1,
        ):
            if evidence_id in expected_set:
                reciprocal_rank = 1.0 / rank
                break

        issues = []

        missing_at_k = expected_set - set(relevant_at_k)

        if not retrieved:
            issues.append("No evidence was retrieved.")

        if missing_at_k:
            issues.append(
                "Expected evidence missing within top-k: "
                + ", ".join(sorted(missing_at_k))
            )

        missing_everywhere = expected_set - set(relevant_anywhere)

        if missing_everywhere:
            issues.append(
                "Expected evidence was not retrieved: "
                + ", ".join(sorted(missing_everywhere))
            )

        # A case passes when all expected evidence appears within top-k.
        passed = recall == 1.0

        return RetrievalCaseReport(
            case_id=scenario.case.case_id,
            k=k,
            expected_evidence_ids=expected,
            retrieved_evidence_ids=retrieved,
            relevant_retrieved_ids=relevant_at_k,
            precision_at_k=precision,
            recall_at_k=recall,
            reciprocal_rank=reciprocal_rank,
            evidence_coverage=coverage,
            passed=passed,
            issues=issues,
        )

    def evaluate_batch(
        self,
        scenarios: list[EvaluationScenario],
        results_by_case_id: dict[str, AgentExecutionResult],
        k: int = 10,
    ) -> RetrievalBatchReport:
        """Evaluate multiple scenarios and aggregate retrieval metrics."""

        if k < 1:
            raise ValueError("k must be at least 1.")

        scenario_ids = [
            scenario.case.case_id
            for scenario in scenarios
        ]

        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("Duplicate scenario case IDs.")

        if set(scenario_ids) != set(results_by_case_id):
            raise ValueError(
                "Scenario IDs and result IDs do not match."
            )

        reports = [
            self.evaluate(
                scenario=scenario,
                result=results_by_case_id[
                    scenario.case.case_id
                ],
                k=k,
            )
            for scenario in scenarios
        ]

        total = len(reports)
        passed = sum(report.passed for report in reports)
        failed = total - passed

        if total:
            mean_precision = sum(
                report.precision_at_k for report in reports
            ) / total

            mean_recall = sum(
                report.recall_at_k for report in reports
            ) / total

            mean_mrr = sum(
                report.reciprocal_rank for report in reports
            ) / total

            mean_coverage = sum(
                report.evidence_coverage for report in reports
            ) / total

            pass_rate = (passed / total) * 100

        else:
            mean_precision = 0.0
            mean_recall = 0.0
            mean_mrr = 0.0
            mean_coverage = 0.0
            pass_rate = 0.0

        return RetrievalBatchReport(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            pass_rate=pass_rate,
            mean_precision_at_k=mean_precision,
            mean_recall_at_k=mean_recall,
            mean_reciprocal_rank=mean_mrr,
            mean_evidence_coverage=mean_coverage,
            reports=reports,
        )
