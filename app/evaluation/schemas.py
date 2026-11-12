from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvaluationCase(BaseModel):
    """Define the expected behaviour for an agent task."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(
        min_length=1,
        max_length=100,
    )

    expected_tool_sequence: list[str] = Field(
        default_factory=list,
        description="Expected tool names in execution order.",
    )

    expected_status: str = Field(
        min_length=1,
        description="Expected final status of the agent task.",
    )

    @field_validator("case_id", "expected_status")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Value must not be blank.")

        return normalized

    @field_validator("expected_tool_sequence")
    @classmethod
    def tool_names_must_not_be_blank(
        cls,
        value: list[str],
    ) -> list[str]:
        normalized = []

        for tool_name in value:
            name = tool_name.strip()

            if not name:
                raise ValueError("Tool names must not be blank.")

            normalized.append(name)

        return normalized


class EvaluationReport(BaseModel):
    """Represent the evaluation results for an agent task."""

    model_config = ConfigDict(extra="forbid")

    case_id: str

    tool_selection_correct: bool

    execution_sequence_correct: bool

    task_status_correct: bool

    policy_compliant: bool

    score: float = Field(
        ge=0,
        le=100,
        description="Overall evaluation score from 0 to 100.",
    )

    passed: bool

    issues: list[str] = Field(default_factory=list)


class BatchEvaluationReport(BaseModel):
    """Summarize the results of evaluating multiple agent tasks."""

    model_config = ConfigDict(extra="forbid")

    total_cases: int = Field(ge=0)

    passed_cases: int = Field(ge=0)

    failed_cases: int = Field(ge=0)

    pass_rate: float = Field(ge=0, le=100)

    average_score: float = Field(ge=0, le=100)

    failure_counts: dict[str, int] = Field(
        default_factory=dict,
    )

    reports: list[EvaluationReport] = Field(
        default_factory=list,
    )


class FailureCategory(BaseModel):
    """Summarize failures for one evaluation dimension."""

    model_config = ConfigDict(extra="forbid")

    category: str
    failed_cases: int = Field(ge=0)
    failure_rate: float = Field(ge=0, le=100)


class FailedCaseSummary(BaseModel):
    """Describe an individual evaluation case that failed."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    score: float = Field(ge=0, le=100)
    issues: list[str] = Field(default_factory=list)


class IssueFrequency(BaseModel):
    """Count how often a specific evaluation issue occurs."""

    model_config = ConfigDict(extra="forbid")

    issue: str
    occurrences: int = Field(ge=1)


class FailureAnalysisReport(BaseModel):
    """Provide an overall analysis of batch evaluation failures."""

    model_config = ConfigDict(extra="forbid")

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=100)
    failure_categories: list[FailureCategory] = Field(
        default_factory=list
    )
    failed_case_details: list[FailedCaseSummary] = Field(
        default_factory=list
    )
    recurring_issues: list[IssueFrequency] = Field(
        default_factory=list
    )