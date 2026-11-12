from datetime import datetime, timezone
from uuid import uuid4

from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationReport,
)
from app.monitoring.schemas import ExecutionTrace
from app.storage.database import SQLiteDatabase
from app.storage.repository import EvaluationHistoryRepository
from app.tools.schemas import ToolStatus


def create_report() -> BatchEvaluationReport:
    return BatchEvaluationReport(
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        pass_rate=1.0,
        average_score=100.0,
        failure_counts={},
        reports=[
            EvaluationReport(
                case_id="case_001",
                tool_selection_correct=True,
                execution_sequence_correct=True,
                task_status_correct=True,
                policy_compliant=True,
                score=100.0,
                passed=True,
                issues=[],
            )
        ],
    )


def create_trace(tool_name: str = "github_search") -> ExecutionTrace:
    now = datetime.now(timezone.utc)

    return ExecutionTrace(
        execution_id=uuid4(),
        tool_name=tool_name,
        status=ToolStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        duration_ms=12.5,
        arguments={"query": "checkout"},
        output={"count": 2},
        policy_decision="allow",
        policy_reason="Searching repository issues is permitted.",
    )


def test_repository_persists_execution_traces(tmp_path):
    database = SQLiteDatabase(tmp_path / "traces.db")
    repository = EvaluationHistoryRepository(database)

    trace = create_trace()

    run_id = repository.save(
        create_report(),
        traces_by_case_id={"case_001": [trace]},
    )

    stored_traces = repository.list_traces(run_id)

    assert len(stored_traces) == 1

    stored = stored_traces[0]

    assert stored.trace_id == trace.trace_id
    assert stored.run_id == run_id
    assert stored.case_id == "case_001"
    assert stored.tool_name == "github_search"
    assert stored.arguments == {"query": "checkout"}
    assert stored.output == {"count": 2}
    assert stored.policy_decision == "allow"
    assert stored.duration_ms == 12.5


def test_repository_filters_traces_by_case(tmp_path):
    database = SQLiteDatabase(tmp_path / "traces.db")
    repository = EvaluationHistoryRepository(database)

    report = BatchEvaluationReport(
        total_cases=2,
        passed_cases=2,
        failed_cases=0,
        pass_rate=1.0,
        average_score=100.0,
        failure_counts={},
        reports=[
            EvaluationReport(
                case_id=case_id,
                tool_selection_correct=True,
                execution_sequence_correct=True,
                task_status_correct=True,
                policy_compliant=True,
                score=100.0,
                passed=True,
                issues=[],
            )
            for case_id in ["case_001", "case_002"]
        ],
    )

    run_id = repository.save(
        report,
        traces_by_case_id={
            "case_001": [create_trace("slack_search")],
            "case_002": [create_trace("github_search")],
        },
    )

    case_one_traces = repository.list_traces(
        run_id,
        case_id="case_001",
    )

    assert len(case_one_traces) == 1
    assert case_one_traces[0].tool_name == "slack_search"

    all_traces = repository.list_traces(run_id)

    assert len(all_traces) == 2


def test_repository_returns_empty_list_when_run_has_no_traces(tmp_path):
    database = SQLiteDatabase(tmp_path / "traces.db")
    repository = EvaluationHistoryRepository(database)

    run_id = repository.save(create_report())

    assert repository.list_traces(run_id) == []