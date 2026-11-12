
import sqlite3
import time

import pytest

from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationReport,
)
from app.storage.database import SQLiteDatabase
from app.storage.repository import EvaluationHistoryRepository


@pytest.fixture
def repository(tmp_path):
    database = SQLiteDatabase(
        tmp_path / "evaluation_history.db"
    )
    return EvaluationHistoryRepository(database)


def make_batch_report() -> BatchEvaluationReport:
    reports = [
        EvaluationReport(
            case_id="case_001",
            tool_selection_correct=True,
            execution_sequence_correct=True,
            task_status_correct=True,
            policy_compliant=True,
            score=100,
            passed=True,
            issues=[],
        ),
        EvaluationReport(
            case_id="case_002",
            tool_selection_correct=False,
            execution_sequence_correct=False,
            task_status_correct=True,
            policy_compliant=True,
            score=50,
            passed=False,
            issues=[
                "The agent selected an unexpected set of tools.",
                "The agent executed tools in an unexpected order.",
            ],
        ),
    ]

    return BatchEvaluationReport(
        total_cases=2,
        passed_cases=1,
        failed_cases=1,
        pass_rate=50.0,
        average_score=75.0,
        failure_counts={
            "tool_selection": 1,
            "execution_sequence": 1,
            "task_status": 0,
            "policy_compliance": 0,
        },
        reports=reports,
    )


def test_save_returns_unique_run_id(repository):
    report = make_batch_report()

    first_id = repository.save(report)
    second_id = repository.save(report)

    assert first_id != second_id


def test_save_and_retrieve_evaluation_run(repository):
    report = make_batch_report()

    run_id = repository.save(report)
    stored = repository.get(run_id)

    assert stored is not None
    assert stored.run_id == run_id
    assert stored.total_cases == 2
    assert stored.passed_cases == 1
    assert stored.failed_cases == 1
    assert stored.pass_rate == 50.0
    assert stored.average_score == 75.0


def test_retrieved_run_preserves_individual_case_results(repository):
    report = make_batch_report()

    run_id = repository.save(report)
    stored = repository.get(run_id)

    assert stored is not None
    assert len(stored.reports) == 2

    failed_case = stored.reports[1]

    assert failed_case.case_id == "case_002"
    assert failed_case.passed is False
    assert failed_case.score == 50
    assert len(failed_case.issues) == 2


def test_retrieved_run_preserves_failure_counts(repository):
    run_id = repository.save(make_batch_report())

    stored = repository.get(run_id)

    assert stored is not None
    assert stored.failure_counts == {
        "tool_selection": 1,
        "execution_sequence": 1,
        "task_status": 0,
        "policy_compliance": 0,
    }


def test_get_returns_none_for_unknown_run(repository):
    stored = repository.get("unknown-run-id")

    assert stored is None


def test_list_runs_returns_saved_runs(repository):
    first_id = repository.save(make_batch_report())
    second_id = repository.save(make_batch_report())

    runs = repository.list_runs()

    assert len(runs) == 2
    assert {run.run_id for run in runs} == {
        first_id,
        second_id,
    }


def test_list_runs_returns_newest_first(repository):
    first_id = repository.save(make_batch_report())

    time.sleep(0.002)

    second_id = repository.save(make_batch_report())

    runs = repository.list_runs()

    assert runs[0].run_id == second_id
    assert runs[1].run_id == first_id


def test_list_runs_supports_pagination(repository):
    for _ in range(3):
        repository.save(make_batch_report())

    first_page = repository.list_runs(limit=2, offset=0)
    second_page = repository.list_runs(limit=2, offset=2)

    assert len(first_page) == 2
    assert len(second_page) == 1


def test_list_runs_handles_empty_history(repository):
    runs = repository.list_runs()

    assert runs == []


def test_list_runs_rejects_invalid_limit(repository):
    with pytest.raises(ValueError, match="Limit"):
        repository.list_runs(limit=0)

    with pytest.raises(ValueError, match="Limit"):
        repository.list_runs(limit=101)


def test_list_runs_rejects_negative_offset(repository):
    with pytest.raises(ValueError, match="Offset"):
        repository.list_runs(offset=-1)


def test_database_initialization_is_idempotent(tmp_path):
    database_path = tmp_path / "history.db"

    SQLiteDatabase(database_path)
    SQLiteDatabase(database_path)

    with sqlite3.connect(database_path) as connection:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    table_names = {row[0] for row in tables}

    assert "evaluation_runs" in table_names
    assert "evaluation_case_results" in table_names


def test_failed_save_rolls_back_entire_transaction(repository):
    report = make_batch_report()

    duplicate_report = BatchEvaluationReport(
        total_cases=2,
        passed_cases=1,
        failed_cases=1,
        pass_rate=50.0,
        average_score=75.0,
        failure_counts={},
        reports=[
            report.reports[0],
            report.reports[0],
        ],
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository.save(duplicate_report)

    assert repository.list_runs() == []


def test_history_survives_repository_recreation(tmp_path):
    database_path = tmp_path / "persistent_history.db"

    first_database = SQLiteDatabase(database_path)
    first_repository = EvaluationHistoryRepository(first_database)

    run_id = first_repository.save(make_batch_report())

    second_database = SQLiteDatabase(database_path)
    second_repository = EvaluationHistoryRepository(second_database)

    stored = second_repository.get(run_id)

    assert stored is not None
    assert stored.run_id == run_id
    assert stored.total_cases == 2
