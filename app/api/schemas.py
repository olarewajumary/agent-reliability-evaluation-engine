from pydantic import BaseModel, ConfigDict

from app.agent.schemas import AgentExecutionResult
from app.evaluation.schemas import EvaluationCase


class EvaluationRunRequest(BaseModel):
    """Validate an API request to evaluate agent executions."""

    model_config = ConfigDict(extra="forbid")

    cases: list[EvaluationCase]
    results_by_case_id: dict[str, AgentExecutionResult]