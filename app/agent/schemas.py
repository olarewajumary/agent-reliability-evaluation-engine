from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

class AgentTaskRequest(BaseModel):
    """Validate a task submitted to the agent."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(
        min_length=1,
        max_length=2000,
    )

    context: dict[str, Any] = Field(default_factory=dict)

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

class PlannedAction(BaseModel):
    """A single action proposed by the agent planner."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool_name")
    @classmethod
    def tool_name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Tool name must not be blank.")

        return normalized

class ExecutionPlan(BaseModel):
    """A structured plan proposed for an agent task."""

    model_config = ConfigDict(extra="forbid")

    rationale: str = Field(min_length=1, max_length=1000)
    actions: list[PlannedAction] = Field(min_length=1, max_length=10)

    @field_validator("rationale")
    @classmethod
    def rationale_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Plan rationale must not be blank.")

        return normalized

class AgentExecutionResult(BaseModel):
    """Represent the outcome of an agent task execution."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID

    status: str = Field(min_length=1)

    tool_results: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    plan: ExecutionPlan | None = None

    message: str = Field(min_length=1)

    @field_validator("status", "message")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value must not be blank.")

        return normalized