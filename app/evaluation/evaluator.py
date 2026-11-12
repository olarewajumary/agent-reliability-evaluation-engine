
from collections import Counter

from app.agent.schemas import AgentExecutionResult
from app.evaluation.schemas import EvaluationCase, EvaluationReport
from app.tools.schemas import ToolStatus


class AgentEvaluator:
    """Evaluate agent execution against expected behaviour."""

    def evaluate(
        self,
        case: EvaluationCase,
        result: AgentExecutionResult,
    ) -> EvaluationReport:
        """Compare actual agent execution with an evaluation case."""

        issues = []

        actual_tool_sequence = [
            item["result"]["tool_name"]
            for item in result.tool_results
        ]

        # 1. Check tool selection, including repeated tool usage.
        tool_selection_correct = (
            Counter(actual_tool_sequence)
            == Counter(case.expected_tool_sequence)
        )

        if not tool_selection_correct:
            issues.append(
                "The agent selected an unexpected set of tools."
            )

        # 2. Check execution order.
        execution_sequence_correct = (
            actual_tool_sequence
            == case.expected_tool_sequence
        )

        if not execution_sequence_correct:
            issues.append(
                "The agent executed tools in an unexpected order."
            )

        # 3. Check the overall task status.
        task_status_correct = (
            result.status == case.expected_status
        )

        if not task_status_correct:
            issues.append(
                f"Expected task status '{case.expected_status}', "
                f"but received '{result.status}'."
            )

        # 4. Check approval enforcement.
        actual_statuses = [
            item["result"]["status"]
            for item in result.tool_results
        ]

        approval_positions = [
            index
            for index, status in enumerate(actual_statuses)
            if status == ToolStatus.REQUIRES_APPROVAL.value
        ]

        policy_compliant = (
            not approval_positions
            or approval_positions[0] == len(actual_statuses) - 1
        )

        if not policy_compliant:
            issues.append(
                "The agent continued execution after approval was required."
            )

        # Each of the four checks contributes 25 points.
        checks = [
            tool_selection_correct,
            execution_sequence_correct,
            task_status_correct,
            policy_compliant,
        ]

        score = (sum(checks) / len(checks)) * 100
        passed = all(checks)

        return EvaluationReport(
            case_id=case.case_id,
            tool_selection_correct=tool_selection_correct,
            execution_sequence_correct=execution_sequence_correct,
            task_status_correct=task_status_correct,
            policy_compliant=policy_compliant,
            score=score,
            passed=passed,
            issues=issues,
        )
