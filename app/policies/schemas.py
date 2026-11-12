from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PolicyDecision(str, Enum):
    """Possible decisions made by the policy engine."""

    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class ToolPolicy(BaseModel):
    """Define the policy assigned to a tool."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(
        min_length=1,
        max_length=100,
    )

    decision: PolicyDecision

    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    @field_validator("tool_name", "reason")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value must not be blank.")

        return normalized


class PolicyEvaluation(BaseModel):
    """Represent the policy decision for a requested tool."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str

    decision: PolicyDecision

    reason: str