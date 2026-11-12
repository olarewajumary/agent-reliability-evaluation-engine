
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class SQLiteDatabase:
    """Manage SQLite connections and initialize database tables."""

    def __init__(
        self,
        database_path: str | Path = "data/evaluation_history.db",
    ) -> None:
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection and manage its transaction."""

        connection = sqlite3.connect(str(self.database_path))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the evaluation history tables if necessary."""

        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    total_cases INTEGER NOT NULL,
                    passed_cases INTEGER NOT NULL,
                    failed_cases INTEGER NOT NULL,
                    pass_rate REAL NOT NULL,
                    average_score REAL NOT NULL,
                    failure_counts_json TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_case_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    tool_selection_correct INTEGER NOT NULL,
                    execution_sequence_correct INTEGER NOT NULL,
                    task_status_correct INTEGER NOT NULL,
                    policy_compliant INTEGER NOT NULL,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    issues_json TEXT NOT NULL,

                    FOREIGN KEY (run_id)
                        REFERENCES evaluation_runs(run_id)
                        ON DELETE CASCADE,

                    UNIQUE (run_id, case_id)
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_evaluation_runs_created_at
                ON evaluation_runs(created_at)
                """
            )
