import json
from pathlib import Path

import pytest

from app.evaluation.dataset import (
    load_evaluation_dataset,
    load_evaluation_scenarios,
)

from fastapi.testclient import TestClient

from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = PROJECT_ROOT / "data" / "evaluation_cases.json"
SCENARIOS_PATH = PROJECT_ROOT / "data" / "evaluation_scenarios.json"


def test_evaluation_dataset_contains_25_cases():
    cases = load_evaluation_dataset(CASES_PATH)

    assert len(cases) == 25
    assert len({case.case_id for case in cases}) == 25


def test_scenario_dataset_contains_25_scenarios():
    scenarios = load_evaluation_scenarios(SCENARIOS_PATH)

    assert len(scenarios) == 25
    assert len({
        scenario.case.case_id
        for scenario in scenarios
    }) == 25


def test_scenario_ids_match_evaluation_case_ids():
    cases = load_evaluation_dataset(CASES_PATH)
    scenarios = load_evaluation_scenarios(SCENARIOS_PATH)

    case_ids = {case.case_id for case in cases}
    scenario_ids = {
        scenario.case.case_id
        for scenario in scenarios
    }

    assert case_ids == scenario_ids


def test_scenario_expectations_match_evaluation_dataset():
    cases = load_evaluation_dataset(CASES_PATH)
    scenarios = load_evaluation_scenarios(SCENARIOS_PATH)

    cases_by_id = {
        case.case_id: case
        for case in cases
    }

    for scenario in scenarios:
        expected_case = cases_by_id[scenario.case.case_id]

        assert (
            scenario.case.expected_tool_sequence
            == expected_case.expected_tool_sequence
        )
        assert (
            scenario.case.expected_status
            == expected_case.expected_status
        )


def test_every_scenario_defines_expected_evidence():
    scenarios = load_evaluation_scenarios(SCENARIOS_PATH)

    assert all(
        scenario.expected_evidence_ids
        for scenario in scenarios
    )


def test_scenario_dataset_rejects_duplicate_case_ids(tmp_path):
    scenario = {
        "case": {
            "case_id": "duplicate_case",
            "expected_tool_sequence": ["slack_search"],
            "expected_status": "completed",
        },
        "objective": "Find checkout evidence.",
        "context": {},
        "tool_requests": [
            {
                "tool_name": "slack_search",
                "arguments": {"query": "502"},
            }
        ],
        "expected_evidence_ids": ["slack:slack-msg-001"],
    }

    dataset_path = tmp_path / "duplicate_scenarios.json"
    dataset_path.write_text(
        json.dumps([scenario, scenario]),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="duplicate case IDs",
    ):
        load_evaluation_scenarios(dataset_path)


def test_scenario_dataset_rejects_empty_dataset(tmp_path):
    dataset_path = tmp_path / "empty_scenarios.json"
    dataset_path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        load_evaluation_scenarios(dataset_path)


def test_scenario_dataset_rejects_missing_expected_evidence(tmp_path):
    scenario = {
        "case": {
            "case_id": "missing_evidence",
            "expected_tool_sequence": ["slack_search"],
            "expected_status": "completed",
        },
        "objective": "Find checkout evidence.",
        "context": {},
        "tool_requests": [
            {
                "tool_name": "slack_search",
                "arguments": {"query": "502"},
            }
        ],
        "expected_evidence_ids": [],
    }

    dataset_path = tmp_path / "missing_evidence.json"
    dataset_path.write_text(
        json.dumps([scenario]),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must define at least one expected evidence ID",
    ):
        load_evaluation_scenarios(dataset_path)


def test_scenario_dataset_rejects_non_list_json(tmp_path):
    dataset_path = tmp_path / "invalid_dataset.json"
    dataset_path.write_text(
        json.dumps({"case_id": "not_a_list"}),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must contain a JSON list",
    ):
        load_evaluation_scenarios(dataset_path)


def test_all_25_scenarios_run_through_retrieval_api():
    scenarios = load_evaluation_scenarios(SCENARIOS_PATH)

    client = TestClient(app)

    response = client.post(
        "/evaluations/retrieval/run",
        json={
            "k": 5,
            "scenarios": [
                scenario.model_dump(mode="json")
                for scenario in scenarios
            ],
        },
    )

    assert response.status_code == 200

    report = response.json()

    assert report["total_cases"] == 25
    assert report["passed_cases"] == 19
    assert report["failed_cases"] == 6
    assert report["pass_rate"] == 76
