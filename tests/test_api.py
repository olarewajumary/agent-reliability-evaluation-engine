import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_evaluation_repository
from app.main import app
from app.storage.database import SQLiteDatabase
from app.storage.repository import EvaluationHistoryRepository


@pytest.fixture
def repository(tmp_path):
    database = SQLiteDatabase(
        tmp_path / "api_test_history.db"
    )
    return EvaluationHistoryRepository(database)


@pytest.fixture
def client(repository):
    app.dependency_overrides[get_evaluation_repository] = (
        lambda: repository
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def valid_evaluation_payload():
    return {
        "cases": [
            {
                "case_id": "case_001",
                "expected_tool_sequence": [],
                "expected_status": "completed",
            }
        ],
        "results_by_case_id": {
            "case_001": {
                "task_id": "12345678-1234-5678-1234-567812345678",
                "status": "completed",
                "tool_results": [],
                "message": "Task completed without requiring tools.",
            }
        },
    }


def test_run_evaluation_endpoint_persists_results(client, repository):
    response = client.post(
        "/evaluations/run",
        json=valid_evaluation_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["run_id"]
    assert data["report"]["total_cases"] == 1
    assert data["report"]["passed_cases"] == 1

    stored_run = repository.get(data["run_id"])

    assert stored_run is not None
    assert stored_run.total_cases == 1


def test_list_evaluation_runs_endpoint(client):
    client.post(
        "/evaluations/run",
        json=valid_evaluation_payload(),
    )

    response = client.get("/evaluations")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_evaluation_runs_supports_pagination(client):
    client.post(
        "/evaluations/run",
        json=valid_evaluation_payload(),
    )
    client.post(
        "/evaluations/run",
        json=valid_evaluation_payload(),
    )

    response = client.get("/evaluations?limit=1&offset=0")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_evaluation_run_endpoint(client):
    create_response = client.post(
        "/evaluations/run",
        json=valid_evaluation_payload(),
    )

    run_id = create_response.json()["run_id"]

    response = client.get(f"/evaluations/{run_id}")

    assert response.status_code == 200
    assert response.json()["run_id"] == run_id
    assert response.json()["total_cases"] == 1


def test_get_unknown_evaluation_run_returns_404(client):
    response = client.get(
        "/evaluations/unknown-run-id"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation run not found."


def test_analyze_evaluation_run_endpoint(client):
    create_response = client.post(
        "/evaluations/run",
        json=valid_evaluation_payload(),
    )

    run_id = create_response.json()["run_id"]

    response = client.get(
        f"/evaluations/{run_id}/analysis"
    )

    assert response.status_code == 200
    assert response.json()["total_cases"] == 1


def test_analyze_unknown_run_returns_404(client):
    response = client.get(
        "/evaluations/unknown-run-id/analysis"
    )

    assert response.status_code == 404


def test_invalid_evaluation_payload_returns_422(client):
    response = client.post(
        "/evaluations/run",
        json={
            "cases": [],
            "results_by_case_id": {},
            "unexpected_field": "not allowed",
        },
    )

    assert response.status_code == 422


def test_invalid_pagination_limit_returns_422(client):
    response = client.get("/evaluations?limit=500")

    assert response.status_code == 422