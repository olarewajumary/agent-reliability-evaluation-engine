import json

import pytest

from app.agent.schemas import AgentExecutionResult
from app.evaluation.dataset import load_evaluation_dataset
from app.evaluation.evaluator import AgentEvaluator
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import EvaluationCase


def make_result(
    tool_names: list[str],
    status: str = "completed",
    tool_statuses: list[str] | None = None,
) -> AgentExecutionResult:
    """Create a sample execution result for testing."""

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


@pytest.fixture
def runner():
    return EvaluationRunner(AgentEvaluator())


def test_load_evaluation_dataset(tmp_path):
    dataset = [
        {
            "case_id": "case_001",
            "expected_tool_sequence": ["github_search"],
            "expected_status": "completed",
        }
    ]

    dataset_file = tmp_path / "cases.json"
    dataset_file.write_text(
        json.dumps(dataset),
        encoding="utf-8",
    )

    cases = load_evaluation_dataset(dataset_file)

    assert len(cases) == 1
    assert cases[0].case_id == "case_001"


def test_dataset_rejects_non_list_content(tmp_path):
    dataset_file = tmp_path / "cases.json"
    dataset_file.write_text(
        json.dumps({"cases": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_evaluation_dataset(dataset_file)


def test_dataset_rejects_duplicate_case_ids(tmp_path):
    dataset = [
        {
            "case_id": "duplicate",
            "expected_tool_sequence": [],
            "expected_status": "completed",
        },
        {
            "case_id": "duplicate",
            "expected_tool_sequence": [],
            "expected_status": "completed",
        },
    ]

    dataset_file = tmp_path / "cases.json"
    dataset_file.write_text(
        json.dumps(dataset),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_evaluation_dataset(dataset_file)


def test_runner_evaluates_multiple_cases(runner):
    cases = [
        EvaluationCase(
            case_id="case_001",
            expected_tool_sequence=["github_search"],
            expected_status="completed",
        ),
        EvaluationCase(
            case_id="case_002",
            expected_tool_sequence=["github_search"],
            expected_status="completed",
        ),
    ]

    results = {
        "case_001": make_result(
            ["github_search"],
            status="completed",
        ),
        "case_002": make_result(
            ["github_search"],
            status="failed",
        ),
    }

    report = runner.run(cases, results)

    assert report.total_cases == 2
    assert report.passed_cases == 1
    assert report.failed_cases == 1
    assert report.pass_rate == 50
    assert report.average_score == 87.5


def test_runner_counts_failure_categories(runner):
    cases = [
        EvaluationCase(
            case_id="case_001",
            expected_tool_sequence=["github_search"],
            expected_status="completed",
        )
    ]

    results = {
        "case_001": make_result(
            ["slack_search"],
            status="failed",
        )
    }

    report = runner.run(cases, results)

    assert report.failure_counts == {
        "tool_selection": 1,
        "execution_sequence": 1,
        "task_status": 1,
        "policy_compliance": 0,
    }


def test_runner_rejects_missing_execution_results(runner):
    cases = [
        EvaluationCase(
            case_id="case_001",
            expected_tool_sequence=[],
            expected_status="completed",
        )
    ]

    with pytest.raises(ValueError, match="Missing execution results"):
        runner.run(cases, {})


def test_runner_rejects_unexpected_execution_results(runner):
    cases = [
        EvaluationCase(
            case_id="case_001",
            expected_tool_sequence=[],
            expected_status="completed",
        )
    ]

    results = {
        "unknown_case": make_result([])
    }

    with pytest.raises(ValueError, match="Unexpected execution results"):
        runner.run(cases, results)


def test_runner_rejects_duplicate_case_ids(runner):
    case = EvaluationCase(
        case_id="case_001",
        expected_tool_sequence=[],
        expected_status="completed",
    )

    with pytest.raises(ValueError, match="duplicate"):
        runner.run(
            [case, case],
            {"case_001": make_result([])},
        )


def test_runner_handles_empty_dataset(runner):
    report = runner.run([], {})

    assert report.total_cases == 0
    assert report.passed_cases == 0
    assert report.failed_cases == 0
    assert report.pass_rate == 0
    assert report.average_score == 0
    assert report.reports == []


def test_runner_preserves_individual_reports(runner):
    cases = [
        EvaluationCase(
            case_id="case_001",
            expected_tool_sequence=["github_search"],
            expected_status="completed",
        )
    ]

    results = {
        "case_001": make_result(["github_search"])
    }

    report = runner.run(cases, results)

    assert len(report.reports) == 1
    assert report.reports[0].case_id == "case_001"
    assert report.reports[0].passed is True