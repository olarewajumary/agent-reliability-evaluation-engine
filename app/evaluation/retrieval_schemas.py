
from pydantic import BaseModel, ConfigDict, Field


class RetrievalCaseReport(BaseModel):
    """Retrieval quality for one evaluation scenario."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    k: int = Field(ge=1)

    expected_evidence_ids: list[str]
    retrieved_evidence_ids: list[str]
    relevant_retrieved_ids: list[str]

    precision_at_k: float = Field(ge=0, le=1)
    recall_at_k: float = Field(ge=0, le=1)
    reciprocal_rank: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)

    passed: bool
    issues: list[str] = Field(default_factory=list)


class RetrievalBatchReport(BaseModel):
    """Aggregate retrieval quality across evaluation scenarios."""

    model_config = ConfigDict(extra="forbid")

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)

    pass_rate: float = Field(ge=0, le=100)

    mean_precision_at_k: float = Field(ge=0, le=1)
    mean_recall_at_k: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    mean_evidence_coverage: float = Field(ge=0, le=1)

    reports: list[RetrievalCaseReport] = Field(
        default_factory=list,
    )
