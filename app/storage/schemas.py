
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.schemas import EvaluationReport
from app.tools.schemas import ToolStatus

class StoredEvaluationRun(BaseModel):
    """Represent an evaluation run retrieved from persistent storage."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: datetime

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)

    pass_rate: float = Field(ge=0, le=100)
    average_score: float = Field(ge=0, le=100)

    failure_counts: dict[str, int] = Field(
        default_factory=dict
    )

    reports: list[EvaluationReport] = Field(
        default_factory=list
    )


class StoredExecutionTrace(BaseModel):
    """An execution trace retrieved from persistent storage."""

    model_config = ConfigDict(extra="forbid")

    trace_id: UUID
    run_id: str
    case_id: str
    execution_id: UUID
    tool_name: str
    status: ToolStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    arguments: dict[str, Any]
    output: dict[str, Any]
    policy_decision: str | None = None
    policy_reason: str | None = None
    error: str | None = None