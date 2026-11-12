import json
from datetime import datetime, timezone
from uuid import uuid4

from app.evaluation.schemas import BatchEvaluationReport, EvaluationReport
from app.monitoring.schemas import ExecutionTrace
from app.storage.database import SQLiteDatabase
from app.storage.schemas import StoredEvaluationRun, StoredExecutionTrace


class EvaluationHistoryRepository:
    """Persist evaluation runs, case reports, and execution traces."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def save(
        self,
        report: BatchEvaluationReport,
        traces_by_case_id: dict[str, list[ExecutionTrace]] | None = None,
    ) -> str:
        """Save a report and its traces atomically."""

        run_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        traces_by_case_id = traces_by_case_id or {}

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO evaluation_runs (
                    run_id, created_at, total_cases, passed_cases,
                    failed_cases, pass_rate, average_score,
                    failure_counts_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    created_at,
                    report.total_cases,
                    report.passed_cases,
                    report.failed_cases,
                    report.pass_rate,
                    report.average_score,
                    json.dumps(report.failure_counts),
                ),
            )

            for case_report in report.reports:
                connection.execute(
                    """
                    INSERT INTO evaluation_case_results (
                        run_id, case_id, tool_selection_correct,
                        execution_sequence_correct, task_status_correct,
                        policy_compliant, score, passed, issues_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        case_report.case_id,
                        int(case_report.tool_selection_correct),
                        int(case_report.execution_sequence_correct),
                        int(case_report.task_status_correct),
                        int(case_report.policy_compliant),
                        case_report.score,
                        int(case_report.passed),
                        json.dumps(case_report.issues),
                    ),
                )

            for case_id, traces in traces_by_case_id.items():
                for trace in traces:
                    connection.execute(
                        """
                        INSERT INTO execution_traces (
                            trace_id, run_id, case_id, execution_id,
                            tool_name, status, started_at, finished_at,
                            duration_ms, arguments_json, output_json,
                            policy_decision, policy_reason, error
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(trace.trace_id),
                            run_id,
                            case_id,
                            str(trace.execution_id),
                            trace.tool_name,
                            trace.status.value,
                            trace.started_at.isoformat(),
                            trace.finished_at.isoformat(),
                            trace.duration_ms,
                            json.dumps(trace.arguments),
                            json.dumps(trace.output),
                            trace.policy_decision,
                            trace.policy_reason,
                            trace.error,
                        ),
                    )

        return run_id

    def get(self, run_id: str) -> StoredEvaluationRun | None:
        """Retrieve one evaluation run by its ID."""

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM evaluation_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

            if row is None:
                return None

            case_rows = connection.execute(
                """
                SELECT *
                FROM evaluation_case_results
                WHERE run_id = ?
                ORDER BY id ASC
                """,
                (run_id,),
            ).fetchall()

        reports = [
            EvaluationReport(
                case_id=case["case_id"],
                tool_selection_correct=bool(
                    case["tool_selection_correct"]
                ),
                execution_sequence_correct=bool(
                    case["execution_sequence_correct"]
                ),
                task_status_correct=bool(
                    case["task_status_correct"]
                ),
                policy_compliant=bool(case["policy_compliant"]),
                score=case["score"],
                passed=bool(case["passed"]),
                issues=json.loads(case["issues_json"]),
            )
            for case in case_rows
        ]

        return StoredEvaluationRun(
            run_id=row["run_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            total_cases=row["total_cases"],
            passed_cases=row["passed_cases"],
            failed_cases=row["failed_cases"],
            pass_rate=row["pass_rate"],
            average_score=row["average_score"],
            failure_counts=json.loads(row["failure_counts_json"]),
            reports=reports,
        )

    def list_runs(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[StoredEvaluationRun]:
        """List evaluation runs, newest first."""

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100.")

        if offset < 0:
            raise ValueError("Offset cannot be negative.")

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id
                FROM evaluation_runs
                ORDER BY created_at DESC, run_id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

        runs = []

        for row in rows:
            run = self.get(row["run_id"])
            if run is not None:
                runs.append(run)

        return runs

    def list_traces(
        self,
        run_id: str,
        case_id: str | None = None,
    ) -> list[StoredExecutionTrace]:
        """Retrieve traces for a run, optionally filtered by case."""

        query = """
            SELECT *
            FROM execution_traces
            WHERE run_id = ?
        """
        parameters: list[str] = [run_id]

        if case_id is not None:
            query += " AND case_id = ?"
            parameters.append(case_id)

        query += " ORDER BY started_at ASC, trace_id ASC"

        with self.database.connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            StoredExecutionTrace(
                trace_id=row["trace_id"],
                run_id=row["run_id"],
                case_id=row["case_id"],
                execution_id=row["execution_id"],
                tool_name=row["tool_name"],
                status=row["status"],
                started_at=datetime.fromisoformat(row["started_at"]),
                finished_at=datetime.fromisoformat(row["finished_at"]),
                duration_ms=row["duration_ms"],
                arguments=json.loads(row["arguments_json"]),
                output=json.loads(row["output_json"]),
                policy_decision=row["policy_decision"],
                policy_reason=row["policy_reason"],
                error=row["error"],
            )
            for row in rows
        ]