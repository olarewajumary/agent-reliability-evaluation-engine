
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.schemas import EvaluationReport


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
