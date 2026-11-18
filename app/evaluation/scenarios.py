
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.evaluation.schemas import EvaluationCase
from app.tools.schemas import ToolRequest


class EvaluationScenario(BaseModel):
    """Define a task and its expected execution and retrieval behaviour."""

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

    expected_evidence_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Stable IDs of evidence expected from successful "
            "retrieval tool outputs."
        ),
    )

    @field_validator("objective")
    @classmethod
    def objective_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Objective must not be blank.")

        return normalized

    @field_validator("expected_evidence_ids")
    @classmethod
    def evidence_ids_must_be_valid(
        cls,
        value: list[str],
    ) -> list[str]:
        normalized = []

        for evidence_id in value:
            evidence_id = evidence_id.strip()

            if not evidence_id:
                raise ValueError("Evidence IDs must not be blank.")

            normalized.append(evidence_id)

        if len(normalized) != len(set(normalized)):
            raise ValueError("Expected evidence IDs must be unique.")

        return normalized