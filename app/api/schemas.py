from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.schemas import AgentExecutionResult
from app.evaluation.schemas import EvaluationCase
from app.evaluation.scenarios import EvaluationScenario


class EvaluationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[EvaluationCase]
    results_by_case_id: dict[str, AgentExecutionResult]


class ScenarioEvaluationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarios: list[EvaluationScenario]


class RetrievalEvaluationRunRequest(BaseModel):
    """Request a retrieval evaluation using executable scenarios."""

    model_config = ConfigDict(extra="forbid")

    scenarios: list[EvaluationScenario] = Field(min_length=1)

    k: int = Field(default=10, ge=1, le=100)

    @field_validator("scenarios")
    @classmethod
    def scenarios_must_define_expected_evidence(
        cls,
        value: list[EvaluationScenario],
    ) -> list[EvaluationScenario]:
        case_ids = [
            scenario.case.case_id
            for scenario in value
        ]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Duplicate scenario case IDs.")

        for scenario in value:
            if not scenario.expected_evidence_ids:
                raise ValueError(
                    f"Scenario '{scenario.case.case_id}' must define "
                    "at least one expected evidence ID."
                )

        return value