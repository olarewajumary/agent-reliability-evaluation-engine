from uuid import uuid4

import pytest

from app.agent.schemas import AgentExecutionResult
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.scenarios import EvaluationScenario


def make_scenario(
    expected_evidence_ids: list[str],
    case_id: str = "retrieval_001",
) -> EvaluationScenario:
    return EvaluationScenario(
        case={
            "case_id": case_id,
            "expected_tool_sequence": ["slack_search"],
            "expected_status": "completed",
        },
        objective="Find the checkout failure evidence.",
        tool_requests=[],
        expected_evidence_ids=expected_evidence_ids,
    )


def make_result(
    tool_results: list[dict],
) -> AgentExecutionResult:
    return AgentExecutionResult(
        task_id=uuid4(),
        status="completed",
        tool_results=tool_results,
        message="Task completed.",
    )


def make_slack_result(
    message_ids: list[str],
) -> dict:
    return {
        "result": {
            "tool_name": "slack_search",
            "status": "success",
            "output": {
                "messages": [
                    {
                        "message_id": message_id,
                        "channel": "engineering",
                        "text": "Simulated message.",
                        "author": "developer_01",
                    }
                    for message_id in message_ids
                ]
            },
        },
        "trace": {},
    }


def make_github_result(
    issue_numbers: list[int],
) -> dict:
    return {
        "result": {
            "tool_name": "github_search",
            "status": "success",
            "output": {
                "issues": [
                    {
                        "issue_number": issue_number,
                        "title": "Simulated issue",
                        "body": "Simulated issue body.",
                        "state": "open",
                    }
                    for issue_number in issue_numbers
                ]
            },
        },
        "trace": {},
    }


def test_retrieval_metrics_for_relevant_results():
    scenario = make_scenario(
        [
            "slack:slack-msg-001",
            "github:142",
        ]
    )

    result = make_result(
        [
            make_slack_result(
                [
                    "slack-msg-002",
                    "slack-msg-001",
                ]
            ),
            make_github_result([142]),
        ]
    )

    report = RetrievalEvaluator().evaluate(
        scenario=scenario,
        result=result,
        k=3,
    )

    assert report.retrieved_evidence_ids == [
        "slack:slack-msg-002",
        "slack:slack-msg-001",
        "github:142",
    ]

    assert report.precision_at_k == pytest.approx(2 / 3)
    assert report.recall_at_k == 1.0
    assert report.reciprocal_rank == 0.5
    assert report.evidence_coverage == 1.0
    assert report.passed is True


def test_retrieval_fails_when_expected_evidence_is_missing():
    scenario = make_scenario(
        ["slack:slack-msg-001"]
    )

    result = make_result(
        [
            make_slack_result(["slack-msg-002"]),
        ]
    )

    report = RetrievalEvaluator().evaluate(
        scenario=scenario,
        result=result,
        k=5,
    )

    assert report.recall_at_k == 0.0
    assert report.evidence_coverage == 0.0
    assert report.reciprocal_rank == 0.0
    assert report.passed is False
    assert any(
        "not retrieved" in issue
        for issue in report.issues
    )


def test_failed_tool_execution_does_not_count_as_retrieval():
    scenario = make_scenario(
        ["slack:slack-msg-001"]
    )

    result = make_result(
        [
            {
                "result": {
                    "tool_name": "slack_search",
                    "status": "failure",
                    "output": {
                        "messages": [
                            {"message_id": "slack-msg-001"}
                        ]
                    },
                },
                "trace": {},
            }
        ]
    )

    report = RetrievalEvaluator().evaluate(
        scenario=scenario,
        result=result,
    )

    assert report.retrieved_evidence_ids == []
    assert report.passed is False
    assert "No evidence was retrieved." in report.issues


def test_duplicate_evidence_is_counted_only_once():
    scenario = make_scenario(
        ["slack:slack-msg-001"]
    )

    result = make_result(
        [
            make_slack_result(["slack-msg-001"]),
            make_slack_result(["slack-msg-001"]),
        ]
    )

    report = RetrievalEvaluator().evaluate(
        scenario=scenario,
        result=result,
        k=2,
    )

    assert report.retrieved_evidence_ids == [
        "slack:slack-msg-001"
    ]

    assert report.precision_at_k == 0.5
    assert report.recall_at_k == 1.0


def test_unknown_tool_outputs_are_not_treated_as_evidence():
    scenario = make_scenario(
        ["slack:slack-msg-001"]
    )

    result = make_result(
        [
            {
                "result": {
                    "tool_name": "unknown_tool",
                    "status": "success",
                    "output": {
                        "message_id": "slack-msg-001",
                    },
                },
                "trace": {},
            }
        ]
    )

    report = RetrievalEvaluator().evaluate(
        scenario=scenario,
        result=result,
    )

    assert report.retrieved_evidence_ids == []
    assert report.passed is False


def test_evaluator_rejects_scenario_without_expected_evidence():
    scenario = make_scenario([])

    result = make_result([])

    with pytest.raises(
        ValueError,
        match="no expected evidence IDs",
    ):
        RetrievalEvaluator().evaluate(
            scenario=scenario,
            result=result,
        )


def test_batch_evaluation_aggregates_metrics():
    evaluator = RetrievalEvaluator()

    first = make_scenario(
        ["slack:slack-msg-001"],
        case_id="case_001",
    )

    second = make_scenario(
        ["slack:slack-msg-003"],
        case_id="case_002",
    )

    results = {
        "case_001": make_result(
            [make_slack_result(["slack-msg-001"])]
        ),
        "case_002": make_result(
            [make_slack_result(["slack-msg-002"])]
        ),
    }

    report = evaluator.evaluate_batch(
        scenarios=[first, second],
        results_by_case_id=results,
        k=5,
    )

    assert report.total_cases == 2
    assert report.passed_cases == 1
    assert report.failed_cases == 1
    assert report.pass_rate == 50.0
    assert report.mean_recall_at_k == 0.5


def test_batch_evaluation_rejects_mismatched_case_ids():
    scenario = make_scenario(
        ["slack:slack-msg-001"]
    )

    with pytest.raises(
        ValueError,
        match="IDs do not match",
    ):
        RetrievalEvaluator().evaluate_batch(
            scenarios=[scenario],
            results_by_case_id={},
        )


def test_batch_evaluation_rejects_duplicate_scenario_ids():
    first = make_scenario(
        ["slack:slack-msg-001"],
        case_id="duplicate",
    )

    second = make_scenario(
        ["slack:slack-msg-002"],
        case_id="duplicate",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate scenario case IDs",
    ):
        RetrievalEvaluator().evaluate_batch(
            scenarios=[first, second],
            results_by_case_id={},
        )


def test_evaluator_rejects_invalid_k():
    scenario = make_scenario(
        ["slack:slack-msg-001"]
    )

    result = make_result([])

    with pytest.raises(
        ValueError,
        match="k must be at least 1",
    ):
        RetrievalEvaluator().evaluate(
            scenario=scenario,
            result=result,
            k=0,
        )