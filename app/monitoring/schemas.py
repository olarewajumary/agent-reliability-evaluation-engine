from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.tools.schemas import ToolStatus


class ExecutionTrace(BaseModel):
    """Record the lifecycle and outcome of a tool execution."""

    model_config = ConfigDict(extra="forbid")

    trace_id: UUID = Field(default_factory=uuid4)

    execution_id: UUID

    tool_name: str = Field(
        min_length=1,
        max_length=100,
    )

    status: ToolStatus

    started_at: datetime

    finished_at: datetime

    duration_ms: float = Field(
        ge=0,
        description="Total execution time in milliseconds.",
    )

    error: str | None = None

    @field_validator("tool_name")
    @classmethod
    def tool_name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Tool name must not be blank.")

        return normalized

    @field_validator("started_at", "finished_at")
    @classmethod
    def timestamps_must_be_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include timezone information.")

        return value