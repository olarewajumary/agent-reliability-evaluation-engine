from unittest.mock import Mock

import pytest

from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationServiceResult,
)
from app.evaluation.service import EvaluationService
from app.storage.database import SQLiteDatabase
from app.storage.repository import EvaluationHistoryRepository


@pytest.fixture
def batch_report():
    return BatchEvaluationReport(
        total_cases=2,
        passed_cases=1,
        failed_cases=1,
        pass_rate=50.0,
        average_score=75.0,
        failure_counts={
            "tool_selection": 1,
            "execution_sequence": 1,
        },
        reports=[],
    )


@pytest.fixture
def service(tmp_path, batch_report):
    database = SQLiteDatabase(
        tmp_path / "evaluation_history.db"
    )
    repository = EvaluationHistoryRepository(database)

    runner = Mock(spec=EvaluationRunner)
    runner.run.return_value = batch_report

    return EvaluationService(
        runner=runner,
        repository=repository,
    ), repository, runner


def test_run_returns_evaluation_report_and_run_id(service, batch_report):
    evaluation_service, repository, runner = service

    result = evaluation_service.run(
        cases=[],
        results_by_case_id={},
    )

    assert isinstance(result, EvaluationServiceResult)
    assert result.run_id
    assert result.report == batch_report

    runner.run.assert_called_once_with(
        cases=[],
        results_by_case_id={},
    )

    stored_run = repository.get(result.run_id)

    assert stored_run is not None
    assert stored_run.total_cases == 2
    assert stored_run.pass_rate == 50.0


def test_run_persists_each_evaluation_as_a_separate_run(service):
    evaluation_service, repository, runner = service

    first_result = evaluation_service.run([], {})
    second_result = evaluation_service.run([], {})

    assert first_result.run_id != second_result.run_id
    assert len(repository.list_runs()) == 2
    assert runner.run.call_count == 2


def test_failed_evaluation_is_not_saved(service):
    evaluation_service, repository, runner = service

    runner.run.side_effect = RuntimeError("Evaluation failed")

    with pytest.raises(RuntimeError, match="Evaluation failed"):
        evaluation_service.run([], {})

    assert repository.list_runs() == []