from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    REQUIRES_APPROVAL = "requires_approval"


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID = Field(default_factory=uuid4)
    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool_name")
    @classmethod
    def tool_name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Tool name must not be blank.")
        return normalized


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    tool_name: str = Field(min_length=1, max_length=100)
    status: ToolStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    policy_decision: str | None = None
    policy_reason: str | None = None

    @field_validator("tool_name")
    @classmethod
    def tool_name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Tool name must not be blank.")
        return normalized