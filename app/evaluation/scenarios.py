
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.evaluation.schemas import EvaluationCase
from app.tools.schemas import ToolRequest


class EvaluationScenario(BaseModel):
    """Define a task and its planned tool requests for evaluation."""

    model_config = ConfigDict(extra="forbid")

    case: EvaluationCase

    objective: str = Field(
        min_length=1,
        max_length=2000,
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
    )

    tool_requests: list[ToolRequest] = Field(
        default_factory=list,
    )

    @field_validator("objective")
    @classmethod
    def objective_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Objective must not be blank.")

        return normalized
