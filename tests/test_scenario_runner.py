
import pytest

from app.evaluation.scenario_runner import ScenarioRunner
from app.evaluation.scenarios import EvaluationScenario
from app.api.dependencies import get_scenario_runner
from app.tools.schemas import ToolRequest


@pytest.fixture
def scenario_runner() -> ScenarioRunner:
    return get_scenario_runner()


def test_scenario_runner_executes_slack_search(
    scenario_runner: ScenarioRunner,
):
    scenario = EvaluationScenario(
        case={
            "case_id": "scenario_001",
            "expected_tool_sequence": ["slack_search"],
            "expected_status": "completed",
        },
        objective="Find reports of checkout failures.",
        context={"team": "engineering"},
        tool_requests=[
            ToolRequest(
                tool_name="slack_search",
                arguments={"query": "checkout"},
            )
        ],
    )

    results = scenario_runner.run([scenario])

    result = results["scenario_001"]

    assert result.status == "completed"
    assert len(result.tool_results) == 1

    tool_result = result.tool_results[0]["result"]

    assert tool_result["tool_name"] == "slack_search"
    assert tool_result["status"] == "success"
    assert tool_result["output"]["count"] > 0


def test_scenario_runner_stops_when_approval_is_required(
    scenario_runner: ScenarioRunner,
):
    scenario = EvaluationScenario(
        case={
            "case_id": "scenario_002",
            "expected_tool_sequence": [
                "create_ticket",
                "github_search",
            ],
            "expected_status": "requires_approval",
        },
        objective="Create a ticket and then search GitHub.",
        tool_requests=[
            ToolRequest(
                tool_name="create_ticket",
                arguments={
                    "title": "Checkout failure",
                    "description": "Investigate checkout errors.",
                },
            ),
            ToolRequest(
                tool_name="github_search",
                arguments={"query": "checkout"},
            ),
        ],
    )

    results = scenario_runner.run([scenario])

    result = results["scenario_002"]

    assert result.status == "requires_approval"

    # GitHub search must not execute after approval is requested.
    assert len(result.tool_results) == 1

    assert (
        result.tool_results[0]["result"]["status"]
        == "requires_approval"
    )


def test_scenario_runner_rejects_duplicate_case_ids(
    scenario_runner: ScenarioRunner,
):
    scenario = EvaluationScenario(
        case={
            "case_id": "duplicate",
            "expected_tool_sequence": [],
            "expected_status": "completed",
        },
        objective="Test duplicate case IDs.",
    )

    with pytest.raises(
        ValueError,
        match="duplicate case IDs",
    ):
        scenario_runner.run([scenario, scenario])


def test_scenario_runner_returns_empty_results_for_empty_input(
    scenario_runner: ScenarioRunner,
):
    assert scenario_runner.run([]) == {}
