
from pydantic import BaseModel, ConfigDict

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
