
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentTaskRequest(BaseModel):
    """Validate a task submitted to the agent."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(
        min_length=1,
        max_length=2000,
        description="What the agent is expected to accomplish.",
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional information available to the agent.",
    )

    @field_validator("objective")
    @classmethod
    def objective_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Objective must not be blank.")

        return normalized


class AgentTask(BaseModel):
    """Represent a validated task inside the application."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID = Field(default_factory=uuid4)

    objective: str = Field(
        min_length=1,
        max_length=2000,
    )

    context: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
