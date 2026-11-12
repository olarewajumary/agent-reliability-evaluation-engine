import pytest

from app.agent.schemas import AgentExecutionResult
from app.evaluation.evaluator import AgentEvaluator
from app.evaluation.schemas import EvaluationCase


@pytest.fixture
def evaluator():
    return AgentEvaluator()


def make_execution_result(
    tool_names: list[str],
    status: str = "completed",
    tool_statuses: list[str] | None = None,
) -> AgentExecutionResult:
    """Build a sample execution result for evaluation tests."""

    if tool_statuses is None:
        tool_statuses = ["success"] * len(tool_names)

    return AgentExecutionResult(
        task_id="12345678-1234-5678-1234-567812345678",
        status=status,
        message="Test execution.",
        tool_results=[
            {
                "result": {
                    "tool_name": tool_name,
                    "status": tool_status,
                },
                "trace": {},
            }
            for tool_name, tool_status in zip(
                tool_names,
                tool_statuses,
            )
        ],
    )


def test_evaluator_passes_correct_execution(evaluator):
    case = EvaluationCase(
        case_id="case_001",
        expected_tool_sequence=["github_search"],
        expected_status="completed",
    )

    result = make_execution_result(["github_search"])

    report = evaluator.evaluate(case, result)

    assert report.passed is True
    assert report.score == 100
    assert report.issues == []


def test_evaluator_detects_unexpected_tool(evaluator):
    case = EvaluationCase(
        case_id="case_002",
        expected_tool_sequence=["github_search"],
        expected_status="completed",
    )

    result = make_execution_result(["slack_search"])

    report = evaluator.evaluate(case, result)

    assert report.tool_selection_correct is False
    assert report.passed is False


def test_evaluator_detects_wrong_execution_order(evaluator):
    case = EvaluationCase(
        case_id="case_003",
        expected_tool_sequence=[
            "github_search",
            "slack_search",
        ],
        expected_status="completed",
    )

    result = make_execution_result(
        ["slack_search", "github_search"]
    )

    report = evaluator.evaluate(case, result)

    assert report.tool_selection_correct is True
    assert report.execution_sequence_correct is False


def test_evaluator_detects_incorrect_task_status(evaluator):
    case = EvaluationCase(
        case_id="case_004",
        expected_tool_sequence=["github_search"],
        expected_status="completed",
    )

    result = make_execution_result(
        ["github_search"],
        status="failed",
    )

    report = evaluator.evaluate(case, result)

    assert report.task_status_correct is False
    assert report.passed is False


def test_evaluator_accepts_approval_as_final_action(evaluator):
    case = EvaluationCase(
        case_id="case_005",
        expected_tool_sequence=["create_ticket"],
        expected_status="requires_approval",
    )

    result = make_execution_result(
        ["create_ticket"],
        status="requires_approval",
        tool_statuses=["requires_approval"],
    )

    report = evaluator.evaluate(case, result)

    assert report.policy_compliant is True
    assert report.passed is True


def test_evaluator_detects_execution_after_approval(evaluator):
    case = EvaluationCase(
        case_id="case_006",
        expected_tool_sequence=[
            "create_ticket",
            "github_search",
        ],
        expected_status="completed",
    )

    result = make_execution_result(
        ["create_ticket", "github_search"],
        tool_statuses=[
            "requires_approval",
            "success",
        ],
    )

    report = evaluator.evaluate(case, result)

    assert report.policy_compliant is False
    assert report.passed is False


def test_evaluator_handles_empty_tool_sequence(evaluator):
    case = EvaluationCase(
        case_id="case_007",
        expected_tool_sequence=[],
        expected_status="completed",
    )

    result = make_execution_result([])

    report = evaluator.evaluate(case, result)

    assert report.passed is True
    assert report.score == 100


def test_evaluator_calculates_partial_score(evaluator):
    case = EvaluationCase(
        case_id="case_008",
        expected_tool_sequence=["github_search"],
        expected_status="completed",
    )

    result = make_execution_result(
        ["github_search"],
        status="failed",
    )

    report = evaluator.evaluate(case, result)

    assert report.score == 75
    assert report.passed is False


def test_evaluator_detects_missing_tool(evaluator):
    case = EvaluationCase(
        case_id="case_009",
        expected_tool_sequence=[
            "github_search",
            "slack_search",
        ],
        expected_status="completed",
    )

    result = make_execution_result(["github_search"])

    report = evaluator.evaluate(case, result)

    assert report.tool_selection_correct is False
    assert report.execution_sequence_correct is False


def test_evaluator_report_contains_case_id(evaluator):
    case = EvaluationCase(
        case_id="case_010",
        expected_tool_sequence=["github_search"],
        expected_status="completed",
    )

    result = make_execution_result(["github_search"])

    report = evaluator.evaluate(case, result)

    assert report.case_id == "case_010"
