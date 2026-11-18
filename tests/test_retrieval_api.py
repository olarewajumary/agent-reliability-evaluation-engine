from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_retrieval_endpoint_evaluates_scenario():
    response = client.post(
        "/evaluations/retrieval/run",
        json={
            "k": 5,
            "scenarios": [
                {
                    "case": {
                        "case_id": "api_retrieval_001",
                        "expected_tool_sequence": ["slack_search"],
                        "expected_status": "completed",
                    },
                    "objective": "Find the checkout 502 failure.",
                    "context": {},
                    "tool_requests": [
                        {
                            "tool_name": "slack_search",
                            "arguments": {
                                "query": "502",
                            },
                        }
                    ],
                    "expected_evidence_ids": [
                        "slack:slack-msg-001",
                    ],
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_cases"] == 1
    assert body["passed_cases"] == 1
    assert body["failed_cases"] == 0
    assert body["reports"][0]["recall_at_k"] == 1.0
    assert body["reports"][0]["evidence_coverage"] == 1.0


def test_retrieval_endpoint_rejects_scenario_without_expected_evidence():
    response = client.post(
        "/evaluations/retrieval/run",
        json={
            "scenarios": [
                {
                    "case": {
                        "case_id": "api_retrieval_002",
                        "expected_tool_sequence": ["slack_search"],
                        "expected_status": "completed",
                    },
                    "objective": "Find checkout failures.",
                    "tool_requests": [],
                    "expected_evidence_ids": [],
                }
            ],
        },
    )

    assert response.status_code == 422


def test_retrieval_endpoint_rejects_invalid_k():
    response = client.post(
        "/evaluations/retrieval/run",
        json={
            "k": 0,
            "scenarios": [
                {
                    "case": {
                        "case_id": "api_retrieval_003",
                        "expected_tool_sequence": ["slack_search"],
                        "expected_status": "completed",
                    },
                    "objective": "Find checkout failures.",
                    "tool_requests": [
                        {
                            "tool_name": "slack_search",
                            "arguments": {"query": "checkout"},
                        }
                    ],
                    "expected_evidence_ids": [
                        "slack:slack-msg-001",
                    ],
                }
            ],
        },
    )

    assert response.status_code == 422